"""
CropCare AI - 테스트셋 평가

학습에 사용하지 않은 data/dataset/test 로 최종 성능을 측정한다.
전체 정확도, 클래스별 정확도, 혼동행렬을 출력한다.

--tta 를 주면 원본 + 좌우반전 로짓을 평균하는 테스트타임 증강으로 평가한다
(학습 없이 소폭의 정확도 향상, 추론과 동일한 방식으로 배포하려면 ml_service도 맞춤).

Usage:
    python evaluate.py --data-dir ../data/dataset --checkpoint checkpoints/best_model.pth [--tta]
"""

import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/dataset")
    parser.add_argument("--checkpoint", default="checkpoints/best_model.pth")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--split", default="test")
    parser.add_argument("--tta", action="store_true", help="원본+좌우반전 로짓 평균")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    num_classes = ckpt["num_classes"]

    arch = ckpt.get("arch", "resnet18")
    model = getattr(models, arch)(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()

    img_size = int(ckpt.get("img_size", 224))  # 추론 해상도는 학습과 일치
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    ds = datasets.ImageFolder(str(Path(args.data_dir) / args.split), transform=tf)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    classes = ds.classes

    n = len(classes)
    confusion = [[0] * n for _ in range(n)]
    correct = total = 0

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            logits = model(images)
            if args.tta:
                logits = logits + model(torch.flip(images, dims=[3]))
            preds = F.softmax(logits, dim=1).argmax(1).cpu()
            for t, p in zip(labels.tolist(), preds.tolist()):
                confusion[t][p] += 1
                total += 1
                correct += int(t == p)

    mode = "TTA(flip)" if args.tta else "single"
    print(f"Device: {device} | test images: {total} | classes: {n} | img_size: {img_size} | mode: {mode}\n")
    print(f"{'class':<18} {'acc':>6} {'n':>5}")
    print("-" * 32)
    for i, name in enumerate(classes):
        row_total = sum(confusion[i])
        acc = 100.0 * confusion[i][i] / row_total if row_total else 0.0
        print(f"{name:<18} {acc:>5.1f}% {row_total:>5}")
    print("-" * 32)
    print(f"{'OVERALL':<18} {100.0 * correct / total:>5.1f}% {total:>5}\n")

    header = "T\\P  " + " ".join(f"{i:>4}" for i in range(n))
    print("혼동행렬 (행=실제, 열=예측)")
    print(header)
    for i in range(n):
        print(f"{i:>3}  " + " ".join(f"{confusion[i][j]:>4}" for j in range(n)))
    print("\n인덱스:", ", ".join(f"{i}={name}" for i, name in enumerate(classes)))


if __name__ == "__main__":
    main()
