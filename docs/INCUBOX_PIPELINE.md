# 인큐박스 - 분석 파이프라인

촬영 한 장이 들어와서 감염률·권고가 나가기까지. 백엔드 `app/services/incubation/`에
구현한다. **학습이 필요한 단계는 3단계(칸별 추론) 하나뿐이고, 그것도 기존 모델을 그대로 쓴다.**

```
원본 이미지
   │
   ▼
① 격자 보정 ── ArUco 4개 검출 (장치) / 사용자 4점 (수동) ── 실패 → grid_ok=false, 중단
   │
   ▼
② 칸 크롭 ── 24칸, 여백 6%, 정사각 패딩 ── 빈 칸 판정
   │
   ▼
③ 칸별 추론 ── 기존 predict_all() → 고추 클래스 {0,1,6} 재정규화
   │
   ▼
④ 시계열 판정 ── 직전 촬영의 상태 + 이번 확률 → 래치된 상태
   │
   ▼
⑤ 감염률·곡선·평탄 ── 발현/유효, 곡선 점 추가, 종료 제안
   │
   ▼
⑥ 권고 ── 등급 → 행동 목록 + 기존 농약 목록
```

## ① 격자 보정

### 장치 모드 — ArUco

- `cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)`, ID 0·1·2·3.
- 마커 중심이 아니라 **트레이 안쪽 모서리**를 기준점으로 쓴다. 마커 30mm가 트레이
  테두리(8mm) 안쪽에 있으므로, 각 마커의 트레이 안쪽 꼭짓점을 취한다 (ID 0은 우하단
  꼭짓점, ID 1은 좌하단, ID 2는 좌상단, ID 3은 우상단).
- 네 점 → `cv2.getPerspectiveTransform` → `cv2.warpPerspective`로 **2750 × 1700px**
  정규 좌표계(5px/mm, 트레이 550 × 340mm)로 편다.
- 검출 조건: 4개 모두. 3개만 잡히면 나머지 하나를 평행사변형 가정으로 보간하되
  `corners_interpolated: true` 기록. 2개 이하 → 실패.
- 실패 시 `grid_ok=false`로 저장하고 판독 생략. 연속 3회 실패 → `grid_failure` 이벤트.
  원인은 대개 트레이가 밀렸거나 마커 스티커 오염.

### 수동 모드 — 사용자 4점

앱에서 사용자가 격자 종이 네 모서리를 탭한다. 좌상→시계방향. 같은 변환을 적용한다.
Phase 0 스크립트(아래)도 이 경로.

## ② 칸 크롭

정규 좌표계에서 칸 위치는 상수다 (트레이 도면 [INCUBOX_HARDWARE](INCUBOX_HARDWARE.md)).
가로(장축) 4칸 × 세로(단축) 6줄, 칸 내부 130 × 50mm.

```
5px/mm 기준:  테두리 8mm → 40px,  칸막이 4mm → 20px,  칸 130×50mm → 650×250px
열 c (0~3, 가로), 줄 r (0~5, 세로):
  x0 = 40 + c × (650 + 20)      # 40 + 4×650 + 3×20 + 40 = 2740 ≈ 2750
  y0 = 40 + r × (250 + 20)      # 40 + 6×250 + 5×20 + 40 = 1680 ≈ 1700
  cell_index = r × 4 + c        # 트레이 번호 − 1
```

mm 값은 트레이 최종 도면에서 상수 테이블(`TRAY_SPEC`)로 가져온다. 도면이 바뀌면 테이블만 바꾼다.

- 각 칸에 **여백 6%**(과실이 칸막이에 기대는 경우 대비).
- 크롭은 650×250 직사각형. 기존 `_transform`은 Resize → CenterCrop이라 긴 과실의 양끝이
  잘린다. 그래서 **정사각 패딩**: 650×650 캔버스에 트레이 색(중회색)으로 채우고 크롭을
  중앙에 놓은 뒤 모델 입력 크기로 줄인다. 과실 전체가 들어간다.
- 칸 크롭은 `cells/{seq}/{cell}.jpg`로 저장 — 재학습 데이터.

### 빈 칸 판정

