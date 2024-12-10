from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.logger import logger
import boto3
import os
import uuid
import openai
from pinecone import Pinecone
import io
from typing import List
import uvicorn
import PyPDF2
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
#openai 0.28.0

class ChatRequest(BaseModel):
    query: str



DB_FILE = "file_mappings.db"

def init_db():
    """Initialize SQLite database and create mappings table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_mappings (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            s3_key TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()


# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace '*' with specific domains for production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = "lylebot-bucket"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "lylebot-index"
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)


# Delete all vectors in the index
# index.delete(delete_all=True)
# print("All vectors have been deleted from the index.")
# exit()





def save_mapping(doc_id, filename, s3_key):
    """Save a new mapping in the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO file_mappings (doc_id, filename, s3_key)
        VALUES (?, ?, ?)
    """, (doc_id, filename, s3_key))
    conn.commit()
    conn.close()

def get_mapping(doc_id):
    """Retrieve a mapping for the given doc_id."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT filename, s3_key FROM file_mappings WHERE doc_id = ?
    """, (doc_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"filename": result[0], "s3_key": result[1]}
    return None




def log_message(message):
    """Log execution messages."""
    logger.info(message)
    print(message)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to S3 and process it."""
    log_message(f"Uploading file: {file.filename}")

    doc_id = str(uuid.uuid4())  # Generate unique document ID
    filename = file.filename

    try:
        # Read file content into memory
        file_content = await file.read()

        # Upload the PDF file to S3
        pdf_key = f"{doc_id}/{filename}"
        s3_client.upload_fileobj(io.BytesIO(file_content), BUCKET_NAME, pdf_key)
        log_message(f"Uploaded {filename} to S3 as {pdf_key}.")

        # Save the mapping in SQLite
        save_mapping(doc_id, filename, pdf_key)

        # Convert file content to text and upload the text file
        text_content = await convert_to_text(filename, file_content)
        text_key = f"{doc_id}/{doc_id}.txt"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=text_key, Body=text_content)
        log_message(f"Uploaded text version to S3 as {text_key}.")

        # Chunk the text and process with Pinecone
        chunks = chunk_text(text_content)
        log_message(f"Chunked text into {len(chunks)} chunks.")
        vectors = await vectorize_chunks(chunks, doc_id, filename)
        index.upsert(vectors)
        log_message(f"Uploaded vectors to Pinecone for document {doc_id}.")

        return {"message": "File uploaded and processed successfully.", "doc_id": doc_id}
    except Exception as e:
        log_message(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete/{doc_id}")
async def delete_file(doc_id: str):
    """Delete a document and its associated data."""
    try:
        original_key = f"{doc_id}.original"
        text_key = f"{doc_id}.txt"
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=original_key)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=text_key)
        log_message(f"Deleted files {original_key} and {text_key} from S3.")

        # Delete vectors from Pinecone
        index.delete(filter={"doc_id": doc_id})
        log_message(f"Deleted vectors for document {doc_id} from Pinecone.")

        return {"message": f"Document {doc_id} deleted successfully."}
    except Exception as e:
        log_message(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/")
async def chat_with_bot(request: ChatRequest):
    """Handle user query and return relevant response."""
    query = request.query
    session_id = str(uuid.uuid4())
    log_key = f"chat_logs/{session_id}.txt"

    try:
        log_message(f"Received query: {query}")

        # Vectorize query
        query_vector = await embed_text(query)

        # Find top chunks in Pinecone
        top_chunks = index.query(vector=query_vector, top_k=5, include_metadata=True)

        log_message(f"Top chunks found: {len(top_chunks['matches'])}")

        # Retrieve original documents and generate response
        context = "\n".join([match["metadata"]["text"] for match in top_chunks["matches"]])
        chatbot_response = generate_response(query, context)

        # Extract unique document IDs and filenames
        sources = []
        for match in top_chunks["matches"]:
            doc_id = match["metadata"].get("doc_id")
            mapping = get_mapping(doc_id)
            if mapping and {"doc_id": doc_id, "name": mapping["filename"]} not in sources:
                sources.append({"doc_id": doc_id, "name": mapping["filename"]})

        # Log the interaction
        log_content = f"Query: {query}\nResponse: {chatbot_response}\n\n"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=log_key, Body=log_content.encode("utf-8"))
        log_message(f"Logged conversation to {log_key}.")

        return {"response": chatbot_response, "session_id": session_id, "sources": sources}
    except Exception as e:
        log_message(f"Error in chat process: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/download/{doc_id}")
