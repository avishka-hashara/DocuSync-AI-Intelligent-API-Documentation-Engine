import os
import uuid
import json
import urllib.request
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from ast_parser import extract_code_chunks

load_dotenv()

# --- NEW: Hardcode to Project 1 ("DocuSync Core API") for testing ---
PROJECT_ID = 1 
# --------------------------------------------------------------------

client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "codebase_docs"
vector_size = 2048

if not client.collection_exists(collection_name=COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"Created new collection: '{COLLECTION_NAME}'")

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

def ingest_directory(directory_path):
    print(f"\nScanning directory: {directory_path} for Project ID: {PROJECT_ID}\n")
    
    points_to_insert = []
    
    for root, dirs, files in os.walk(directory_path):
        if "venv" in root or "__pycache__" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                print(f"File: {file}")
                
                try:
                    chunks = extract_code_chunks(filepath)
                    for chunk in chunks:
                        print(f"  -> Embedding {chunk['type']}: {chunk['name']}...")
                        vector = get_embedding(chunk['code'])
                        
                        points_to_insert.append(
                            PointStruct(
                                id=str(uuid.uuid4()),
                                vector=vector,
                                payload={
                                    "project_id": PROJECT_ID, # <-- NEW: Tagging the vector!
                                    "name": chunk['name'],
                                    "type": chunk['type'],
                                    "code": chunk['code'],
                                    "filepath": filepath,
                                    "language": "python"
                                }
                            )
                        )
                except Exception as e:
                    print(f"  -> [ERROR] Failed to parse {file}: {e}")

    if points_to_insert:
        print(f"\nSaving {len(points_to_insert)} code chunks into Qdrant...")
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points_to_insert
        )
        print("Ingestion complete! Your codebase is now searchable.\n")
    else:
        print("\nNo valid code chunks found to ingest.\n")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ingest_directory(current_dir)