`sample_count < 24`이거나 과실이 빠진 칸. 크롭의 **그레이스케일 표준편차 < 12** 이고
평균이 트레이 색 ±15 이내면 빈 칸 → `is_empty=true`, `state=invalid`, 분모에서 제외.
임계는 Phase 0 데이터로 조정.

## ③ 칸별 추론

```python
dist = dict(ml_service.predict_all(crop_path))   # {model_class_id: prob} 9개
pepper = {k: dist[k] for k in (0, 1, 6)}          # 탄저, 흰가루, 정상
z = sum(pepper.values())
p_anth, p_powd, p_heal = pepper[0]/z, pepper[1]/z, pepper[6]/z
```

무·배추 6개 클래스의 확률 질량을 버리고 고추 3개로 재정규화한다. 챔버 안에 무·배추는
없다. 이렇게 하면 모델이 "무 검은무늬병 0.4"처럼 엉뚱한 곳에 질량을 두더라도 고추
안에서의 상대 비율로 판정된다.

기존 모델을 **수정하지 않는다.** `predict_all`은 이미 전체 분포를 돌려준다. CPU에서 24칸
≈ 10초(ResNet50). 배치 추론으로 줄일 수 있으나 v0에선 불필요.

### Mock 모드

체크포인트가 없으면 `predict_all`이 고정 분포를 반환한다. 파이프라인은 그대로 돌아가되
모든 칸이 같은 값이 된다 — 개발·테스트용. 기존 테스트 관례와 동일.

## ④ 시계열 판정

칸 상태는 **래치**된다. 직전 촬영의 상태와 이번 확률로 다음 상태를 정한다.

```
상태: healthy → suspect → expressed   (되돌아가지 않음)
                invalid (빈 칸·판독 불가, 고정)

입력: prev_state, p_anth(이번), p_anth(직전)

if prev_state == expressed:            expressed
elif is_empty:                         invalid
elif p_anth ≥ 0.60 and prev_p ≥ 0.60:  expressed     # 연속 2회
elif p_anth ≥ 0.60:                    suspect        # 1회. 다음 촬영에서 확정
elif p_anth ≥ 0.40:                    suspect
else:                                  healthy (prev가 suspect였어도 healthy로 — 단발 노이즈)
```

- **연속 2회 ≥ 0.60**이 발현 확정. 하루 3회 촬영이면 최대 8시간 안에 확정된다.
  단발 오분류(조명 반사, 물방울)를 거른다.
- `suspect`는 UI에서 "관찰 중"으로 보인다. 분자에 넣지 않는다.
- 첫 촬영(seq 0, D+0)은 **판정하지 않는다**. 기준 사진이다. 소독 직후 병반이 보이면
  그건 잠복이 아니라 이미 발병한 과실 → 채취 오류. seq 0에서 `p_anth ≥ 0.6`인 칸은
  `invalid`로 두고 `sampling_error` 경고.
- 임계 0.60/0.40은 Phase 0에서 ROC로 조정한다. 목표: 발현 칸 놓침(FN) ≤ 5%를 만족하는
  범위에서 FP 최소.

## ⑤ 감염률·곡선·평탄

```
cells_valid     = state ≠ invalid 인 칸 수
cells_expressed = state == expressed 인 칸 수
infection_rate  = cells_expressed / cells_valid     (cells_valid == 0 → null)
```

- 촬영마다 `(seq, day, infection_rate)`를 곡선에 추가.
- **평탄**: 마지막 새 발현 이후 **6회 촬영(≈48시간)** 동안 변화 없고 `day ≥ 5` →
  `plateau=true`, 앱에 "종료해도 됩니다" 제안. 자동 종료는 하지 않는다 — 사용자가
  확인한다.
- **최대 `day ≥ 10`** → `max_days` 사유로 자동 종료. 그 이후는 2차 부패로 판독이 무의미.
- `cells_valid < 12`면 (절반 이상 무효) 결과에 `low_sample` 경고. 등급은 내되 재검사 권고.

## ⑥ 권고

