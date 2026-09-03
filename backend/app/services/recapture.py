"""혼동 병해쌍 판별부위 유도 (구성 B·C·D의 레퍼런스 구현).

1차 진단의 상위 두 후보가 시각적으로 유사한 혼동쌍이고 신뢰도 마진이 좁으면,
그 두 병을 가르는 특정 식물 부위를 사용자에게 다시 촬영하도록 안내한다.

혼동쌍은 model_class_id(폴더 앞 숫자) 기준으로 정의한다:
    1 고추흰가루병 · 2 무검은무늬병 · 3 무노균병 · 4 배추검은썩음병 · 5 배추노균병

주의: 아래 병리 단서(포자층 위치·잎맥 흑변 등)는 표준 병징에 근거하나
배포 전 식물병리 자료로 검증할 것.
"""

from app.schemas.diagnosis import RecaptureCandidate, RecaptureGuidance

# 상위 1·2위 신뢰도 차이가 이 값 미만이면 혼동으로 보고 유도 발동
DEFAULT_MARGIN = 0.20

# 다시점 융합 시 2차(판별부위) 촬영에 주는 가중 — 표적 촬영이라 1차보다 크게
FUSE_WEIGHT_SECOND = 0.6

# frozenset(model_class_id 쌍) -> 판별부위·촬영지침·클래스별 시각단서
CONFUSION_PAIRS: dict[frozenset[int], dict] = {
    frozenset({2, 3}): {
        "region": "잎 뒷면",
        "instruction": "잎을 뒤집어 병반이 있는 부위의 뒷면을 근접 촬영하세요.",
        "cues": {
            3: "뒷면에 회백색 솜털 같은 곰팡이(포자층)가 보이면 노균병입니다.",
            2: "뒷면이 깨끗하고 앞면 병반이 동심원(과녁) 무늬면 검은무늬병입니다.",
        },
    },
    frozenset({4, 5}): {
        "region": "잎맥·잎 가장자리",
        "instruction": "잎맥과 잎 가장자리의 변색 부위를 촬영하세요.",
        "cues": {
            4: "잎맥이 검게 변하고 가장자리가 V자로 노래지면 검은썩음병입니다.",
            5: "잎 뒷면에 회백색 포자와 각진 반점이 있으면 노균병입니다.",
        },
    },
}


def check_recapture(
    predictions: list[tuple[int, float]],
    class_names: dict[int, str],
    margin_threshold: float = DEFAULT_MARGIN,
) -> RecaptureGuidance | None:
    """상위 두 후보가 혼동쌍이고 마진이 좁으면 유도 지침을, 아니면 None을 반환."""
    if len(predictions) < 2:
        return None

    (c1, p1), (c2, p2) = predictions[0], predictions[1]
    margin = p1 - p2
    if margin >= margin_threshold:
        return None

    entry = CONFUSION_PAIRS.get(frozenset({c1, c2}))
    if entry is None:
        return None

    candidates = [
        RecaptureCandidate(name=class_names.get(cid, str(cid)), cue=cue)
        for cid, cue in entry["cues"].items()
        if cid in (c1, c2)
    ]
    return RecaptureGuidance(
        region=entry["region"],
        instruction=entry["instruction"],
        margin=round(margin, 4),
        candidates=candidates,
    )


def fuse_predictions(
    dist1: list[tuple[int, float]],
    dist2: list[tuple[int, float]],
    weight_second: float = FUSE_WEIGHT_SECOND,
) -> list[tuple[int, float]]:
    """1차 촬영 분포와 2차(판별부위) 촬영 분포를 가중 평균해 재정렬 (구성 E).

    2차 촬영이 두 병을 가르는 표적 부위이므로 더 큰 가중을 준다.
    """
    d1 = dict(dist1)
    d2 = dict(dist2)
    w1 = 1.0 - weight_second
    classes = set(d1) | set(d2)
    fused = {c: w1 * d1.get(c, 0.0) + weight_second * d2.get(c, 0.0) for c in classes}
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


def apply_pair_specialist(
    fused: list[tuple[int, float]],
    spec: dict[int, float] | None,
    first_predictions: list[tuple[int, float]],
) -> list[tuple[int, float]]:
    """혼동쌍 전용 분류기(구성 E)의 2-클래스 판단으로 두 후보의 상대 비중만 재분배한다.

    두 클래스가 차지하던 합계 질량은 보존하고, 그 안에서의 분배를 전문가 분류기 확률로 대체.
    다른 클래스는 그대로 두므로, 쌍이 우세하지 않으면 영향이 작다.

    대상 쌍은 전문가 분류기가 학습한 두 클래스(spec의 키)이며, 그 쌍이 실제로 1차 진단의
    상위 두 후보 — 즉 재촬영을 유도한 혼동쌍 — 였을 때만 적용한다. 무 전용 분류기를
    배추 혼동쌍(4·5) 재촬영에 적용하면 무 후보(2·3)의 순위가 근거 없이 뒤집히기 때문이다.
    """
    if not spec or len(spec) != 2 or len(first_predictions) < 2:
        return fused

    pair = frozenset(spec)
    if frozenset(c for c, _ in first_predictions[:2]) != pair:
        return fused

    a, b = tuple(pair)
    d = dict(fused)
    if a not in d or b not in d:
        return fused
    sa, sb = spec.get(a, 0.0), spec.get(b, 0.0)
    s = sa + sb
    if s <= 0:
        return fused
    combined = d[a] + d[b]
    d[a] = combined * sa / s
    d[b] = combined * sb / s
    return sorted(d.items(), key=lambda x: x[1], reverse=True)
