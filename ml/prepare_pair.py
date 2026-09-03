"""무 혼동쌍(검은무늬병 vs 노균병) 전용 2-클래스 데이터셋 생성.

data/dataset(한글 폴더의 NFC/NFD 트윈 오염 이력)을 우회하여 AI Hub 원천데이터에서
직접 읽고, ASCII 폴더명(2_black / 3_downy)으로 출력한다. 폴더 앞 숫자 = model_class_id
이므로 ml_service의 파싱과 호환된다.

    python prepare_pair.py --out ../data/mu_pair
"""

import argparse
import random
import shutil
from pathlib import Path

# 원천 파일명 field idx3(disease code) -> (model_class_id, ASCII 폴더명)
PAIR_CLASSES = {
    "03": (2, "2_black"),   # 무검은무늬병
    "04": (3, "3_downy"),   # 무노균병
}
IMG_EXTS = {".jpg", ".jpeg", ".png"}


def find_raw_root() -> Path:
    base = Path(__file__).resolve().parent.parent / "data" / "_aihub_raw"
    for p in base.rglob("원천데이터"):
        if p.is_dir():
            return base  # rglob 대상은 base 전체
    raise SystemExit(f"원천데이터를 찾을 수 없습니다: {base}")


def classify(filename: str):
    parts = filename.split("_")
    if len(parts) < 5:
        return None
    return PAIR_CLASSES.get(parts[3])


def split_counts(n, train_ratio, val_ratio):
    if n <= 2:
        return n, 0, 0
    n_val = max(1, round(n * val_ratio))
    n_test = max(1, round(n * (1.0 - train_ratio - val_ratio)))
    n_train = n - n_val - n_test
    if n_train < 1:
        n_train, n_val, n_test = n - 2, 1, 1
    return n_train, n_val, n_test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/mu_pair")
    ap.add_argument("--cap", type=int, default=500)
    ap.add_argument("--train-ratio", type=float, default=0.70)
    ap.add_argument("--val-ratio", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    raw = find_raw_root()
    out = Path(args.out).resolve()
    rng = random.Random(args.seed)

    buckets: dict[str, list[Path]] = {f: [] for _, f in PAIR_CLASSES.values()}
    for path in raw.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMG_EXTS:
            continue
        cls = classify(path.name)
        if cls:
            buckets[cls[1]].append(path)

    if out.exists():
        shutil.rmtree(out)

    print(f"{'class':<10} {'train':>6} {'val':>5} {'test':>5} {'total':>6}")
    print("-" * 36)
    for folder, files in buckets.items():
        files = sorted(files)
        rng.shuffle(files)
        if args.cap and len(files) > args.cap:
            files = files[: args.cap]
        n_tr, n_va, n_te = split_counts(len(files), args.train_ratio, args.val_ratio)
        groups = {
            "train": files[:n_tr],
            "val": files[n_tr:n_tr + n_va],
            "test": files[n_tr + n_va:n_tr + n_va + n_te],
        }
        for split, group in groups.items():
            dest = out / split / folder
            dest.mkdir(parents=True, exist_ok=True)
            for f in group:
                shutil.copy2(f, dest / f.name)
        print(f"{folder:<10} {n_tr:>6} {n_va:>5} {n_te:>5} {len(files):>6}")
    print(f"\n완료 -> {out}")


if __name__ == "__main__":
    main()
