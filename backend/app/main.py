import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base
from app.config import UPLOADS_DIR, BASE_DIR

from app.api import (
    auth_router,
    generator_router,
    logo_router,
    content_router,
    sentiment_router,
    assistant_router
)


# ============================================================
# DIRECTORIES
# ============================================================

# backend/
BACKEND_PATH = Path(__file__).resolve().parent.parent

# backend/uploads/
UPLOADS_PATH = Path(UPLOADS_DIR)

# frontend/
FRONTEND_PATH = BACKEND_PATH.parent / "frontend"

# Make sure uploads directory exists
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="BrandCraft AI API",
    description="Backend API for BrandCraft Generative AI Branding Automation System",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API ROUTERS
# ============================================================

app.include_router(auth_router.router)
app.include_router(generator_router.router)
app.include_router(logo_router.router)
app.include_router(content_router.router)
app.include_router(sentiment_router.router)
app.include_router(assistant_router.router)


# ============================================================
# LOGO FILE SERVING
# ============================================================

# Main path used by BrandCraft
app.mount(
    "/backend/uploads",
    StaticFiles(
        directory=str(UPLOADS_PATH),
        check_dir=True
    ),
    name="uploads"
)

# Additional simple path for frontend compatibility
app.mount(
    "/uploads",
    StaticFiles(
        directory=str(UPLOADS_PATH),
        check_dir=True
    ),
    name="uploads_public"
)


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def read_root():
    index_file = FRONTEND_PATH / "index.html"

    if index_file.exists():
        return FileResponse(str(index_file))

    return {
        "message": "BrandCraft API is online. Frontend files not found."
    }


@app.get("/styles.css")
def get_css():
    css_file = FRONTEND_PATH / "styles.css"

    if css_file.exists():
        return FileResponse(
            str(css_file),
            media_type="text/css"
        )

    return {
        "error": "CSS not found"
    }


@app.get("/app.js")
def get_js():
    js_file = FRONTEND_PATH / "app.js"

    if js_file.exists():
        return FileResponse(
            str(js_file),
            media_type="application/javascript"
        )

    return {
        "error": "JS not found"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "uploads_directory": str(UPLOADS_PATH),
        "uploads_exists": UPLOADS_PATH.exists(),
        "frontend_exists": FRONTEND_PATH.exists()
    }