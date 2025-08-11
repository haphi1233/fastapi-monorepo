#!/usr/bin/env python
"""
Startup script for API Gateway with proper path configuration
"""
import sys
import os
import asyncio

# Add current directory to path for libs imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import and run the gateway
from gateway_main import main

if __name__ == "__main__":
    asyncio.run(main())
