from fastapi import APIRouter

from app.core.config import settings
from app.schemas.diagnosis import HealthResponse
from app.services.ml_service import is_model_loaded, load_model

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    load_model()
    return HealthResponse(
        status="ok",
        model_loaded=is_model_loaded(),
        version=settings.app_version,
    )
