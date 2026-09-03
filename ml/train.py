"""
CropCare AI - CNN 학습 스크립트

Usage:
    python train.py --data-dir ../data/dataset --epochs 20
    # 정확도 개선 파인튜닝(소수 클래스 균형 + 고해상도, 기존 체크포인트에서 이어학습):
    python train.py --data-dir ../data/dataset --arch resnet50 \
        --resume checkpoints/best_model.pth --balanced-sampler \
        --img-size 256 --lr 2e-5 --epochs 12 --output checkpoints/best_model_ft.pth
"""

import argparse
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, models, transforms


def build_model(num_classes: int, arch: str = "resnet18") -> nn.Module:
    if arch == "resnet50":
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    else:
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def get_transforms(img_size: int):
    # 확대 여지를 두고 크롭하도록 리사이즈 기준은 크롭보다 약간 크게
    resize = round(img_size * 1.14)
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


def make_balanced_sampler(dataset) -> WeightedRandomSampler:
    """클래스별 등장 확률을 역빈도로 맞춰 소수 클래스(무노균병 등)를 균형 있게 학습."""
    counts = Counter(t for _, t in dataset.samples)
    class_weight = {c: 1.0 / n for c, n in counts.items()}
    sample_weights = [class_weight[t] for _, t in dataset.samples]
    return WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)


@torch.no_grad()
def evaluate(model, loader, device, num_classes):
    model.eval()
    correct = total = 0
    per_class_correct = [0] * num_classes
    per_class_total = [0] * num_classes
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        preds = model(images).argmax(1)
        for t, p in zip(labels.tolist(), preds.tolist()):
            per_class_total[t] += 1
            per_class_correct[t] += int(t == p)
            total += 1
            correct += int(t == p)
    per_class = [
        (100.0 * per_class_correct[i] / per_class_total[i]) if per_class_total[i] else 0.0
        for i in range(num_classes)
    ]
    return 100.0 * correct / total, per_class


def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
    return total_loss / len(loader), 100.0 * correct / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, required=True, help="ImageFolder root (train/val subdirs)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--output", type=str, default="checkpoints/best_model.pth")
    parser.add_argument("--resume", type=str, default=None, help="Checkpoint to resume from")
    parser.add_argument("--arch", type=str, default="resnet18", choices=["resnet18", "resnet50"])
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=224, help="입력 해상도 (미세 병징엔 256 권장)")
    parser.add_argument("--balanced-sampler", action="store_true",
                        help="클래스 역빈도 가중 샘플링으로 소수 클래스 균형")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    train_tf, val_tf = get_transforms(args.img_size)

    train_ds = datasets.ImageFolder(str(data_dir / "train"), transform=train_tf)
    val_ds = datasets.ImageFolder(str(data_dir / "val"), transform=val_tf)

    if args.balanced_sampler:
        sampler = make_balanced_sampler(train_ds)
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                                  num_workers=args.num_workers)
    else:
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                                  num_workers=args.num_workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    num_classes = len(train_ds.classes)
    model = build_model(num_classes, args.arch).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0

    print(f"Device: {device}, Classes: {num_classes}, img_size: {args.img_size}, "
          f"balanced_sampler: {args.balanced_sampler}")

    if args.resume:
        ckpt = torch.load(args.resume, map_location=device)
        if ckpt.get("arch", "resnet18") != args.arch:
            raise SystemExit(f"Arch mismatch: checkpoint {ckpt.get('arch', 'resnet18')} vs --arch {args.arch}")
        if ckpt["classes"] != train_ds.classes:
            raise SystemExit(f"Class mismatch: checkpoint {ckpt['classes']} vs dataset {train_ds.classes}")
        model.load_state_dict(ckpt["model_state_dict"])
        best_acc, _ = evaluate(model, val_loader, device, num_classes)
        print(f"Resumed from {args.resume} (val_acc: {best_acc:.1f}%)")

    for epoch in range(args.epochs):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_acc, per_class = evaluate(model, val_loader, device, num_classes)
        scheduler.step()
        weak = " | ".join(
            f"{i}:{per_class[i]:.0f}%" for i in range(num_classes) if per_class[i] < 90.0
        )
        print(f"Epoch {epoch + 1}/{args.epochs} - loss: {train_loss:.4f}, "
              f"train_acc: {train_acc:.1f}%, val_acc: {val_acc:.1f}%"
              + (f"  (약점 {weak})" if weak else ""))

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                "model_state_dict": model.state_dict(),
                "classes": train_ds.classes,
                "num_classes": num_classes,
                "arch": args.arch,
                "img_size": args.img_size,
            }, output_path)
            print(f"  Saved best model (val_acc: {val_acc:.1f}%)")

    print(f"Training complete. Best val accuracy: {best_acc:.1f}%")


if __name__ == "__main__":
    main()
