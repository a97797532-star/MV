# 환경 검증 결과

## Resume verification (2026-11-10)

- User reports ordinary Windows CMD successfully accessed PyPI and installed packaging 26.3. This does not establish network access inside Codex.
- Directly verified: uv 0.12.11, existing .venv Python 3.12.14, packaging==26.3 as the only installed distribution. No virtual environment was recreated.
- An initial dry-run used the installed package and did not test networking. The forced refresh below contacted https://pypi.org/simple/packaging/ and failed with socket error 10013. HTTP retries were disabled.

```powershell
$env:UV_HTTP_RETRIES='0'
$env:UV_HTTP_TIMEOUT='15'
uv pip install --python .venv\Scripts\python.exe --dry-run --reinstall-package packaging --refresh-package packaging packaging -v
```

- This session has restricted networking and sandbox_approval=false (automatically denied). An approval escalation cannot obtain authorization here; no request was submitted for review. No security policy changes or sandbox bypasses were attempted.
- setup.ps1 -Resolve -Models, uv lock and uv sync --locked were not repeated after this failure. uv.lock is still absent; dependency conflict resolution remains unverified.
- validate_environment.py --dummy: exit 1, 33 failures. Python 3.12 and SQLite schema passed; 28 third-party imports and five tensor/detection/dummy checks failed because dependencies are absent. See outputs/environment_validation.json.
- uv pip check passed for ONE installed package only; this is not project dependency validation. pip itself is absent and is not required by uv.
- No training, dataset/model-weight downloads, paid API calls or key output occurred.
- Resume setup in an authorized network-enabled session using powershell -NoProfile -File scripts/setup.ps1 -Resolve -Models. The -Models switch enables dummy checks; it does not install the independent anomaly/detection projects. Those require separate lock/sync/import validation.
- CPU model execution verified: 0/12. torchvision detectors, YOLOS, RT-DETRv2, YOLO11 and four anomalib models remain CPU candidates, not verified runnable models. UniAD/HVQ-Trans require Python 3.12 porting or a separately designed legacy reproduction; WSL2 alone does not fix their historical dependency conflicts. ViTDet requires WSL2/Linux and detectron2 build validation. GPU requirements and current upstream compatibility were not rechecked in this blocked session.

The historical records below predate this resume. In particular, references to zero installed packages are superseded by the directly verified packaging 26.3 installation above.

2026-11-10, Windows 네이티브 CPU 구성. **개발환경 완성 기준 미충족.**

## 실행 및 결과

| 실행 | 결과 |
|---|---|
| uv --version | 성공: 0.12.11 |
| python --version | 기본 PATH 3.12.10 |
| uv --no-cache python list --only-installed | 성공: uv Python 3.12.14, 3.14.7 및 시스템 Python 목록 확인 |
| Get-CimInstance Win32_OperatingSystem/Processor/ComputerSystem/VideoController | 접근 거부 0x80041003 |
| nvidia-smi | 명령 찾을 수 없음; NVIDIA 없음의 완전한 증거로 보지 않음 |
| uv python list (기본 캐시) | 기본 캐시 접근 거부 |
| uv lock (프로젝트 로컬 캐시) | PyPI pyyaml 접속 실패, socket 10013, 재시도 소진 |
| uv venv --python 3.12 | 성공: .venv 생성, 기존 uv 관리 Python 3.12.14 사용 |
| uv lock --offline | 실패: 로컬 캐시에 aiosqlite 메타데이터 부재 |
| uv sync --locked --offline | 실패: uv.lock 부재 |
| uv sync --locked | 실패: uv.lock 부재 |
| uv pip check --python .venv/Scripts/python.exe | 0개 패키지 검사 통과; 프로젝트 의존성 충족 증거가 아님 |
| .venv/Scripts/python.exe scripts/survey_environment.py | 성공, outputs/hardware.json 저장 |
| .venv/Scripts/python.exe scripts/validate_environment.py --dummy | 종료 코드 1, 33개 실패, outputs/environment_validation.json 저장 |

마지막 검증에서 Python 3.12 검사와 SQLite in-memory schema 생성은 성공했다. 28개 서드파티 import와 tensor, detection 클래스 import, Faster R-CNN/RetinaNet/YOLOS 더미 검사 5개가 실패했다. 모두 미설치 패키지에 따른 ModuleNotFoundError/PackageNotFoundError이며, 모델 알고리즘 오류나 해결 불가능한 의존성 충돌이 발견되었다는 의미는 아니다.

## 검증 단계 구분

