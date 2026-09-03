"""CNN 추론 서비스.

학습된 체크포인트(ml/checkpoints/best_model.pth)가 있으면 실제 추론을,
없거나 torch 미설치 시 mock 예측을 반환한다.

체크포인트의 classes는 ImageFolder 정렬 순서("0_고추탄저병" ...)이며,
폴더명 앞 숫자 = model_class_id = 예측 인덱스가 되도록 데이터가 구성되어 있다.
"""

from functools import lru_cache
from pathlib import Path

from app.core.config import settings

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# 체크포인트가 없을 때 사용하는 mock 예측
_MOCK_PREDICTIONS: list[tuple[int, float]] = [(0, 0.87), (1, 0.08), (2, 0.03)]


def _model_path() -> Path:
    model_path = settings.ml_model_path
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parent.parent.parent / model_path
    return model_path


@lru_cache(maxsize=1)
def _load_model():
    """체크포인트를 로드해 (model, class_ids, device)를 캐시한다. 실패 시 None."""
    path = _model_path()
    if not path.exists():
        return None
    try:
        import torch
        from torchvision import models

        device = "cuda" if torch.cuda.is_available() else "cpu"
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        num_classes = checkpoint["num_classes"]

        arch = checkpoint.get("arch", "resnet18")
        model = getattr(models, arch)(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        # 폴더명("2_무검은무늬병")의 앞 숫자를 model_class_id로 사용
        class_ids: list[int] = []
        for idx, name in enumerate(checkpoint.get("classes", [])):
            head = str(name).split("_", 1)[0]
            class_ids.append(int(head) if head.isdigit() else idx)

        # 추론 해상도는 학습 해상도와 일치시킨다(구 체크포인트는 224)
        img_size = int(checkpoint.get("img_size", 224))

        return model, class_ids, device, img_size
    except Exception:
        return None


@lru_cache(maxsize=1)
def _load_pair_model():
    """혼동쌍 전용 2-클래스 분류기(pair_mu.pth)를 로드해 캐시한다. 없으면 None.

    폴더명 앞 숫자로 model_class_id를 파싱하므로 클래스는 예: '2_black','3_downy'.
    """
    path = _model_path().parent / "pair_mu.pth"
    if not path.exists():
        return None
    try:
        import torch
        from torchvision import models

        device = "cuda" if torch.cuda.is_available() else "cpu"
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        arch = checkpoint.get("arch", "resnet18")
        model = getattr(models, arch)(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, checkpoint["num_classes"])
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        class_ids = [int(str(n).split("_", 1)[0]) for n in checkpoint.get("classes", [])]
        img_size = int(checkpoint.get("img_size", 224))
        return model, class_ids, device, img_size
    except Exception:
        return None


def load_model() -> None:
    """앱 시작 시 모델 캐시를 예열한다(체크포인트 없으면 무동작)."""
    _load_model()
    _load_pair_model()


def is_model_loaded() -> bool:
    return _load_model() is not None


def _transform(img_size: int = 224):
    from torchvision import transforms

    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def predict_all(image_path: Path) -> list[tuple[int, float]]:
    """모든 클래스의 (model_class_id, confidence)를 confidence 내림차순으로 반환.

    다시점 융합(구성 E)에서 두 촬영의 전체 분포가 필요하므로 top_k로 자르지 않는다.
    체크포인트/torch 없으면 mock 분포로 폴백.
    """
    loaded = _load_model()
    if loaded is None:
        return _MOCK_PREDICTIONS

    import torch
    import torch.nn.functional as F
    from PIL import Image

    model, class_ids, device, img_size = loaded
    image = Image.open(image_path).convert("RGB")
    tensor = _transform(img_size)(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = F.softmax(model(tensor), dim=1)[0]

    pairs = [(class_ids[i], probs[i].item()) for i in range(len(class_ids))]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs


def predict(image_path: Path, top_k: int = 3) -> list[tuple[int, float]]:
    """(model_class_id, confidence) 리스트를 confidence 내림차순으로 top_k개 반환."""
    return predict_all(image_path)[:top_k]


def predict_pair(image_path: Path) -> dict[int, float] | None:
    """혼동쌍 전용 분류기로 추론해 {model_class_id: prob}를 반환. 모델 없으면 None."""
    loaded = _load_pair_model()
    if loaded is None:
        return None

    import torch
    import torch.nn.functional as F
    from PIL import Image

    model, class_ids, device, img_size = loaded
    image = Image.open(image_path).convert("RGB")
    tensor = _transform(img_size)(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = F.softmax(model(tensor), dim=1)[0]

    return {class_ids[i]: probs[i].item() for i in range(len(class_ids))}
