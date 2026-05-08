import os
import zipfile
import shutil
import uuid
import json
import httpx
import asyncio
import logging
import re
import git
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from ast_parser import extract_code_chunks
from ws_manager import manager
from database import SessionLocal
import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
COLLECTION_NAME = "codebase_docs"

# Extensions we support now
SUPPORTED_EXTENSIONS = {".py", ".php", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".go"}

async def get_embedding(text):
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", 
        "Content-Type": "application/json"
    }
    data = {
        "model": "nvidia/llama-nemotron-embed-vl-1b-v2:free", 
        "input": text
    }
    
    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.post(url, headers=headers, json=data, timeout=60.0)
        res = response.json()
        return res['data'][0]['embedding']

def generic_code_chunker(filepath):
    """
    A simple chunker for non-python files. 
    It tries to split by functions/classes or just chunks of lines.
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Very basic splitting: look for common keywords or just split by size
    # For now, let's split by about 1500 characters with some overlap
    chunk_size = 1500
    overlap = 200
    chunks = []
    
    for i in range(0, len(content), chunk_size - overlap):
        chunk_text = content[i:i + chunk_size]
        chunks.append({
            "name": os.path.basename(filepath),
            "type": "Code Chunk",
            "code": chunk_text,
            "filepath": os.path.basename(filepath)
        })
    return chunks

async def ingest_zip_archive(zip_path: str, extract_path: str, project_id: int):
    logger.info(f"Starting ingestion for project {project_id}")
    db = SessionLocal()
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    
    # Give the frontend a moment to connect its WebSocket
    await asyncio.sleep(2)
    
    # Ensure collection exists
    try:
        if not client.collection_exists(COLLECTION_NAME):
            logger.info(f"Creating collection {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=2048, distance=Distance.COSINE)
            )
    except Exception as e:
        logger.error(f"Qdrant error: {e}")
        await manager.broadcast({"status": "failed", "message": f"Vector DB Error: {str(e)}"}, project_id)
        return

    try:
        if project:
            project.status = "ingesting"
            db.commit()

        logger.info(f"Broadcasting extraction status for project {project_id}")
        await manager.broadcast({"status": "extracting", "message": "Extracting codebase..."}, project_id)
        
        # 1. Unzip the file
        logger.info(f"Unzipping {zip_path} to {extract_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        top_level = os.listdir(extract_path)
        logger.info(f"Extracted top-level contents: {top_level}")

        # 2. Walk the directory and parse code
        files_to_process = []
        for root, dirs, files in os.walk(extract_path):
            if any(x in root for x in ["venv", "__pycache__", ".git", "node_modules", "vendor", "public", "storage"]): 
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        logger.info(f"Total supported files found: {total_files}")
        
        if total_files == 0:
            await manager.broadcast({
                "status": "failed", 
                "message": "No supported code files found (.py, .php, .js, etc.)"
            }, project_id)
            return

        await manager.broadcast({
            "status": "processing", 
            "message": f"Found {total_files} files. Starting ingestion...",
            "total": total_files,
            "current": 0
        }, project_id)

        points_to_insert = []
        for i, filepath in enumerate(files_to_process):
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1].lower()
            
            await manager.broadcast({
                "status": "processing", 
                "message": f"Processing {filename}...",
                "total": total_files,
                "current": i + 1,
                "file": filename
            }, project_id)

            try:
                if ext == ".py":
                    chunks = extract_code_chunks(filepath)
                else:
                    chunks = generic_code_chunker(filepath)
                
                for chunk in chunks:
                    vector = await get_embedding(chunk['code'])
                    points_to_insert.append(PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "project_id": project_id,
                            "name": chunk['name'],
                            "type": chunk.get('type', 'Code'),
                            "code": chunk['code'],
                            "filepath": filename,
                            "language": ext[1:] # py, php, js, etc.
                        }
                    ))
            except Exception as e:
                logger.error(f"Error parsing {filename}: {e}")
                continue

        if points_to_insert:
            logger.info(f"Upserting {len(points_to_insert)} points to Qdrant")
            client.upsert(collection_name=COLLECTION_NAME, points=points_to_insert)

            if project:
                project.status = "completed"
                db.commit()

            await manager.broadcast({
                "status": "completed", 
                "message": "Ingestion complete! Codebase is ready.",
                "total": total_files,
                "current": total_files
            }, project_id)
            logger.info(f"Project {project_id} fully ingested.")
        else:
            if project:
                project.status = "failed"
                db.commit()
            await manager.broadcast({
                "status": "failed", 
                "message": "Could not extract any code chunks from the files."
            }, project_id)

    except Exception as e:
        logger.error(f"Ingestion error for project {project_id}: {e}")
        if project:
            project.status = "failed"
            db.commit()
        await manager.broadcast({
            "status": "failed", 
            "message": f"An error occurred: {str(e)}"
        }, project_id)

    finally:
        db.close()
        logger.info(f"Cleaning up paths for project {project_id}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)

async def clone_and_ingest(repo_url: str, clone_path: str, project_id: int, github_access_token: str = None):
    db = SessionLocal()
    try:
        # 1. Update status to cloning
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project:
            project.status = "cloning"
            db.commit()
        
        await manager.broadcast({"status": "cloning", "message": "Cloning repository..."}, project_id)

        # 2. Clone repository
        logger.info(f"Cloning repository {repo_url} to {clone_path}")
        
        if github_access_token:
            # Inject token into URL for authentication
            auth_url = repo_url.replace("https://", f"https://{github_access_token}@")
            git.Repo.clone_from(auth_url, clone_path)
        else:
            git.Repo.clone_from(repo_url, clone_path)

        # 3. Update status to ingesting
        if project:
            project.status = "ingesting"
            db.commit()
        
        await manager.broadcast({"status": "ingesting", "message": "Ingesting codebase..."}, project_id)

        # 4. Ensure Qdrant collection exists
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=2048, distance=Distance.COSINE)
            )

        # 5. Walk and process .py files
        files_to_process = []
        for root, dirs, files in os.walk(clone_path):
            if any(x in root for x in [".git", "venv", "node_modules", "__pycache__"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        points_to_insert = []

        for i, filepath in enumerate(files_to_process):
            filename = os.path.basename(filepath)
            await manager.broadcast({
                "status": "ingesting",
                "message": f"Processing {filename}...",
                "total": total_files,
                "current": i + 1
            }, project_id)

            try:
                chunks = extract_code_chunks(filepath)
                for chunk in chunks:
                    vector = await get_embedding(chunk['code'])
                    points_to_insert.append(PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "project_id": project_id,
                            "name": chunk['name'],
                            "type": chunk.get('type', 'Code'),
                            "code": chunk['code'],
                            "filepath": filename,
                            "language": "python"
                        }
                    ))
            except Exception as e:
                logger.error(f"Error parsing {filename}: {e}")
                continue

        # 6. Upsert to Qdrant
        if points_to_insert:
            client.upsert(collection_name=COLLECTION_NAME, points=points_to_insert)

            # 7. Final status update
            if project:
                project.status = "completed"
                db.commit()
            
            await manager.broadcast({"status": "completed", "message": "Sync complete!"}, project_id)
        else:
            if project:
                project.status = "failed"
                db.commit()
            await manager.broadcast({"status": "failed", "message": "No code chunks found to ingest."}, project_id)

    except Exception as e:
        logger.error(f"Clone/Ingest error: {e}")
        if project:
            project.status = "failed"
            db.commit()
        await manager.broadcast({"status": "failed", "message": str(e)}, project_id)
    finally:
        db.close()
        if os.path.exists(clone_path):
            shutil.rmtree(clone_path)