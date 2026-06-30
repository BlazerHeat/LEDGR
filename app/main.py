"""LEDGR API — FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.core.db import db
from app.core.errors import register_exception_handlers
from app.routers import auth, categories, transactions

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    try:
        yield
    finally:
        if db.is_connected():
            await db.disconnect()


app = FastAPI(
    title="LEDGR API",
    version=__version__,
    description=(
        "REST API for LEDGR — a unified personal-finance, bill-splitting and "
        "AI-analytics platform. This deployment implements the Personal Ledger "
        "feature (transactions) plus the supporting authentication endpoints."
    ),
    lifespan=lifespan,
)

_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)


@app.get("/", tags=["Meta"], summary="Service info")
async def root() -> dict:
    return {
        "name": "LEDGR API",
        "version": __version__,
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
    }


@app.get("/healthz", tags=["Meta"], summary="Health check")
async def healthz() -> dict:
    return {"status": "ok", "database": "connected" if db.is_connected() else "disconnected"}
