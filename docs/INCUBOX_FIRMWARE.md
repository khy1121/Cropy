# 인큐박스 - 펌웨어 사양

Raspberry Pi Zero 2 W에서 동작하는 장치 소프트웨어. **추론은 하지 않는다.** 촬영·전송·
온습도 제어·오프라인 큐만 담당하는 얇은 기기다. 판독 로직은 전부 백엔드
([INCUBOX_PIPELINE](INCUBOX_PIPELINE.md))에 있다.

## 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| OS | Raspberry Pi OS Lite (64-bit) | GUI 불필요 |
| 언어 | Python 3.11 | `picamera2`, `smbus2`, `gpiozero` 모두 Python |
| 카메라 | `picamera2` (libcamera) | Camera Module 3 공식 스택. 수동 포커스·노출 제어 |
| 센서 | `smbus2` 직접 I²C | SHT31 단일 명령 측정 |
| GPIO | `gpiozero` | 출력 2핀. 단순 |
| HTTP | `requests` | multipart 업로드 |
| 서비스 | `systemd` | 부팅 시 자동 시작, 크래시 시 재시작 |
| 설정 | `/etc/incubox/config.toml` | 프로비저닝 시 기록 |
| 큐·상태 | `/var/lib/incubox/` (SQLite + 이미지) | 전원 단절 대비 |

저장소 위치: `device/` (새 디렉터리). 구조는 아래.

```
device/
├── incubox/
│   ├── main.py          # 진입점, 상태기계 루프
│   ├── camera.py        # picamera2 래퍼, 고정 파라미터
│   ├── climate.py       # SHT31 읽기, 히터 히스테리시스
│   ├── uploader.py      # 큐 + 재시도 + 업로드
│   ├── schedule.py      # 촬영 시각 계산
│   ├── config.py        # config.toml 로드·검증
│   └── cli.py           # calibrate / provision / status 명령
├── systemd/incubox.service
├── requirements.txt
└── README.md
```

## 상태기계

```
              부팅
               │
               ▼
        ┌─────────────┐
        │   IDLE      │ ← 검사 없음. 히터 OFF. 60초마다 서버에 run 조회
        └──────┬──────┘
               │ 서버가 활성 run 할당 (또는 로컬에 활성 run 기록)
               ▼
        ┌─────────────┐
        │  RUNNING    │ ← 히터 제어 ON. 센서 60초 기록. 촬영 스케줄 대기
        └──┬───────┬──┘
           │       │ 촬영 시각
           │       ▼
           │  ┌──────────┐
           │  │ CAPTURE  │ → LED ON → 2초 → 촬영 → LED OFF → 큐 적재 → RUNNING
           │  └──────────┘
           │ 서버가 run 종료 통지 / 로컬 종료 명령
           ▼
        ┌─────────────┐
        │  CLEANUP    │ ← 히터 OFF. 큐 비우기. 상태 LED 점멸 "세척하세요"
        └──────┬──────┘
               ▼ 큐 빈 후
             IDLE

   모든 상태에서: SAFETY 검사 (센서 > 31℃ 또는 센서 오류 → 히터 강제 OFF + 서버 알림)
```

상태는 `/var/lib/incubox/state.json`에 기록해 재부팅 후 복원한다. 활성 run이 있으면
RUNNING으로 바로 복귀한다.

## 촬영

### 스케줄

- 기본 **08:00 · 14:00 · 20:00** (장치 로컬 시각, `config.toml`의 `capture_times`).
- run 시작 즉시 1회 추가 촬영 (D+0 기준 사진).
- 부팅 직후 시각이 불확실하면(NTP 미동기) **촬영하지 않고** 동기화를 기다린다. Pi Zero에는
  RTC가 없다. 10분 안에 동기화되지 않으면 마지막 알려진 시각 + 단조시계로 추정하고
  업로드 메타에 `clock_unsynced: true`를 표시한다.
- 촬영 시각을 놓쳤으면(전원 단절 등) 복구 즉시 1회 촬영하고 스케줄로 복귀. 하루 최대 4회.

