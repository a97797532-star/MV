#!/usr/bin/env bash
# 한글 안내: 환경 또는 배치 실행 진입점입니다. 프로젝트 위치·고정 의존성·출력 경로를 확인하세요.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mv_run_dir="${1:?Usage: bash scripts/run_resolution_batches.sh outputs/RUN [batch_size]}"
mv_batch_size="${2:-5000}"
while true; do
  uv run --locked python scripts/resolution_batch.py --run "$mv_run_dir" --batch-size "$mv_batch_size"
  mv_remaining="$(uv run --locked python -c 'import json,sys; from pathlib import Path; print(json.loads((Path(sys.argv[1])/"resolution_batch_status.json").read_text())["pending"])' "$mv_run_dir")"
  if [[ "$mv_remaining" == 0 ]]; then break; fi
done
uv run --locked python scripts/resolution_batch.py --run "$mv_run_dir" --batch-size 1 --finalize
uv run --locked python scripts/enrich_analysis_results.py "$mv_run_dir"
uv run --locked python scripts/validate_artifacts.py "$mv_run_dir"
echo "Image resolution analysis completed. Refresh the integrated report using update_project_reports.py and the run's related_runs.json."
