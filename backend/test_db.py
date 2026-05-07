import urllib.request
import json
import os
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# Load environment variables
load_dotenv()

# --- 1. Helper function to get embeddings from OpenRouter ---
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

# --- 2. Main Execution ---
print("1. Generating embedding for our code snippet...")
code_text = "def calculate_total(price, tax): return price + (price * tax)"
vector = get_embedding(code_text)
vector_size = len(vector)
print(f"   Success! Vector size is {vector_size} dimensions.")

print("\n2. Connecting to local Qdrant Vector Database...")
# Connects to the Qdrant instance running via Docker
client = QdrantClient(url="http://localhost:6333")
collection_name = "doc_chunks"

print("\n3. Creating collection (if it doesn't exist)...")
# We must tell Qdrant exactly how large the vectors will be
if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"   Created new collection: '{collection_name}'")
else:
    print(f"   Collection '{collection_name}' already exists.")

print("\n4. Inserting data into Qdrant...")
point_id = str(uuid.uuid4())
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=point_id,
            vector=vector,
            # The payload is where we store the actual text so we can read it later
            payload={"text": code_text, "source": "billing.py", "language": "python"}
        )
    ]
)

print(f"\nSUCCESS! Inserted code snippet into Qdrant with ID: {point_id}")