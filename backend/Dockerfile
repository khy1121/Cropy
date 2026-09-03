# CropCare AI - Backend (FastAPI + PyTorch CPU 추론)
#
# 학습된 체크포인트(*.pth)는 저장소에 없고 이미지에도 굽지 않는다.
# docker-compose가 ml/checkpoints를 /models로 마운트하며, 없으면 백엔드는
# Mock 모드로 뜬다 (GET /api/v1/health 의 model_loaded 로 확인).

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성을 먼저 설치해 코드 변경 시 torch 재설치를 피한다 (레이어 캐시)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# SQLite 파일과 업로드 이미지는 볼륨으로 분리한다 (컨테이너 재생성 시 보존)
ENV DATABASE_URL=sqlite:////data/cropcare.db \
    UPLOAD_DIR=/data/uploads \
    ML_MODEL_PATH=/models/best_model.pth
RUN mkdir -p /data/uploads /models

EXPOSE 8000

# 워커를 늘리면 워커 수만큼 모델이 메모리에 복제된다. 기본은 단일 워커.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
