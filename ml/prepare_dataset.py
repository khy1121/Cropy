"""
CropCare AI - AI Hub 노지작물 이미지 → ImageFolder (train/val/test)

AI Hub '노지 작물 질병 진단'(dataSetSn=147) 원천데이터의 파일명에는
작물/병해 코드가 인코딩되어 있다:
    V006_79_{type}_{disease:02d}_{crop:02d}_{area:02d}_{grow:02d}_{risk}_...
    예) V006_79_1_01_01_01_13_1_...  → type=1(질병), disease=01(고추탄저병), crop=01(고추)
        V006_79_0_00_01_01_13_0_...  → type=0(정상),  disease=00,            crop=01(고추정상)

질병은 disease 코드로, 정상(type=0)은 crop 코드로 분류하여
data/dataset/{train,val,test}/<classid>_<name>/ 로 복사한다.
클래스 폴더명 앞 숫자 = model_class_id (ImageFolder 정렬 인덱스와 일치).

Usage:
    python prepare_dataset.py \
        --src "../data/_aihub_raw/073.노지_작물_질병_진단/01.데이터/2.Validation/원천데이터" \
        --out ../data/dataset --train-ratio 0.70 --val-ratio 0.15 --normal-cap 200
"""

import argparse
import random
import shutil
from pathlib import Path

# disease code(파일명 index 3) -> (model_class_id, 폴더명)
DISEASE_CLASSES: dict[str, tuple[int, str]] = {
    "01": (0, "0_고추탄저병"),
    "02": (1, "1_고추흰가루병"),
    "03": (2, "2_무검은무늬병"),
    "04": (3, "3_무노균병"),
    "05": (4, "4_배추검은썩음병"),
    "06": (5, "5_배추노균병"),
}

# 정상(type=0) 이미지: crop code(파일명 index 4) -> (model_class_id, 폴더명)
NORMAL_CLASSES: dict[str, tuple[int, str]] = {
    "01": (6, "6_고추정상"),
    "02": (7, "7_무정상"),
    "03": (8, "8_배추정상"),
}

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def classify(filename: str) -> tuple[int, str] | None:
    parts = filename.split("_")
    if len(parts) < 5:
        return None
    type_code, disease_code, crop_code = parts[2], parts[3], parts[4]
    if disease_code in DISEASE_CLASSES:
        return DISEASE_CLASSES[disease_code]
    if type_code == "0" and crop_code in NORMAL_CLASSES:
        return NORMAL_CLASSES[crop_code]
    return None


def three_way_split(n: int, train_ratio: float, val_ratio: float) -> tuple[int, int, int]:
    """각 분할에 최소 1개를 보장하며 (train, val, test) 개수를 반환."""
    if n <= 2:
        # 너무 적으면 전부 train (평가 불가하지만 파이프라인은 동작)
        return n, 0, 0
    n_val = max(1, round(n * val_ratio))
    n_test = max(1, round(n * (1.0 - train_ratio - val_ratio)))
    n_train = n - n_val - n_test
    if n_train < 1:  # 재조정
        n_train, n_val, n_test = n - 2, 1, 1
    return n_train, n_val, n_test


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="원천데이터 루트 (작물 폴더들을 재귀 탐색)")
    parser.add_argument("--out", default="../data/dataset")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--normal-cap", type=int, default=200, help="정상 클래스당 최대 이미지 수 (균형용)")
    parser.add_argument("--disease-cap", type=int, default=0, help="질병 클래스당 최대 이미지 수 (0=무제한)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    rng = random.Random(args.seed)

    all_folders = [f for _, f in DISEASE_CLASSES.values()] + [f for _, f in NORMAL_CLASSES.values()]
    normal_folders = {f for _, f in NORMAL_CLASSES.values()}
    buckets: dict[str, list[Path]] = {f: [] for f in all_folders}

    skipped = 0
    for path in src.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMG_EXTS:
            continue
        cls = classify(path.name)
        if cls is None:
            skipped += 1
            continue
        buckets[cls[1]].append(path)

    if out.exists():
        shutil.rmtree(out)

    totals = {"train": 0, "val": 0, "test": 0}
    print(f"{'class':<18} {'train':>6} {'val':>5} {'test':>5} {'total':>6}")
    print("-" * 46)
    for folder in all_folders:
        files = sorted(buckets[folder])
        rng.shuffle(files)
        # 클래스 균형을 위해 상한 적용
        cap = args.normal_cap if folder in normal_folders else args.disease_cap
        if cap and len(files) > cap:
            files = files[:cap]

        n_train, n_val, n_test = three_way_split(len(files), args.train_ratio, args.val_ratio)
        groups = {
            "train": files[:n_train],
            "val": files[n_train:n_train + n_val],
            "test": files[n_train + n_val:n_train + n_val + n_test],
        }
        for split, group in groups.items():
            dest_dir = out / split / folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            for f in group:
                shutil.copy2(f, dest_dir / f.name)
            totals[split] += len(group)

        print(f"{folder:<18} {n_train:>6} {n_val:>5} {n_test:>5} {len(files):>6}")

    print("-" * 46)
    print(f"{'TOTAL':<18} {totals['train']:>6} {totals['val']:>5} {totals['test']:>5} "
          f"{sum(totals.values()):>6}")
    if skipped:
        print(f"(미매칭으로 건너뜀: {skipped})")
    print(f"\n완료 → {out.resolve()}")


if __name__ == "__main__":
    main()
