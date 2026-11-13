#!/usr/bin/env bash
# 한글 안내: 환경 또는 배치 실행 진입점입니다. 프로젝트 위치·고정 의존성·출력 경로를 확인하세요.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v uv >/dev/null || { echo 'uv가 없습니다. docs/INSTALL_LINUX.md를 확인하세요.' >&2; exit 1; }
uv python find 3.12
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-2}"
export UV_CONCURRENT_INSTALLS="${UV_CONCURRENT_INSTALLS:-2}"
export UV_CONCURRENT_BUILDS="${UV_CONCURRENT_BUILDS:-1}"
uv sync --locked
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked pytest -q
