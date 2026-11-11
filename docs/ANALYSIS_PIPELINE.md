# 통합 분석 실행

프로젝트 루트에서 실행한다. 모든 실행은 새 UTC outputs 폴더를 만들고 원본을 쓰지 않는다. 출력 경로를 직접 지정할 때 이미 존재하면 실패한다. 같은 실행을 이어갈 때만 `--resume`을 명시하고 데이터 경로·limit·class-policy·lock을 유지하고, 기존 단계 캐시의 생산자 소스를 확인한다. CLI 전역 옵션은 하위 명령 앞에, 단계 옵션은 뒤에 쓴다.

```bash
export REALIAD_DATA_ROOT="/실제/dataset"
uv run --locked python -m mv_analysis.cli --help
uv run --locked python -m mv_analysis.cli metadata --limit 20
uv run --locked python -m mv_analysis.cli --output outputs/smoke-myname run-all --limit 100
```

20장 metadata는 CSV/JSON과 선택 표본의 dataset_category_distribution.png를 생성한다. 밝기·위치·해상도 그림은 해당 단계에서 생성한다. limit은 정렬된 첫 N장이므로 대표성 있는 성능 표본이 아니다. 첫 100장이 train NG를 포함하지 않으면 heatmap이 중단할 수 있으며 표본을 늘리거나 적절한 별도 복사 표본을 준비한다. 원본은 이동하지 않는다.

## 단계별 전체 실행

```bash
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis validate-data
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume mask-audit
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume brightness
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume heatmap
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume bbox
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume resolution
uv run --locked python -m mv_analysis.cli --output outputs/my-analysis --resume report
```

복사 완료 전 전체 단계를 실행하지 않는다. validate-data와 metadata는 동일한 메타데이터 검증 기능을 공유한다. 별도 명령의 출력은 자동 연결되지 않으므로 같은 --output/--resume을 사용한다. --limit이 있는 실행은 모든 후속 명령에도 같은 --limit을 붙인다.

## 전체 파이프라인

```bash
uv sync --locked
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked pytest -q
uv run --locked python -m mv_analysis.cli --output outputs/preflight-smoke run-all --limit 100
# 위 검증의 증거를 scripts/record_preflight.py로 기록:
uv run --locked python scripts/record_preflight.py --smoke outputs/preflight-smoke
# 사용자/데이터 소유자가 복사 완료를 확인한 뒤:
uv run --locked python -m mv_analysis.cli run-all --full --transfer-complete
```

전체 실행은 decode 검증·복사 완료 표시·preflight·10GiB 이상 디스크·마스크 검증을 요구한다. 마스크 정책 미확정은 히트맵·박스만 보류하며 메타데이터·밝기·해상도를 계속한다. 10GiB는 안전 하한이며 실제 생성량 보장은 아니다. 표본의 wall time을 전체 JPG/마스크 수로 환산한 예상 소요시간과 파일 크기를 실행 로그에서 먼저 검토한다. 작업 중 Ctrl+C를 눌러도 성공 출력은 유지된다. 밝기/해상도는 jsonl 성공 행을 재사용하고 실패 행을 다시 시도한다. 메타데이터·마스크 감사·히트맵·박스는 단계 단위 재계산이다. 모든 단계가 이미지별 재개를 지원하는 것은 아니다.

## 산출물과 해석

