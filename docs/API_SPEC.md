# CropCare AI - API Specification

Base URL: `http://localhost:8000/api/v1`
정적 파일: `http://localhost:8000/uploads/{filename}` (진단 이미지)

프론트엔드는 `next.config.js`의 rewrite로 `/api/*`·`/uploads/*`를 백엔드로 프록시하므로,
브라우저에서는 동일 출처 상대경로로 호출한다.

대상 작물은 **고추·무·배추** 3종이며, 모델 클래스는 병해 6종 + 정상 3종으로 총 9개다.

## Endpoints

| Method | Path | 설명 |
|--------|------|------|
| POST | `/diagnose` | 이미지 진단 |
| POST | `/diagnose/{id}/refine` | 판별부위 2차 촬영으로 재확정 |
| GET | `/history` | 진단 이력 목록 |
| GET | `/history/{id}` | 진단 상세 |
| GET | `/diseases` | 병해 목록 (검색·필터) |
| GET | `/diseases/{id}` | 병해 상세 |
| GET | `/health` | 헬스체크 |

---

### POST /diagnose

병해 이미지 진단.

**Request:** `multipart/form-data`

| Field | In | Type | Required | 설명 |
|-------|-----|------|----------|------|
| file | body | image (jpg/png) | Yes | `Content-Type`이 `image/*`여야 한다 |
| crop_type | query | string | No | `고추` / `무` / `배추`. 생략 시 예측된 병해의 작물로 채운다 |

**Response:** `200 OK`

```json
{
  "id": "3f9a1c02-77b1-4e0a-9c31-8a5d2b6e4f10",
  "disease_name": "무 검은무늬병",
  "crop_type": "무",
  "category": "disease",
  "severity": "medium",
  "confidence": 0.46,
  "top_predictions": [
    { "name": "무 검은무늬병", "confidence": 0.46 },
    { "name": "무 노균병", "confidence": 0.41 },
    { "name": "배추 노균병", "confidence": 0.08 }
  ],
  "description": "잎에 동심원 무늬의 흑갈색 원형 반점이 생기고 병반 주위가 황변합니다. ...",
  "causes": ["고온다습과 잦은 강우", "연작 토양", "질소 부족으로 약해진 잎", "종자 감염"],
  "pesticides": [
    {
      "name": "마스터키 (가스가마이신.티플루자마이드 액상수화제)",
      "dilution": "2000배 -",
      "usage": "발병 초부터 경엽처리",
      "safety": { "phi_days": 14, "reentry_hours": null },
      "active_ingredient": "가스가마이신.티플루자마이드 액상수화제",
      "safety_notes": "안전사용기준: 수확14일전 / 사용횟수: 2회 이내"
    }
  ],
  "prevention": ["건전 종자 사용 및 종자 소독", "3년 이상 연작 회피", "균형 시비"],
  "image_url": "/uploads/3f9a1c02-....jpg",
  "refined_image_url": null,
  "created_at": "2026-07-02T12:00:00Z",
  "recapture": {
    "region": "잎 뒷면",
    "instruction": "잎을 뒤집어 병반이 있는 부위의 뒷면을 근접 촬영하세요.",
    "margin": 0.05,
    "candidates": [
      { "name": "무 노균병", "cue": "뒷면에 회백색 솜털 같은 곰팡이(포자층)가 보이면 노균병입니다." },
      { "name": "무 검은무늬병", "cue": "뒷면이 깨끗하고 앞면 병반이 동심원(과녁) 무늬면 검은무늬병입니다." }
    ]
  }
}
```

**필드 참고**

- `category`: `disease` | `normal` — `normal`은 병징이 없는 건전주 예측이며 `pesticides`가 비어 있다.
- `severity`: `low` | `medium` | `high`
- `refined_image_url`: 판별부위 2차 촬영으로 재확정한 경우 그 사진의 URL.
  재확정 전에는 `null`이다.
