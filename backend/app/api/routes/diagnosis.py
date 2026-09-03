from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.diagnosis import DiagnoseResponse, PaginatedHistory
from app.services import diagnosis_service

router = APIRouter()

# 상한 검사를 위해 조금씩 읽는다 — 큰 파일을 통째로 메모리에 올리지 않기 위함
_CHUNK_SIZE = 64 * 1024


async def _read_image_upload(file: UploadFile) -> bytes:
    """업로드를 검증하며 읽는다. 상한을 넘으면 다 읽기 전에 중단한다.

    현장에서 올라오는 스마트폰 사진이 수십 MB에 이를 수 있어, 요청 본문을
    통째로 메모리에 적재하지 않도록 청크 단위로 누적하며 상한을 확인한다.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    limit = settings.max_upload_bytes
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(_CHUNK_SIZE):
        size += len(chunk)
        if size > limit:
            raise HTTPException(
                status_code=413,
                detail=f"이미지는 {settings.max_upload_mb}MB 이하만 업로드할 수 있습니다.",
            )
        chunks.append(chunk)

    if size == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    content = b"".join(chunks)
    # Content-Type은 클라이언트가 정하는 값이라 신뢰할 수 없다. 실제로 열리는
    # 이미지인지 확인해 두지 않으면 추론 단계에서 500으로 터진다.
    try:
        Image.open(BytesIO(content)).verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다. 다른 사진으로 시도해 주세요.")

    return content


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    file: UploadFile = File(...),
    crop_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    content = await _read_image_upload(file)
    return diagnosis_service.diagnose_image(db, content, file.filename or "image.jpg", crop_type)


@router.post("/diagnose/{diagnosis_id}/refine", response_model=DiagnoseResponse)
async def refine(
    diagnosis_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """혼동쌍 판별부위 2차 촬영으로 진단을 재확정 (구성 E: 다시점 융합)."""
    content = await _read_image_upload(file)

    try:
        result = diagnosis_service.refine_diagnosis(
            db, diagnosis_id, content, file.filename or "image.jpg"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="진단 기록을 찾을 수 없습니다.")
    return result


@router.get("/history", response_model=PaginatedHistory)
def history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return diagnosis_service.get_history(db, page, size)


@router.get("/history/{diagnosis_id}", response_model=DiagnoseResponse)
def history_detail(diagnosis_id: str, db: Session = Depends(get_db)):
    result = diagnosis_service.get_diagnosis_detail(db, diagnosis_id)
    if not result:
        raise HTTPException(status_code=404, detail="진단 기록을 찾을 수 없습니다.")
    return result
