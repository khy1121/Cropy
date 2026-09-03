# CropCare AI - Architecture

## 시스템 구성

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  ML Engine  │
│  (Next.js)  │     │  (FastAPI)  │     │  (PyTorch)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │  (SQLAlch.) │
                    └─────────────┘
```

ML 엔진은 별도 프로세스가 아니라 백엔드 프로세스 안에서 동작한다.
`app/services/ml_service.py`가 체크포인트를 `lru_cache`로 한 번만 로드해 상주시키고,
앱 시작(lifespan) 때 예열한다. 체크포인트가 없으면 고정 분포를 반환하는
**Mock 모드**로 떨어져 ML 없이도 전 구간 개발·테스트가 가능하다.

개발 환경에서 프론트엔드는 `next.config.js`의 rewrite로 `/api/*`와 `/uploads/*`를
`localhost:8000`으로 프록시한다. 브라우저는 동일 출처로만 통신한다.

## 디렉터리 구조

```
cropy/
├── docs/                 # 프로젝트 문서
├── backend/              # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/   # diagnosis, diseases, health
│   │   ├── core/         # 설정(pydantic-settings), DB 엔진·세션
│   │   ├── models/       # SQLAlchemy 엔티티
│   │   ├── schemas/      # Pydantic 스키마
│   │   ├── services/     # 진단·추론·유도촬영·시딩 로직
│   │   └── data/seed/    # 병해·농약 시드 JSON
│   ├── scripts/          # sync_pesticides.py (PSIS 동기화)
│   └── tests/            # pytest (API 스모크 + 유도촬영 단위)
├── frontend/             # Next.js 웹 앱 (App Router)
│   └── src/
│       ├── app/          # 라우트: / , /history , /history/[id]
│       ├── components/   # DiagnoseForm, DiagnosisResult, RecapturePanel …
│       ├── lib/api.ts    # 백엔드 호출
│       └── types/        # 백엔드 스키마와 대응하는 TS 타입
├── ml/                   # CNN 학습·평가·추론
│   ├── prepare_dataset.py    # AI Hub 원천 → ImageFolder 9클래스
│   ├── prepare_pair.py       # 무 혼동쌍 2클래스 데이터셋
│   ├── train.py / evaluate.py / predict.py
│   └── checkpoints/          # *.pth (git 제외)
├── data/                 # 원천·가공 데이터셋 (git 제외)
└── docker-compose.yml    # 백엔드 + 프론트 단일 호스트 배포
```

## 배포 구성

`docker-compose.yml`은 두 컨테이너를 띄우고 프론트엔드 포트만 외부에 노출한다.

```
브라우저 ──▶ frontend:3000 ──(rewrite)──▶ backend:8000
                                             │
                            /models (ro)  ───┤  체크포인트 (호스트 마운트)
                            /data (volume) ──┘  SQLite + 업로드 이미지
```

브라우저가 백엔드를 직접 호출하지 않으므로 CORS 설정이 필요 없고, API가 반환하는
`/uploads/...` 상대경로 이미지도 같은 오리진에서 해결된다.

`BACKEND_ORIGIN`은 런타임이 아니라 **빌드 인자**다. Next.js standalone 산출물은
`next.config.js`를 포함하지 않고 rewrite 목적지를 빌드 시점에 굳혀 넣기 때문에,
환경변수로 주면 조용히 무시된다.

## 기술 스택

| 계층 | 기술 |
|------|------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 3, Iconify(Lucide) |
| Backend | FastAPI 0.115, SQLAlchemy 2.0, Pydantic v2 |
| ML | PyTorch, torchvision — ResNet50 fine-tune (9클래스) + ResNet18 혼동쌍 분류기 |
| Database | SQLite (개발), PostgreSQL (운영 상정) |
| Storage | 로컬 파일 시스템 — `backend/uploads/`, `StaticFiles`로 서빙 |

## 데이터 흐름

### 1차 진단

1. Frontend → `POST /api/v1/diagnose` (multipart image)
2. `uploads/{uuid}.jpg`로 저장
3. ML 추론 → 클래스별 softmax → 상위 3개 `(model_class_id, confidence)`
4. `model_class_id`로 `diseases` 조인 → 병해 설명·원인·예방·연관 농약 조회
5. **유도촬영 판정**: 상위 두 후보가 사전 정의된 혼동쌍이고 마진 < 0.20이면
   판별부위 재촬영 지침(`recapture`)을 응답에 동봉
6. `diagnoses` 테이블에 이력 저장 → 통합 결과 JSON 반환

### 재확정 (유도촬영이 발동한 경우)

7. 사용자가 지정된 부위를 촬영 → `POST /api/v1/diagnose/{id}/refine`
8. 1차·2차 사진의 **전체 클래스 분포**를 각각 추론
9. 가중 평균으로 융합 (2차 촬영 가중 0.6 — 표적 부위이므로 더 신뢰)
10. 혼동쌍 전용 분류기가 있고 1차 상위 두 후보가 그 쌍이면, 쌍 내부 비중만 재분배
    (합계 질량 보존 → 쌍 밖 클래스는 영향 없음)
11. 기존 `diagnoses` 행을 갱신하고 재확정 결과 반환

유도촬영·융합의 상세 설계와 실측 근거는 [MODEL_SPEC.md](MODEL_SPEC.md)를 참고.

## 외부 연동

- **농약안전정보시스템(PSIS) OpenAPI** — 구현 완료.
  `backend/scripts/sync_pesticides.py`가 작물×병해별 등록 농약을 조회해
  시드 JSON을 재생성한다. 농약 추천은 학습 문제가 아니라 법적 등재 정보의
  조회 문제이므로 모델이 아닌 공공데이터로 해결한다.
- 농촌진흥청 작물병해충 정보 — 미연동. 현재 병해 설명·원인·예방은 수기 시드 데이터다.

## 알려진 구조적 제약

- **인증 없음.** 진단 이력이 전역 공유된다 (사용자·농장 개념 Phase 2).
- **마이그레이션 도구 없음.** `create_all()`로 스키마를 만들고, 추가된 칼럼만
  `ensure_columns()`가 보완한다 (칼럼 삭제·타입 변경은 미지원).
  시드 데이터는 매 기동마다 JSON을 목표 상태로 동기화한다
  ([DATABASE.md](DATABASE.md#seed-data) 참고).
- **업로드 정리 없음.** `uploads/`가 무한히 증가한다. 업로드 크기는
  `MAX_UPLOAD_MB`(기본 10MB)로 제한되고 2차 촬영 사진도 DB에 기록되지만,
  오래된 파일을 정리하는 절차는 없다.
- **단일 프로세스 전제.** 모델을 프로세스 메모리에 상주시키므로 워커를 늘리면
  워커 수만큼 메모리를 쓴다 (ResNet50 기준 체크포인트 94MB).
