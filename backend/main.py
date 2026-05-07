from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="DocuSync AI API")

# --- NEW: CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Allow Next.js frontend
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)
# -------------------------------

# Connect to our local Qdrant container
client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "codebase_docs"

class ChatRequest(BaseModel):
    question: str

def get_embedding(text):
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "model": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
        "input": text
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        return res['data'][0]['embedding']

def ask_llm(context, question):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""You are DocuSync AI, an expert API documentation assistant. 
    Use the following exact codebase context to answer the developer's question.
    If the answer is not in the context, say "I cannot find this in the current documentation."
    
    CONTEXT:
    {context}
    
    QUESTION:
    {question}
    
    ANSWER:"""

    data = json.dumps({
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        return res['choices'][0]['message']['content']

@app.get("/")
def read_root():
    return {"status": "DocuSync API is running"}

@app.post("/api/v1/chat")
def chat_with_codebase(request: ChatRequest):
    try:
        question_vector = get_embedding(request.question)
        
        search_response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=question_vector,
            limit=3
        )
        
        search_results = getattr(search_response, "points", search_response)
        
        if not search_results:
            return {"answer": "I don't have enough context in the database to answer that.", "sources": []}
        
        context = ""
        sources = []
        for hit in search_results:
            payload = hit.payload
            context += f"--- {payload['type']} {payload['name']} (from {payload['filepath']}) ---\n"
            context += f"{payload['code']}\n\n"
            sources.append({"name": payload['name'], "file": payload['filepath']})
            
        answer = ask_llm(context, request.question)
        
        return {
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))