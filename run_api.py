#!/usr/bin/env python
"""Simple script to run the FastAPI server with proper Python path."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

# Now import and run
import uvicorn
from api.main import app

if __name__ == "__main__":
    print("🚀 Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)