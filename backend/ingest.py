import os
import uuid
import json
import urllib.request
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# Import the parser we just built!
from ast_parser import extract_code_chunks

# Load environment variables
load_dotenv()

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")
collection_name = "codebase_docs"
vector_size = 2048 # Size for OpenRouter's free embedding model

# Create collection if it doesn't exist
if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"Created new collection: '{collection_name}'")

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
    print(f"\nScanning directory: {directory_path}\n")
    
    points_to_insert = []
    
    for root, dirs, files in os.walk(directory_path):
        # SECURITY/COST CHECK: Do not scan the virtual environment or cache folders!
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
                        # 1. Generate the AI vector for the code
                        vector = get_embedding(chunk['code'])
                        
                        # 2. Prepare the data package for Qdrant
                        points_to_insert.append(
                            PointStruct(
                                id=str(uuid.uuid4()),
                                vector=vector,
                                payload={
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

    # 3. Bulk insert everything into the database
    if points_to_insert:
        print(f"\nSaving {len(points_to_insert)} code chunks into Qdrant...")
        client.upsert(
            collection_name=collection_name,
            points=points_to_insert
        )
        print("Ingestion complete! Your codebase is now searchable.\n")
    else:
        print("\nNo valid code chunks found to ingest.\n")

if __name__ == "__main__":
    # Let's test it by ingesting the backend folder we are currently building!
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ingest_directory(current_dir)