| 단계 | 핵심 결과 | 주의점 |
|---|---|---|
| Metadata | image_metadata.csv, mask_metadata.csv, image_mask_pairs.csv, image_metadata_with_split.csv, metadata_validation_report.json | --split-policy windows-project-v1: 기존 seed42 제품 split 재현; 기본 hash는 초기 탐색용 |
| Mask audit | mask_policy.json | 전체 선택 마스크 픽셀 분포, binary 외에는 중단 |
| Brightness | brightness_per_image/summary/comparison/review_candidates.csv, train 통계, histogram PNG, 보고서 | BGR→GRAY [0,255], d/overlap은 관측 차이, 증강은 train 통계 |
| Heatmap | heatmap_summary.csv, occupancy_known/positive.npy, heatmap_groups.json, PNG | Train NG, (group,64,64), known=관측수, positive=면적분율 합 |
| BBox | defect_bboxes.csv, image_component_summary.csv, bbox_errors.csv, classes.json, defect_coco.json, yolo_labels, validation JSON, PNG | xyxy exclusive, 8연결, YOLO 0/COCO 1 기반, OK 빈 라벨 |
| Resolution | per_view_information_loss.csv, category_view_loss_summary.csv, per_image_stepwise_changes.csv, review_priority_images.csv, PNG | 원본 JPG 분석, square resize, 정보 변화와 모델 성능 구별 |
| Report | REAL_IAD_FINAL_ANALYSIS.md, run.json | 없는 결과는 미완료, 보고서 생성 자체는 전체 분석 성공이 아님 |

클래스 기본 defect_type이며 `bbox --class-policy category_defect_type`를 선택하려면 최초 metadata부터 같은 class-policy를 기록한다. 한 NG에 여러 성분이 있어도 파일명에 한 유형만 있으므로 동일 클래스로 가정한다. COCO는 박스 export이며 segmentation AP용 polygon 라벨은 아니다.

해상도는 정사각 1024/512/256으로 area resize한 뒤 원본 크기로 linear 복원한다. 비정사각 원본은 aspect 변형 정책이 적용된다. SSIM은 Gaussian local 11×11, PSNR은 전체 컬러 MSE, edge recall/F1은 Canny 100/200 동일 좌표 교집합, energy/contrast는 비율이다. 고주파 항목은 Laplacian 대리 지표다. 512→256은 별도 512 기준 비교다. 실제 결함 보존성은 bbox/원본 overlay 검수와 후속 모델 실험으로 확인한다.

## Notebook 순서

01 metadata → 02 brightness → 03 heatmap → 04 bbox → 05 resolution → 06 report. 먼저 CLI로 실행 manifest와 mask policy를 준비하고 `MV_ANALYSIS_RUN=outputs/실행폴더`를 설정한다. 모든 Notebook은 기존 모듈/CLI를 호출하고 출력물을 읽는다. 커널 재시작 후 처음부터 실행할 수 있다. 커널은 `uv run --locked jupyter lab`에서 시작한다. 실행 결과와 개인 경로가 저장되지 않도록 커밋 전 Restart Kernel and Clear Outputs 후 저장한다. Windows 기존 Notebook은 legacy/windows_snapshot에 출력 제거 복사본으로 보존했다. 공식 01~06 Notebook은 새 모듈을 호출한다.


## NG/마스크 구분 정책 (2026-11-11 수정)

NG는 불량 제품의 촬영 이미지이며 모든 시점에 위치 마스크가 제공된다고 가정하지 않는다. has_mask는 실제 연결 여부이고 NG 원래 상태는 유지한다. 전체 NG를 메타데이터·밝기·해상도에 포함한다. 마스크 기반 위치 분석은 연결된 NG만 사용하며 미주석 NG에 빈 마스크/빈 YOLO 라벨을 만들지 않는다. 정상 OK의 빈 YOLO 라벨과 구분한다. ng_without_mask.csv에서 경로·대체 stem 후보를 조사하며 파일 부재만으로 의도적 미제공과 유실을 확정할 수 없다. 제공된 PNG의 연결 성공률·decode 오류를 별도 기록한다. 회색조 PNG는 손상으로 판정하지 않고 mask-thresholds의 민감도/overlay 검증 뒤 정책을 정한다.


## 최신 실행 정책 정정

