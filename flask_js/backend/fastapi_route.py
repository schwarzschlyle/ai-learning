from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import List
import uvicorn

DATABASE_URL = "sqlite:///./instance/mydatabase.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/contacts")
def get_contacts(db: Session = Depends(get_db)):
    contacts = db.query(Contact).all()
    return {"contacts": [contact.to_dict() for contact in contacts]}

@app.post("/create_contact")
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    if not contact.firstName or not contact.lastName or not contact.email:
        raise HTTPException(status_code=400, detail="Enter proper info")

    new_contact = Contact(
        firstName=contact.firstName,
        lastName=contact.lastName,
        email=contact.email,
    )

    try:
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "User created!"}

@app.patch("/update_contact/{user_id}")
def update_contact(user_id: int, contact: ContactCreate, db: Session = Depends(get_db)):
    existing_contact = db.query(Contact).filter(Contact.id == user_id).first()

    if not existing_contact:
        raise HTTPException(status_code=404, detail="User not found")

    existing_contact.firstName = contact.firstName or existing_contact.firstName
    existing_contact.lastName = contact.lastName or existing_contact.lastName
    existing_contact.email = contact.email or existing_contact.email

    db.commit()
    db.refresh(existing_contact)

    return {"message": "User updated"}

@app.delete("/delete_contact/{user_id}")
def delete_contact(user_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == user_id).first()

    if not contact:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(contact)
    db.commit()

    return {"message": "User deleted successfully"}

# Main entry point
if __name__ == "__main__":
    uvicorn.run("fastapi_route:app", host="0.0.0.0", port=5000)
