from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import diagnosis, diseases, health
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, ensure_columns
from app.services.ml_service import load_model
from app.services.seed import seed_database

settings.upload_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    load_model()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 기반 농작물 병해충 진단 및 스마트 방제 지원 플랫폼",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(diagnosis.router, prefix="/api/v1", tags=["diagnosis"])
app.include_router(diseases.router, prefix="/api/v1/diseases", tags=["diseases"])
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")
