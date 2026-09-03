# 인큐박스 - Database Schema

기존 [DATABASE](DATABASE.md)의 확장. `backend/app/models/entities.py`에 추가하며
`Base.metadata.create_all()`로 생성된다. 기존 테이블은 건드리지 않는다.

## ER 개요

```
devices ──< incubation_runs ──< incubation_captures ──< incubation_cells
                │                       │
                │                       └──< device_events
                │
                └── (field_label 로 diagnoses 와 느슨하게 연결)

diseases (기존) ── model_class_id=0 고추 탄저병 ── 권고의 농약 목록 출처
```

`incubation_runs`와 `diagnoses`는 FK로 묶지 않는다. 둘 다 `field_label`(문자열)을 갖고,
조회 시 같은 라벨끼리 모아 보여준다. 사용자 인증·농장 엔티티가 없는 현재 구조에서
가장 단순한 연결이다. 인증이 들어오면 `farm_id`로 승격한다.

## Tables

### devices

등록된 인큐박스.

| Column | Type | Description |
|--------|------|-------------|
| device_id | VARCHAR(64) PK | 장치가 자기 선언. 예: `incubox-0001` |
| token_hash | VARCHAR(128) | 장치 토큰의 SHA-256. 원문은 저장하지 않는다 |
| label | VARCHAR(100) | 사용자 표시명. 예: `작목반 1호기` |
| firmware | VARCHAR(20) | |
| last_seen_at | DATETIME(tz) | 마지막 요청 시각 |
| created_at | DATETIME(tz) | server_default now() |

### pair_codes

프로비저닝용 1회성 코드. 10분 후 만료, 사용 즉시 삭제.

| Column | Type | Description |
|--------|------|-------------|
| code | VARCHAR(6) PK | |
| expires_at | DATETIME(tz) | |

### incubation_runs

검사 세션 하나.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) PK | uuid4 (기존 `diagnoses.id`와 동일 방식) |
| device_id | VARCHAR(64) FK devices, NULL | 수동 모드면 NULL |
| mode | VARCHAR(10) | `device` / `manual` |
| field_label | VARCHAR(100), INDEX | 밭 이름 |
| crop_type | VARCHAR(100) | 현재 `고추` |
| target_class_id | INTEGER | 판정 대상 병해의 `model_class_id`. 현재 항상 `0`(고추 탄저병). 확장 대비 |
| status | VARCHAR(10), INDEX | `running` / `finished` / `aborted` |
| sample_count | INTEGER | 기본 24 |
| sampled_at | DATETIME(tz) | 채취 시각 |
| disinfection_confirmed_at | DATETIME(tz) | 소독 확인 시각 (NOT NULL — 없으면 생성 거부) |
| started_at | DATETIME(tz) | server_default now() |
| ended_at | DATETIME(tz) | |
| end_reason | VARCHAR(20) | `plateau` / `user` / `max_days` / `aborted` |
| infection_rate | FLOAT | 최신(진행 중) 또는 최종(종료) 감염률. 0~1 |
| grade | VARCHAR(10) | `low` / `caution` / `high` / NULL |
| cells_valid | INTEGER | 판정 가능 칸 수 (분모) |
| cells_expressed | INTEGER | 발현 칸 수 (분자) |
| plateau_since_seq | INTEGER | 이 seq 이후 새 발현 없음. NULL이면 아직 |
| warnings | JSON | 활성 경고 목록. `["low_humidity"]` |
| notes | TEXT | |

`infection_rate`·`grade`·`cells_*`는 매 촬영마다 갱신되는 **비정규화 캐시**다. 원본은
`incubation_cells`에서 언제든 재계산할 수 있다. 목록 화면이 run마다 셀을 조인하지 않게
하려는 것.

### incubation_captures

