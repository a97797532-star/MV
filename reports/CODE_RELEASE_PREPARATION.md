# MV 공통 코드 배포 검증 기록

확인일: 2026-11-13. 코드 Commit과 실제 원격 반영은 구분한다. 사용자가 Commit 후 Push도 명시적으로 승인했다. 이 문서는 최종 배포 직전의 검증 증거이며 원격 반영 여부는 GitHub main의 Commit과 로컬 HEAD를 대조해 확인한다.

## 코드 Commit

- `614fe82 feat: add shared Real-IAD loaders and Korean code guidance`
- `5b0babd build: share portable loader checks and validation tools`
- `c11a3b6 feat: share crop review and preprocessing experiment tools`
- `515aa07 test: add dataset and crop regression coverage`
- `8a0c329 build: define private canonical data handoff and release schema`

이후 검증 기록 문서만 추가 Commit한다. 기존 문서 Commit 1fcd00b를 중복 생성하거나 이력을 다시 쓰지 않았다. 각 단계에서 명시한 파일만 Stage하고 전체 git diff --cached를 보존·검토했다. git add .는 사용하지 않았다.

## 실제 검증

| 구분 | 결과 | 검증 범위 |
|---|---|---|
| 기존 작업 폴더 | 145 passed, 경고1 | 합성/좌표/라벨/Single/Five/12입력Adapter/로컬HTTP |
| 새 로컬 Clone | 145 passed, 경고1 | 비공개 outputs·dataset 없이 새 .venv, import 경로도 Clone 내부 확인 |
| 새 환경 설치 | 170개 패키지 성공 | Python3.12.14, uv sync --locked --offline; 기존 패키지 캐시 재사용 |
| 환경 dummy | failed=[] | CPU tensor/NMS/OpenCV/import |
| 합성 Smoke | 10장/2제품/12Adapter 통과 | 양성·빈·미제공 마스크, 5시점 배치(2,5,3,256,256) |
| 실제 v2 Smoke | 10장/2제품/12Adapter 통과 | 기존 저장 좌표 그대로 사용. 4개 유효NG/1개미주석NG/5개OK |
| UI 모의 테스트 | 15/17/31 검사 통과 | Node DOM/image 모의검사. 실제 브라우저 화면은 UNVERIFIED |
| 원본 보호 | 지정6개 파일 SHA 동일 | uv.lock, 기준/v1/v2 CSV, Crop Ledger, 제품GT Ledger |
| 변경분 공개 검사 | 금지 산출물0 | 원본/마스크/weights/.env/JSONL/대형결과 제외, 자격증명 패턴과 개인경로 검사 |

새 Clone은 로컬 Git 저장소에서 복제했다. 인터넷을 통한 cold Clone/패키지 다운로드와 팀원4명 개별 설치 성공은 검증하지 않았다. 전체145개 중 경고1개는 기존 NumPy timedelta 사용 중단 경고다. 12개 실모델 생성/forward/학습/성능 비교, 가중치 다운로드, 유료API 호출은 수행하지 않았다.

## 한글 주석 보강

프로젝트 자체 소스133개(그중Python125개)에 파일 역할·함수 처리·입력 설명을 보강했다. 원본 좌표, 결측 NG, 사람 승인, 중복 Normalize/Crop과 배치 타깃의 주의점을 한글로 설명한다. 외부 모델 소스와 legacy/windows_snapshot은 수정하지 않았다.

주석 보강 전후 Python AST를 비교했다. 124개는 동일하고, finalize_data_loader_validation.py 한 파일은 문서 예제의 개인 절대 경로만 일반 예제로 바꿨다. 별도로 새 이식 가능한 Smoke 명령과 회귀 테스트를 추가했다. 기존 분석 결과와 체크포인트는 수정하지 않았다. 주석 변경도 소스 해시를 바꾸므로 과거 체크포인트를 새 소스에 맞게 강제로 통과시키지 않는다. 변경 전 소스·해시와 단계별 staged diff는 Git 제외된 outputs/code_release_preparation_20261113_v1에 보존한다.

## Canonical Manifest

- 실제151,050행 CSV는 Git에 넣지 않았다. 약113MiB이며 개인 절대 경로/검수 필드가 있어 공개 권한 확인이 필요하다.
- 접근 제한 팀 배포 방식으로 수령한다. 승인 Ledger 원본은 공통 로더 실행에 필요한 배포물이 아니다.
- 버전·크기·해시 식별자: [canonical_manifest.release.json](../configs/data/canonical_manifest.release.json).
- 배포 스키마: [행 스키마](../schemas/preprocessing_manifest.schema.json).
- v2 hash: `d1c13cae3fc352f457cb22f9955280e0ce140827a449465d5e05519fd6c9073d`.
- v2 전체 좌표/그룹/승인 일치와 변경43장 마스크 보존은 확인했다. 새 v2 전체 타깃 계약/eligibility 고정은 아직 별도 작업이다.

