"""시드 동기화 테스트: JSON을 목표 상태로 보고 DB를 맞추는지 검증한다."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import Disease, DiseasePesticide, Pesticide
from app.services import seed as seed_module


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_dir(tmp_path, monkeypatch):
    """시드 JSON을 테스트에서 자유롭게 바꿔 쓸 수 있는 임시 디렉터리."""
    directory = tmp_path / "seed"
    directory.mkdir()
    monkeypatch.setattr(seed_module, "SEED_DIR", directory)

    def write(diseases, pesticides, mappings):
        (directory / "diseases.json").write_text(json.dumps(diseases, ensure_ascii=False), encoding="utf-8")
        (directory / "pesticides.json").write_text(json.dumps(pesticides, ensure_ascii=False), encoding="utf-8")
        (directory / "disease_pesticides.json").write_text(json.dumps(mappings, ensure_ascii=False), encoding="utf-8")

    return write


DISEASE = {
    "key": "radish_alternaria",
    "name": "무 검은무늬병",
    "crop_type": "무",
    "description": "초기 설명",
    "severity": "medium",
    "model_class_id": 2,
}
PEST_A = {"key": "a", "name": "농약A", "dilution": "1000배", "phi_days": 7}
PEST_B = {"key": "b", "name": "농약B", "dilution": "500배", "phi_days": 3}
MAP_A = {"disease_key": "radish_alternaria", "pesticide_key": "a", "priority": 1}
MAP_B = {"disease_key": "radish_alternaria", "pesticide_key": "b", "priority": 2}


def test_seeds_initial_state(db, seed_dir):
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)

    disease = db.query(Disease).one()
    assert disease.name == "무 검은무늬병"
    assert [p.name for p in disease.pesticides] == ["농약A"]


def test_reseed_is_idempotent(db, seed_dir):
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)
    seed_module.seed_database(db)

    assert db.query(Disease).count() == 1
    assert db.query(Pesticide).count() == 1
    assert db.query(DiseasePesticide).count() == 1


def test_updates_changed_fields(db, seed_dir):
    """JSON 내용을 고치면 기존 행에 반영되어야 한다 (기존에는 무시됐다)."""
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)

    seed_dir(
        [{**DISEASE, "description": "고친 설명", "severity": "high"}],
        [{**PEST_A, "dilution": "2000배", "phi_days": 14}],
        [MAP_A],
    )
    seed_module.seed_database(db)

    disease = db.query(Disease).one()
    assert disease.description == "고친 설명"
    assert disease.severity == "high"
    pesticide = db.query(Pesticide).one()
    assert pesticide.dilution == "2000배"
    assert pesticide.phi_days == 14


def test_drops_deregistered_pesticide(db, seed_dir):
    """PSIS 재동기화로 빠진 농약은 매핑과 함께 제거되어야 한다."""
    seed_dir([DISEASE], [PEST_A, PEST_B], [MAP_A, MAP_B])
    seed_module.seed_database(db)
    assert db.query(Pesticide).count() == 2

    # 농약B가 등록 목록에서 빠진 상황
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)

    assert [p.name for p in db.query(Pesticide).all()] == ["농약A"]
    assert db.query(DiseasePesticide).count() == 1
    assert [p.name for p in db.query(Disease).one().pesticides] == ["농약A"]


def test_updates_mapping_priority(db, seed_dir):
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)

    seed_dir([DISEASE], [PEST_A], [{**MAP_A, "priority": 5}])
    seed_module.seed_database(db)

    assert db.query(DiseasePesticide).one().priority == 5


def test_keeps_disease_rows_referenced_by_history(db, seed_dir):
    """질병은 진단 이력이 FK로 참조하므로 시드에서 빠져도 삭제하지 않는다."""
    seed_dir([DISEASE], [PEST_A], [MAP_A])
    seed_module.seed_database(db)

    seed_dir([], [PEST_A], [])
    seed_module.seed_database(db)

    assert db.query(Disease).count() == 1
