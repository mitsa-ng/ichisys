from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import admin, auth, pools, draw, warehouse, payments, events, setup, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Ichiban Kuji API", version="1.0.0", lifespan=lifespan)

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
