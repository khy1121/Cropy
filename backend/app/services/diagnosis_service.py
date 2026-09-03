import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Disease, Diagnosis
from app.schemas.diagnosis import (
    DiagnoseResponse,
    DiagnosisSummary,
    DiseaseDetail,
    PaginatedHistory,
    PesticideInfo,
    PesticideSafety,
    PredictionItem,
)
from app.services.ml_service import predict, predict_all, predict_pair
from app.services.recapture import apply_pair_specialist, check_recapture, fuse_predictions


def _pesticide_to_schema(pesticide) -> PesticideInfo:
    return PesticideInfo(
        name=pesticide.name,
        dilution=pesticide.dilution,
        usage=pesticide.usage_method,
        active_ingredient=pesticide.active_ingredient,
        safety_notes=pesticide.safety_notes,
        safety=PesticideSafety(
            phi_days=pesticide.phi_days,
            reentry_hours=pesticide.reentry_hours,
        ),
    )


def _image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"/uploads/{Path(image_path).name}"


def diagnose_image(db: Session, file_bytes: bytes, filename: str, crop_type: str | None) -> DiagnoseResponse:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix or ".jpg"
    saved_name = f"{uuid.uuid4()}{ext}"
    saved_path = settings.upload_dir / saved_name
    saved_path.write_bytes(file_bytes)

    predictions = predict(saved_path)
    diseases_by_class = {
        d.model_class_id: d
        for d in db.query(Disease).filter(
            Disease.model_class_id.in_([p[0] for p in predictions])
        ).all()
    }

    top_predictions: list[PredictionItem] = []
    primary_disease: Disease | None = None
    primary_confidence = 0.0

    for class_id, confidence in predictions:
        disease = diseases_by_class.get(class_id)
        if disease:
            top_predictions.append(PredictionItem(name=disease.name, confidence=confidence))
            if primary_disease is None:
                primary_disease = disease
                primary_confidence = confidence

    if primary_disease is None:
        primary_disease = db.query(Disease).first()
        primary_confidence = predictions[0][1] if predictions else 0.0
        if primary_disease:
            top_predictions = [PredictionItem(name=primary_disease.name, confidence=primary_confidence)]

    pesticides = [_pesticide_to_schema(p) for p in primary_disease.pesticides] if primary_disease else []

    # 혼동쌍 판별부위 유도(구성 B·C·D): 상위 두 후보가 유사 병해쌍이고 마진이 좁으면
    # 두 병을 가르는 특정 부위를 다시 촬영하도록 안내
    class_names = {cid: d.name for cid, d in diseases_by_class.items()}
    recapture = check_recapture(predictions, class_names)

    diagnosis = Diagnosis(
        disease_id=primary_disease.id,
        confidence=primary_confidence,
        top_predictions=[p.model_dump() for p in top_predictions],
        image_path=str(saved_path),
        crop_type=crop_type or primary_disease.crop_type,
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    return DiagnoseResponse(
        id=diagnosis.id,
        disease_name=primary_disease.name,
        crop_type=diagnosis.crop_type,
        category=primary_disease.category,
        severity=primary_disease.severity,
        confidence=primary_confidence,
        top_predictions=top_predictions,
        description=primary_disease.description,
        causes=primary_disease.causes or [],
        pesticides=pesticides,
        prevention=primary_disease.prevention or [],
        image_url=_image_url(diagnosis.image_path),
        created_at=diagnosis.created_at,
        recapture=recapture,
    )


def refine_diagnosis(
    db: Session, diagnosis_id: str, file_bytes: bytes, filename: str
) -> DiagnoseResponse | None:
    """판별부위 2차 촬영으로 진단을 재확정한다 (구성 E: 다시점 융합).

    원본 사진과 2차 사진의 전체 분포를 가중 융합해 최상위 병해를 갱신한다.
    """
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        return None

    original_path = Path(diagnosis.image_path) if diagnosis.image_path else None
    if not original_path or not original_path.exists():
        raise ValueError("원본 진단 이미지를 찾을 수 없어 재확정할 수 없습니다.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix or ".jpg"
    second_name = f"{uuid.uuid4()}{ext}"
    second_path = settings.upload_dir / second_name
    second_path.write_bytes(file_bytes)

    dist1 = predict_all(original_path)
    dist2 = predict_all(second_path)
    fused_full = fuse_predictions(dist1, dist2)
    # 혼동쌍 전용 분류기가 있으면 2차(판별부위) 사진으로 쌍 내부 비중을 재분배 (정식 구성 E).
    # 1차 진단의 상위 두 후보가 그 분류기의 쌍일 때만 적용된다.
    fused_full = apply_pair_specialist(fused_full, predict_pair(second_path), dist1)
    fused = fused_full[:3]

    diseases_by_class = {
        d.model_class_id: d
        for d in db.query(Disease).filter(
            Disease.model_class_id.in_([c for c, _ in fused])
        ).all()
    }

    top_predictions: list[PredictionItem] = []
    primary_disease: Disease | None = None
    primary_confidence = fused[0][1] if fused else diagnosis.confidence

    for class_id, confidence in fused:
        disease = diseases_by_class.get(class_id)
        if disease:
            top_predictions.append(PredictionItem(name=disease.name, confidence=confidence))
            if primary_disease is None:
                primary_disease = disease
                primary_confidence = confidence

    if primary_disease is None:
        primary_disease = diagnosis.disease

    diagnosis.disease_id = primary_disease.id
    diagnosis.confidence = primary_confidence
    diagnosis.top_predictions = [p.model_dump() for p in top_predictions]
    diagnosis.refined_image_path = str(second_path)
    db.commit()
    db.refresh(diagnosis)

    return DiagnoseResponse(
        id=diagnosis.id,
        disease_name=primary_disease.name,
        crop_type=diagnosis.crop_type,
        category=primary_disease.category,
        severity=primary_disease.severity,
        confidence=primary_confidence,
        top_predictions=top_predictions,
        description=primary_disease.description,
        causes=primary_disease.causes or [],
        pesticides=[_pesticide_to_schema(p) for p in primary_disease.pesticides],
        prevention=primary_disease.prevention or [],
        image_url=_image_url(diagnosis.image_path),
        refined_image_url=_image_url(diagnosis.refined_image_path),
        created_at=diagnosis.created_at,
        recapture=None,
    )


def get_history(db: Session, page: int, size: int) -> PaginatedHistory:
    query = db.query(Diagnosis).order_by(Diagnosis.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return PaginatedHistory(
        items=[
            DiagnosisSummary(
                id=d.id,
                disease_name=d.disease.name,
                confidence=d.confidence,
                crop_type=d.crop_type,
                image_url=_image_url(d.image_path),
                created_at=d.created_at,
            )
            for d in items
        ],
        total=total,
        page=page,
        size=size,
    )


def get_diagnosis_detail(db: Session, diagnosis_id: str) -> DiagnoseResponse | None:
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        return None

    disease = diagnosis.disease
    return DiagnoseResponse(
        id=diagnosis.id,
        disease_name=disease.name,
        crop_type=diagnosis.crop_type,
        category=disease.category,
        severity=disease.severity,
        confidence=diagnosis.confidence,
        top_predictions=[PredictionItem(**p) for p in (diagnosis.top_predictions or [])],
        description=disease.description,
        causes=disease.causes or [],
        pesticides=[_pesticide_to_schema(p) for p in disease.pesticides],
        prevention=disease.prevention or [],
        image_url=_image_url(diagnosis.image_path),
        refined_image_url=_image_url(diagnosis.refined_image_path),
        created_at=diagnosis.created_at,
    )


def list_diseases(db: Session, q: str | None, crop_type: str | None) -> list[DiseaseDetail]:
    query = db.query(Disease)
    if q:
        query = query.filter(Disease.name.contains(q))
    if crop_type:
        query = query.filter(Disease.crop_type == crop_type)

    return [
        DiseaseDetail(
            id=d.id,
            name=d.name,
            name_en=d.name_en,
            crop_type=d.crop_type,
            category=d.category,
            description=d.description,
            causes=d.causes or [],
            prevention=d.prevention or [],
            severity=d.severity,
            pesticides=[_pesticide_to_schema(p) for p in d.pesticides],
        )
        for d in query.all()
    ]


def get_disease(db: Session, disease_id: int) -> DiseaseDetail | None:
    disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not disease:
        return None

    return DiseaseDetail(
        id=disease.id,
        name=disease.name,
        name_en=disease.name_en,
        crop_type=disease.crop_type,
        category=disease.category,
        description=disease.description,
        causes=disease.causes or [],
        prevention=disease.prevention or [],
        severity=disease.severity,
        pesticides=[_pesticide_to_schema(p) for p in disease.pesticides],
    )