회색조 PNG를 파일 손상으로 간주하지 않는다. mask-audit는 파일 decode/짝 크기 검증과 threshold 확정을 구분한다. 정확한 이진 인코딩이면 자동 정책을 도출할 수 있으나, 회색조면 mask-thresholds의 비교/overlay 검수 결과를 남기고 최종 정책을 보류한다. 이 경우 run-all은 밝기·해상도를 계속 실행하고 mask_stages_deferred.json에 위치 단계 보류를 남긴다. 미주석 NG는 개수 차이 때문에 실행을 차단하지 않는다. 현재 확정 수는 OK 72,840 / NG 78,210 / 위치 정답 NG 51,329 / 미제공 NG 26,881이다. fire_hood의 HS/QS 충돌 10장은 영상 분석에 포함하되 유형 라벨은 UNRESOLVED로 기록한다.


## 실제 전체 실행의 산출물 계보

전체 decode/metadata는 outputs/full_20261111_v4에 보존했다. 해상도 계산에서 같은 참조 통계의 중복 계산을 줄이고 4 worker 및 스트리밍 체크포인트 읽기를 적용한 뒤 합성 9 tests와 실제 100장 표본을 재검증했다. 기존 전체 메타데이터의 모든 JPG size/mtime를 다시 확인하고 scripts/continue_image_analysis.py로 outputs/full_20261111_v6에 복사했다. 원래 v4 출력은 수정하지 않았다. v6 run.json의 provenance에 원래 실행·source hash를 보존한다. 이는 이미 완료된 메타데이터 재사용이며 미실행 영상을 성공으로 추가한 것이 아니다. 밝기·해상도는 v6에서 현재 소스/lock으로 계산한다.

`MV_ANALYSIS_WORKERS=1`처럼 설정하면 메모리/CPU 제약에 맞춰 영상 처리 동시성을 낮출 수 있다. 기본은 최대 4 worker이며 OpenCV 내부 스레드는 1이다. 이 설정은 계산 지표와 lock을 바꾸지 않는다. 전체 PNG 무결성은 scripts/audit_mask_integrity.py의 독립 출력에 남긴다.


## 회색조 마스크 정책 검증 완료 (2026-11-11)

실제 30품목×112 품목/유형 조합에서 336장, 6개 임계값을 비교했고 overlay 30개를 만들었다. 전체 PNG 51,329장의 decode/짝 크기 검증은 0오류였다. [공식 Real-IAD EvalPerPixelAUC](https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249)의 양수 마스크 처리와 실제 경계 수축/분절 관측을 함께 근거로, 본 프로젝트 위치 분석은 grayscale >0, 면적 필터 없음으로 고정했다. 이는 모든 결함 경계의 의미적 정확도 증명이 아니다. 초기 보류 상태는 이 검증으로 갱신되었다. 원본 회색조 마스크는 그대로 보존한다.

다른 실행에서 재현하려면 전체 metadata/decode 실행의 mask-audit와 mask-thresholds 결과를 먼저 만든 뒤 새 공간 분석 실행을 만든다. 아래 경로는 본인 실제 출력으로 바꾼다.

```bash
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 --output outputs/full-metadata --resume mask-audit
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 --output outputs/full-metadata --resume mask-thresholds
uv run --locked python scripts/continue_image_analysis.py --metadata-run outputs/full-metadata --output outputs/spatial-analysis
uv run --locked python scripts/approve_mask_policy.py --integrity outputs/full-metadata --study outputs/full-metadata --run outputs/spatial-analysis
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 --output outputs/spatial-analysis --resume heatmap
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 --output outputs/spatial-analysis --resume bbox
```

최초 전체 metadata는 validate-data 명령으로 끝나야 한다. 승인 스크립트는 전체 무결성/30품목 민감도 비교 증거가 없거나 기존 policy가 있으면 실패한다. 정책 파일을 덮어쓰지 않는다. run-all은 미검증 회색조를 자동 threshold 처리하지 않으므로 image 단계 완료 후 위 검증/위치 단계를 이어서 실행한다. root/limit/class-policy/lock/source 설정을 동일하게 유지한다.


## 제공된 빈 마스크와 코드 버전별 체크포인트