## 원격 반영 대상과 제외 대상

필수 공통 로더·전처리·Resolver·환경/데이터 검사·검증·테스트 코드는 모두 Commit했다. pyproject.toml과 uv.lock은 이미 추적된 동일 버전으로 유지했다. 12개 모델의 실제 학습 엔트리포인트는 아직 구현되지 않았으므로 배포 완료라고 주장하지 않는다.

원본JPG/PNG, 개인데이터, .venv/.env, 키, 모델weights, 외부소스캐시, 승인원장, 전체Manifest/NPY/Parquet, 결과ZIP/PDF는 이번 변경 Commit에 없다. 공개 검토를 마치지 않은 로컬 보고서·통계·PDF/ZIP은 미추적 또는ignore 상태로 보존한다. 기존에 이미 추적된 과거 문서는 이력에서 삭제하지 않았다.

## 팀원 실행

원본 main 반영 후 개인Fork에서 최신 main을 동기화하고 [공통 코드 배포 안내](../docs/team/CODE_RELEASE.md)를 따른다. 데이터 없이 먼저 아래를 실행할 수 있다.

```bash
uv sync --locked
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked python scripts/smoke_test_shared_data.py --synthetic
uv run --locked pytest -q
```

실데이터는 승인된4개Canonical파일과원본데이터를별도로받아 개인 data_root로 Smoke를 실행한다. 오래된 v1 eligibility를 v2 학습의 확정 계약으로 쓰지 않는다.

## Push 대상

`origin = https://github.com/whrjsdnr/MV.git`, 대상 브랜치 main을 확인했다. 최종 Fetch 후 원격이 선행하지 않는지 확인하고 아래 명령만 사용한다. 강제 Push/Reset/Clean/무단Merge는 하지 않는다.

```bash
git push origin main
```

## Commit별 파일 목록

### shared_loaders (23개)

- `mv_analysis/__init__.py`
- `mv_analysis/adaptive_crop_gate.py`
- `mv_analysis/background_brightness.py`
- `mv_analysis/cli.py`
- `mv_analysis/core.py`
- `mv_analysis/crop_manifest.py`
- `mv_analysis/data/__init__.py`
- `mv_analysis/data/adapters.py`
- `mv_analysis/data/collate.py`
- `mv_analysis/data/datasets.py`
- `mv_analysis/data/manifest.py`
- `mv_analysis/data/targets.py`
- `mv_analysis/legacy_bridge.py`
- `mv_analysis/mask_validation.py`
- `mv_analysis/object_aware_crop.py`
- `mv_analysis/presence_heatmaps.py`
- `mv_analysis/regional_cli.py`
- `mv_analysis/report.py`
- `mv_analysis/schema.py`
- `mv_analysis/splits.py`
- `mv_analysis/stages.py`
- `mv_analysis/yolo_center_hybrid.py`
- `mv_analysis/yolo_crop_geometry.py`

### environment_validation (25개)

- `scripts/check_git_safety.py`
- `scripts/finalize_data_loader_validation.py`
- `scripts/inventory_dataset.py`
- `scripts/record_preflight.py`
- `scripts/resolve_filename_class_conflicts.py`
- `scripts/select_final_preprocessing.py`
- `scripts/setup.sh`
- `scripts/smoke_test_data_loaders.py`
- `scripts/smoke_test_shared_data.py`
- `scripts/validate_artifacts.py`
- `scripts/validate_bbox_review_server.py`
- `scripts/validate_crop_range_review.py`
- `scripts/validate_detection_exports.py`
- `scripts/validate_environment.py`
- `scripts/validate_filename_class_resolution.py`
- `scripts/validate_final_preprocessing_decode.py`
- `scripts/validate_known_loader_cases.py`
- `scripts/validate_mask_thresholds.py`
- `scripts/validate_object_aware_crop.py`
- `scripts/validate_pdf_report.py`
- `scripts/validate_regional_results.py`
- `scripts/validate_resolution_results.py`
- `scripts/validate_yolo11_offline_experiment.py`
- `scripts/verify_bbox_backend_parity.py`
- `scripts/verify_source_preservation.py`

### preprocessing_experiments (68개)

