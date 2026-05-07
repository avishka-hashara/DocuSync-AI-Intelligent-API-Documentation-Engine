import os
import zipfile
import shutil
import uuid
import json
import urllib.request
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from ast_parser import extract_code_chunks

client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
COLLECTION_NAME = "codebase_docs"

def get_embedding(text):
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
    data = json.dumps({"model": "nvidia/llama-nemotron-embed-vl-1b-v2:free", "input": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        return res['data'][0]['embedding']

def ingest_zip_archive(zip_path: str, extract_path: str, project_id: int):
    # Ensure collection exists
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=2048, distance=Distance.COSINE)
        )

    try:
        # 1. Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        # 2. Walk the directory and parse code
        points_to_insert = []
        for root, dirs, files in os.walk(extract_path):
            if any(x in root for x in ["venv", "__pycache__", ".git", "node_modules"]): 
                continue
                
            for file in files:
                if file.endswith(".py"):
                    try:
                        filepath = os.path.join(root, file)
                        chunks = extract_code_chunks(filepath)
                        for chunk in chunks:
                            vector = get_embedding(chunk['code'])
                            points_to_insert.append(PointStruct(
                                id=str(uuid.uuid4()),
                                vector=vector,
                                payload={
                                    "project_id": project_id,
                                    "name": chunk['name'],
                                    "type": chunk['type'],
                                    "code": chunk['code'],
                                    "filepath": file # Store filename only for privacy
                                }
                            ))
                    except:
                        continue

        if points_to_insert:
            client.upsert(collection_name=COLLECTION_NAME, points=points_to_insert)
            print(f"Project {project_id} fully ingested.")

    finally:
        # 3. PRODUCTION CLEANUP: Remove temp files
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)