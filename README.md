# CropCare AI

**AI 기반 농작물 병해충 진단 및 스마트 방제 지원 플랫폼**

Version 1.0 · Author: 김헌영

## 기능

- 📷 사진 업로드 → CNN 기반 병해충 진단
- 📊 신뢰도 및 Top-N 예측 제공
- 🔍 혼동되는 두 병해가 접전이면 판별부위(예: 잎 뒷면) 재촬영을 유도하고 결과를 재확정
- 📋 병 설명, 발병 원인, 예방 방법
- 💊 등록 농약 추천 (희석비, 사용법, 안전사용기준)
- 📁 진단 이력 저장 및 조회

## 프로젝트 구조

```
cropy/
├── docs/          # PRD, Architecture, API, DB, Model 스펙
├── backend/       # FastAPI REST API
├── frontend/      # Next.js 웹 앱
├── ml/            # PyTorch 학습·추론
└── data/          # 데이터셋 (학습용)
```

## 빠른 시작

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

웹 앱: http://localhost:3000

### 3. ML 모델 학습 (선택)

```bash
cd ml
pip install -r requirements.txt
python train.py --data-dir ../data/dataset --epochs 20 --arch resnet50
```

학습된 모델은 `ml/checkpoints/best_model.pth`에 저장됩니다.  
모델이 없으면 Backend는 **Mock 모드**로 샘플 진단 결과를 반환합니다.

- `--arch resnet18|resnet50`: 백본 선택 (체크포인트에 기록되어 백엔드/평가 스크립트가 자동 인식)
- `--resume <checkpoint>`: 기존 체크포인트에서 이어 학습 (현재 val 정확도보다 좋아질 때만 저장)
- `python evaluate.py`: test 분할로 전체/클래스별 정확도와 혼동행렬 출력
- GPU 학습(Colab): `python pack_for_colab.py`로 `colab_bundle.zip` 생성 → `train_colab.ipynb`를 Colab에서 실행

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/diagnose` | 이미지 진단 |
| POST | `/api/v1/diagnose/{id}/refine` | 판별부위 2차 촬영으로 재확정 |
| GET | `/api/v1/history` | 진단 이력 |
| GET | `/api/v1/history/{id}` | 진단 상세 |
| GET | `/api/v1/diseases` | 병해충 목록 |
| GET | `/api/v1/health` | 헬스체크 |

자세한 스펙은 [docs/API_SPEC.md](docs/API_SPEC.md) 참고.

## 문서

- [PRD](docs/PRD.md) - 제품 요구사항
- [Architecture](docs/ARCHITECTURE.md) - 시스템 구조
- [API Spec](docs/API_SPEC.md) - REST API
- [Database](docs/DATABASE.md) - DB 스키마
- [Model Spec](docs/MODEL_SPEC.md) - CNN 모델

### 인큐박스 (잠복감염 검사기, 기획 단계 · 비공개)

- [기획안](docs/INCUBOX_PLAN.md) - 왜·무엇·로드맵 (시작점)
- [검정 절차서](docs/INCUBOX_PROTOCOL.md) - 채취·소독·배양·판독 SOP, [기록지](docs/templates/incubox_record_sheet.md)
- [하드웨어](docs/INCUBOX_HARDWARE.md) - 챔버·트레이·카메라·전기·BOM
- [펌웨어](docs/INCUBOX_FIRMWARE.md) - 장치 상태기계·촬영·온습도·업로드 큐
- [API](docs/INCUBOX_API_SPEC.md) · [DB](docs/INCUBOX_DATABASE.md) · [파이프라인](docs/INCUBOX_PIPELINE.md) - 백엔드 확장
- [UI](docs/INCUBOX_UI_SPEC.md) - 앱 화면
- [검증 계획](docs/INCUBOX_VALIDATION.md) - Phase 0~3 지표·통과 기준·일정
- [발명신고서](docs/INCUBOX_INVENTION.md) - 청구항 초안·선행기술·출원 체크리스트

## 기술 스택

- **Frontend:** Next.js 15, TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, SQLite
- **ML:** PyTorch, ResNet50 (AI Hub 노지 작물 질병 진단 데이터셋)

9개 클래스(고추·무·배추 병해 6종 + 정상 3종) 기준 실측 정확도는
val 94.7% / test 93.1%입니다. 자세한 내용은 [MODEL_SPEC](docs/MODEL_SPEC.md) 참고.

## 배포 (Docker)

```bash
docker compose up -d --build   # → http://localhost:3000
```

브라우저는 프론트엔드 오리진 하나만 호출합니다. `/api`와 `/uploads`는 Next.js
rewrite가 backend 컨테이너로 프록시하므로 백엔드 포트를 외부에 열 필요도,
CORS를 설정할 필요도 없습니다.

**체크포인트는 별도로 준비해야 합니다.** `ml/checkpoints/`가 `/models`로 마운트되며,
`best_model.pth`가 없으면 백엔드는 Mock 모드로 뜹니다. 확인:

```bash
curl http://localhost:3000/api/v1/health   # model_loaded 가 true 여야 정상
```

진단 이력(SQLite)과 업로드 이미지는 `cropcare-data` 볼륨에 남아 컨테이너를
다시 만들어도 보존됩니다.

### 다른 도메인에 배포할 때

`BACKEND_ORIGIN`은 **빌드 시점**에 주입됩니다. Next.js standalone 산출물은
rewrite 목적지를 빌드 때 굳혀 넣으므로 런타임 환경변수로는 바뀌지 않습니다.
값을 바꾸려면 다시 빌드하세요.

```bash
docker compose build --build-arg BACKEND_ORIGIN=https://api.example.com frontend
```

프론트와 백엔드를 서로 다른 도메인에 올려 브라우저가 백엔드를 직접 호출하게 하려면,
백엔드의 `CORS_ORIGINS`를 프론트 도메인으로 바꾸고 프론트는 HTTPS/HTTP가 섞이지
않도록 맞춰야 합니다.

## 테스트

```bash
cd backend
.venv\Scripts\python -m pytest tests
```

학습된 체크포인트는 저장소에 포함되지 않으므로(`.gitignore`), 클린 클론이나 CI에서는
Mock 모드로 동작합니다. 테스트는 체크포인트 유무와 무관하게 통과합니다.

## 농약 데이터 동기화 (PSIS)

농약 추천 데이터는 농촌진흥청 PSIS OpenAPI의 등록 농약 정보를 사용합니다.

```bash
cd backend
.venv\Scripts\python scripts/sync_pesticides.py --api-key <PSIS_API_KEY>
```

API 키는 [PSIS OpenAPI 신청](https://psis.rda.go.kr/psis/share/api/apiReqstAddForm.ps?menuId=PS00383)에서 발급받습니다. 실행 후 백엔드를 재시작하면 DB에 반영됩니다.

## 다음 단계

1. 사용자 인증 및 농장별 이력 관리