async def download_pdf(doc_id: str):
    """Retrieve the original PDF file for the given document ID."""
    try:
        mapping = get_mapping(doc_id)  # Retrieve mapping from SQLite
        if not mapping:
            raise HTTPException(status_code=404, detail="Document ID not found.")

        pdf_key = mapping["s3_key"]

        # Generate a pre-signed URL with Content-Disposition set to inline
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": pdf_key,
                "ResponseContentDisposition": "inline",  # Ensure the file is displayed in the browser
                "ResponseContentType": "application/pdf"  # Explicitly set the content type as PDF
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return {"download_url": download_url}
    except Exception as e:
        log_message(f"Error retrieving PDF file for doc_id {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



async def convert_to_text(filename, file_content):
    """Convert file content to text and enrich it using an LLM."""
    try:
        if filename.endswith(".pdf"):
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            raw_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
        elif filename.endswith(".txt"):
            # Handle plain text files
            raw_text = file_content.decode("utf-8")
        else:
            raise ValueError("Unsupported file type for conversion.")
        
        # Enrich text using OpenAI GPT model
        log_message("Enriching text using OpenAI GPT model.")
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an advanced AI designed to process and enhance documents. "
                        "Your task is to improve readability, correct typos, fix grammar issues, and refine the content "
                        "without changing the core meaning. Return the enhanced text in plain form."
                        "Try to use markdown to arrange the texts neatly"
                        "If there are mathematical equations, use latex syntax."
                    )
                },
                {"role": "user", "content": raw_text},
            ],
            max_tokens=4000,  # Adjust based on typical document length
            temperature=0.3,
        )
        enriched_text = response["choices"][0]["message"]["content"]
        log_message("Text enrichment completed.")
        return enriched_text
    except Exception as e:
        log_message(f"Error converting and enriching text: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to convert and enrich text: {str(e)}")


def chunk_text(text):
    """Chunk text into manageable pieces."""
    return [text[i:i + 500] for i in range(0, len(text), 500)]

async def vectorize_chunks(chunks, doc_id, filename):
    """Embed chunks using OpenAI and prepare them for Pinecone."""
    vectors = []
    for chunk in chunks:
        embedding = await embed_text(chunk)
        vectors.append({
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {"doc_id": doc_id, "text": chunk, "filename": filename}  # Dynamically use actual file name
        })
    return vectors



async def embed_text(text):
    """Generate embeddings using OpenAI."""
    response = openai.Embedding.create(input=text, model="text-embedding-3-large")
    return response["data"][0]["embedding"]

