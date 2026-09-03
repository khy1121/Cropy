# CropCare AI 기술 스택

> AI 기반 농작물 병해충 진단 및 스마트 방제 지원 플랫폼에서 사용하는 기술을 계층별로 정리한 문서입니다.
> 버전은 `backend/requirements.txt`, `frontend/package.json`, `ml/requirements.txt` 기준입니다.

## 한눈에 보기

| 계층 | 기술 | 버전 | 역할 |
|------|------|------|------|
| 프론트엔드 | Next.js (React) | 15.x (React 19) | 모바일 퍼스트 웹 앱 |
| 스타일링 | Tailwind CSS | 3.4.x | 당근마켓풍 브라운/카키/옐로 디자인 시스템 |
| 백엔드 | FastAPI | 0.115.x | REST API 서버 |
| DB | SQLite + SQLAlchemy | 2.0.x (ORM) | 진단 이력·병해·농약 데이터 저장 |
| AI/ML | PyTorch + torchvision | 2.12.x (+cpu) | ResNet50 기반 9클래스 병해 분류 |
| 배포 | Docker Compose | - | 백엔드 + 프론트 단일 호스트 배포 |
| 언어 | TypeScript / Python | 5.7 / 3.13 | 프론트 / 백엔드·ML |

---

## 1. 프론트엔드 (`frontend/`)

**Next.js 15 + React 19 + TypeScript** 조합의 웹 앱입니다. 스마트폰으로 밭에서 바로 사진을 찍어 올리는 사용 흐름에 맞춰 **모바일 퍼스트**로 설계했습니다.

