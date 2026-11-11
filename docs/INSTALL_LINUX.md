# WSL2 Ubuntu 설치

Windows의 WSL2 Ubuntu 터미널에서 실행한다. 이 문서의 실제 검증 대상은 Ubuntu 24.04 x86_64, Python 3.12이다. WSL 설치 자체가 필요한 팀원은 Windows PowerShell에서 `wsl --install -d Ubuntu-24.04`를 실행하고 재부팅/계정 생성을 마친다. 회사 장비 권한은 관리자에게 확인한다.

```bash
cat /etc/os-release
uname -a
sudo apt update
sudo apt install -y git curl libgl1 libglib2.0-0
```

OS와 WSL 커널을 확인하고 Git·다운로드 도구·OpenCV 런타임을 설치한다. sudo는 Ubuntu 비밀번호를 요구할 수 있다. 패키지를 못 찾으면 배포판/네트워크를 확인한다. 시스템 Python을 교체하지 않는다.

[uv 공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)에 따라 uv를 설치한다. 설치 스크립트는 먼저 내려받아 검토한다.

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/mv-uv-install.sh
less /tmp/mv-uv-install.sh
sh /tmp/mv-uv-install.sh
source "$HOME/.local/bin/env"
uv --version
uv python install 3.12
```

uv 설치는 프로젝트 의존성 설치와 다르다. curl DNS/인증서 오류는 네트워크를 확인하고 보안 검사를 끄지 않는다. Python 설치는 Python 런타임만 받으며 데이터나 모델을 받지 않는다. 기존 3.12가 있으면 그대로 사용할 수 있다.

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/whrjsdnr/MV.git
cd MV
bash scripts/setup.sh
```

프로젝트 루트에서 setup을 실행하면 Python 확인, `uv sync --locked`, offline 더미 검증, pytest 순으로 실행하며 하나라도 실패하면 중단한다. 다른 프로젝트의 VIRTUAL_ENV 경고가 있으면 `deactivate` 후 실행한다. 프로젝트 .venv는 별개다. `uv.lock`을 삭제하거나 무작정 재생성하지 않는다. Linux 플랫폼 불일치라면 이 변경이 반영된 pyproject/lock을 함께 받았는지 확인한다.

```bash
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked pytest -q
uv pip check
```

검증 JSON은 `outputs/environment/<UTC 실행시각>/validation.json`에 보존한다. failed가 빈 배열이어야 통과다. pytest exit 0과 passed 수를 함께 확인한다. 실제 데이터 검사는 [DATASET_SETUP.md](DATASET_SETUP.md)를 따른다.

## 선택 CUDA

기본 lock은 CPU이다. NVIDIA Windows 드라이버와 WSL GPU 노출을 먼저 준비하고 Ubuntu에서 `nvidia-smi`를 확인한다. WSL 안에 임의로 Linux 디스플레이 드라이버를 설치하지 않는다. CUDA 실험은 별도 디렉터리·pyproject·lock으로 만들고 [PyTorch 공식 설치 선택기](https://pytorch.org/get-started/locally/)에서 해당 드라이버/버전에 맞는 명령을 확인한다. `torch.cuda.is_available()`와 실제 GPU 텐서 연산을 별도로 검증한다. 이 작업에서는 CUDA 환경이나 12종 모델 독립 환경을 구축했다고 주장하지 않는다.


setup.sh는 cold install의 메모리 압박을 줄이도록 다운로드/설치 동시성 2, 빌드 동시성 1을 기본값으로 사용한다. 기존 UV_CONCURRENT_* 환경변수가 있으면 그 값을 유지한다. 이는 패키지 버전이나 잠금 파일을 바꾸지 않는다.
