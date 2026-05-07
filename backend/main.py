from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
import urllib.request
import json
import os
from dotenv import load_dotenv

# Import our new database configurations
from database import get_db
import models

load_dotenv()

app = FastAPI(title="DocuSync AI API")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "codebase_docs"

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    question: str

class ProjectCreate(BaseModel):
    name: str

# --- AI Helper Functions ---
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

# --- API Routes ---
@app.get("/")
def read_root():
    return {"status": "DocuSync API is running"}

# NEW: Create a Project
@app.post("/api/v1/projects")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    try:
        # For our MVP, we will hardcode the owner_id to 1 (our dummy user)
        # In a production app, this ID would come from a decoded JWT login token
        new_project = models.Project(name=project.name, owner_id=1)
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        return new_project
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Get all Projects for the current user
@app.get("/api/v1/projects")
def get_projects(db: Session = Depends(get_db)):
    try:
        # Fetch all projects belonging to user 1
        projects = db.query(models.Project).filter(models.Project.owner_id == 1).all()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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