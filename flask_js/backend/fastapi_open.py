from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import List
import os
import uvicorn
import logging
import openai
from pinecone import Pinecone

# Set up logging to capture logs in the backend
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_open")

# Logs storage (to be sent to frontend)
logs = []

def log_to_frontend(message: str):
    """ Log messages that need to be sent to the frontend """
    logs.append(message)
    logger.info(message)
    print(f"LOGGED MESSAGE: {message}")

# Database setup
DATABASE_URL = "sqlite:///./instance/mydatabase.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pinecone and OpenAI Initialization
api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    raise ValueError("Pinecone API key is not set. Please set the PINECONE_API_KEY environment variable.")

pc = Pinecone(api_key=api_key)
index = pc.Index("ada-index")

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")

# Models
class EmailRequest(BaseModel):
    query: str
    purpose: str

class Contact(Base):
    __tablename__ = "contact"

    id = Column(Integer, primary_key=True, index=True)
    firstName = Column(String(80), nullable=False)
    lastName = Column(String(80), nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "email": self.email,
        }

class ContactCreate(BaseModel):
    firstName: str
    lastName: str
    email: str

Base.metadata.create_all(bind=engine)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints
@app.get("/contacts", response_model=dict)
def get_contacts(db: Session = Depends(get_db)):
    """Retrieve all contacts."""
    try:
        contacts = db.query(Contact).all()
        return {"contacts": [contact.to_dict() for contact in contacts]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create_contact", response_model=dict)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    try:
        new_contact = Contact(
            firstName=contact.firstName,
            lastName=contact.lastName,
            email=contact.email,
        )
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        vectorize_and_upsert_contact(new_contact)
        return {"message": "User created!", "contact": new_contact.to_dict()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/generate_email")
def generate_email(email_request: EmailRequest, db: Session = Depends(get_db)):
    """Generate a professional email for a contact using OpenAI's ChatCompletion."""
    try:
        query = email_request.query
        purpose = email_request.purpose
        log_to_frontend(f"Generating email for: {query} about: {purpose}")

        # Perform semantic search
        query_vector = openai.Embedding.create(
            input=query,
            model="text-embedding-ada-002"
        )['data'][0]['embedding']

        results = index.query(vector=query_vector, top_k=2, include_metadata=False)

        if not results["matches"]:
            log_to_frontend("No matching contacts found.")
            raise HTTPException(status_code=404, detail="No matching contacts found")

        top_match = results["matches"][0]
        contact_id = int(top_match["id"])
        contact = db.query(Contact).filter(Contact.id == contact_id).first()

        if not contact:
            log_to_frontend(f"Contact with ID {contact_id} not found.")
            raise HTTPException(status_code=404, detail="Contact not found")

        # Generate email using OpenAI's ChatCompletion
        prompt = (
            f"Compose a professional email to {contact.firstName} {contact.lastName} "
            f"({contact.email}) regarding {purpose}. Start with 'Dear {contact.firstName} {contact.lastName},' "
            f"and end with a formal closing."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7,
        )

        email_content = response['choices'][0]['message']['content'].strip()
        log_to_frontend(f"Generated email for {contact.firstName} {contact.lastName}")
        return {
            "contact": contact.to_dict(),
            "emailContent": email_content
        }
    except Exception as e:
        log_to_frontend(f"Error generating email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")

def vectorize_and_upsert_contact(contact):
    """Vectorize and upsert a single contact."""
    try:
        contact_text = f"{contact.firstName} {contact.lastName} {contact.email}"
        response = openai.Embedding.create(
            input=contact_text,
            model="text-embedding-ada-002"
        )
        vector = response['data'][0]['embedding']
        index.upsert(vectors=[(str(contact.id), vector)])
        log_to_frontend(f"Upserted vector for contact ID {contact.id}")
    except Exception as e:
        logger.error(f"Error vectorizing contact ID {contact.id}: {str(e)}")
        log_to_frontend(f"Error vectorizing contact ID {contact.id}: {str(e)}")

@app.get("/logs")
def get_logs():
    """Fetch the latest logs."""
    return {"logs": logs[-7:]}





@app.patch("/update_contact/{contact_id}", response_model=dict)
def update_contact(contact_id: int, updated_contact: ContactCreate, db: Session = Depends(get_db)):
    """Update a contact's information and update the vector in Pinecone."""
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Update contact fields
        contact.firstName = updated_contact.firstName
        contact.lastName = updated_contact.lastName
        contact.email = updated_contact.email
        db.commit()
        db.refresh(contact)

        # Update the vector in Pinecone
        vectorize_and_upsert_contact(contact)
        return {"message": "Contact updated successfully", "contact": contact.to_dict()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating contact: {str(e)}")


@app.delete("/delete_contact/{contact_id}", response_model=dict)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a contact and its vector from Pinecone."""
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Remove the contact from Pinecone
        try:
            index.delete(ids=[str(contact_id)])
            log_to_frontend(f"Deleted vector for contact ID {contact_id} from Pinecone")
        except Exception as e:
            log_to_frontend(f"Error deleting vector for contact ID {contact_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting vector: {str(e)}")

        # Delete the contact from the database
        db.delete(contact)
        db.commit()
        return {"message": "Contact deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting contact: {str(e)}")




if __name__ == "__main__":
    log_to_frontend("Starting application...")
    uvicorn.run("fastapi_open:app", host="0.0.0.0", port=5000)
