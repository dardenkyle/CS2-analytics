#!/usr/bin/env python
"""Simple script to run the FastAPI backend server."""

import uvicorn

from api.main import app

if __name__ == "__main__":
    print("🚀 Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
