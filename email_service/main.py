from fastapi import FastAPI

app = FastAPI(title="Email Service")

@app.get("/health")
def health_check():
    return {"status": "ok"}
