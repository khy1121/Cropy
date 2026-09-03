from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# create_all()은 이미 존재하는 테이블에 칼럼을 추가하지 못한다. 마이그레이션 도구를
# 도입하기 전까지, 나중에 생긴 칼럼만 누락 시 덧붙여 기존 DB(진단 이력)를 보존한다.
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("diagnoses", "refined_image_path", "VARCHAR(500)"),
]


def ensure_columns() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, ddl_type in _ADDED_COLUMNS:
        if table not in tables:
            continue  # create_all()이 방금 만들었다면 이미 최신 스키마다
        if column in {c["name"] for c in inspector.get_columns(table)}:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