### 파라미터 (고정)

초기 설정(`cli.py calibrate`)에서 정하고 `config.toml`에 저장한다. 이후 run마다 동일.

| 파라미터 | 값 | 이유 |
|----------|-----|------|
| 해상도 | 4608 × 2592 (풀) | 칸당 픽셀 확보 |
| 포맷 | JPEG 품질 90 | 3~5MB. 업로드 상한 10MB 이내 |
| 포커스 | `AfMode=Manual`, `LensPosition=<calibrated>` | 매 촬영 동일 초점면 |
| 노출 | `AeEnable=False`, `ExposureTime`·`AnalogueGain` 고정 | 조명 고정이므로 AE 불필요. 칸 간 비교 일관성 |
| 화이트밸런스 | `AwbEnable=False`, `ColourGains` 고정 | 병반 색(갈색·분홍)이 판정 단서. AWB가 흔들면 안 됨 |
| 조명 | LED ON → 2초 안정 → 촬영 → OFF | |
| 연속 촬영 | 2장, 선명도(라플라시안 분산) 높은 쪽 선택 | 진동·노이즈 대비 |

### 파일명과 메타

```
/var/lib/incubox/queue/{run_id}/{seq:04d}_{YYYYMMDDTHHMMSS}.jpg
/var/lib/incubox/queue/{run_id}/{seq:04d}_{YYYYMMDDTHHMMSS}.json
```

```json
{
  "run_id": "a1b2c3d4-...",
  "seq": 7,
  "captured_at": "2026-08-25T08:00:12+09:00",
  "clock_unsynced": false,
  "temp_c": 26.4,
  "humidity_pct": 96.1,
  "lens_position": 4.2,
  "exposure_us": 8000,
  "analogue_gain": 1.5,
  "sharpness": 182.3,
  "firmware": "0.1.0"
}
```

`seq`는 run 안에서 단조 증가. 서버는 `(run_id, seq)`로 중복 업로드를 거른다.

## 온습도 제어

### 루프 (60초 주기)

```
read SHT31 → (temp, rh)
if 읽기 실패 3회 연속:  히터 OFF, 상태 FAULT_SENSOR, 서버 알림
elif temp > 31.0:       히터 OFF, 상태 FAULT_OVERHEAT, 서버 알림
elif state == RUNNING:
    if temp < 25.5: 히터 ON
    elif temp > 27.5: 히터 OFF
    # 25.5~27.5 사이는 현 상태 유지 (히스테리시스)
else:                   히터 OFF
append (ts, temp, rh, heater_on) → climate 로그 (로컬 SQLite)
```

- 히터 최대 연속 ON **30분**. 초과 시 10분 강제 OFF (매트 과열·센서 표류 대비).
- RH < 85%가 60분 지속 → 서버 알림 `low_humidity` ("물 보충").
- 온도 < 23℃가 120분 지속 → 서버 알림 `low_temp` ("실내가 너무 춥습니다").
- 온도 > 30℃가 60분 지속 → 서버 알림 `high_temp` ("30℃ 이상 실내에 두지 마세요").

기후 로그는 촬영 업로드에 **직전 촬영 이후 구간의 요약**(min/max/mean, 히터 듀티)을
함께 실어 보낸다. 원시 60초 로그는 장치에 7일 보관.

## 업로드

### 프로토콜

`POST {server}/api/v1/incubation/{run_id}/capture` · `multipart/form-data`
([INCUBOX_API_SPEC](INCUBOX_API_SPEC.md)).

헤더: `X-Device-Id: <device_id>`, `X-Device-Token: <token>`.

### 큐와 재시도

- 촬영 직후 파일을 큐 디렉터리에 쓰고 **즉시 업로드 시도**.
- 실패 시 지수 백오프 **30초 → 1분 → 2분 → … → 최대 15분**, 무기한 재시도.
- 큐는 **FIFO**. 오래된 것부터. seq 순서가 서버에서도 유지된다.
- 업로드 성공(2xx) 시 로컬 파일 삭제. 4xx(검증 오류) 시 `failed/`로 옮기고 다음 항목 진행 —
  한 장이 계속 막으면 안 된다.
