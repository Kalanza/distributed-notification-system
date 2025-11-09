from fastapi import FastAPI

app = FastAPI(title="API Gateway")

@app.get("/health")
def health_check():
    return {"status": "ok"}
