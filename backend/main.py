from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import urllib.request
import json
import os
from dotenv import load_dotenv

from database import get_db
import models
import ingest 

load_dotenv()

app = FastAPI(title="DocuSync AI API")

# --- BROAD CORS FOR DOCKER ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = "codebase_docs"

class ChatRequest(BaseModel):
    question: str
    project_id: int

class ProjectCreate(BaseModel):
    name: str
    path: str 

@app.get("/")
def read_root():
    return {"status": "DocuSync API is running"}

@app.post("/api/v1/projects")
def create_project(project: ProjectCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        new_project = models.Project(name=project.name, owner_id=1)
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        background_tasks.add_task(ingest.ingest_directory, project.path, new_project.id)
        return {"project": new_project, "message": "Ingestion started"}
    except Exception as e:
        db.rollback()
        print(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/projects")
def get_projects(db: Session = Depends(get_db)):
    try:
        projects = db.query(models.Project).filter(models.Project.owner_id == 1).all()
        # Ensure we return an empty list instead of None if no projects found
        return projects if projects else []
    except Exception as e:
        print(f"Database Fetch Error: {e}")
        # Returning an empty list on error prevents the frontend .map() crash
        return []

@app.post("/api/v1/chat")
def chat_with_codebase(request: ChatRequest):
    try:
        question_vector = ingest.get_embedding(request.question)
        
        search_response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=question_vector,
            query_filter=Filter(
                must=[FieldCondition(key="project_id", match=MatchValue(value=request.project_id))]
            ),
            limit=3
        )
        
        search_results = getattr(search_response, "points", search_response)
        
        if not search_results:
            return {"answer": "I don't have enough context in the database.", "sources": []}
        
        context = ""
        sources = []
        for hit in search_results:
            payload = hit.payload
            context += f"--- {payload.get('name', 'Code')} ---\n{payload.get('code', '')}\n\n"
            sources.append({"name": payload.get('name'), "file": payload.get('filepath')})
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        prompt = f"Use the context below to answer: {request.question}\n\nCONTEXT:\n{context}"

        data = json.dumps({
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            return {
                "answer": res['choices'][0]['message']['content'],
                "sources": sources
            }
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))