# CropCare AI - Database Schema

개발 환경은 SQLite(`backend/cropcare.db`), 운영은 PostgreSQL을 상정한다.
스키마는 `backend/app/models/entities.py`의 SQLAlchemy 모델이 단일 정의원이며,
앱 시작 시 `Base.metadata.create_all()`로 생성된다 (마이그레이션 도구 미도입).

## ER 개요

```
diseases ──< disease_pesticides >── pesticides
    │
    └──< diagnoses (history)
```

## Tables

### diseases

병해 6종 + 정상 3종 = 9행. 모델 클래스와 1:1로 대응한다.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 병해명 (한글). 예: `무 검은무늬병` |
| name_en | VARCHAR(200) | 영문명 |
| crop_type | VARCHAR(100) | 작물: `고추` / `무` / `배추` |
| category | VARCHAR(50) | `disease` / `normal` (정상=건전주 클래스) |
| description | TEXT | 증상 설명 |
| causes | JSON | 원인 목록 (string 배열) |
| prevention | JSON | 예방 방법 (string 배열) |
| severity | VARCHAR(20) | `low` / `medium` / `high` |
| model_class_id | INTEGER UNIQUE, INDEX | ML 클래스 ID (0~8) |

**`model_class_id`가 시스템의 조인 키다.** 학습 데이터의 클래스 폴더명 앞 숫자
(`2_무검은무늬병`)가 그대로 체크포인트에 기록되고, 추론 결과가 이 값으로 돌아와
`diseases` 행을 찾는다. ImageFolder의 정렬 순서에 의존하지 않으므로 나중에
클래스를 추가해도 기존 ID가 밀리지 않는다.

| model_class_id | 병해 | category |
|---|---|---|
| 0 | 고추 탄저병 | disease |
| 1 | 고추 흰가루병 | disease |
| 2 | 무 검은무늬병 | disease |
| 3 | 무 노균병 | disease |
| 4 | 배추 검은썩음병 | disease |
| 5 | 배추 노균병 | disease |
| 6 | 고추 정상 | normal |
| 7 | 무 정상 | normal |
| 8 | 배추 정상 | normal |

### pesticides

PSIS(농약안전정보시스템) 등록 농약 정보. 현재 23행.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| name | VARCHAR(200) | `상표명 (품목명)` 형식 |
| active_ingredient | VARCHAR(200) | 유효성분·제형 |
| registration_no | VARCHAR(50) | `PSIS-{pestiCode}` |
| dilution | VARCHAR(100) | 희석배수 |
| usage_method | TEXT | 사용법 (살포 시기·방법) |
| phi_days | INTEGER | 안전사용기준 — 수확 전 마지막 살포일 |
| reentry_hours | INTEGER | 재입장 시간 (PSIS 미제공, 현재 전부 NULL) |
| safety_notes | TEXT | 안전사용기준·사용횟수 원문 |

### disease_pesticides

병해당 최대 5개 농약을 유효성분이 겹치지 않게 선정해 매핑한다. 현재 25행.

| Column | Type | Description |
|--------|------|-------------|
| disease_id | FK → diseases, PK | |
| pesticide_id | FK → pesticides, PK | |
| priority | INTEGER | 낮을수록 우선 추천 |

정상 클래스(6·7·8)에는 매핑이 없다.

### diagnoses

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) PK | UUID4 문자열 |
| disease_id | FK → diseases | 최종 확정 병해 |
| confidence | FLOAT | Top-1 신뢰도 |
| top_predictions | JSON | `[{name, confidence}, ...]` (최대 3개) |
| image_path | VARCHAR(500) | 1차 사진의 서버 저장 경로 |
| refined_image_path | VARCHAR(500) | 판별부위 2차 촬영 사진 경로 (미재확정 시 NULL) |
| crop_type | VARCHAR(100) | 사용자 선택값 또는 예측 병해의 작물 |
| created_at | DATETIME | server_default=now() |

`POST /diagnose/{id}/refine`은 새 행을 만들지 않고 **기존 행의
`disease_id` · `confidence` · `top_predictions` · `refined_image_path`를 갱신한다.**
`image_path`(1차 사진)는 보존되므로 어떤 두 장으로 재확정했는지 추적할 수 있다.

## 스키마 변경

마이그레이션 도구를 도입하기 전까지, 나중에 추가된 칼럼은 앱 시작 시
`ensure_columns()`(`app/core/database.py`)가 보완한다. `create_all()`은 이미 존재하는
테이블에 칼럼을 추가하지 못하므로, 누락된 칼럼만 `ALTER TABLE ... ADD COLUMN`으로
덧붙여 기존 진단 이력을 보존한다. 멱등이며 대상 목록은 `_ADDED_COLUMNS`에 있다.

칼럼을 추가할 때는 SQLAlchemy 모델과 `_ADDED_COLUMNS` 양쪽을 함께 갱신해야 한다.
칼럼 삭제·타입 변경은 지원하지 않는다 (Alembic 도입 대상).

## Seed Data

`backend/app/data/seed/`의 JSON 3종을 앱 시작 시 `seed_database()`가 적재한다.

| 파일 | 행 수 | 출처 |
|------|-------|------|
| `diseases.json` | 9 | 수기 작성 (증상·원인·예방) |
| `pesticides.json` | 23 | PSIS OpenAPI (`scripts/sync_pesticides.py`로 재생성) |
| `disease_pesticides.json` | 25 | 동일 |

**시드 JSON이 목표 상태다.** 시딩은 매 기동마다 DB를 그 상태로 맞춘다.

| 대상 | 식별 기준 | 동작 |
|------|-----------|------|
| 농약 | `name` | 없으면 추가, 있으면 내용 갱신, **JSON에서 빠지면 삭제** |
| 질병 | `model_class_id` | 없으면 추가, 있으면 내용 갱신, 삭제하지 않음 |
| 매핑 | (disease, pesticide) | JSON에 있는 조합만 남기고 나머지는 삭제, `priority` 갱신 |

JSON을 고치거나 `sync_pesticides.py`로 등록 농약을 다시 받으면 그 변경이 재기동 시
반영된다. 등록이 취소되어 목록에서 빠진 농약은 매핑과 함께 제거되므로 계속
추천되는 일이 없다.

**질병 행만 삭제하지 않는다.** `diagnoses.disease_id`가 FK로 참조하므로 클래스를
지우면 과거 진단 이력이 깨진다. 클래스 제거는 수동 마이그레이션 대상이다.

시딩은 `PESTICIDE_FIELDS`·`DISEASE_FIELDS`에 나열된 칼럼만 건드린다.
깨끗한 재적재가 필요하면 `backend/cropcare.db`를 삭제하고 백엔드를 재시작한다
(진단 이력도 함께 사라진다).