| 감염률 | grade | title | actions |
|--------|-------|-------|---------|
| < 0.05 | `low` | 낮음 — 정기 예방 관리를 유지하세요 | 정기 예방 살포 유지 · 2~3주 뒤 재검사 · 아래쪽 과실 주 1회 점검 |
| 0.05 ~ 0.20 | `caution` | 주의 — 강우 전 예방 살포가 필요합니다 | 비 오기 전 등록 살균제 살포 · 아래쪽·병든 과실 제거해 밭 밖으로 · 1~2주 뒤 재검사 |
| ≥ 0.20 | `high` | 높음 — 지금 방제를 시작하세요 | 즉시 살포, 7일 간격 · 계통 다른 약제로 교차 · 붉어진 과실 조기 수확 · 1주 뒤 재검사 |

- `pesticides`: `diseases.model_class_id == 0`의 기존 농약 목록 그대로. **추천 로직 추가 없음.**
- `caveat`: 표본 수에 따른 신뢰구간 문구. `n=24`: 감염률 0.125에서 95% CI ≈ ±13%p.
  계산: `1.96 × sqrt(p(1−p)/n)`. 등급 경계(0.05, 0.20)가 CI 안에 있으면 "경계 근처 —
  재검사로 확인" 문구 추가.
- 경계값은 **가설**. [INCUBOX_VALIDATION](INCUBOX_VALIDATION.md) Phase 3에서 보정.

## Phase 0 스크립트 — `ml/incubation_grid.py`

장치·백엔드 없이 스마트폰 사진으로 파이프라인 ①~③을 검증한다.

```
python incubation_grid.py <image_dir> --corners 120,80 3900,95 3880,2500 110,2480 \
    --rows 6 --cols 4 --out results.csv [--checkpoint ../ml/checkpoints/best_model.pth]
```

| 옵션 | 설명 |
|------|------|
| `image_dir` | 한 run의 사진들. 파일명 `YYYYMMDD_HHMM.jpg` 정렬 |
| `--corners` | 격자 네 모서리 픽셀 좌표 (좌상→시계). 고정 거치라면 한 번만 |
| `--corners-per-image` | 사진마다 다르면 `corners.json` 경로 |
| `--rows/--cols` | 세로 줄 수 / 가로 칸 수. 기본 6/4 (트레이 도면과 동일 배열) |
| `--margin` | 칸 여백 비율, 기본 0.06 |
| `--out` | CSV: `image, seq, day, cell, p_anth, p_powd, p_heal, is_empty` |
| `--save-cells DIR` | 칸 크롭 저장 (육안 대조·재학습용) |

출력 CSV에 사람이 기록지의 육안 판정 열(`label`)을 붙이면
`ml/evaluate_incubation.py`(별도)가 칸별 정확도·FN·FP·ROC를 낸다.

순서: `incubation_grid.py` 먼저(Phase 0 시작 시), `evaluate_incubation.py`는 데이터가
5일치 쌓인 뒤.

## 성능 목표

| 항목 | 목표 |
|------|------|
| 촬영 수신 → 결과 | ≤ 30초 (CPU) |
| 격자 검출 실패율 (장치) | < 1% |
| 칸별 탄저/정상 정확도 (Phase 0) | ≥ 90% |
| 발현 칸 놓침 (FN) | ≤ 5% |
| 빈 칸 오판 | 0 |

## 알려진 한계

- **2차 부패**(세균성 물러짐, 잿빛곰팡이)는 학습 클래스에 없다. 모델이 이를 탄저로 볼지
  정상으로 볼지 알 수 없다. Phase 0에서 측정하고, 필요하면 챔버 전용 모델에 `rot` 클래스.
- **도메인 갭**: 학습 데이터는 노지 사진(잎·과실·흙 배경). 챔버는 회색 트레이 + 균일 조명.
  정사각 패딩의 트레이색 배경은 학습 분포에 없다. Phase 0 정확도가 낮으면 첫 조치는
  **챔버 크롭으로 파인튜닝**(9-class 유지, 챔버 이미지 추가).
- 초기 병반 2mm 이하는 해상도 한계. 다음 촬영에서 커진 뒤 잡힌다 — 확정이 8시간 늦어질 뿐.
