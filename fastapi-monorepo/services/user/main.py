from fastapi import FastAPI

app = FastAPI()

@app.get("/user/health")
def health_check():
    return {"status": "user service is running"}
