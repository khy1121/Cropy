"""CropCare AI - CNN 추론 모듈"""

from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def get_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def load_model(checkpoint_path: Path, device: str | None = None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    num_classes = checkpoint["num_classes"]
    arch = checkpoint.get("arch", "resnet18")
    model = getattr(models, arch)(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    return model, checkpoint.get("classes", []), device


def predict(image_path: Path, checkpoint_path: Path, top_k: int = 3) -> list[tuple[int, float]]:
    model, classes, device = load_model(checkpoint_path)
    image = Image.open(image_path).convert("RGB")
    tensor = get_transform()(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = F.softmax(outputs, dim=1)[0]

    top_probs, top_indices = probs.topk(min(top_k, len(classes)))
    return [(idx.item(), prob.item()) for idx, prob in zip(top_indices, top_probs)]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python predict.py <image_path> <checkpoint_path>")
        sys.exit(1)
    results = predict(Path(sys.argv[1]), Path(sys.argv[2]))
    for idx, conf in results:
        print(f"class_id={idx}, confidence={conf:.4f}")