has_mask=True인 PNG의 모든 픽셀이 0이면 annotation_status=provided_empty로 기록한다. 기존 파일에 실제로 주어진 정답을 따라 박스는 0개이며 YOLO 라벨은 빈 파일이지만 분류 status=NG는 유지한다. 이는 has_mask=False인 NG에 임의 빈 마스크/라벨을 만드는 것과 다르다. 미제공 NG는 탐지 라벨에서 제외한다. 이 구분을 실제 합성 테스트로 확인했다.

해당 구분을 보완한 공간 분석은 outputs/spatial_20261111_v7이며, 앞선 v6의 부분 출력은 보존했다. 이미 끝난 >0 Train 히트맵의 수치와 그림은 provenance를 남겨 v7에 복사했다. bbox는 동일 데이터의 검증된 width/height를 사용하므로 정상 JPG를 다시 디코드하지 않는다. overlay 검수용 원본만 읽는다.

run.json의 config.source_sha256은 최초 실행을, stage_sources와 명령별 source_sha256은 각 단계의 실제 구현을 기록한다. 기존 캐시가 있는 단계의 생산자 소스가 바뀌면 재사용을 거부한다. 검증된 이전 메타데이터로 아직 계산하지 않은 새 단계를 시작하는 것은 허용하고 단계 소스를 별도 기록한다. root/limit/class-policy/lock 변경은 계속 거부한다.


## 장시간 해상도 분석의 짧은 배치 재개

장기 실행 프로세스가 SIGTERM(143)로 종료되어 성공 2,680장 체크포인트를 보존했다. 종료를 유발한 외부 주체/시간제한 여부는 확정하지 않았다. 디스크/메모리 부족이나 Python 계산 예외로 단정하지 않는다. scripts/resolution_batch.py는 같은 core 지표를 사용해 미완료 이미지만 지정한 수만큼 추가하고 종료한다. 기존 성공 표본 3장을 다시 계산해 1e-10 허용 오차로 수치 동등성을 확인한 후 이어간다. 배치 상태와 실제 소요시간은 resolution_batch_status.json/resolution_batches.jsonl에 기록한다.

```bash
# 프로젝트 루트, 앞 배치 종료 후 반복. 동시에 두 배치를 실행하지 않는다.
uv run --locked python scripts/resolution_batch.py --run outputs/full_20261111_v6 --batch-size 2000
# success=target인 경우에만 최종 CSV/PNG를 생성한다:
uv run --locked python scripts/resolution_batch.py --run outputs/full_20261111_v6 --batch-size 1 --finalize
uv run --locked python scripts/enrich_analysis_results.py outputs/full_20261111_v6
uv run --locked python scripts/validate_artifacts.py outputs/full_20261111_v6
```

부분 체크포인트는 최종 CSV/그림의 전체 완료를 의미하지 않는다. finalization은 모든 JPG가 끝나지 않으면 실패한다. 원본과 이전 실행 결과는 보존한다.


## 실제 분리 실행을 Notebook에서 열기

```bash
# 01 metadata / 02 brightness / 05 resolution / 06 integrated report
export MV_ANALYSIS_RUN="outputs/full_20261111_v6"
uv run --locked jupyter lab
# 03 heatmap / 04 bbox를 열 때는 별도 커널/서버 환경에서:
export MV_ANALYSIS_RUN="outputs/spatial_20261111_v7"
uv run --locked jupyter lab
```

분리 실행의 연결은 image 실행 폴더의 related_runs.json을 따른다. 06은 reports/REAL_IAD_FINAL_ANALYSIS.md의 실제 통합 보고서를 읽는다. Notebook 커널을 이미 시작했다면 환경변수 변경이 반영되도록 새 커널/서버에서 시작하거나 첫 셀의 run을 본인 경로로 지정한다. 실행이 끝나지 않은 단계의 결과를 Notebook이 대신 계산했다고 간주하지 않는다.


