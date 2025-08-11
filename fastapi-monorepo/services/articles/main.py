import os
import sys
from fastapi import FastAPI

from .app.routers import articles

app = FastAPI(
    title="Articles API",
    description="Articles API",
    version="0.0.1",
)

app.include_router(articles.router)
