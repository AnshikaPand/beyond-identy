"""
Beyond Identity - Root Application Entrypoint
Exposes `app` so that both:
  - uvicorn main:app --reload --port 8000
  - uvicorn app.main:app --reload --port 8000
work seamlessly both locally and on cloud platforms like Render.
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
