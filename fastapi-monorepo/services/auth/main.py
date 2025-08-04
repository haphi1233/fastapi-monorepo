from fastapi import FastAPI
from libs.db.session import SessionLocal
from sqlalchemy import text
from .app.routers import user
import sys 
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = FastAPI()

@app.get("/auth/health")
def health_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "database connected"}
    finally:
        db.close()

app.include_router(user.router)
