# 모델 양자화 및 온디바이스 포팅 계획 (NPU / 모바일)

> CropCare AI의 ResNet50 진단 모델(`ml/checkpoints/best_model.pth`, val 96.2% / test 93.1%)을
> **① RK3588 NPU(Orange Pi 5)** 와 **② 스마트폰 온디바이스** 로 포팅하기 위한 양자화 가이드입니다.
>
> 원칙: **FP32로 먼저 동작 확인 → 양자화 → 정확도 재검증 → 배포.** 양자화는 항상 "검증된 변환"이어야 합니다.

---

## 1. 왜 양자화인가

| 항목 | FP32 (현재) | INT8 (양자화 후) |
|---|---|---|
| 모델 크기 | ~100MB | **~25MB** (1/4) |
| 추론 속도 | CPU 0.3~1초 | NPU 수십 ms / 모바일 2~4배 가속 |
| 전력·발열 | CPU 풀가동 | NPU/DSP 오프로드로 대폭 절감 |
| 정확도 | test 93.1% | 통상 −1%p 이내 (ResNet 계열은 PTQ에 강한 편) |

- **NPU(RKNN)**: RK3588 NPU는 INT8 연산이 기본 → 변환 과정에 양자화가 **내장되어 있어 선택이 아님**
- **모바일**: 앱 용량·발열·배터리 문제로 INT8이 **사실상 필수**

---

## 2. 공통 파이프라인

두 타깃 모두 같은 뼈대를 공유합니다:

```
best_model.pth (PyTorch, FP32)
      │  torch.onnx.export (opset 17, 입력 1×3×224×224 고정)
      ▼
model.onnx  ──────────── FP32 기준선: 이 시점에 test 정확도 측정 (기준값 확보)
      │
      ├─ [NPU]    rknn-toolkit2 → PTQ(INT8) → model.rknn
      └─ [모바일]  ONNX Runtime 정적 양자화 → model.quant.onnx
      │
      ▼
정확도 재검증 (test 셋) → 하락 >1~2%p면 QAT로 재학습 → pair_mu 재생성
```

### 2-1. ONNX 내보내기

```python
# ml/export_onnx.py (신규 작성 대상)
import torch, torchvision

ckpt = torch.load("checkpoints/best_model.pth", map_location="cpu")
model = torchvision.models.resnet50(num_classes=9)   # 체크포인트의 arch 필드로 분기
model.load_state_dict(ckpt["model_state_dict"])       # 실제 키 이름은 train.py 저장 형식 확인
model.eval()

dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy, "checkpoints/model.onnx",
                  opset_version=17,
                  input_names=["image"], output_names=["logits"])
```

⚠️ **전처리 일치가 정확도의 절반입니다.** 학습 때 쓴 리사이즈 방식·정규화(mean/std)를 타깃 런타임에서 **바이트 단위로 동일하게** 재현해야 합니다. `ml/predict.py`의 transform을 기준 사본으로 삼으세요.

### 2-2. 캘리브레이션 데이터셋

PTQ는 대표 이미지로 활성값 분포를 측정합니다. 대충 고르면 특정 클래스만 정확도가 무너집니다.

- **train 분할에서 클래스당 30~60장, 총 300~500장** (9클래스 균등)
- 반드시 **실사용 분포 포함**: 야외 광량 차이, 흔들림, 잎 클로즈업 등
- test 셋은 캘리브레이션에 절대 사용 금지 (검증 오염)

```bash
# 예: 캘리브레이션 목록 생성
find ../data/dataset/train -name "*.jpg" | shuf | awk -F/ '{print > "calib_"$(NF-1)".txt"}'
# 클래스별로 균등 샘플링해 calib_list.txt로 병합
```

---

## 3. 타깃 ① — RK3588 NPU (Orange Pi 5)

### 3-1. 도구: rknn-toolkit2

