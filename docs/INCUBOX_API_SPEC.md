# 인큐박스 - API Specification

기존 [API_SPEC](API_SPEC.md)의 확장. Base URL·프록시·오류 형식은 동일하다.

Base URL: `http://localhost:8000/api/v1`
정적 파일: `/uploads/incubation/{run_id}/{filename}` (촬영 원본), `/uploads/incubation/{run_id}/cells/{seq}/{cell}.jpg` (칸 크롭)

호출자는 둘이다.

| 호출자 | 인증 | 설명 |
|--------|------|------|
| 앱 (브라우저) | 없음 (기존과 동일) | 검사 시작·조회·종료, 장치 페어링 |
| 장치 (인큐박스) | `X-Device-Id` + `X-Device-Token` 헤더 | 촬영 업로드, 상태 폴링, 이벤트 |

## Endpoints

| Method | Path | 호출자 | 설명 |
|--------|------|--------|------|
| POST | `/devices/pair-code` | 앱 | 장치 등록용 페어 코드 발급 |
| POST | `/devices/provision` | 장치 | 페어 코드로 장치 등록, 토큰 수신 |
| GET | `/devices` | 앱 | 내 장치 목록 |
| GET | `/devices/{device_id}/assignment` | 장치 | 할당된 활성 run 조회 |
| POST | `/incubation` | 앱 | 검사 시작 |
| GET | `/incubation` | 앱 | 검사 목록 |
| GET | `/incubation/{run_id}` | 앱·장치 | 검사 상세 (감염률·칸·곡선·환경) |
| POST | `/incubation/{run_id}/capture` | 장치 | 촬영 업로드 → 즉시 판독 |
| POST | `/incubation/{run_id}/manual-capture` | 앱 | 수동 모드 사진 업로드 (Phase 0·장치 없는 농가) |
| POST | `/incubation/{run_id}/finish` | 앱 | 검사 종료 확정 |
| POST | `/incubation/{run_id}/events` | 장치 | 알림·FAULT 이벤트 |

---

### POST /devices/pair-code

앱의 "장치 추가" 화면이 호출. 10분 유효한 6자리 코드.

**Response:** `201 Created`

```json
{ "pair_code": "482913", "expires_at": "2026-08-22T10:10:00+09:00" }
```

### POST /devices/provision

장치 CLI `incubox provision`이 호출.

**Request:** `application/json`

```json
{ "pair_code": "482913", "device_id": "incubox-0001", "firmware": "0.1.0" }
```

**Response:** `201 Created`

```json
{ "device_id": "incubox-0001", "token": "dvc_…", "server_time": "2026-08-22T10:02:11+09:00" }
```

| 오류 | 조건 |
|------|------|
| 400 | 코드 만료·불일치 |
| 409 | 이미 등록된 `device_id` (재등록은 앱에서 삭제 후) |

### GET /devices

```json
[
  { "device_id": "incubox-0001", "label": "작목반 1호기", "last_seen_at": "2026-08-22T09:58:00+09:00",
    "active_run_id": "a1b2…", "firmware": "0.1.0" }
]
```

### GET /devices/{device_id}/assignment

장치가 IDLE일 때 60초마다 폴링.

**Response:** `200 OK`

```json
{ "run_id": "a1b2…", "capture_times": ["08:00", "14:00", "20:00"] }
```

활성 run이 없으면 `{ "run_id": null }`.

---

### POST /incubation

검사 시작. 장치 모드면 `device_id`를 주고, 수동 모드면 생략.

**Request:** `application/json`

```json
{
  "field_label": "윗밭",
  "crop_type": "고추",
  "device_id": "incubox-0001",
  "sample_count": 24,
  "sampled_at": "2026-08-22T08:30:00+09:00",
  "disinfection_confirmed": true,
  "notes": "마지막 살포 8/15 마스터키"
}
```

| Field | Required | 설명 |
|-------|----------|------|
| field_label | Yes | 밭 이름. 같은 라벨의 기존 진단 이력과 묶인다 |
| crop_type | Yes | 현재 `고추`만 허용 |
| device_id | No | 없으면 수동 모드 |
| sample_count | No | 기본 24. 트레이 칸 수 이하 |
| sampled_at | Yes | 채취 시각 |
| disinfection_confirmed | Yes | **`true`가 아니면 400**. 앱 위저드가 소독 단계를 강제한다 |
| notes | No | |

