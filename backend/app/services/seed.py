import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.entities import Disease, Pesticide, DiseasePesticide


SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

# 시드 JSON이 관리하는 필드 — 여기 없는 칼럼은 시딩이 건드리지 않는다
PESTICIDE_FIELDS = (
    "name",
    "active_ingredient",
    "registration_no",
    "dilution",
    "usage_method",
    "phi_days",
    "reentry_hours",
    "safety_notes",
)
DISEASE_FIELDS = (
    "name",
    "name_en",
    "crop_type",
    "category",
    "description",
    "causes",
    "prevention",
    "severity",
)


def _pesticide_values(item: dict) -> dict:
    return {field: item.get(field) for field in PESTICIDE_FIELDS}


def _disease_values(item: dict) -> dict:
    return {
        "name": item["name"],
        "name_en": item.get("name_en"),
        "crop_type": item["crop_type"],
        "category": item.get("category", "disease"),
        "description": item.get("description"),
        "causes": item.get("causes", []),
        "prevention": item.get("prevention", []),
        "severity": item.get("severity", "medium"),
    }


def _apply(entity, values: dict) -> None:
    """바뀐 필드만 대입한다 (불필요한 UPDATE와 dirty 판정을 피하기 위해)."""
    for field, value in values.items():
        if getattr(entity, field) != value:
            setattr(entity, field, value)


def seed_database(db: Session) -> None:
    """시드 JSON을 목표 상태로 보고 DB를 거기에 맞춘다.

    JSON을 수정하거나 scripts/sync_pesticides.py로 등록 농약을 다시 받으면 그 변경이
    반영되어야 한다. 따라서 누락분 추가에 그치지 않고, 기존 행의 내용을 갱신하며
    목록에서 빠진 농약·매핑은 제거한다. 등록이 취소된 농약이 계속 추천되면
    안 되기 때문이다.

    단, 질병 행은 삭제하지 않는다. 진단 이력(diagnoses.disease_id)이 FK로 참조하므로
    클래스를 지우면 과거 이력이 깨진다. 클래스 제거는 수동 마이그레이션 대상이다.
    """
    diseases_data = json.loads((SEED_DIR / "diseases.json").read_text(encoding="utf-8"))
    pesticides_data = json.loads((SEED_DIR / "pesticides.json").read_text(encoding="utf-8"))
    mappings = json.loads((SEED_DIR / "disease_pesticides.json").read_text(encoding="utf-8"))

    # 농약: 이름 기준 upsert
    pesticide_map: dict[str, Pesticide] = {}
    for item in pesticides_data:
        values = _pesticide_values(item)
        pesticide = db.query(Pesticide).filter(Pesticide.name == values["name"]).first()
        if pesticide is None:
            pesticide = Pesticide(**values)
            db.add(pesticide)
        else:
            _apply(pesticide, values)
        pesticide_map[item["key"]] = pesticide
    db.flush()

    # 질병: model_class_id 기준 upsert
    disease_map: dict[str, Disease] = {}
    for item in diseases_data:
        disease = (
            db.query(Disease)
            .filter(Disease.model_class_id == item["model_class_id"])
            .first()
        )
        values = _disease_values(item)
        if disease is None:
            disease = Disease(model_class_id=item["model_class_id"], **values)
            db.add(disease)
        else:
            _apply(disease, values)
        disease_map[item["key"]] = disease
    db.flush()

    # 질병-농약 매핑: 시드에 있는 조합만 남긴다
    desired: set[tuple[int, int]] = set()
    for mapping in mappings:
        disease = disease_map[mapping["disease_key"]]
        pesticide = pesticide_map[mapping["pesticide_key"]]
        desired.add((disease.id, pesticide.id))

        priority = mapping.get("priority", 1)
        row = (
            db.query(DiseasePesticide)
            .filter(
                DiseasePesticide.disease_id == disease.id,
                DiseasePesticide.pesticide_id == pesticide.id,
            )
            .first()
        )
        if row is None:
            db.add(
                DiseasePesticide(
                    disease_id=disease.id,
                    pesticide_id=pesticide.id,
                    priority=priority,
                )
            )
        elif row.priority != priority:
            row.priority = priority

    for row in db.query(DiseasePesticide).all():
        if (row.disease_id, row.pesticide_id) not in desired:
            db.delete(row)
    db.flush()

    # 시드 목록에서 빠진 농약 제거 (매핑을 먼저 지웠으므로 참조가 남지 않는다)
    seed_names = {item["name"] for item in pesticides_data}
    for pesticide in db.query(Pesticide).all():
        if pesticide.name not in seed_names:
            db.delete(pesticide)

    db.commit()
