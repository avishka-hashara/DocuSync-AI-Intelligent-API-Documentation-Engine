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
# Import our ingestion logic (we will modify ingest.py slightly in the next step)
import ingest 

load_dotenv()

app = FastAPI(title="DocuSync AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "codebase_docs"

class ChatRequest(BaseModel):
    question: str
    project_id: int

class ProjectCreate(BaseModel):
    name: str
    path: str # The local path the user wants to ingest

# --- API Routes ---

@app.post("/api/v1/projects")
def create_project(project: ProjectCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        # 1. Save project to Postgres
        new_project = models.Project(name=project.name, owner_id=1)
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        # 2. Start ingestion in the BACKGROUND so the UI doesn't freeze
        # We pass the new ID so the vectors are tagged correctly
        background_tasks.add_task(ingest.ingest_directory, project.path, new_project.id)
        
        return {"project": new_project, "message": "Ingestion started in background"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/projects")
def get_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).filter(models.Project.owner_id == 1).all()

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
            return {"answer": "I don't have enough context.", "sources": []}
        
        context = ""
        sources = []
        for hit in search_results:
            context += f"--- {hit.payload['name']} ---\n{hit.payload['code']}\n\n"
            sources.append({"name": hit.payload['name'], "file": hit.payload['filepath']})
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
        prompt = f"Context:\n{context}\n\nQuestion: {request.question}\nAnswer:"
        data = json.dumps({"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            return {"answer": res['choices'][0]['message']['content'], "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))