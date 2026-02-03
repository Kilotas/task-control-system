from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.domain.services.cache_service import init_cache
from src.core.database import dispose_engine
from src.core.exceptions import register_exception_handlers

from src.api.v1 import api_v1_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = await init_cache()
    try:
        yield
    finally:
        await cache.close()
        await dispose_engine()



app = FastAPI(
    title=settings.app_name,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


register_exception_handlers(app)


app.include_router(api_v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}