#!/usr/bin/env python
"""
Startup script for Articles Service with proper path configuration
"""
import sys
import os

# Add parent directory to path for libs imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now import and run the main app
from services.articles.main import app
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