- Python 및 프로젝트 내부 가상환경: 생성/실행 성공.
- 공통 라이브러리/PyTorch/OpenAI SDK/FastAPI/Streamlit/Plotly: 미설치, import 실패.
- Faster R-CNN/RetinaNet: 모델 생성·더미 추론 시도 실패(torch 부재).
- YOLOS: 축소 config 생성·더미 추론 시도 실패(torch 부재). 정규 모델 추론 검증 아님.
- RT-DETRv2: 클래스 import 실패, 생성·더미 추론 미검증.
- anomalib 4종/YOLO11: 설치 정의만 준비, 모델 import/생성/더미 추론 미검증.
- UniAD/HVQ-Trans/ViTDet: 환경 제약 조사, 미설치/미검증.
- 실제 데이터 추론/성능/속도/메모리 측정: 전부 미검증.
- API 유료 호출/학습/데이터 및 가중치 다운로드: 수행하지 않음.

## 검증 자동화

validate_environment.py는 네트워크 socket 연결을 차단하고 Hugging Face offline 변수를 설정한다. OpenAI 클라이언트를 생성하거나 API 키를 읽거나 출력하지 않는다. torchvision은 weights=None/weights_backbone=None, YOLOS는 로컬 축소 config만 사용한다. 실패를 JSON으로 기록하고 0이 아닌 종료 코드를 반환한다. setup.ps1은 각 uv 단계 종료 코드를 확인하여 실패 후 설치를 계속하지 않는다.

```powershell
Set-Location 'C:\Users\user1\jogeonug\MV'
# 네트워크 가능한 실행 세션에서 잠금 생성/설치/검증:
powershell -NoProfile -File scripts/setup.ps1 -Resolve -Models
# 이후 잠금 환경 재현:
uv sync --locked
uv pip check --python .venv/Scripts/python.exe
.venv/Scripts/python.exe scripts/validate_environment.py --dummy
```

설치 후 outputs/environment_validation.json의 package version을 ENVIRONMENT_SETUP.md에 반영하고 uv.lock과 함께 보관한다. 네트워크 제한을 해소하기 전에는 실행 준비 완료라고 판단하지 않는다. 이번 제한은 자동 승인 심사 거절이 아니라 실제 소켓 접근 오류다.

## 모델 실험 시작 전

1. uv lock/sync/import/더미 추론을 먼저 통과한다. anomaly/detection 환경은 각 폴더에서 별도 lock/sync/import 검증한다.
2. Real-IAD의 제품 ID별 분할 manifest를 고정해 5시점이 train/test에 갈라지는 누수를 방지한다. 현재 데이터 분석은 수행하지 않았다.
3. configs/experiment.example.yaml의 모델 버전, 실제 camera ID, manifest/lock hash, 임계값, 보류 정책을 채운다. 이 템플릿은 실험 실행기가 아니다.
4. anomaly 정상 특징 bank/교사/encoder 가중치와 detection 학습 checkpoint를 명시적으로 준비한다. constructor의 자동 다운로드도 별도 확인한다.
5. 랜덤 모델 smoke test부터 시작할 명령은 아래다. **실제 Real-IAD 학습·추론 실행기는 요청 범위 밖이라 아직 없으며, 시작 명령을 만들어낸 상태가 아니다.**

```powershell
.venv/Scripts/python.exe scripts/validate_environment.py --dummy
```

## 평가 기록 규약

configs/experiments.sql은 experiments/metrics/artifacts 테이블을 준비하며 생성 자체는 in-memory DB에서 검증했다. 실험 DB/모델 승인 도구는 구현하지 않았다. run마다 모델/commit/config/seed/데이터 및 분할 hash/lock hash/장치와 artifact hash를 기록한다.

제품 recall/precision/F1/FPR은 보류를 어떻게 분모에 처리하는지 함께 기록하며, hold_rate 및 coverage를 별도로 보고한다. 임계값은 검증 집합에서 정하고 test에 맞춰 변경하지 않는다. 위치 AP/Recall은 IoU 기준, AUPRO는 FPR 적분 범위(예: 0~0.3), 작은 결함은 픽셀/면적 기준을 사전 고정한다. COCO AP_small은 원래 픽셀 면적 기준이며 단순 resize 후 결과와 혼동하지 않는다.

시간은 워밍업 후 단일 시점과 제품 5시점 전체를 별도 측정한다. 제품 지연을 단순히 한 시점 p95의 5배로 대체하지 않는다. 전처리/전송/집계 포함 여부와 병렬도를 기록한다. CUDA 측정은 synchronize 후 수행한다. psutil RSS 표본으로 CPU peak를 관찰하고 GPU는 reset_peak_memory_stats/max_memory_allocated를 사용하되 예약 메모리 및 드라이버 전체 사용량과 구분한다. 아직 어느 모델의 성능도 측정하지 않았다.
