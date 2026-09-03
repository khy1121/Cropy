"""
CropCare AI - Colab 학습용 번들 생성

data/dataset의 이미지를 짧은 변 256px로 리사이즈해 용량을 줄이고,
train.py와 함께 colab_bundle.zip으로 묶는다. (원본 dataset은 그대로 둠)

Usage:
    python pack_for_colab.py --data-dir ../data/dataset --out colab_bundle.zip
"""

import argparse
import shutil
import tempfile
from pathlib import Path

from PIL import Image

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def resize_copy(src: Path, dest: Path, short_side: int = 256) -> None:
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = short_side / min(w, h)
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.BILINEAR)
        im.save(dest.with_suffix(".jpg"), "JPEG", quality=90)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/dataset")
    parser.add_argument("--out", default="colab_bundle.zip")
    parser.add_argument("--short-side", type=int, default=288,
                        help="256px 크롭 학습에 여유를 두려면 288 이상 권장")
    parser.add_argument("--include-checkpoint", default="checkpoints/best_model.pth",
                        help="이어학습(fine-tune) 시작점으로 번들에 포함할 체크포인트 (없으면 건너뜀)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out = Path(args.out).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "bundle"
        n = 0
        for src in data_dir.rglob("*"):
            if not src.is_file() or src.suffix.lower() not in IMG_EXTS:
                continue
            rel = src.relative_to(data_dir)
            dest = staging / "dataset" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            resize_copy(src, dest, args.short_side)
            n += 1
        shutil.copy2(Path(__file__).parent / "train.py", staging / "train.py")

        ckpt = Path(args.include_checkpoint)
        if not ckpt.is_absolute():
            ckpt = Path(__file__).parent / ckpt
        ckpt_included = ckpt.exists()
        if ckpt_included:
            dest_ckpt = staging / "checkpoints" / "best_model.pth"
            dest_ckpt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ckpt, dest_ckpt)

        shutil.make_archive(str(out.with_suffix("")), "zip", staging)

    size_mb = out.stat().st_size / 1e6
    ck = "with checkpoint" if ckpt_included else "no checkpoint (from-scratch only)"
    print(f"{n} images -> {out} ({size_mb:.0f} MB) [{ck}]")


if __name__ == "__main__":
    main()
