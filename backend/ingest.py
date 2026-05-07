import os
import uuid
import json
import urllib.request
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from ast_parser import extract_code_chunks

load_dotenv()

client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "codebase_docs"

def get_embedding(text):
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
    data = json.dumps({"model": "nvidia/llama-nemotron-embed-vl-1b-v2:free", "input": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        return res['data'][0]['embedding']

def ingest_directory(directory_path: str, project_id: int):
    # Ensure collection exists
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(COLLECTION_NAME, vectors_config=VectorParams(size=2048, distance=Distance.COSINE))

    points_to_insert = []
    for root, dirs, files in os.walk(directory_path):
        if any(x in root for x in ["venv", "__pycache__", ".git", "node_modules"]): continue
        for file in files:
            if file.endswith(".py"):
                try:
                    chunks = extract_code_chunks(os.path.join(root, file))
                    for chunk in chunks:
                        vector = get_embedding(chunk['code'])
                        points_to_insert.append(PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload={"project_id": project_id, **chunk}
                        ))
                except: continue

    if points_to_insert:
        client.upsert(collection_name=COLLECTION_NAME, points=points_to_insert)
        print(f"Project {project_id} ingestion complete.")