def generate_response(query, context):
    """Generate chatbot response tailored for a professional hiring manager context."""
    
    # Define the system prompt with advanced structure
    system_prompt = (
        "You are Lylebot, a cutting-edge AI assistant designed to support hiring managers in assessing "
        "Lyle's qualifications, projects, and overall fit for professional opportunities. "
        "Avoid using Lyle's full name unless explicitly asked."
        "You excel in professional communication, adapting to hiring managers' needs with clarity and precision.\n\n"
        "### Behavioral Guidelines:\n"
        "- **Professional Relevance**: Respond strictly based on the provided context; avoid speculation.\n"
        "- **Concise and Structured Responses**: Use headings, bullet points, or numbered lists for readability.\n"
        "- **Clarify and Redirect**: When queries are unclear, ask for clarification while providing guidance.\n"
        "- **Boundary Management**: Politely decline to answer unrelated queries, suggesting contacting Lyle instead.\n"
        "- **Hiring Manager Persona Adaptation**: Adjust tone to match senior-level professionalism and industry standards.\n"
        "- **Meta-Cognitive Follow-Up**: Suggest follow-up questions or areas for further discussion if appropriate.\n\n"
        "### Response Strategy:\n"
        "- **Direct Match**: Extract and present relevant information concisely.\n"
        "- **Partial Match**: Explain missing links, offer context, or ask follow-up questions.\n"
        "- **No Match**: Politely explain that the query falls outside your scope and suggest alternatives.\n\n"
        "### Example Scenarios:\n"
        "1. **Direct Query**: 'What is Lyle's experience in React development?'\n"
        "   - Response: 'Lyle has experience in React development, including building dynamic front-end applications, such as [Project Name].'"
        "2. **Partial Query**: 'Tell me about Lyle's work.'\n"
        "   - Response: 'Could you clarify which aspect of Lyle's work interests you? For instance, his technical skills, past projects, or certifications?'\n"
        "3. **Unrelated Query**: 'What is the weather today?'\n"
        "   - Response: 'I'm focused on professional context. For general queries, please contact Lyle.'\n\n"
        "### Professional Context:\n"
        "If you need mathematical symbols to write your response, use latex syntax."
        f"{context}\n\n"
        "Now, generate a response to the query below, adhering to these principles."
    )
    
    # Generate the response using OpenAI's API
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}"},
        ],
        max_tokens=800,  # Allows more elaborate but concise responses
        temperature=0.3,  # Enhances precision over creativity
        top_p=0.85,  # Balances diversity while maintaining relevance
        frequency_penalty=0.2,  # Reduces redundancy
        presence_penalty=0.3,  # Encourages nuanced exploration of context
    )
    print(response["choices"][0]["message"]["content"])
    return response["choices"][0]["message"]["content"]





class EmailRequest(BaseModel):
    companyName: str
    jobDescription: str

@app.post("/generate_email/")
async def generate_email(request: EmailRequest):
    try:
        # Generate email content using OpenAI
        prompt = f"""
        Generate a professional email for a job application to Lyle. The email should include the company name, job description, and a polite expression of interest in the position.
        
        Company: {request.companyName}
        Job Description: {request.jobDescription}

        The email should be addressed to Lyle, expressing interest in the role and requesting a discussion.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o",  # You can replace this with your chosen model
            messages=[
                {"role": "system", "content": "You are an assistant who helps users generate professional emails."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,  # You can adjust the number of tokens based on the expected length of the email
            temperature=0.7  # Adjust temperature to control creativity (0.7 is a good balance)
        )

        email_content = response["choices"][0]["message"]["content"]
        
        # Return the generated email content
        return {"emailContent": email_content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")


@app.post("/send_email/")
async def send_email(request: EmailRequest):
    try:
        # Generate email content using OpenAI (same logic as above)
        prompt = f"""
        Generate a professional email for a job application to Lyle. The email should include the company name, job description, and a polite expression of interest in the position.
        
        Company: {request.companyName}
        Job Description: {request.jobDescription}

        The email should be addressed to Lyle, expressing interest in the role and requesting a discussion.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Replace with the desired model
            messages=[
                {"role": "system", "content": "You are an assistant who helps users generate professional emails."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )

        email_content = response["choices"][0]["message"]["content"]

        # Send the email via SMTP or any email service provider
        # For simplicity, let's assume the email is sent successfully
        # Use your email sending logic here (e.g., SMTP, SendGrid, etc.)

        # Here, we're simulating a successful email send
        return {"status": "success", "message": "Email sent successfully."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")



@app.get("/list_uploaded_files/")
async def list_uploaded_files():
    """Retrieve all uploaded PDF files from the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT doc_id, filename, s3_key FROM file_mappings")
        files = [{"doc_id": row[0], "filename": row[1], "s3_key": row[2]} for row in cursor.fetchall()]
        conn.close()
        return {"files": files}
    except Exception as e:
        log_message(f"Error retrieving files: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve uploaded files.")



if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=5000)