| 기술 | 버전 | 왜 쓰는가 |
|------|------|-----------|
| [Next.js](https://nextjs.org) | ^15.1 | React 프레임워크. App Router 사용, `output: "standalone"`으로 Docker 이미지를 최소화 |
| React | ^19.0 | UI 컴포넌트 라이브러리 |
| TypeScript | ^5.7 | 정적 타입으로 API 응답 타입(`src/types/diagnosis.ts`) 안전하게 관리 |
| Tailwind CSS | ^3.4 | 유틸리티 클래스 기반 스타일링. 브라운/카키/옐로 토큰으로 서비스 아이덴티티 구현 |
| @iconify/tailwind + Lucide | ^1.2 | 아이콘을 CSS 클래스로 사용 (별도 아이콘 컴포넌트 불필요) |
| PostCSS + Autoprefixer | - | Tailwind 빌드 파이프라인 |

### 구조

```
frontend/src/
├── app/              # App Router 페이지 (홈=진단, history=이력)
├── components/       # AppBar, BottomNav, DiagnoseForm,
│                     # DiagnosisResult, RecapturePanel, TextSizeToggle
├── lib/api.ts        # 백엔드 API 호출 래퍼
└── types/            # API 응답 타입 정의
```

### 핵심 설계: API 프록시 (rewrites)

브라우저는 **프론트엔드 오리진 하나만** 호출합니다. `next.config.js`의 rewrite가 `/api/*`와 `/uploads/*`를 백엔드로 프록시하므로:

- **CORS 설정이 필요 없음** — 브라우저 입장에선 같은 오리진
- 백엔드 포트를 외부에 열 필요 없음
- 주의: `localhost` 대신 `127.0.0.1`을 명시 (Node가 localhost를 IPv6로 먼저 해석해 uvicorn 연결이 실패하는 문제 회피)

---

## 2. 백엔드 (`backend/`)

**FastAPI + Python 3.13** REST API 서버입니다. 이미지 업로드를 받아 ML 추론을 수행하고, 병해 정보·농약 추천·진단 이력을 제공합니다.

| 기술 | 버전 | 왜 쓰는가 |
|------|------|-----------|
| [FastAPI](https://fastapi.tiangolo.com) | 0.115.6 | 비동기 REST API 프레임워크. `/docs`에서 Swagger 문서 자동 생성 |
| Uvicorn | 0.34.0 | ASGI 서버 (프로덕션에서도 단일 워커 — 워커마다 모델이 메모리에 복제되기 때문) |
| SQLAlchemy | 2.0.36 | ORM. 진단 이력, 병해, 농약 테이블 관리 |
| SQLite | - | 파일 기반 DB. 단일 호스트 규모에 충분하고 운영 부담 zero |
| Pydantic (+settings) | 2.10 / 2.7 | 요청·응답 스키마 검증, 환경변수 기반 설정(`core/config.py`) |
| Pillow | 11.0.0 | 업로드 이미지 검증·전처리 |
| python-multipart | 0.0.20 | 이미지 파일 업로드(multipart/form-data) 파싱 |
| aiofiles | 24.1.0 | 업로드 파일 비동기 저장 |
| httpx | 0.28.1 | PSIS(농약안전정보시스템) API 동기화 스크립트(`scripts/sync_pesticides.py`)에서 사용 |
| pytest | 9.1.1 | 테스트 (`backend/tests/`) |

### 구조 (계층형 아키텍처)

```
backend/app/
├── main.py           # 앱 진입점
├── api/routes/       # 엔드포인트 (diagnose, history, diseases, health …)
├── services/         # 비즈니스 로직
│   ├── ml_service.py        # 모델 로드·추론 (체크포인트 없으면 Mock 모드)
│   ├── diagnosis_service.py # 진단 처리·이력 저장
│   ├── recapture.py         # 혼동쌍 접전 시 판별부위 재촬영 유도 (특허 출원 대상)
│   └── seed.py              # 병해·농약 시드 데이터
├── models/           # SQLAlchemy 모델
├── schemas/          # Pydantic 스키마
└── core/             # 설정, DB 세션
```

### 주요 API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/diagnose` | 이미지 진단 |
| POST | `/api/v1/diagnose/{id}/refine` | 판별부위 2차 촬영으로 재확정 |
| GET | `/api/v1/history`, `/history/{id}` | 진단 이력 |
| GET | `/api/v1/diseases` | 병해충 목록 |
| GET | `/api/v1/health` | 헬스체크 (`model_loaded`로 Mock 모드 여부 확인) |

---

## 3. AI / ML (`ml/`)

**PyTorch** 기반 이미지 분류 파이프라인입니다.

| 기술 | 버전 | 왜 쓰는가 |
|------|------|-----------|
| PyTorch | 2.12.1+cpu (서빙) / ≥2.6 (학습) | 딥러닝 프레임워크 |
| torchvision | 0.27.1+cpu | 사전학습 ResNet 백본, 이미지 변환 |
| NumPy | ≥2.1 | 수치 연산 |

### 모델

- **ResNet50** 전이학습, **9클래스** — 고추·무·배추 3작물 × (병해 + 정상)
- 성능: **val 96.2% / test 93.1%**
- 학습은 **Google Colab GPU**에서 (`pack_for_colab.py` → `train_colab.ipynb`), 서빙은 **CPU 추론**
- 백엔드는 CUDA 없는 `+cpu` 휠 사용 → Docker 이미지 약 200MB (CUDA 빌드는 2GB+)
- 체크포인트에 백본 정보가 기록되어 백엔드가 resnet18/50을 자동 인식

### 스크립트

| 파일 | 역할 |
|------|------|
| `train.py` | 학습 (`--arch`, `--resume` 지원, val 정확도 개선 시에만 저장) |
| `evaluate.py` | test 분할 정확도·혼동행렬 |
| `predict.py` | 단건 추론 |
| `prepare_dataset.py` / `prepare_pair.py` | 데이터셋 분할 / 혼동쌍 통계(`pair_mu.pth`) 생성 |
| `pack_for_colab.py` | Colab 학습 번들 생성 |

체크포인트(`ml/checkpoints/*.pth`)는 **저장소에 포함하지 않으며**, 없으면 백엔드가 자동으로 **Mock 모드**로 동작합니다.

---

## 4. 데이터 & 외부 연동

| 항목 | 기술 |
|------|------|
| 진단 이력·병해·농약 DB | SQLite (`cropcare.db`) |
| 업로드 이미지 | 로컬 파일시스템 (`uploads/`, Docker에선 볼륨) |
| 농약 데이터 | **PSIS(농약안전정보시스템) OpenAPI** — `sync_pesticides.py`로 등록농약 시드 갱신 (API 키 필요) |

---

## 5. 배포 (Docker)

```
docker compose up -d --build   →   http://localhost:3000
```

| 항목 | 내용 |
|------|------|
| 백엔드 이미지 | `python:3.13-slim` + CPU 전용 torch |
| 프론트 이미지 | `node:22-alpine` 멀티스테이지 빌드 (deps → builder → runner), Next.js standalone 출력 |
| 네트워크 | 백엔드는 `expose`만 (외부 미노출), 프론트만 3000 포트 공개 |
| 영속화 | `cropcare-data` 볼륨에 SQLite + 업로드 이미지, `ml/checkpoints`는 읽기전용 마운트 |
| 헬스체크 | `/api/v1/health` 30초 간격 (첫 기동 시 모델 로드 대기 60초) |

⚠️ **주의**: `BACKEND_ORIGIN`은 **빌드 시점** 인자(build args)입니다. Next.js standalone이 rewrite 목적지를 빌드 산출물에 굳혀 넣기 때문에 런타임 환경변수로는 바꿀 수 없고, 변경 시 `docker compose up -d --build`로 재빌드해야 합니다.

### 로컬 개발 실행

```bash
# Backend
cd backend && .venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev   # http://localhost:3000
```

---

## 6. 기술 선택 이유 요약

- **Next.js rewrite 프록시** → CORS 제거, 단일 오리진, 백엔드 비노출
- **SQLite** → 단일 호스트 MVP에 서버 DB 운영 부담 없이 충분
- **CPU 전용 torch 휠** → 추론만 하므로 이미지 크기 1/10로 절감
- **Colab 학습 / 로컬 CPU 서빙 분리** → GPU 비용 없이 학습·서빙 모두 해결
- **Mock 모드** → 체크포인트 없이도 전체 스택 개발·테스트 가능
