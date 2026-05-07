import os
import zipfile
import shutil
import uuid
import json
import httpx
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from ast_parser import extract_code_chunks
from ws_manager import manager

client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
COLLECTION_NAME = "codebase_docs"

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

async def ingest_zip_archive(zip_path: str, extract_path: str, project_id: int):
    # Ensure collection exists
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=2048, distance=Distance.COSINE)
        )

    try:
        await manager.broadcast({"status": "extracting", "message": "Extracting codebase..."}, project_id)
        
        # 1. Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        # 2. Walk the directory and parse code
        files_to_process = []
        for root, dirs, files in os.walk(extract_path):
            if any(x in root for x in ["venv", "__pycache__", ".git", "node_modules"]): 
                continue
            for file in files:
                if file.endswith(".py"):
                    files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        await manager.broadcast({
            "status": "processing", 
            "message": f"Found {total_files} Python files. Starting ingestion...",
            "total": total_files,
            "current": 0
        }, project_id)

        points_to_insert = []
        for i, filepath in enumerate(files_to_process):
            filename = os.path.basename(filepath)
            await manager.broadcast({
                "status": "processing", 
                "message": f"Processing {filename}...",
                "total": total_files,
                "current": i + 1,
                "file": filename
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
                            "type": chunk['type'],
                            "code": chunk['code'],
                            "filepath": filename
                        }
                    ))
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                continue

        if points_to_insert:
            client.upsert(collection_name=COLLECTION_NAME, points=points_to_insert)
            await manager.broadcast({
                "status": "completed", 
                "message": "Ingestion complete! Codebase is ready.",
                "total": total_files,
                "current": total_files
            }, project_id)
            print(f"Project {project_id} fully ingested.")
        else:
            await manager.broadcast({
                "status": "failed", 
                "message": "No valid Python code found in the ZIP archive."
            }, project_id)

    except Exception as e:
        print(f"Ingestion error: {e}")
        await manager.broadcast({
            "status": "failed", 
            "message": f"An error occurred: {str(e)}"
        }, project_id)

    finally:
        # 3. Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)