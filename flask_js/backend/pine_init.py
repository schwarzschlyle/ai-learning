import sqlite3
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from transformers import pipeline
import os

# Initialize Pinecone and SentenceTransformer
api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    raise ValueError("Pinecone API key is not set. Please set the PINECONE_API_KEY environment variable.")

pc = Pinecone(api_key=api_key)
print("API connected")
index = pc.Index("mini-index")

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
email_generator = pipeline(
    "text-generation", 
    model="distilgpt2", 
    tokenizer="distilgpt2", 
    truncation=False, 
    pad_token_id=50256
)

db_path = "instance/mydatabase.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def get_contact_by_id(contact_id):
    """Fetch contact details by ID from the database."""
    cursor.execute("SELECT id, firstName, lastName, email FROM contact WHERE id=?", (contact_id,))
    return cursor.fetchone()

def semantic_search(query, top_k=1):
    """Perform semantic search using Pinecone."""
    query_vector = model.encode(query, convert_to_tensor=False)
    results = index.query(vector=query_vector.tolist(), top_k=top_k, include_metadata=False)
    return results

def generate_email(contact, purpose):
    """Generate a personalized email draft for a contact."""
    first_name, last_name, email = contact[1], contact[2], contact[3]
    prompt = (f"Subject: {purpose} Email\n\n"
              f"Dear {first_name} {last_name},\n\n"
              f"I want to {purpose}")
            

    email_content = email_generator(prompt, max_length=150, num_return_sequences=1)[0]["generated_text"]

    email_content = email_content.split("\n")[:8]  
    return "\n".join(email_content)

def main():
    print("Welcome to the Smart Contact Recommendation and Messaging System!")
    while True:
        query = input("\nEnter your search query (or type 'exit' to quit): ")
        if query.lower() == "exit":
            print("Goodbye!")
            break

        print("\nSearching for matching contacts...")
        results = semantic_search(query)
        
        if not results["matches"]:
            print("No matching contacts found.")
            continue

        print("\nMatching contacts:")
        contacts = []
        for match in results["matches"]:
            contact_id = match["id"]
            contact = get_contact_by_id(contact_id)
            if contact:
                contacts.append(contact)
                print(f"- {contact[1]} {contact[2]} ({contact[3]}) [Score: {match['score']:.2f}]")
        
        purpose = input("\nEnter the purpose of the email (e.g., event invitation, follow-up): ")
        print("\nGenerating email drafts...\n")
        
        drafts = []
        for contact in contacts:
            email_content = generate_email(contact, purpose)
            print(f"--- Email for {contact[1]} {contact[2]} ({contact[3]}) ---")
            print(email_content)
            print("\n")
            drafts.append((contact, email_content))
        
        save_option = input("Would you like to save these drafts to a file? (yes/no): ")
        if save_option.lower() == "yes":
            with open("email_drafts.txt", "w") as f:
                for contact, email_content in drafts:
                    f.write(f"--- Email for {contact[1]} {contact[2]} ({contact[3]}) ---\n")
                    f.write(email_content + "\n\n")
            print("Email drafts saved to 'email_drafts.txt'.")

if __name__ == "__main__":
    main()
