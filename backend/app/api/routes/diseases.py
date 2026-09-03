from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.diagnosis import DiseaseDetail
from app.services import diagnosis_service

router = APIRouter()


@router.get("", response_model=list[DiseaseDetail])
def list_diseases(
    q: str | None = Query(None),
    crop_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return diagnosis_service.list_diseases(db, q, crop_type)


@router.get("/{disease_id}", response_model=DiseaseDetail)
def get_disease(disease_id: int, db: Session = Depends(get_db)):
    result = diagnosis_service.get_disease(db, disease_id)
    if not result:
        raise HTTPException(status_code=404, detail="병해충 정보를 찾을 수 없습니다.")
    return result