- 변환은 **x86 리눅스 PC**에서 (rknn-toolkit2), 보드에서는 경량 런타임 **rknn-toolkit-lite2**로 추론
- 설치: [airockchip/rknn-toolkit2](https://github.com/airockchip/rknn-toolkit2) (Python 3.8~3.12, pip 휠 제공)

### 3-2. 변환 (PC에서)

```python
# ml/convert_rknn.py (신규 작성 대상)
from rknn.api import RKNN

rknn = RKNN()
# 전처리(mean/std)를 RKNN 그래프에 내장 — 앱 쪽 전처리 실수 여지 제거
rknn.config(mean_values=[[123.675, 116.28, 103.53]],   # ImageNet mean ×255 (train.py 값 확인!)
            std_values=[[58.395, 57.12, 57.375]],
            target_platform="rk3588")
rknn.load_onnx(model="checkpoints/model.onnx")
rknn.build(do_quantization=True, dataset="calib_list.txt")   # ← 여기서 INT8 PTQ 수행
rknn.export_rknn("checkpoints/model.rknn")
```

### 3-3. 보드에서 추론

```python
# backend/app/services/ 에 rknn 추론 경로 추가 (ml_service.py 분기)
from rknnlite.api import RKNNLite

rknn = RKNNLite()
rknn.load_rknn("/models/model.rknn")
rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)   # RK3588은 NPU 3코어
outputs = rknn.inference(inputs=[img_array])           # → logits, softmax는 numpy로
```

### 3-4. 백엔드 통합 방향

- `ml_service.py`에 **백엔드 선택 로직** 추가: `ML_RUNTIME=torch|rknn` 환경변수
  - `torch`: 기존 경로 (개발 PC, x86 서버)
  - `rknn`: RKNNLite 경로 (Orange Pi 5)
- softmax·Top-N·혼동쌍 판정 로직은 logits 이후 공통 코드로 유지 → 런타임만 갈아끼우는 구조
- Docker 사용 시 `/dev/dri`, NPU 디바이스 노드 패스스루 필요 → **NPU 경로는 네이티브 실행 권장** (단순함)

---

## 4. 타깃 ② — 스마트폰 온디바이스

### 4-1. 런타임 선택

| 런타임 | 장점 | 권장 상황 |
|---|---|---|
| **ONNX Runtime Mobile** | ONNX 하나로 iOS/Android 공통, NNAPI/CoreML EP로 가속 | **1순위 권장** — 파이프라인이 NPU 경로와 ONNX를 공유 |
| ExecuTorch (PyTorch 공식) | torch 생태계 일관성 | PyTorch 도구체인을 유지하고 싶을 때 |
| TFLite | 모바일 실적 최다 | 이미 TFLite 인프라가 있을 때 (ONNX→TF 변환이 번거로움) |

→ **ONNX Runtime Mobile 기준으로 진행.** ONNX 내보내기(2-1)를 NPU와 공유하므로 관리 포인트가 하나입니다.

### 4-2. 정적 양자화 (PC에서)

```python
# ml/quantize_onnx.py (신규 작성 대상)
from onnxruntime.quantization import quantize_static, CalibrationDataReader, QuantType

class CalibReader(CalibrationDataReader):
    ...  # calib_list.txt의 이미지를 predict.py와 동일한 전처리로 공급

quantize_static("checkpoints/model.onnx",
                "checkpoints/model.quant.onnx",
                CalibReader(),
                quant_format=QuantFormat.QDQ,      # NNAPI/CoreML 호환에 유리
                activation_type=QuantType.QUInt8,
                weight_type=QuantType.QInt8)
```

### 4-3. 앱 통합 시 주의

- **전처리를 네이티브로 재현**: 리사이즈 보간법(bilinear 여부)까지 predict.py와 일치시킬 것 — 미묘한 차이가 1~2%p를 갉아먹는 단골 원인
- 가속: Android는 NNAPI EP, iOS는 CoreML EP 지정 (미지원 기기는 CPU 폴백 자동)
- 병해·농약 데이터는 SQLite를 앱에 번들 → 완전 오프라인 (SUDA 문서 Phase 3과 합류)
- 재촬영 유도(recapture) 로직은 서버 코드(`recapture.py`)를 앱 쪽으로 이식하거나, 온라인 시 서버 위임/오프라인 시 로컬 판정의 이중 경로 설계

---

## 5. 정확도 검증 프로토콜 (모든 타깃 공통·필수)

**양자화는 "변환 성공"이 아니라 "검증 통과"로 끝납니다.**

1. **기준선**: FP32 ONNX로 test 셋 전체 정확도 + 클래스별 정확도 + 혼동행렬 (evaluate.py를 ONNX 입력을 받도록 확장)
2. **양자화 후 동일 측정** — 합격 기준(제안):
   - 전체 정확도 하락 **≤ 1.5%p**
   - 클래스별 하락 **≤ 3%p** (특정 병해만 무너지는지 반드시 확인)
3. **혼동쌍 정합**: 재촬영 유도는 근소한 확률 차이로 판정하므로,
   - 양자화 모델 출력으로 `prepare_pair.py`를 다시 돌려 **`pair_mu.pth`를 재생성**
   - FP32 대비 재촬영 트리거율 변화 확인 (과다/과소 트리거 모두 UX 문제)
4. **불합격 시 단계적 대응**:
   - 캘리브레이션 셋 확대·재구성 (가장 흔한 원인)
   - 민감 레이어(첫 conv, 마지막 fc) FP16/FP32 유지하는 혼합 정밀도
   - 그래도 안 되면 **QAT**(Quantization-Aware Training): train.py에 `torch.ao.quantization` QAT 삽입 후 수 epoch 미세조정 — ResNet은 여기까지 갈 확률이 낮음
5. **실기기 스모크 테스트**: 폰/보드에서 실제 촬영 이미지 20~30장으로 FP32 서버 결과와 **판정 일치율** 비교

---

## 6. 로드맵 & 산출물

| 단계 | 작업 | 산출물 |
|---|---|---|
| 1 | ONNX export + FP32 기준선 측정 | `ml/export_onnx.py`, 기준 성적표 |
| 2 | 캘리브레이션 셋 구성 | `calib_list.txt` (클래스 균등 300~500장) |
| 3 | RKNN 변환 + 보드 검증 | `model.rknn`, `ml_service.py` 런타임 분기 |
| 4 | ONNX 정적 양자화 + 검증 | `model.quant.onnx`, 검증 리포트 |
| 5 | pair_mu 재생성·재촬영 트리거 검증 | 양자화용 `pair_mu.pth` |
| 6 | 모바일 앱 PoC (ONNX Runtime Mobile) | 진단 1시나리오 동작 데모 |

### 관리 원칙

- 체크포인트 버전마다 **FP32/RKNN/ONNX-quant 성적을 한 표로 기록** (모델 카드)
- 재학습(retrain) 시 1→5 파이프라인 전체 재실행 — 스크립트화해서 수동 단계 제거
- 관련 문서: 배포 환경은 [ORANGEPI5_DEPLOY.md](ORANGEPI5_DEPLOY.md), 온디바이스 전체 그림은 [SUDA_INTEGRATION.md](SUDA_INTEGRATION.md), 모델 스펙은 [MODEL_SPEC.md](MODEL_SPEC.md)
