from fastapi import FastAPI

app = FastAPI(title="DocuSync AI API")

@app.get("/")
def read_root():
    return {"status": "DocuSync API is running", "version": "0.1.0"}