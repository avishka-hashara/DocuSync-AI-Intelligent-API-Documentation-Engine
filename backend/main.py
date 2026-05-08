from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os
import shutil
import uuid
import urllib.request
import json
from dotenv import load_dotenv

# Local imports
from database import get_db
import models
import ingest 
from ws_manager import manager

load_dotenv()

app = FastAPI(title="DocuSync AI API")

# Broad CORS for the Docker network
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

# Sandbox for processing ZIP files
UPLOAD_DIR = "/app/temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    question: str
    project_id: int

@app.websocket("/ws/progress/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    await manager.connect(websocket, project_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)

@app.get("/")
def read_root():
    return {"status": "DocuSync API is running"}

@app.get("/api/v1/projects")
def get_projects(db: Session = Depends(get_db)):
    try:
        projects = db.query(models.Project).filter(models.Project.owner_id == 1).all()
        return projects if projects else []
    except Exception:
        return []

@app.post("/api/v1/projects")
async def create_project(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    try:
        # Ensure Dummy User exists
        user = db.query(models.User).filter(models.User.id == 1).first()
        if not user:
            user = models.User(email="founder@docusync.ai")
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create Project in DB
        new_project = models.Project(name=name, owner_id=user.id, status="pending")
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        # Save ZIP temporarily
        project_uuid = str(uuid.uuid4())
        zip_path = os.path.join(UPLOAD_DIR, f"{project_uuid}.zip")
        extract_path = os.path.join(UPLOAD_DIR, project_uuid)

        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Trigger Ingestion in Background
        background_tasks.add_task(ingest.ingest_zip_archive, zip_path, extract_path, new_project.id)
        
        return {"project": new_project, "status": "Ingestion started"}
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/projects/sync")
async def sync_github_repo(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    repo_url: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Ensure Dummy User exists
        user = db.query(models.User).filter(models.User.id == 1).first()
        if not user:
            user = models.User(email="founder@docusync.ai")
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create Project in DB
        new_project = models.Project(name=name, owner_id=user.id, status="pending")
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        # Generate unique path for cloning
        project_uuid = str(uuid.uuid4())
        clone_path = os.path.join("/app/cloned_repos", project_uuid)

        # Trigger Ingestion in Background
        background_tasks.add_task(ingest.clone_and_ingest, repo_url, clone_path, new_project.id)
        
        return {"project": new_project, "status": "Sync started"}
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat_with_codebase(request: ChatRequest):
    try:
        question_vector = await ingest.get_embedding(request.question)
        
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
        
        prompt = f"Using this code context, answer the question: {request.question}\n\nCONTEXT:\n{context}"

        data = json.dumps({
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            return {"answer": res['choices'][0]['message']['content'], "sources": sources}
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))