- 디스크 여유 < 500MB면 가장 오래된 `failed/`부터 삭제.
- Wi-Fi 끊김은 흔하다. 7일 run에서 큐가 21장 × 5MB ≈ 100MB까지 쌓일 수 있다. 32GB SD면 충분.

### 서버 폴링

RUNNING 중 **5분마다** `GET /api/v1/incubation/{run_id}` 로 run 상태 확인. `status`가
`finished`면 CLEANUP으로. IDLE 중 **60초마다** `GET /api/v1/devices/{device_id}/assignment`로
새 run 할당 확인.

## 설정 파일

`/etc/incubox/config.toml`

```toml
[device]
id = "incubox-0001"
token = "…"                      # 프로비저닝 시 서버가 발급
server = "https://cropcare.example.com"
timezone = "Asia/Seoul"

[capture]
times = ["08:00", "14:00", "20:00"]
width = 4608
height = 2592
jpeg_quality = 90
lens_position = 4.2              # calibrate가 기록
exposure_us = 8000
analogue_gain = 1.5
colour_gains = [1.8, 1.6]
led_warmup_s = 2.0

[climate]
target_c = 26.5
on_below_c = 25.5
off_above_c = 27.5
overheat_c = 31.0
max_heater_on_min = 30
low_rh_alert = 85

[gpio]
heater = 18
led = 12
status_led = 17

[i2c]
sht31_addr = 0x44
```

## CLI

| 명령 | 동작 |
|------|------|
| `incubox provision --server URL --pair-code XXXX` | 서버에 장치 등록, 토큰 수신, config 기록 |
| `incubox calibrate` | 라이브 프리뷰 없이: 포커스 스윕으로 선명도 최대 `LensPosition` 탐색 → 흰 종이 기준 노출·WB 고정 → ArUco 4개 검출 확인 → 조명 균일도 출력 → config 갱신 |
| `incubox capture --test` | 즉시 1장 촬영, 업로드 없이 `/tmp`에 저장 |
| `incubox status` | 상태·온습도·히터·큐 길이·마지막 업로드 |
| `incubox heater on/off --minutes N` | 수동 테스트 |

## 프로비저닝

1. SD에 OS 굽기. `wpa_supplicant` 또는 Pi Imager로 Wi-Fi 설정.
2. 첫 부팅 → `incubox provision --server … --pair-code …`. 페어 코드는 앱의 "장치 추가"
   화면에서 발급(10분 유효).
3. `incubox calibrate` — 빈 트레이를 넣은 상태로.
4. `systemctl enable --now incubox`.

## 로그

- `journalctl -u incubox`. 레벨 INFO. 촬영·업로드·상태 전이·알림·FAULT.
- 장치 로컬 로그 7일 보관. 서버 업로드 시 `device_events` 로 중요 이벤트(FAULT, 알림)만 전송.

## 상태 LED (GPIO17)

| 패턴 | 의미 |
|------|------|
| 꺼짐 | IDLE |
| 4초 주기 1회 점멸 | RUNNING 정상 |
| 1초 주기 점멸 | 업로드 대기 중 (네트워크 없음) |
| 빠른 점멸 | FAULT (센서·과열) |
| 켜짐 유지 | CLEANUP — 세척 필요 |

## 테스트

- **단위**: 히스테리시스 로직(온도 시퀀스 → 히터 상태), 스케줄 계산(시각 놓침·시각 미동기),
  큐 순서·백오프. 하드웨어 없이 `pytest`.
- **통합(실기)**: 7일 빈 트레이 운전. 기준은 [INCUBOX_HARDWARE](INCUBOX_HARDWARE.md) 체크리스트.
- **네트워크 단절 시험**: Wi-Fi를 24시간 끊고 복구 → 큐 전량 순서대로 업로드 확인.
- **전원 단절 시험**: RUNNING 중 전원 차단 → 복구 → 상태 복원·보충 촬영·히터 재개 확인.
