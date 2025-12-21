"""
Entry point for running the ScholarSync API from the new src/ structure.
"""
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the API
from src.api import app
import uvicorn
import os

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
        access_log=os.getenv("UVICORN_ACCESS_LOG", "0") == "1",
        reload=True
    )
