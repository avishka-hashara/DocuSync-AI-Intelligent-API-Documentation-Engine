import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def test_api(url, model, data_key, input_val):
    print(f"Testing {url} with model {model}...")
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "model": model,
        data_key: input_val
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Success! Status: {response.status}")
            return True
    except Exception as e:
        print(f"FAILED: {e}")
        if hasattr(e, 'read'):
            print(f"Details: {e.read().decode()}")
        return False

# Test Embedding
test_api("https://openrouter.ai/api/v1/embeddings", 
         "nvidia/llama-nemotron-embed-vl-1b-v2:free", 
         "input", "test")

# Test Chat
test_api("https://openrouter.ai/api/v1/chat/completions", 
         "openrouter/free", 
         "messages", [{"role": "user", "content": "hi"}])
