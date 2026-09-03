# Orange Pi 5 (16GB) 배포 가이드

> CropCare AI 전체 스택(FastAPI 백엔드 + Next.js 프론트 + ResNet50 CPU 추론)을
> **Orange Pi 5 (Rockchip RK3588S, ARM64, 16GB RAM)** 한 대에 올리는 상세 설명서입니다.
>
> 결론부터: **16GB 모델이면 여유롭게 돌아갑니다.** 예상 상주 메모리는 백엔드(모델 포함) 1.5~2GB + 프론트 0.3GB 수준.
> 유일하게 주의할 점은 **ARM64(aarch64) 아키텍처 차이** — 특히 PyTorch 설치 방법이 x86과 다릅니다.

---

## 0. 사전 준비물

| 항목 | 권장 |
|---|---|
| 보드 | Orange Pi 5 16GB (RK3588S) |
| 저장장치 | **NVMe SSD 128GB+ 강력 권장** (M.2 슬롯). microSD는 느리고 수명 문제 |
| 전원 | 5V/4A USB-C (전력 부족 시 부팅 불안정) |
| OS 이미지 | **Ubuntu 22.04/24.04 Server** (Orange Pi 공식 또는 [Armbian](https://www.armbian.com/orangepi-5/) — Armbian 쪽이 커널 관리가 깔끔해서 권장) |
| 네트워크 | 유선 이더넷 권장 (초기 설치 시 수 GB 다운로드) |

### OS 굽기 & 첫 부팅

1. [Armbian Orange Pi 5 이미지](https://www.armbian.com/orangepi-5/) 다운로드 (Ubuntu 기반, Server 버전)
2. balenaEtcher 등으로 microSD에 굽고 첫 부팅 → 초기 계정 설정
3. (권장) `armbian-config` → NVMe로 시스템 이전 후 SD 제거
4. 기본 업데이트:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl build-essential
```

아키텍처 확인 — 반드시 `aarch64`가 나와야 합니다:

```bash
uname -m   # → aarch64
```

---

## 1. 프로젝트 옮기기

```bash
# PC에서 보드로 복사 (git 저장소가 있다면 clone이 더 깔끔)
scp -r C:\cropy user@<orangepi-ip>:~/cropy
# 또는
git clone <repo-url> ~/cropy
```

⚠️ **반드시 함께 옮겨야 하는 것 (저장소에 없는 파일들):**

| 경로 | 내용 | 없으면? |
|---|---|---|
| `ml/checkpoints/best_model.pth` | 학습된 ResNet50 체크포인트 | 백엔드가 **Mock 모드**로 뜸 (`/api/v1/health`의 `model_loaded: false`) |
| `ml/checkpoints/pair_mu.pth` | 혼동쌍 통계 (재촬영 유도용) | 재촬영 유도 기능 비활성 |
| `backend/cropcare.db` | 병해·농약 시드가 든 SQLite | 첫 기동 시 시드 재생성 로직에 의존 |

`frontend/node_modules`, `backend/.venv`는 **옮기지 마세요** — x86용 바이너리라 ARM에서 못 씁니다. 보드에서 새로 설치합니다.

```bash
# 복사했다면 정리
rm -rf ~/cropy/frontend/node_modules ~/cropy/backend/.venv
```

---

## 2. 방법 A — Docker Compose (권장: 가장 간단)

이 프로젝트의 Dockerfile 베이스 이미지(`python:3.13-slim`, `node:22-alpine`)는 모두 **ARM64 공식 이미지가 존재**하므로 compose가 거의 그대로 동작합니다. 단 한 곳만 고치면 됩니다.

### 2-1. Docker 설치

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 재로그인 후
docker run --rm hello-world
```

### 2-2. ⚠️ 필수 수정: PyTorch 설치 라인 (ARM64 차이점 핵심)

`backend/requirements.txt`의 `+cpu` 휠은 **x86_64 전용**입니다. ARM64에는 `+cpu` 빌드가 없고, **PyPI 기본 `torch`가 이미 CPU 빌드**입니다. ARM64에서는 이렇게 바꿉니다:

```diff
- --extra-index-url https://download.pytorch.org/whl/cpu
-
- torch==2.12.1+cpu
- torchvision==0.27.1+cpu
+ torch==2.12.1
+ torchvision==0.27.1
```

> 원본을 유지하고 싶다면 `requirements.arm64.txt`를 따로 만들고
> `backend/Dockerfile`의 `COPY requirements.txt .` 라인만 바꿔도 됩니다.
> `--extra-index-url` 줄을 남겨둬도 무해합니다(단순히 매칭 휠이 없어 PyPI로 폴백) — 하지만 명시적으로 지우는 편이 명확합니다.

### 2-3. 빌드 & 실행

```bash
cd ~/cropy
docker compose up -d --build
```

- 첫 빌드는 **20~40분** 걸립니다 (torch 다운로드 ~100MB + Next.js 빌드가 ARM CPU에서 느림). 정상입니다.
- Next.js 빌드 중 메모리 사용이 치솟지만 16GB면 문제없습니다.

### 2-4. 확인

```bash
docker compose ps                          # 두 컨테이너 모두 Up (backend는 healthy까지 최대 1분)
curl http://localhost:3000/api/v1/health   # {"status":"ok","model_loaded":true,...}
```

같은 공유기의 스마트폰/PC에서 `http://<orangepi-ip>:3000` 접속 → 사진 업로드 → 진단까지 눌러봐야 진짜 확인입니다.

---

## 3. 방법 B — 네이티브 실행 (Docker 없이, 자원 최대 활용)

### 3-1. 백엔드

```bash
# Python 3.11+ (Ubuntu 24.04 기본 3.12로 충분. 3.13 고집할 필요 없음)
sudo apt install -y python3-venv python3-dev

cd ~/cropy/backend
python3 -m venv .venv
source .venv/bin/activate

# ARM64용으로 torch 라인 수정 (2-2 참고) 후:
pip install -r requirements.txt

# 실행 (0.0.0.0 바인딩해야 외부 접속 가능)
ML_MODEL_PATH=../ml/checkpoints/best_model.pth \
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3-2. 프론트엔드

```bash
# Node 22 설치
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

cd ~/cropy/frontend
npm ci
npm run build        # 프로덕션 빌드 (dev 모드는 상시 운용에 부적합)
npm run start        # 포트 3000
```

> `next.config.js`가 기본으로 `http://127.0.0.1:8000`에 프록시하므로 같은 보드에서는 환경변수 없이 동작합니다.

### 3-3. systemd로 부팅 시 자동 시작

`/etc/systemd/system/cropcare-backend.service`:

```ini
[Unit]
Description=CropCare AI Backend
After=network.target

[Service]
User=orangepi
WorkingDirectory=/home/orangepi/cropy/backend
Environment=ML_MODEL_PATH=/home/orangepi/cropy/ml/checkpoints/best_model.pth
ExecStart=/home/orangepi/cropy/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/cropcare-frontend.service`:

```ini
[Unit]
Description=CropCare AI Frontend
After=cropcare-backend.service

[Service]
User=orangepi
WorkingDirectory=/home/orangepi/cropy/frontend
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cropcare-backend cropcare-frontend
```

---

## 4. 성능 예상과 튜닝

### RK3588S에서의 추론 속도

RK3588S는 Cortex-A76 ×4 + A55 ×4 구성입니다. ResNet50 CPU 추론(224×224, 단건)은 대략 **0.3~1초** 수준 — 사진 진단 UX에는 충분합니다.

튜닝 포인트:

```bash
# torch가 big 코어를 쓰도록 스레드 제한 (A55까지 긁으면 오히려 느려질 수 있음)
export OMP_NUM_THREADS=4
export TORCH_NUM_THREADS=4
```

- uvicorn은 **단일 워커 유지** (Dockerfile 주석대로 — 워커 수만큼 모델이 RAM에 복제됨)
- 발열: 진단 요청이 잦으면 방열판+팬 필수. `watch cat /sys/class/thermal/thermal_zone0/temp`로 확인, 85°C 근처면 스로틀링

### (선택·고급) RK3588 NPU 활용 — RKNN

RK3588S에는 **6 TOPS NPU**가 있습니다. `best_model.pth` → ONNX → RKNN 변환(rknn-toolkit2)하면 추론을 수십 ms로 줄이고 CPU를 비울 수 있습니다. 다만:

- 변환·양자화 후 **정확도 재검증 필수** (val/test 셋으로 `evaluate.py` 상당의 검증)
- `ml_service.py`에 RKNN 추론 경로 추가 필요 (현재는 torch 전용)
- 상세 절차(변환·캘리브레이션·정확도 검증)는 [QUANTIZATION.md](QUANTIZATION.md) 참고
- 현재 CPU 추론으로도 UX가 충분하므로 **나중에 해도 되는 최적화**입니다. Incubox(임베디드 상시 추론)나 SUDA 온디바이스 음성(→ `SUDA_INTEGRATION.md`)과 병행할 때 진짜 가치가 생깁니다.

---

## 5. 완전 오프라인 운용 — 인터넷 없이 돌아가는가?

**네, 서비스 전체가 오프라인에서 동작합니다.** 추론·조회 경로에 외부 API 호출이 하나도 없기 때문입니다.

### 오프라인에서 되는 것 (= 서비스 전부)

| 기능 | 동작 방식 |
|---|---|
| 모델 추론 | `best_model.pth`를 로컬 디스크에서 로드해 CPU/NPU로 계산. 체크포인트를 직접 `load_state_dict` 하므로 torchvision 사전학습 가중치 다운로드도 발생하지 않음 |
| 병해 설명·농약 추천 | 로컬 SQLite(`cropcare.db`) 조회 |
| 이미지 저장·진단 이력·재촬영 유도 | 로컬 파일시스템 + DB |
| 프론트 ↔ 백엔드 | 같은 보드 안 `127.0.0.1` 프록시 — 외부망 무관 |

폰과 보드가 **같은 로컬 네트워크**에만 묶여 있으면, 그 네트워크에 인터넷이 없어도 진단부터 농약 추천까지 전부 동작합니다.

### 인터넷이 필요한 순간 (설치·갱신 때 한정)

| 작업 | 시점 |
|---|---|
| Docker 빌드 / `pip`·`npm` 설치 | 최초 설치 시 1회 |
| PSIS 농약 데이터 갱신 (`sync_pesticides.py`) | 갱신할 때만 — 시드가 이미 DB에 있어 평소 불필요 |
| OS 업데이트·코드 배포 | 유지보수 때만 |

### 밭 한가운데 구성: 보드를 Wi-Fi AP(핫스팟)로

공유기조차 없는 현장에서는 오렌지파이가 직접 SSID를 뿌리는 구성이 실용적입니다:

```
[스마트폰] ←Wi-Fi→ [오렌지파이 5: AP + CropCare 풀스택]   (인터넷 없음)
```

```bash
# NetworkManager 사용 시 가장 간단한 방법
sudo nmcli device wifi hotspot ifname wlan0 ssid CropCare password <8자리이상>
# 폰에서 SSID 접속 후 → http://10.42.0.1:3000
```

- 부팅 시 자동 시작: `nmcli connection modify Hotspot connection.autoconnect yes`
- 더 세밀한 제어가 필요하면 `hostapd` + `dnsmasq` 조합 사용

⚠️ **시계 주의**: 오프라인이면 NTP 동기화가 안 되므로, RTC 배터리가 없는 보드는 재부팅 후 시각이 틀어져 진단 이력 타임스탬프가 어긋날 수 있습니다. RTC 모듈을 달거나, 접속한 폰의 시간으로 맞추는 동기 스크립트를 두세요.

> 음성 대화(SUDA)까지 온디바이스로 올리는 완전 오프라인 로드맵은 [SUDA_INTEGRATION.md](SUDA_INTEGRATION.md) 참고.

---

## 6. 외부 접속·운영 팁

| 목적 | 방법 |
|---|---|
| 공유기 내부 접속 | `http://<보드IP>:3000` — 보드 IP는 `ip a`로 확인, 공유기에서 고정 IP 할당 권장 |
| 밭에서 폰으로 접속 | 보드에 USB LTE 라우터/테더링 + [Tailscale](https://tailscale.com) 설치가 가장 간단하고 안전 (포트포워딩 불필요) |
| HTTPS 필요 시 | 카메라 API 등은 HTTP 오리진에서 제한될 수 있음 → Tailscale의 `tailscale serve` 또는 Caddy 리버스 프록시로 TLS |
| 백업 | Docker: `cropcare-data` 볼륨 / 네이티브: `backend/cropcare.db` + `backend/uploads/` 를 주기적으로 복사 |
| 로그 확인 | `docker compose logs -f backend` / `journalctl -u cropcare-backend -f` |

---

## 7. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `pip install torch==2.12.1+cpu` 실패 (`No matching distribution`) | ARM64에는 `+cpu` 휠이 없음 → **2-2 수정** 적용 |
| `/api/v1/health`가 `model_loaded: false` | 체크포인트 미복사 또는 `ML_MODEL_PATH` 경로 오류. Docker는 `ml/checkpoints/` 마운트 확인 |
| 프론트에서 API 호출 실패 (Docker) | `BACKEND_ORIGIN`은 **빌드타임** 인자 — 바꿨다면 `docker compose up -d --build`로 재빌드 |
| Next.js 빌드 중 멈춘 듯 | ARM에서 원래 느림(수 분). `free -h`로 메모리 확인하며 대기 |
| 외부 기기에서 접속 안 됨 | 네이티브 실행 시 `--host 0.0.0.0` 누락 여부, 방화벽(`sudo ufw status`) 확인 |
| 발열로 갑자기 느려짐 | 스로틀링 — 방열판/팬 장착, 케이스 통풍 |
| SD카드에서 자꾸 뻗음 | SD 수명/속도 문제 — NVMe로 이전 |

---

## 8. 체크리스트 요약

- [ ] Armbian/Ubuntu ARM64 설치, NVMe 이전
- [ ] 프로젝트 복사 + **체크포인트(`*.pth`) 별도 복사**
- [ ] `requirements.txt`의 torch 라인 ARM64용으로 수정 ← **유일한 코드 변경**
- [ ] `docker compose up -d --build` (또는 네이티브 + systemd)
- [ ] `curl http://localhost:3000/api/v1/health` → `model_loaded: true`
- [ ] 폰에서 실제 사진 업로드 → 진단 결과 확인
- [ ] (선택) Tailscale로 외부 접속, NPU(RKNN) 최적화는 추후
