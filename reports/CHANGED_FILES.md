# GitHub 업로드 후보와 변경 파일

Push는 실행하지 않았다. 아래는 git ls-files --cached --others --exclude-standard로 확인한 로컬 후보다. 기존 미추적 Windows 문서와 .env.example은 보존 파일이며, 새로 생성한 분석 코드/문서와 구분한다.

| 파일 | 상태 |
|---|---|
| [.env.example](../.env.example) | 기존 파일 보존 |
| [.github/pull_request_template.md](../.github/pull_request_template.md) | 새 파일/문서 |
| [ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md) | 기존 파일 보존 |
| [ENVIRONMENT_VALIDATION.md](../ENVIRONMENT_VALIDATION.md) | 기존 파일 보존 |
| [MODEL_COMPATIBILITY.md](../MODEL_COMPATIBILITY.md) | 기존 파일 보존 |
| [README.md](../README.md) | 새 파일/문서 |
| [docs/ANALYSIS_PIPELINE.md](../docs/ANALYSIS_PIPELINE.md) | 새 파일/문서 |
| [docs/DATASET_SETUP.md](../docs/DATASET_SETUP.md) | 새 파일/문서 |
| [docs/ENVIRONMENT_VALIDATION.md](../docs/ENVIRONMENT_VALIDATION.md) | 새 파일/문서 |
| [docs/GIT_GITHUB_BEGINNER_GUIDE.md](../docs/GIT_GITHUB_BEGINNER_GUIDE.md) | 새 파일/문서 |
| [docs/INSTALL_LINUX.md](../docs/INSTALL_LINUX.md) | 새 파일/문서 |
| [docs/MIGRATION_AUDIT.md](../docs/MIGRATION_AUDIT.md) | 새 파일/문서 |
| [docs/TEAM_GIT_WORKFLOW.md](../docs/TEAM_GIT_WORKFLOW.md) | 새 파일/문서 |
| [docs/TEAM_ONBOARDING.md](../docs/TEAM_ONBOARDING.md) | 새 파일/문서 |
| [docs/archive/pyproject.windows.toml](../docs/archive/pyproject.windows.toml) | 새 파일/문서 |
| [docs/archive/uv.windows.lock](../docs/archive/uv.windows.lock) | 새 파일/문서 |
| [mv_analysis/__init__.py](../mv_analysis/__init__.py) | 새 파일/문서 |
| [mv_analysis/cli.py](../mv_analysis/cli.py) | 새 파일/문서 |
| [mv_analysis/core.py](../mv_analysis/core.py) | 새 파일/문서 |
| [mv_analysis/mask_validation.py](../mv_analysis/mask_validation.py) | 새 파일/문서 |
| [mv_analysis/report.py](../mv_analysis/report.py) | 새 파일/문서 |
| [mv_analysis/schema.py](../mv_analysis/schema.py) | 새 파일/문서 |
| [mv_analysis/stages.py](../mv_analysis/stages.py) | 새 파일/문서 |
| [notebooks/01_metadata_analysis.ipynb](../notebooks/01_metadata_analysis.ipynb) | 새 파일/문서 |
| [notebooks/02_brightness_analysis.ipynb](../notebooks/02_brightness_analysis.ipynb) | 새 파일/문서 |
| [notebooks/03_defect_heatmap.ipynb](../notebooks/03_defect_heatmap.ipynb) | 새 파일/문서 |
| [notebooks/04_bbox_annotation.ipynb](../notebooks/04_bbox_annotation.ipynb) | 새 파일/문서 |
| [notebooks/05_resolution_information_loss.ipynb](../notebooks/05_resolution_information_loss.ipynb) | 새 파일/문서 |
| [notebooks/06_integrated_report.ipynb](../notebooks/06_integrated_report.ipynb) | 새 파일/문서 |
| [pyproject.toml](../pyproject.toml) | 기존 설정 수정 |
| [reports/ANALYSIS_EXECUTION_LOG.md](../reports/ANALYSIS_EXECUTION_LOG.md) | 새 파일/문서 |
| [reports/ENVIRONMENT_MIGRATION_REPORT.md](../reports/ENVIRONMENT_MIGRATION_REPORT.md) | 새 파일/문서 |
| [reports/FINAL_PYTEST_RESULTS.txt](../reports/FINAL_PYTEST_RESULTS.txt) | 새 파일/문서 |
| [reports/GIT_UPLOAD_SAFETY.json](../reports/GIT_UPLOAD_SAFETY.json) | 새 파일/문서 |
| [reports/INSTALL_FAILURE_LOG.md](../reports/INSTALL_FAILURE_LOG.md) | 새 파일/문서 |
| [reports/MASK_THRESHOLD_VALIDATION.md](../reports/MASK_THRESHOLD_VALIDATION.md) | 새 파일/문서 |
| [reports/REAL_IAD_FINAL_ANALYSIS.md](../reports/REAL_IAD_FINAL_ANALYSIS.md) | 새 파일/문서 |
| [reports/WINDOWS_COUNT_DIFFERENCE_EVIDENCE.json](../reports/WINDOWS_COUNT_DIFFERENCE_EVIDENCE.json) | 새 파일/문서 |
| [reports/dataset_inventory.json](../reports/dataset_inventory.json) | 새 파일/문서 |
| [reports/early_bbox_annotation_issues.json](../reports/early_bbox_annotation_issues.json) | 새 파일/문서 |
| [reports/layout_precheck.json](../reports/layout_precheck.json) | 새 파일/문서 |
| [reports/lock_comparison.json](../reports/lock_comparison.json) | 새 파일/문서 |
| [reports/preflight_environment.txt](../reports/preflight_environment.txt) | 새 파일/문서 |
| [reports/preflight_passed.json](../reports/preflight_passed.json) | 새 파일/문서 |
| [reports/preflight_pytest.txt](../reports/preflight_pytest.txt) | 새 파일/문서 |
| [scripts/approve_mask_policy.py](../scripts/approve_mask_policy.py) | 새 파일/문서 |
| [scripts/audit_content_hashes.py](../scripts/audit_content_hashes.py) | 새 파일/문서 |
| [scripts/audit_mask_integrity.py](../scripts/audit_mask_integrity.py) | 새 파일/문서 |
| [scripts/check_git_safety.py](../scripts/check_git_safety.py) | 새 파일/문서 |
| [scripts/continue_image_analysis.py](../scripts/continue_image_analysis.py) | 새 파일/문서 |
| [scripts/defect_relative_brightness.py](../scripts/defect_relative_brightness.py) | 새 파일/문서 |
| [scripts/enrich_analysis_results.py](../scripts/enrich_analysis_results.py) | 새 파일/문서 |
| [scripts/finish_image_analysis.py](../scripts/finish_image_analysis.py) | 새 파일/문서 |
| [scripts/finish_spatial_analysis.py](../scripts/finish_spatial_analysis.py) | 새 파일/문서 |
| [scripts/inventory_dataset.py](../scripts/inventory_dataset.py) | 새 파일/문서 |
| [scripts/prepare_quality_manifest.py](../scripts/prepare_quality_manifest.py) | 새 파일/문서 |
| [scripts/record_preflight.py](../scripts/record_preflight.py) | 새 파일/문서 |
| [scripts/render_heatmaps.py](../scripts/render_heatmaps.py) | 새 파일/문서 |
| [scripts/resolution_batch.py](../scripts/resolution_batch.py) | 새 파일/문서 |
| [scripts/review_defect_resolution.py](../scripts/review_defect_resolution.py) | 새 파일/문서 |
| [scripts/run_resolution_batches.sh](../scripts/run_resolution_batches.sh) | 새 파일/문서 |
| [scripts/setup.sh](../scripts/setup.sh) | 새 파일/문서 |
| [scripts/train_brightness_policies.py](../scripts/train_brightness_policies.py) | 새 파일/문서 |
| [scripts/update_project_reports.py](../scripts/update_project_reports.py) | 새 파일/문서 |
| [scripts/validate_artifacts.py](../scripts/validate_artifacts.py) | 새 파일/문서 |
| [scripts/validate_detection_exports.py](../scripts/validate_detection_exports.py) | 새 파일/문서 |
| [scripts/validate_environment.py](../scripts/validate_environment.py) | 새 파일/문서 |
| [scripts/validate_mask_thresholds.py](../scripts/validate_mask_thresholds.py) | 새 파일/문서 |
| [tests/test_pipeline.py](../tests/test_pipeline.py) | 새 파일/문서 |
| [uv.lock](../uv.lock) | 기존 설정 수정 |
| [.gitignore](../.gitignore) | 기존 설정 수정 |

dataset/outputs/.venv/.uv-cache/가중치/.env는 업로드 후보에서 제외됐다. 실제 stage/commit 전 git diff --cached를 사용자가 다시 검토한다. 개인 브랜치에서 commit/PR을 만들며 Push는 사용자가 직접 수행한다.