반복 배치가 필요하면 Ubuntu 터미널에서 `bash scripts/run_resolution_batches.sh outputs/실행폴더 5000`을 사용한다. 이 프로젝트의 현재 실행과 동일 폴더에 동시에 실행하지 않는다. 작업별 flock은 중복 배치 실행을 거부하며 중단 시 OS가 잠금을 해제한다. 별도 PID 파일을 삭제할 필요가 없다. 마지막에는 전체 건수를 확인해 finalize/enrich/형식 검증을 실행하며 보고서 갱신에는 해당 실행의 inventory/threshold-study 경로를 사용한다.


## 기존 Windows 분할과 히트맵 계약 유지

공식 재현에는 전역 옵션 `--split-policy windows-project-v1`을 사용한다. 예: `uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 metadata --limit 20`. 전체 파일 목록을 기준으로 기존 seed42 제품 그룹 분할을 만든 뒤 20장을 선택하므로 표본 크기에 따라 split이 바뀌지 않는다. 기본 hash는 이전 탐색 실행을 재개하기 위한 호환 설정이다. 저장된 기존 manifest를 명시하려면 `--split-manifest /path/to/image_metadata_with_split.csv`를 사용한다.

히트맵 기본 presence는 기존 coarse_occupancy를 재사용하며 1픽셀 결함도 보존한다. occupancy_known은 제공 마스크(제공 빈 마스크 포함) 대비 칸 점유 빈도, occupancy_positive는 비어 있지 않은 마스크 대비 점유 빈도다. 미제공 NG는 n_unknown이며 분모에 넣지 않는다. 관측 0이면 NaN으로 저장한다. `--heatmap-mode area`는 초기 면적 분석 재현 옵션이다. 두 배열 규약은 서로 다른 지표이며 heatmap_schema.json을 확인한다.


## 배경을 분리한 밝기 재검증

`regional-brightness`는 기존 결과를 보존하는 별도 실행이다. [상세 명령 및 불확실성 처리](BACKGROUND_BRIGHTNESS.md). 기본 brightness의 전체 평균과 구분하고 제품 통계는 품질 통과 subset에만 산출한다. `reports/BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md`에서 paired 전체/제품 비교, 배경별 비교, 제외 선택 편향을 확인한다.


기존 분할 재현 실행은 첫 validate-data뿐 아니라 같은 run을 --resume하는 모든 CLI 호출에 전역 `--split-policy windows-project-v1`을 동일하게 지정한다. metadata import는 이 설정과 manifest fingerprint를 새 run.json에 보존한다. 기본 hash는 초기 탐색 결과의 호환용이다. 새07 Notebook은 영역별 밝기 결과를 읽는 확장으로, `MV_REGIONAL_RUN`에서 입력 실행을 선택한다.


해상도 배치 재개는 현재 함수/read-image 정책의 서명과 OpenCV/NumPy 버전, lock fingerprint를 확인한다. 함수/런타임이 달라지면 기존 cache에 결과를 섞지 않고 거부한다. 기존 cache를 현재 서명에 최초 결합할 때 실제 성공 표본3장을1e-10으로 검증한다. full source와 동일한 실제100장 최신 smoke/환경 dummy/22개 pytest 재검증은 reports/FINAL_PREFLIGHT_LOG.txt 및 preflight_passed.json을 참조한다.


최종 primary 결과는 기존 Windows 분할의 outputs/windows_preserved_20261111_v1로 통합한다. 원래 outputs/full_20261111_v6의 해상도 숫자를 재계산하지 않고 split/product 메타데이터만 연결했으며453,150행의 모든 수치가 CSV roundtrip 후 정확히 같음을 검증했다. 원래CSV/JSONL은 그대로 보존한다. 계산 체크포인트를 재개할 때는 원래 full_20261111_v6 배치 worker를 사용하고, 새 수치를 canonical로 붙일 때 새 파생 실행을 만든다. 실제 재연결 근거는 resolution_metadata_rebind_validation.json이다.
