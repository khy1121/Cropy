"""테스트 공용 픽스처: 임시 DB/업로드 디렉터리로 앱을 띄운 TestClient."""

import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="cropcare-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(Path(_tmp) / "uploads")
# 상한 초과 케이스를 저렴하게 만들기 위해 테스트에서는 1MB로 낮춘다
os.environ["MAX_UPLOAD_MB"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _jpeg(size: int = 224, color: tuple[int, int, int] = (120, 160, 80)) -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (size, size), color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def model_available() -> bool:
    """학습된 체크포인트가 실제로 로드되었는지.

    ml/checkpoints/*.pth는 저장소에 포함되지 않으므로(.gitignore), 클린 클론이나
    CI에서는 Mock 모드로 동작한다. 테스트는 어느 쪽에서도 통과해야 한다.
    """
    from app.services.ml_service import is_model_loaded

    return is_model_loaded()


@pytest.fixture(scope="session")
def sample_image() -> bytes:
    return _jpeg()


@pytest.fixture(scope="session")
def second_image() -> bytes:
    """재확정용 2차 촬영 사진 (1차와 구분되도록 색을 달리한다)."""
    return _jpeg(color=(80, 110, 60))


@pytest.fixture(scope="session")
def oversized_image() -> bytes:
    """MAX_UPLOAD_MB(테스트에선 1MB)를 넘는 실제 JPEG."""
    from io import BytesIO
    import random

    from PIL import Image

    # 단색은 과하게 압축되므로 노이즈로 채워 압축을 방해한다
    rng = random.Random(0)
    img = Image.new("RGB", (2200, 2200))
    img.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                 for _ in range(2200 * 2200)])
    buf = BytesIO()
    img.save(buf, "JPEG", quality=100)
    data = buf.getvalue()
    assert len(data) > 1024 * 1024, f"픽스처가 상한을 넘지 못함: {len(data)}"
    return data
