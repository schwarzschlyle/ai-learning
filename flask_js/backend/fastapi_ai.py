from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import List
import os
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from transformers import pipeline
import uvicorn
import logging

# Set up logging to capture logs in the backend
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_ai")

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

# Pinecone and Model Initialization
api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    raise ValueError("Pinecone API key is not set. Please set the PINECONE_API_KEY environment variable.")

pc = Pinecone(api_key=api_key)
index = pc.Index("mini-index")



# index.delete(delete_all=True)
# exit()


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
email_generator = pipeline(
    "text-generation", 
    model="distilgpt2", 
    tokenizer="distilgpt2", 
    truncation=False, 
    pad_token_id=50256
)

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
        vectorize_and_upsert_to_pinecone()
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
        vectorize_and_upsert_to_pinecone()
        return {"message": "User created!", "contact": new_contact.to_dict()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/update_contact/{user_id}", response_model=dict)
def update_contact(user_id: int, contact: ContactCreate, db: Session = Depends(get_db)):
    """Update an existing contact."""
    try:
        existing_contact = db.query(Contact).filter(Contact.id == user_id).first()
        if not existing_contact:
            raise HTTPException(status_code=404, detail="User not found")

        existing_contact.firstName = contact.firstName or existing_contact.firstName
        existing_contact.lastName = contact.lastName or existing_contact.lastName
        existing_contact.email = contact.email or existing_contact.email

        db.commit()
        db.refresh(existing_contact)
        vectorize_and_upsert_to_pinecone()
        return {"message": "User updated", "contact": existing_contact.to_dict()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/delete_contact/{user_id}", response_model=dict)
def delete_contact(user_id: int, db: Session = Depends(get_db)):
    """Delete a contact."""
    try:
        contact = db.query(Contact).filter(Contact.id == user_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="User not found")

        db.delete(contact)
        db.commit()
        vectorize_and_upsert_to_pinecone()
        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate_email")
def generate_email(email_request: EmailRequest, db: Session = Depends(get_db)):
    """
    Generate an email for a contact using semantic search.
    """
    try:
        query = email_request.query
        purpose = email_request.purpose

        # Log the email generation request
        log_to_frontend(f"Generating email for: {query} about: {purpose}")

        # Perform semantic search
        query_vector = model.encode(query, convert_to_tensor=False)
        results = index.query(vector=query_vector.tolist(), top_k=2, include_metadata=False)

        if not results["matches"]:
            log_to_frontend("No matching contacts found.")
            raise HTTPException(status_code=404, detail="No matching contacts found")

        top_match = results["matches"][0]
        contact_id = int(top_match["id"])
        contact = db.query(Contact).filter(Contact.id == contact_id).first()

        if not contact:
            log_to_frontend(f"Contact with ID {contact_id} not found.")
            raise HTTPException(status_code=404, detail="Contact not found")

        # Generate email
        prompt = (f"Subject: {purpose} Email\n\n"
                  f"Dear {contact.firstName} {contact.lastName},\n\n"
                  f"I want to {purpose}. Please let me know how we can proceed.\n\n")
                 
        email_content = email_generator(prompt, max_length=150, num_return_sequences=1)[0]["generated_text"]

        log_to_frontend(f"Generated email for {contact.firstName} {contact.lastName}")
        return {
            "contact": contact.to_dict(),
            "emailContent": email_content
        }
    except Exception as e:
        log_to_frontend(f"Error generating email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")



def vectorize_and_upsert_to_pinecone():
    logger.info("Starting vectorization and upsert to Pinecone...")
    db = SessionLocal()
    contacts = db.query(Contact).all()

    if not contacts:
        logger.warning("Database is empty. Skipping upsert to Pinecone.")
        log_to_frontend("Database is empty. Skipping upsert to Pinecone.")
        return

    try:
        # Fetch all existing vector IDs from Pinecone
        logger.info("Fetching existing vector IDs from Pinecone...")
        existing_ids = set()
        response = index.describe_index_stats()
        vector_count = response.get("total_vector_count", 0)

        if vector_count > 0:
            logger.info(f"Index contains {vector_count} vectors.")
            # If there are existing vectors, fetch them in batches
            for i in range(0, vector_count, 100):  # Fetch 100 IDs at a time
                fetch_response = index.fetch(ids=[str(x) for x in range(i, i + 100)])
                if "vectors" in fetch_response:
                    existing_ids.update(fetch_response["vectors"].keys())

        # Log fetched IDs
        logger.info(f"Fetched {len(existing_ids)} existing IDs from Pinecone.")

        # Collect new vectors for upsertion
        vectors_to_upsert = []
        for contact in contacts:
            contact_id = str(contact.id)
            if contact_id not in existing_ids:
                contact_text = f"{contact.firstName} {contact.lastName} {contact.email}"
                vector = model.encode(contact_text, convert_to_tensor=False)
                vectors_to_upsert.append((contact_id, vector.tolist()))

        # Upsert only new vectors
        if vectors_to_upsert:
            index.upsert(vectors=vectors_to_upsert)
            logger.info(f"{len(vectors_to_upsert)} new vectors upserted to Pinecone.")
            log_to_frontend(f"{len(vectors_to_upsert)} new vectors upserted to Pinecone.")
        else:
            logger.info("No new vectors to upsert. Pinecone is already up-to-date.")
            log_to_frontend("No new vectors to upsert. Pinecone is already up-to-date.")

    except Exception as e:
        logger.error(f"Error during vectorization/upsert: {str(e)}")
        log_to_frontend(f"Error during vectorization/upsert: {str(e)}")
    finally:
        db.close()








# Check if the database has been vectorized and upserted on first run
def check_and_upsert_on_first_run():
    try:
        logger.info("Checking if the database has been vectorized and upserted to Pinecone...")
        if index.describe_index_stats()["vectors"]["count"] == 0:
            logger.info("No vectors found in Pinecone. Starting vectorization and upsert...")
            vectorize_and_upsert_to_pinecone()
        else:
            logger.info("Pinecone index already populated with vectors.")
    except Exception as e:
        logger.error(f"Error during Pinecone check/upsert: {str(e)}")



def upsert_vectors_on_run():
    try:
        logger.info("Starting vectorization and upsert to Pinecone...")
        vectorize_and_upsert_to_pinecone()
    except Exception as e:
        logger.error(f"Error during Pinecone upsert: {str(e)}")




# Expose logs to frontend
@app.get("/logs")
def get_logs():
    """ Fetch the latest logs """
    return {"logs": logs[-7:]}  # Return the last 10 logs for example


# Main Entry
if __name__ == "__main__":
    log_to_frontend("Starting application and vectorization process...")
    upsert_vectors_on_run()  # Always run the vectorization and upsert process

    # Run the FastAPI app
    uvicorn.run("fastapi_ai:app", host="0.0.0.0", port=5000)