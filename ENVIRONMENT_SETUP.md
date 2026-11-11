# 개발환경 구축 기록

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

조사일: 2026-11-10. **부분 구축: 네트워크 제한으로 의존성 설치 및 uv.lock 생성 미완료. 모델 실험 시작 불가.**

## 실측 환경

| 항목 | 확인 결과 |
|---|---|
| OS | Windows 11, build 26200, 25H2; 레지스트리 ProductName은 Windows 10 Pro로 남아 있음 |
| PowerShell | 5.1.26100.9711 |
| uv | 0.12.11 (4b53f66b7, x86_64-pc-windows-msvc) |
| 기본 PATH Python | 3.12.10 |
| 프로젝트 .venv Python | CPython 3.12.14, uv에 이미 설치된 인터프리터 사용 |
| 다른 설치 Python | uv 목록에 3.14.7도 존재, 본 프로젝트에서는 사용하지 않음 |
| CPU | 12th Gen Intel Core i5-12400 |
| RAM | 16,908,730,368 bytes, 약 15.75 GiB |
| GPU | EnumDisplayDevicesW에서 Intel UHD Graphics 730 확인; 동일 장치가 화면별로 중복 열거됨 |
| NVIDIA / CUDA | nvidia-smi 명령 없음; 드라이버 버전 및 CUDA 사용 여부 미검증 |
| 디스크 | 총 약 475.8 GiB, 초기 여유 약 83.24 GiB |
| 기존 파일 | dataset/, RealIAD_OpenCV_Analysis_Assignment_v2/, RealIAD_ScikitImage_Analysis_Assignment_v2/ 보존 |
| 초기 루트 설정 | pyproject.toml, uv.lock, .venv 없음. 분석 과제 설정은 수정하지 않음 |

CIM OS/CPU/RAM/GPU 조회는 0x80041003 권한 오류. CPU는 레지스트리, RAM은 GlobalMemoryStatusEx, GPU는 EnumDisplayDevicesW, 디스크는 shutil.disk_usage로 보완했다. 상세 실측값: outputs/hardware.json. 데이터 내용 분석은 수행하지 않았다.

## 구성

```text
MV/
  pyproject.toml            # Windows AMD64, Python 3.12, CPU PyTorch index
  .python-version
  .venv/                   # 생성 완료, 서드파티 패키지 0개
  .env / .env.example      # 빈 키와 모델 변수; .env는 Git 제외
  .gitignore
  environments/
    anomaly/pyproject.toml # anomalib: 별도 lock/.venv 예정
    detection/pyproject.toml # YOLO11 ultralytics: 별도 lock/.venv 예정
    export/pyproject.toml  # ONNX 계열: 향후 설치
    specialized/README.md # UniAD/HVQ-Trans/ViTDet 격리 계획
  src/
    models/anomaly/ models/detection/
    evaluation/ inference/ agent/ dashboard/ database/
  configs/
    experiment.example.yaml
    experiments.sql
    agent.example.yaml
  scripts/
    setup.ps1
    survey_environment.py
    validate_environment.py
  tests/ checkpoints/ outputs/
```

src는 디렉터리만 준비했다. 학습기, 실제 모델 어댑터, 에이전트 도구, 대시보드 앱은 구현하지 않았다. uv.lock은 생성 실패했으므로 트리에 포함하지 않았다. 현재 pyproject 의존성은 설치 요청 명세이며 버전 고정이 완료된 환경이 아니다.

## 의존성 구성과 실제 버전

**서드파티 설치 버전: 없음.** Python 3.12.14와 uv 0.12.11만 실측 확인했다. 실패한 설치를 성공한 버전 목록으로 기재하지 않았다.

- 공통 실험: torch, torchvision, numpy, scipy, scikit-learn, pandas, Pillow, opencv-python, matplotlib, seaborn, tqdm, PyYAML, psutil, timm, einops, transformers, safetensors.
- 평가: torchmetrics, pycocotools. AUPRO는 anomalib 별도 환경의 지표 사용 예정. 제품 지표는 scikit-learn, 비용 측정은 time/psutil/torch.cuda 사용 예정.
- 에이전트 준비: openai, pydantic, python-dotenv, fastapi, uvicorn, sqlalchemy, aiosqlite. FastAPI는 향후 조회 API, SQLAlchemy/aiosqlite는 SQLite 접근용.
- 대시보드 준비: streamlit, plotly. 3D 학습 패키지는 추가하지 않음. mesh/부위 ID/카메라 근거 연결은 향후 구현.
- MLflow는 설치 비용 대비 현재 필요성이 낮아 보류. 로컬 JSON/CSV + SQLite 구조 준비.

