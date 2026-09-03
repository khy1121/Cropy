from datetime import datetime
from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    name: str
    confidence: float


class RecaptureCandidate(BaseModel):
    """혼동쌍 각 후보와, 판별부위에서 그 후보를 가리키는 시각 단서."""

    name: str
    cue: str


class RecaptureGuidance(BaseModel):
    """1차 진단이 혼동쌍에 낮은 마진으로 떨어졌을 때, 어느 부위를 다시 찍을지 안내."""

    region: str
    instruction: str
    margin: float
    candidates: list[RecaptureCandidate]


class PesticideSafety(BaseModel):
    phi_days: int | None = None
    reentry_hours: int | None = None


class PesticideInfo(BaseModel):
    name: str
    dilution: str | None = None
    usage: str | None = None
    safety: PesticideSafety = Field(default_factory=PesticideSafety)
    active_ingredient: str | None = None
    safety_notes: str | None = None


class DiagnoseResponse(BaseModel):
    id: str
    disease_name: str
    crop_type: str | None = None
    category: str = "disease"
    severity: str = "medium"
    confidence: float
    top_predictions: list[PredictionItem]
    description: str | None = None
    causes: list[str] = []
    pesticides: list[PesticideInfo] = []
    prevention: list[str] = []
    image_url: str | None = None
    refined_image_url: str | None = None
    created_at: datetime
    recapture: RecaptureGuidance | None = None


class DiagnosisSummary(BaseModel):
    id: str
    disease_name: str
    confidence: float
    crop_type: str | None = None
    image_url: str | None = None
    created_at: datetime


class PaginatedHistory(BaseModel):
    items: list[DiagnosisSummary]
    total: int
    page: int
    size: int


class DiseaseDetail(BaseModel):
    id: int
    name: str
    name_en: str | None = None
    crop_type: str
    category: str
    description: str | None = None
    causes: list[str] = []
    prevention: list[str] = []
    severity: str
    pesticides: list[PesticideInfo] = []


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str
