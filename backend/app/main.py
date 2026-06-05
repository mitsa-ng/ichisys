import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.api import admin, auth, pools, draw, warehouse, payments, events, setup, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="Ichiban Kuji", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(pools.router)
app.include_router(draw.router)
app.include_router(warehouse.router)
app.include_router(payments.router)
app.include_router(events.router)
app.include_router(upload.router)
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/api/files", StaticFiles(directory=settings.upload_dir), name="files")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


frontend_dir_env = os.environ.get("FRONTEND_DIST")
if frontend_dir_env:
    frontend_dir = Path(frontend_dir_env)
elif getattr(sys, "frozen", False):
    frontend_dir = Path(sys.executable).parent / "frontend" / "dist"
else:
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_path = frontend_dir / "index.html"
        if not index_path.exists():
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(str(index_path))
