import os
import sys
from fastapi import FastAPI
from app.routers import articles

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = FastAPI(
    title="Articles API",
    description="Articles API",
    version="0.0.1",
)


app.include_router(articles)