anomaly/detection/export는 uv workspace 멤버로 묶지 않은 **독립 프로젝트**다. 각 프로젝트의 uv.lock/.venv로 분리한다. 일반 dependency groups는 충돌을 격리하지 않으므로 사용하지 않았다. anomalib의 opencv-python-headless와 공통 환경 opencv-python의 cv2 중복도 분리로 방지한다. 현재 충돌 해결 성공을 의미하지 않으며, 실제 resolver 성공 여부는 미검증이다. [uv 의존성 관리](https://docs.astral.sh/uv/concepts/projects/dependencies/)

## 재시도 및 재현

현재 도구 실행 환경은 기본 cwd를 C:\로 잡는 경우가 있어 반드시 먼저 경로를 지정한다. 기본 uv cache 접근도 거부되어 각 pyproject에 프로젝트 내부 .uv-cache를 지정했다.

```powershell
Set-Location 'C:\Users\user1\jogeonug\MV'
uv --version
uv venv --python 3.12
# 다음은 PyPI 및 PyTorch 공식 인덱스에 접속 가능한 세션에서 최초 1회:
uv lock
uv sync --locked
uv pip check --python .venv/Scripts/python.exe
.venv/Scripts/python.exe scripts/validate_environment.py --dummy
```

자동 실행(현재 네트워크 제한에서는 실패가 정상):

```powershell
powershell -NoProfile -File scripts/setup.ps1 -Resolve -Models
# uv.lock 생성 후 재현할 때에는 Resolve 없이 실행:
powershell -NoProfile -File scripts/setup.ps1 -Models
```

uv.lock 생성 성공 후 버전 검토와 함께 커밋해야 재현성이 확보된다. .venv/.uv-cache/.env/데이터/체크포인트/출력 DB는 커밋하지 않는다. 현재 존재하는 .venv를 다시 만들기 위해 삭제할 필요는 없다.

독립 환경 설치는 필요할 때 해당 폴더로 이동하여 uv lock, uv sync --locked 실행. 루트의 명령은 하위 환경을 설치하지 않는다. export 환경은 이번 단계에 설치하지 않았다.

## CPU/GPU

현재 CPU 공식 wheel index를 torch와 torchvision에만 explicit하게 지정했다. Intel 내장 GPU를 CUDA로 취급하지 않는다. [PyTorch 공식 설치 안내](https://pytorch.org/get-started/locally/)

NVIDIA GPU를 추가하거나 확인하면 nvidia-smi로 장치/드라이버를 확인하고 공식 설치 선택기의 Windows/Python/CUDA 조합을 선택한다. 별도 GPU 프로젝트에 동일 의존성을 복사하고 torch/torchvision source index를 검증된 CUDA index로 바꾼 후 새 lock을 만든다. 현재 CPU lock을 GPU용이라고 재사용하면 안 된다. 현재는 CUDA 빌드/드라이버 조합을 검증하지 않았다.

배포된 PyTorch 바이너리로 통상 실행할 때에는 호환 NVIDIA 드라이버와 wheel 내 런타임으로 가능하다. 로컬 CUDA Toolkit은 PyTorch 소스 빌드 또는 CUDA 확장 컴파일 시 필요하며, 그 경우 Windows MSVC 등 빌드 도구도 필요하다. 시스템 변경이나 Toolkit 설치는 수행하지 않았다.

## 오류와 조치

1. 기본 uv 캐시 sdists-v9 접근 거부 → 프로젝트 내부 .uv-cache 사용.
2. PyPI 요청 실패, 소켓 오류 10013 → 네트워크 허용 세션 또는 조직의 승인된 패키지 미러 필요. 관리자/방화벽 변경을 시도하지 않음.
3. uv lock --offline → 캐시에 aiosqlite조차 없어 실패. 버전 충돌이 확인된 것은 아님.
4. uv sync --locked → uv.lock 부재로 실패. 빈/가짜 lock을 생성하지 않음.
5. uv pip check → 0개 패키지 검사 통과; 설치가 완료되었다는 의미가 아님.

## 에이전트와 대시보드 후속 준비

.env에 OPENAI_API_KEY와 OPENAI_MODEL 빈 변수를 준비했다. 향후 시작 코드에서 python-dotenv의 load_dotenv('.env', override=False)를 호출한 다음 환경 변수를 읽어야 한다. 자동 로딩 또는 실제 연결까지 구현한 상태는 아니다. 키를 출력하지 않고 API 요청도 하지 않았다. [OpenAI 공식 SDK 문서](https://developers.openai.com/api/docs/libraries)

configs/agent.example.yaml에 5개 도구 이름, 예측 변경 금지, 검수 확정/재학습/운영 교체의 별도 승인 원칙을 기록했다. 도구 구현은 없다. Streamlit/Plotly는 설치 요청만 준비됐으며 import/3D 렌더링은 미검증이다. 향후 Three.js와 같은 프런트엔드로 옮길 때 DB의 inspection_id, camera_id, region_id, model_version으로 2D 근거를 연결한다.

## 향후 고도화

environments/export는 onnx/onnxruntime/onnxscript + torch/torchvision 명세만 준비했다. INT8은 CPU ONNX Runtime의 동적/정적 양자화부터 모델별 연산자 지원과 정확도 비교를 검증한다. GPU Runtime은 CUDA/cuDNN 조건이 별도라 CPU Runtime과 무조건 함께 설치하지 않는다. PyTorch 양자화는 실제 선택 버전의 torch.ao/torchao 경로를 공식 문서로 재확인 후 추가한다. CNN/Attention/ViT/GAN은 기존 torch/timm으로 시작할 수 있어 별도 무거운 GAN 프레임워크는 추가하지 않았다. 주기적 재학습은 데이터 승인·모델 승인·롤백 정책 구현 전 자동 실행하지 않는다.
