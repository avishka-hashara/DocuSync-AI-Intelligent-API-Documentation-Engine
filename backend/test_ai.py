import urllib.request
import json
import os
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()

url = "https://openrouter.ai/api/v1/embeddings"
api_key = os.getenv("OPENROUTER_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = json.dumps({
    "model": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "input": "def hello_world(): print('Hello, DocuSync!')"
}).encode("utf-8")

req = urllib.request.Request(url, data=data, headers=headers)

print("Sending raw request to OpenRouter...")

try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Response:", json.loads(response.read().decode()))
except Exception as e:
    print("\n--- ERROR CAUGHT ---")
    print("Error type:", e)
    if hasattr(e, 'read'):
        print("Error details from OpenRouter:", e.read().decode())