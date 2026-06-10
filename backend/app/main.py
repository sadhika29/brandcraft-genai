import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api import (
    auth_router, generator_router, logo_router,
    content_router, sentiment_router, assistant_router
)

# Create Database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BrandCraft AI API",
    description="Backend API for BrandCraft Generative AI Branding Automation System",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router.router)
app.include_router(generator_router.router)
app.include_router(logo_router.router)
app.include_router(content_router.router)
app.include_router(sentiment_router.router)
app.include_router(assistant_router.router)

# Mount logo uploads directory
UPLOADS_PATH = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
app.mount("/backend/uploads", StaticFiles(directory=str(UPLOADS_PATH)), name="uploads")

# Frontend routes serving
FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "frontend"

@app.get("/")
def read_root():
    index_file = FRONTEND_PATH / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "BrandCraft API is online. Frontend files not found."}

@app.get("/styles.css")
def get_css():
    css_file = FRONTEND_PATH / "styles.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    return {"error": "CSS not found"}

@app.get("/app.js")
def get_js():
    js_file = FRONTEND_PATH / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    return {"error": "JS not found"}