- `scripts/adaptive_crop_gate_experiment.py`
- `scripts/analyze_cross_relations.py`
- `scripts/analyze_preprocessing_evidence.py`
- `scripts/approve_mask_policy.py`
- `scripts/attach_resolution_metadata.py`
- `scripts/audit_content_hashes.py`
- `scripts/audit_full_crop_manifest.py`
- `scripts/audit_mask_integrity.py`
- `scripts/build_analysis_gallery.py`
- `scripts/build_preprocessing_review_package.py`
- `scripts/build_visual_crop_reports.py`
- `scripts/collect_model_preprocessing_sources.py`
- `scripts/compare_windows_brightness_groups.py`
- `scripts/compare_windows_checkpoints.py`
- `scripts/compare_windows_heatmaps.py`
- `scripts/compare_windows_results.py`
- `scripts/continue_image_analysis.py`
- `scripts/crop_range_review.html`
- `scripts/crop_range_review.js`
- `scripts/defect_relative_brightness.py`
- `scripts/enrich_analysis_results.py`
- `scripts/evaluate_yolo_center_hybrid.py`
- `scripts/export_detailed_pdf.py`
- `scripts/export_resolution_meeting_pdf.py`
- `scripts/extend_full_crop_report_manual.py`
- `scripts/finalize_adaptive_crop_report.py`
- `scripts/finalize_preprocessing_review_package.py`
- `scripts/finish_image_analysis.py`
- `scripts/finish_spatial_analysis.py`
- `scripts/freeze_adaptive_crop_gate_recovery.py`
- `scripts/full_crop_gt_validation.py`
- `scripts/generate_full_crop_manifest.py`
- `scripts/materialize_yolo_center_hybrid.py`
- `scripts/object_aware_crop_experiment.py`
- `scripts/object_crop_aligned_quality.py`
- `scripts/polish_adaptive_crop_figures.py`
- `scripts/prepare_manual_crop_review.py`
- `scripts/prepare_quality_manifest.py`
- `scripts/prepare_shared_report_links.py`
- `scripts/product_bbox_review.html`
- `scripts/product_bbox_review.js`
- `scripts/publish_analysis_branch.py`
- `scripts/render_all_pdf_pages.py`
- `scripts/render_heatmaps.py`
- `scripts/render_pipeline_diagram.py`
- `scripts/render_regional_review.py`
- `scripts/report_adaptive_crop_gate.py`
- `scripts/report_background_brightness.py`
- `scripts/report_full_crop_manifest.py`
- `scripts/report_object_aware_crop.py`
- `scripts/report_resolution_detail.py`
- `scripts/report_yolo11_dynamic_crop.py`
- `scripts/resolution_batch.py`
- `scripts/restore_windows_analysis_split.py`
- `scripts/resume_adaptive_crop_gate.py`
- `scripts/resume_preprocessing_review.py`
- `scripts/reuse_verified_product_boxes.py`
- `scripts/review_crop_gate_bboxes.py`
- `scripts/review_crop_ranges.py`
- `scripts/review_defect_resolution.py`
- `scripts/review_loader_findings.py`
- `scripts/review_product_bboxes.py`
- `scripts/run_presence_heatmaps.py`
- `scripts/run_resolution_batches.sh`
- `scripts/train_brightness_policies.py`
- `scripts/update_project_reports.py`
- `scripts/write_model_input_evidence.py`
- `scripts/yolo11_offline_crop_experiment.py`

### regression_tests (17개)

- `tests/crop_range_review_ui.cjs`
- `tests/product_bbox_review_ui.cjs`
- `tests/test_adaptive_crop_freeze_recovery.py`
- `tests/test_adaptive_crop_gate.py`
- `tests/test_background_brightness.py`
- `tests/test_crop_gate_review.py`
- `tests/test_crop_manifest.py`
- `tests/test_crop_range_review.py`
- `tests/test_data_loading.py`
- `tests/test_full_crop_generation.py`
- `tests/test_object_aware_crop.py`
- `tests/test_pipeline.py`
- `tests/test_preserved_contracts.py`
- `tests/test_product_bbox_review.py`
- `tests/test_product_bbox_review_http.py`
- `tests/test_shared_smoke.py`
- `tests/test_yolo_crop_geometry.py`

### release_contract (13개)

- `.gitignore`
- `.github/pull_request_template.md` (대소문자 중복 템플릿 정리)
- `README.md`
- `docs/team/CODE_RELEASE.md`
- `docs/GIT_GITHUB_BEGINNER_GUIDE.md`
- `docs/TEAM_GIT_WORKFLOW.md`
- `docs/TEAM_ONBOARDING.md`
- `docs/MANUAL_CROP_REVIEW.md`
- `docs/PREPROCESSING_METADATA.md`
- `docs/PRODUCT_BBOX_REVIEW.md`
- `configs/data/canonical_manifest.release.json`
- `schemas/preprocessing_manifest.schema.json`
- `reports/MODEL_INPUT_REQUIREMENTS.md`
