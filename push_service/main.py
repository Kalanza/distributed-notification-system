from fastapi import FastAPI

app = FastAPI(title="Push Service")

@app.get("/health")
def health_check():
    return {"status": "ok"}
