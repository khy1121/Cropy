"""PSIS(농약안전정보시스템) OpenAPI에서 작물×병해별 등록 농약을 받아 시드 데이터를 갱신한다.

농약 추천은 학습 대상이 아니라 조회 문제다: 등록 농약 목록은 PSIS에
법적으로 등재돼 있으므로 그대로 가져와 seed(pesticides.json,
disease_pesticides.json)를 재생성한다. 백엔드 재시작 시 seed upsert가
DB에 반영한다.

Usage:
    python scripts/sync_pesticides.py --api-key <PSIS_API_KEY>
    (또는 환경변수 PSIS_API_KEY)

API 키는 https://psis.rda.go.kr > 공공데이터개방 > OpenAPI 신청에서 발급.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "seed"
API_URL = "https://psis.rda.go.kr/openApi/service.do"

# disease_key -> PSIS 검색 조건 (병명은 PSIS 등재 명칭 기준)
DISEASE_QUERIES: dict[str, tuple[str, str]] = {
    "pepper_anthracnose": ("고추", "탄저병"),
    "pepper_powdery_mildew": ("고추", "흰가루병"),
    "radish_alternaria": ("무", "검은무늬병"),
    "radish_downy_mildew": ("무", "노균병"),
    "cabbage_black_rot": ("배추", "검은썩음병"),
    "cabbage_downy_mildew": ("배추", "노균병"),
}

MAX_PER_DISEASE = 5


def fetch_items(client: httpx.Client, api_key: str, crop: str, disease: str) -> list[dict]:
    params = {
        "apiKey": api_key,
        "serviceCode": "SVC01",
        "serviceType": "AA001",
        "cropName": crop,
        "diseaseWeedName": disease,
        "displayCount": "50",
        "startPoint": "1",
    }
    res = client.get(API_URL, params=params, timeout=30)
    res.raise_for_status()
    root = ET.fromstring(res.text)
    items = []
    for node in root.iter("item"):
        items.append({child.tag: (child.text or "").strip() for child in node})
    if not items:  # 일부 응답은 <list> 하위에 바로 필드를 담은 반복 요소를 쓴다
        for node in root.iter("list"):
            item = {child.tag: (child.text or "").strip() for child in node}
            if item.get("pestiKorName"):
                items.append(item)
    return items


def parse_phi_days(use_suittime: str) -> int | None:
    m = re.search(r"수확\s*(\d+)\s*일\s*전", use_suittime)
    return int(m.group(1)) if m else None


def clean_dilution(value: str) -> str | None:
    """PSIS의 dilutUnit은 두 번째 단위가 비면 '2000배 -'처럼 하이픈이 남는다.

    화면에서 희석비는 크게 강조해 보여주는 값이라 꼬리 기호를 지운다.
    '1000~2000배'처럼 중간에 들어간 기호는 건드리지 않는다.
    """
    cleaned = re.sub(r"[\s\-~/]+$", "", (value or "").strip())
    return cleaned or None


def to_pesticide(item: dict, key: str) -> dict:
    use_suittime = item.get("useSuittime", "")
    use_num = item.get("useNum", "")
    notes = " / ".join(x for x in [
        f"안전사용기준: {use_suittime}" if use_suittime else "",
        f"사용횟수: {use_num} 이내" if use_num else "",
    ] if x)
    return {
        "key": key,
        "name": f"{item.get('pestiBrandName', '')} ({item.get('pestiKorName', '')})".strip(),
        "active_ingredient": item.get("pestiKorName") or None,
        "registration_no": f"PSIS-{item.get('pestiCode', '')}",
        "dilution": clean_dilution(item.get("dilutUnit", "")),
        "usage_method": item.get("pestiUse") or None,
        "phi_days": parse_phi_days(use_suittime),
        "reentry_hours": None,
        "safety_notes": notes or None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("PSIS_API_KEY"))
    parser.add_argument("--max-per-disease", type=int, default=MAX_PER_DISEASE)
    args = parser.parse_args()
    if not args.api_key:
        sys.exit("PSIS API 키가 필요합니다 (--api-key 또는 PSIS_API_KEY 환경변수).")

    pesticides: dict[str, dict] = {}
    mappings: list[dict] = []

    with httpx.Client() as client:
        for disease_key, (crop, disease) in DISEASE_QUERIES.items():
            items = fetch_items(client, args.api_key, crop, disease)
            # 같은 품목명(성분·제형)은 대표 상표 하나만 남겨 성분 다양성을 확보
            seen_ingredients: set[str] = set()
            picked = 0
            for item in items:
                ingredient = item.get("pestiKorName", "")
                if not ingredient or ingredient in seen_ingredients:
                    continue
                seen_ingredients.add(ingredient)
                picked += 1
                key = f"psis_{item.get('pestiCode', ingredient)}"
                if key not in pesticides:
                    pesticides[key] = to_pesticide(item, key)
                mappings.append({
                    "disease_key": disease_key,
                    "pesticide_key": key,
                    "priority": picked,
                })
                if picked >= args.max_per_disease:
                    break
            print(f"{crop} {disease}: 등록 {len(items)}건 중 {picked}개 선정")

    if not pesticides:
        sys.exit("가져온 데이터가 없습니다. API 키/파라미터를 확인하세요.")

    (SEED_DIR / "pesticides.json").write_text(
        json.dumps(list(pesticides.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    (SEED_DIR / "disease_pesticides.json").write_text(
        json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nseed 갱신 완료: 농약 {len(pesticides)}개, 매핑 {len(mappings)}개")
    print("백엔드 재시작 시 DB에 반영됩니다.")


if __name__ == "__main__":
    main()
