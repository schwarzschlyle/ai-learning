from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.logger import logger
import boto3
import os
from pathlib import Path
import asyncio
import uuid
import openai
from pinecone import Pinecone
import io
from typing import List
import uvicorn
import PyPDF2
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str



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
# index.delete(delete_all=True)
# exit()



def log_message(message):
    """Log execution messages."""
    logger.info(message)
    print(message)


import io  # Import io for BytesIO operations

uploaded_files = {}  # Dictionary to store document IDs and their associated PDF filenames

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to S3 and process it."""
    log_message(f"Uploading file: {file.filename}")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())

    try:
        # Read file content into memory
        file_content = await file.read()

        # Upload the PDF file to S3
        pdf_key = f"{doc_id}/{file.filename}"  # Use doc_id as a folder-like prefix
        s3_client.upload_fileobj(io.BytesIO(file_content), BUCKET_NAME, pdf_key)
        log_message(f"Uploaded {file.filename} to S3 as {pdf_key}.")

        # Store the PDF file name associated with the document ID
        uploaded_files[doc_id] = pdf_key

        # Convert file content to text and upload the text file
        text_content = await convert_to_text(file.filename, file_content)
        text_key = f"{doc_id}/{doc_id}.txt"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=text_key, Body=text_content)
        log_message(f"Uploaded text version to S3 as {text_key}.")

        # Chunk the text and process with Pinecone
        chunks = chunk_text(text_content)
        log_message(f"Chunked text into {len(chunks)} chunks.")
        vectors = await vectorize_chunks(chunks, doc_id)
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
        # Delete original file and text from S3
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
    """Handle user query and return relevant response, while logging the conversation."""
    query = request.query
    session_id = str(uuid.uuid4())  # Generate a unique session ID
    log_key = f"chat_logs/{session_id}.txt"  # S3 key for storing logs

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
        log_message("Generated chatbot response.")

        # Log the interaction to S3
        log_content = f"Query: {query}\nResponse: {chatbot_response}\n\n"

        # Check if the log file exists
        existing_logs = None
        try:
            response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=log_key)
            if 'Contents' in response:
                # Log file exists, download it
                existing_logs = io.BytesIO()
                s3_client.download_fileobj(Bucket=BUCKET_NAME, Key=log_key, Fileobj=existing_logs)
                existing_logs.seek(0)
                log_content = existing_logs.read().decode("utf-8") + log_content
        except Exception as e:
            log_message(f"No existing log file. Creating a new one: {e}")

        # Upload updated log file
        s3_client.put_object(Bucket=BUCKET_NAME, Key=log_key, Body=log_content.encode("utf-8"))
        log_message(f"Logged conversation to {log_key}.")

        # Return the chatbot response and session ID
        return {"response": chatbot_response, "session_id": session_id}
    except Exception as e:
        log_message(f"Error in chat process: {e}")
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/download/{doc_id}")
async def download_pdf(doc_id: str):
    """Retrieve the original PDF file for the given document ID."""
    try:
        if doc_id not in uploaded_files: 
            raise HTTPException(status_code=404, detail="Document ID not found.")

        pdf_key = uploaded_files[doc_id]  # Get the PDF file key
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": BUCKET_NAME, "Key": pdf_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return {"download_url": download_url}
    except Exception as e:
        log_message(f"Error retrieving PDF file for doc_id {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def convert_to_text(filename, file_content):
    """Convert file content to text."""
    try:
        if filename.endswith(".pdf"):
            # Process PDF files
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""  # Handle None gracefully
            return text
        elif filename.endswith(".txt"):
            # Process plain text files
            return file_content.decode("utf-8")
        else:
            raise ValueError("Unsupported file type for conversion.")
    except Exception as e:
        log_message(f"Error converting file to text: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to convert file to text: {str(e)}")



def chunk_text(text):
    """Chunk text into manageable pieces."""
    return [text[i : i + 500] for i in range(0, len(text), 500)]


async def vectorize_chunks(chunks, doc_id):
    """Embed chunks using OpenAI and prepare them for Pinecone."""
    vectors = []
    for chunk in chunks:
        embedding = await embed_text(chunk)
        vectors.append({"id": str(uuid.uuid4()), "values": embedding, "metadata": {"doc_id": doc_id, "text": chunk}})
    return vectors


async def embed_text(text):
    """Generate embeddings using OpenAI."""
    response = openai.Embedding.create(input=text, model="text-embedding-3-large")
    return response["data"][0]["embedding"]


def generate_response(query, context):
    """Generate chatbot response tailored for hiring managers."""
    system_prompt = (
        "You are Lylebot - a friendly and professional AI assistant representing the online resume of Lyle. "
        "Your role is to engage in a conversational manner, answering hiring-related questions clearly, concisely, and enthusiastically. "
        "Use the provided resume context to respond directly to the hiring manager's questions. "
        "Be very specific with the response and cite sources from the context."
        "If the context does not contain the requested information, respond politely and suggest reaching out to Lyle directly for further details. "
        "Avoid making assumptions or using information outside the provided context. "
        "Always aim to create a positive impression of Lyle's skills, experience, and qualifications. "
        "Find a way to use the context information to address the query."
        "Here is the resume context:\n\n"
        f"{context}"
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}"},
        ],
        max_tokens=400,
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=5000)