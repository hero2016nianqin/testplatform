"""
FastAPI 应用入口
用法: python run.py
      uvicorn run:app --reload
"""
import os
import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    reload = os.environ.get("APP_ENV", "dev") == "dev"
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        workers=1 if reload else 4,
        log_level="info",
    )
