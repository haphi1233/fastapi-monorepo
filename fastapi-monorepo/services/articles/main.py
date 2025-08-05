import os
import sys
from fastapi import FastAPI

# Add path to monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.routers import articles

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = FastAPI(
    title="Articles API",
    description="Articles API",
    version="0.0.1",
)

app.include_router(articles.router)