**Response:** `201 Created` — [IncubationRun](#incubationrun) 객체

| 오류 | 조건 |
|------|------|
| 400 | `disinfection_confirmed` 거짓, crop_type 미지원 |
| 409 | 해당 장치에 이미 활성 run 있음 |

### GET /incubation

`?field_label=`, `?status=`, `?page=&page_size=`. 기존 `/history`와 같은 페이지네이션 형식.

### GET /incubation/{run_id}

**Response:** `200 OK` — [IncubationRun](#incubationrun) 전체.

### POST /incubation/{run_id}/capture

장치 업로드. `multipart/form-data`.

| Field | Type | Required | 설명 |
|-------|------|----------|------|
| file | image/jpeg | Yes | 촬영 원본 |
| meta | JSON string | Yes | 아래 |

`meta`:

```json
{
  "seq": 7,
  "captured_at": "2026-08-25T08:00:12+09:00",
  "clock_unsynced": false,
  "temp_c": 26.4,
  "humidity_pct": 96.1,
  "climate_summary": { "temp_min": 25.6, "temp_max": 27.3, "temp_mean": 26.5,
                       "rh_min": 94.0, "rh_mean": 96.2, "heater_duty": 0.31 },
  "sharpness": 182.3,
  "firmware": "0.1.0"
}
```

서버는 동기적으로 격자 보정 → 칸 크롭 → 추론 → 판정을 수행하고 결과를 돌려준다
(목표 30초 이내, 실측 CPU 기준 24칸 × ResNet50 ≈ 10초).

**Response:** `201 Created`

```json
{
  "capture_id": "c9d8…",
  "seq": 7,
  "grid_ok": true,
  "infection_rate": 0.125,
  "cells_expressed": 3,
  "cells_valid": 24,
  "new_expressions": [5, 17],
  "plateau": false,
  "run_status": "running"
}
```

| 오류 | 조건 |
|------|------|
| 401 | 장치 토큰 불일치 |
| 404 | run 없음 |
| 409 | run이 `finished` — 장치는 CLEANUP으로 |
| 422 | `(run_id, seq)` 중복 — 멱등 처리, 기존 결과 반환 (2xx 아님에 주의: 장치는 큐에서 제거) |
| 400 | 이미지 아님, 10MB 초과 |

`grid_ok: false`면 ArUco 검출 실패. 촬영은 저장되지만 판독은 건너뛴다. 연속 3회 실패 시
run에 `grid_failure` 경고가 붙고 앱이 안내한다.

### POST /incubation/{run_id}/manual-capture

수동 모드. 앱이 스마트폰 사진을 올린다. `multipart/form-data`, `file` + 선택 `captured_at`.
ArUco 마커가 없으므로 **격자 네 모서리 좌표**를 함께 받는다(앱에서 사용자가 4점 지정).

| Field | Type | Required | 설명 |
|-------|------|----------|------|
| file | image | Yes | |
| captured_at | string | No | 기본 서버 시각 |
| corners | JSON string | Yes | `[[x,y],[x,y],[x,y],[x,y]]` 좌상→시계방향, 원본 픽셀 좌표 |

응답은 `/capture`와 같다.

### POST /incubation/{run_id}/finish

**Request:** `{ "reason": "plateau" | "user" | "max_days" }`

**Response:** `200 OK` — 최종 [IncubationRun](#incubationrun). `status: "finished"`,
`infection_rate`·`grade`·`recommendation` 고정.

### POST /incubation/{run_id}/events

장치 알림. `application/json`

```json
{ "type": "low_humidity", "at": "2026-08-24T13:00:00+09:00", "detail": { "rh": 82.1, "minutes": 65 } }
```

`type` ∈ `low_humidity` · `low_temp` · `high_temp` · `fault_sensor` · `fault_overheat` ·
`clock_unsynced` · `grid_failure`(서버 내부) · `power_restored`.

---

## Schemas

### IncubationRun

```json
{
  "id": "a1b2c3d4-…",
  "field_label": "윗밭",
  "crop_type": "고추",
  "device_id": "incubox-0001",
  "mode": "device",
  "status": "running",
  "sample_count": 24,
  "sampled_at": "2026-08-22T08:30:00+09:00",
  "started_at": "2026-08-22T09:10:00+09:00",
  "ended_at": null,
  "day": 3,
  "infection_rate": 0.125,
  "grade": "caution",
  "recommendation": {
    "grade": "caution",
    "title": "주의 — 강우 전 예방 살포가 필요합니다",
    "actions": [
      "비 오기 전에 등록 살균제를 살포하세요",
      "아래쪽 과실과 병든 과실을 제거해 밭 밖으로 내보내세요",
      "1~2주 뒤 같은 밭에서 다시 검사하세요"
    ],
    "pesticides": [ { "name": "…", "dilution": "…", "safety_notes": "…" } ],
    "caveat": "24개 표본 기준 95% 신뢰구간 약 ±13%p. 등급 경계 근처면 재검사로 확인하세요."
  },
  "plateau": false,
  "warnings": ["low_humidity"],
  "cells": [
    { "index": 0, "state": "healthy", "p_anthracnose": 0.04, "expressed_at_seq": null },
    { "index": 5, "state": "expressed", "p_anthracnose": 0.91, "expressed_at_seq": 6 },
    { "index": 9, "state": "suspect", "p_anthracnose": 0.55, "expressed_at_seq": null },
    { "index": 13, "state": "invalid", "p_anthracnose": null, "expressed_at_seq": null }
  ],
  "curve": [
    { "seq": 0, "captured_at": "…", "day": 0.0, "rate": 0.0 },
    { "seq": 6, "captured_at": "…", "day": 2.0, "rate": 0.083 },
    { "seq": 7, "captured_at": "…", "day": 2.25, "rate": 0.125 }
  ],
  "climate": [
    { "seq": 7, "temp_mean": 26.5, "temp_min": 25.6, "temp_max": 27.3, "rh_mean": 96.2, "heater_duty": 0.31 }
  ],
  "latest_image_url": "/uploads/incubation/a1b2…/0007_20260825T080012.jpg",
  "related_diagnoses": [ { "id": "3f9a…", "disease_name": "고추 탄저병", "created_at": "…" } ]
}
```

| 필드 | 값 |
|------|-----|
| `mode` | `device` / `manual` |
| `status` | `running` / `finished` / `aborted` |
| `grade` | `low` (0~5%) / `caution` (5~20%) / `high` (≥20%) / `null` (판정 전) |
| `cells[].state` | `healthy` / `suspect` / `expressed` / `invalid` |
| `related_diagnoses` | 같은 `field_label`의 최근 영상 진단 5건 |

`recommendation.pesticides`는 기존 `diseases.pesticides`(고추 탄저병, `model_class_id=0`)를
그대로 쓴다. 추천 로직은 추가하지 않는다.

## 오류 형식

기존과 동일: `{ "detail": "…" }`.