촬영 한 장.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) PK | uuid4 |
| run_id | VARCHAR(36) FK incubation_runs, INDEX | |
| seq | INTEGER | run 안에서 단조 증가. **UNIQUE (run_id, seq)** — 중복 업로드 멱등 |
| captured_at | DATETIME(tz) | 장치 보고 시각 |
| received_at | DATETIME(tz) | server_default now() |
| clock_unsynced | BOOLEAN | 장치 시각 불확실 플래그 |
| day | FLOAT | `(captured_at − run.started_at)` 일 단위. 곡선 x축 |
| image_path | VARCHAR(500) | 원본 |
| grid_ok | BOOLEAN | ArUco(또는 수동 4점) 보정 성공 |
| corners | JSON | 보정에 쓴 네 모서리 픽셀 좌표 `[[x,y]×4]` |
| temp_c | FLOAT | 촬영 시점 |
| humidity_pct | FLOAT | |
| climate_summary | JSON | 직전 촬영 이후 구간 요약 (min/max/mean, heater_duty) |
| sharpness | FLOAT | 장치 보고 라플라시안 분산 |
| infection_rate | FLOAT | 이 촬영 시점의 누적 감염률 (곡선 y축) |

### incubation_cells

촬영 × 칸. 24칸이면 촬영당 24행.

| Column | Type | Description |
|--------|------|-------------|
| capture_id | VARCHAR(36) FK incubation_captures, PK(1/2) | |
| cell_index | INTEGER, PK(2/2) | 0~23. 트레이 번호 − 1 |
| crop_path | VARCHAR(500) | 칸 크롭 이미지 |
| p_anthracnose | FLOAT | 고추 클래스 재정규화 후 탄저 확률 |
| p_powdery | FLOAT | 흰가루 (참고용) |
| p_healthy | FLOAT | 정상 |
| is_empty | BOOLEAN | 빈 칸 판정 (분산 임계) |
| state | VARCHAR(10) | 이 촬영 시점의 **누적** 상태: `healthy` / `suspect` / `expressed` / `invalid` |
| state_changed | BOOLEAN | 이 촬영에서 상태가 바뀌었는가 (곡선의 "새 발현" 표시) |

`state`는 래치된다. 한 번 `expressed`면 이후 촬영에서도 `expressed`. 판정 규칙은
[INCUBOX_PIPELINE](INCUBOX_PIPELINE.md).

### device_events

장치 알림·FAULT, 서버 내부 경고.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| device_id | VARCHAR(64) FK devices, NULL | 서버 내부 이벤트는 NULL |
| run_id | VARCHAR(36) FK incubation_runs, NULL, INDEX | |
| type | VARCHAR(30) | `low_humidity` 등 ([INCUBOX_API_SPEC](INCUBOX_API_SPEC.md)) |
| at | DATETIME(tz) | 발생 시각 |
| detail | JSON | |
| resolved_at | DATETIME(tz) | 해소 시각. 앱의 활성 경고 = NULL인 것 |

## 인덱스

| 테이블 | 인덱스 | 용도 |
|--------|--------|------|
| incubation_runs | (field_label, started_at DESC) | 밭별 이력 |
| incubation_runs | (device_id, status) | 장치의 활성 run 조회 (60초 폴링) |
| incubation_captures | UNIQUE (run_id, seq) | 멱등 |
| incubation_captures | (run_id, captured_at) | 곡선 |
| device_events | (run_id, resolved_at) | 활성 경고 |

## 파일 저장

```
backend/uploads/incubation/{run_id}/
├── 0000_20260822T091003.jpg          # 원본
├── 0000_20260822T091003.warped.jpg   # 보정 후 (디버그용, 선택)
└── cells/0000/
    ├── 00.jpg … 23.jpg                # 칸 크롭
```

run당 7일 × 3회 × (5MB + 24 × 50KB) ≈ 130MB. 종료 후 **90일** 지나면 원본은 삭제하고
칸 크롭과 최종 사진 1장만 남긴다(정리 스크립트, 별도). 칸 크롭은 모델 재학습 데이터다 —
삭제하지 않는다.

## 마이그레이션

기존과 같이 `create_all()`. 기존 테이블 변경 없음. 신규 테이블만 추가되므로 기존 DB 파일에
그대로 적용된다.