- `recapture`: **혼동쌍 유도촬영 지침.** 상위 두 후보가 사전 정의된 혼동쌍이고 신뢰도 마진이
  임계값(0.20) 미만일 때만 채워지고, 그 외에는 `null`이다. 자세한 동작은
  [MODEL_SPEC.md](MODEL_SPEC.md#혼동쌍-유도촬영)를 참고.

**Errors**

| Status | 조건 |
|--------|------|
| 400 | `Content-Type`이 이미지가 아님 / 빈 파일 / 이미지로 열리지 않는 파일 |
| 413 | 업로드 크기가 `MAX_UPLOAD_MB`(기본 10MB) 초과 |
| 422 | `file` 필드 누락 |

`Content-Type`은 클라이언트가 정하는 값이므로 신뢰하지 않고, 실제로 디코딩되는
이미지인지 확인한 뒤 저장한다. 크기 검사는 본문을 청크 단위로 읽으며 수행하므로
상한을 넘는 요청은 전부 읽기 전에 중단된다.

---

### POST /diagnose/{id}/refine

`recapture` 지침에 따라 촬영한 **판별부위 2차 사진**으로 진단을 재확정한다 (다시점 융합).

1차 사진과 2차 사진의 전체 클래스 분포를 가중 평균(2차 가중 0.6)하고,
혼동쌍 전용 분류기가 있고 1차 진단의 상위 두 후보가 그 분류기의 쌍일 때
쌍 내부의 상대 비중을 재분배한다. 합계 질량은 보존되므로 쌍 밖 클래스는 영향받지 않는다.

**Request:** `multipart/form-data` — `file` (image), 경로 파라미터 `id`는 1차 진단 ID.

**Response:** `200 OK` — `/diagnose`와 동일한 스키마. 단 `recapture`는 항상 `null`이다
(재확정 결과에는 추가 유도를 하지 않는다).

기존 진단 레코드의 `disease_id` · `confidence` · `top_predictions` ·
`refined_image_path`가 **갱신**되며, 새 레코드가 생기지 않는다.
따라서 `/history/{id}`는 재확정 결과와 2차 사진 URL을 함께 반환한다.
`image_url`은 1차 사진을 그대로 가리킨다.

**Errors**

| Status | 조건 |
|--------|------|
| 400 | 이미지가 아님 / 빈 파일 / 디코딩 불가 / 원본 진단 이미지가 디스크에 없음 |
| 413 | 업로드 크기가 `MAX_UPLOAD_MB` 초과 |
| 404 | 해당 `id`의 진단 기록 없음 |

---

### GET /history

진단 이력 목록 (최신순).

**Query:** `page` (기본 1, ≥1), `size` (기본 20, 1~100)

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "3f9a1c02-...",
      "disease_name": "무 검은무늬병",
      "confidence": 0.46,
      "crop_type": "무",
      "image_url": "/uploads/3f9a1c02-....jpg",
      "created_at": "2026-07-02T12:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "size": 20
}
```

**Errors:** `422` — `page < 1` 또는 `size > 100`

---

### GET /history/{id}

진단 상세. `/diagnose`와 동일한 스키마이며 `recapture`는 포함되지 않는다.

**Errors:** `404` — 기록 없음

---

### GET /diseases

병해 목록 (검색·필터).

**Query:** `q` (병해명 부분일치), `crop_type` (정확일치: `고추` / `무` / `배추`)

**Response:** `200 OK` — `DiseaseDetail` 배열

```json
[
  {
    "id": 3,
    "name": "무 검은무늬병",
    "name_en": "Radish Alternaria Black Spot",
    "crop_type": "무",
    "category": "disease",
    "description": "잎에 동심원 무늬의 흑갈색 원형 반점이 생기고 ...",
    "causes": ["고온다습과 잦은 강우", "연작 토양"],
    "prevention": ["건전 종자 사용 및 종자 소독", "3년 이상 연작 회피"],
    "severity": "medium",
    "pesticides": [ { "name": "마스터키 (...)", "dilution": "2000배 -", "...": "..." } ]
  }
]
```

---

### GET /diseases/{id}

병해 상세 (설명, 원인, 예방, 연관 농약). `id`는 DB PK이며 모델 클래스 ID와 다르다.

**Errors:** `404` — 해당 병해 없음

---

### GET /health

헬스체크.

```json
{ "status": "ok", "model_loaded": true, "version": "1.0.0" }
```

`model_loaded`가 `false`면 체크포인트를 찾지 못해 **Mock 모드**로 동작 중이며,
`/diagnose`는 고정된 샘플 분포를 반환한다.
