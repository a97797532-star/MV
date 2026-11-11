# 배경·제품 영역 밝기 분석 실행

프로젝트 루트(`/home/본인/MV`)의 Ubuntu 터미널에서 실행한다. 기존 전체 밝기 구현은 `mv_analysis/stages.py`와 `core.brightness_metrics`이며 별도 brightness.py는 없었다. 확장은 `background_brightness.py`, 실행/집계는 `regional_cli.py`에 있다. 원본을 쓰거나 기존 분석 결과를 갱신하지 않는다.

## 표본 검수

```bash
uv run --locked python -m mv_analysis.cli --output outputs/my_background_sample regional-brightness --source-run outputs/windows_preserved_20261111_v1 --sample --compare-methods
```

기존 분할을 보존한 source-run의 metadata와 검증된 mask_policy가 입력이다. 30품목×5시점×OK/NG 300장을 선택하며 정상 실행 시 300/300 진행률, regional_validation.json 및 CSV/PNG가 생성된다. 경로/입력 누락이면 source-run의 run.json, image_metadata_with_split.csv, brightness_per_image.csv, mask_policy.json을 확인한다. 기본 전경은 제품 GT가 아닌 추정치다. NG 결함 PNG는 결함 통계에만 사용한다.

`foreground_segmentation_examples_01~06.png`는 품목별 한 대표 사례의 A/B/C 오버레이다. `foreground_segmentation_metrics.csv`는 전 표본의 품질 점수다. 우선 그림자·반사·관통 구멍·가장자리 잘림·작은 제품·유사 배경을 검수한다. method agreement는 정답 IoU/Dice가 아니다. 기존 표본 실행은 버전별 폴더에 보존했다.

## 전체 실행 및 재개

실제 검수 후 동일 알고리즘 버전의 검수 근거 JSON을 지정한다. 현재 검수 근거는 `reports/BACKGROUND_SEGMENTATION_REVIEW.json`이다. 새 데이터/새 알고리즘이면 이 파일을 복사해 검증 성공으로 사용하지 말고 다시 표본을 검수한다.

```bash
uv run --locked python -m mv_analysis.cli --output outputs/my_background_full regional-brightness --source-run outputs/windows_preserved_20261111_v1 --full --compare-methods --validation-evidence reports/BACKGROUND_SEGMENTATION_REVIEW.json --batch-size 2000 --workers 2
```

한 번에 2,000장까지 처리하고 성공 행을 regional_checkpoint.jsonl에 즉시 저장한다. 첫 실행 후에는 같은 명령에 전역 `--resume`을 추가해 반복한다. 전체 151,050장을 처리한 후 `--finalize`를 붙이면 집계 CSV와 검증 JSON을 생성한다. source/metadata/policy/hash가 달라지면 재개를 거부하므로 새 폴더를 사용한다. 성공/오류 수는 배치마다 `batch_*.json`에 기록한다. 오류가 있으면 성공 행은 보존하고 해당 경로의 접근 권한·파일 변경·decode 여부를 확인한다. 다른 worker가 같은 출력 폴더를 사용하면 잠금 오류가 나므로 기존 실행이 끝날 때까지 기다린다.

## 출력 해석

- background_type: WHITE/BLACK/GRAY/MIXED/UNKNOWN. 경계 4% 띠, HSV V, OpenCV Lab L, 색상 거리와 연결성을 사용한다. GRAY에는 중간 명도의 유채색 배경도 포함한다. confidence는 보정된 정답 확률이 아니다.
- A: 적응형 경계 색상/2차 조명 모델. B: GrabCut. C: 색상 seed watershed. 전경은 긴 변256에서 계산하므로 미세 경계/문자/구멍은 사람이 검수해야 한다.
- accepted_heuristic: 품질 필터 통과. 확정 정답이나 분할 성공률/정확도가 아니다. 불확실/실패는 product_* 및 background_* 영역 통계를 결측으로 남기고 whole_*는 유지한다.
- defect_*: 제공 PNG의 >0 영역. 제품 내 추정 annulus가 충분하고 결함과 제품의 위치가 일치해야 local 차이를 계산한다. 마스크 없는 NG는 NG로 유지한다.
- before_after: whole_all과 whole_paired/product를 구분한다. paired는 같은 통과 영상들이므로 품질 제외에 따른 선택 효과와 영역 변경 효과를 나누어 볼 수 있다. 유효 OK/NG 각각2장 미만이면 비교 통계는 결측이다.
- augmentation: Train 품질 통과 통계만 사용한다. 정상 전용 AD 통계와 NG 포함 통계는 별도다. Validation/Test와 원본 파일은 변경하지 않는다.

## 보고서 갱신

```bash
uv run --locked python scripts/report_background_brightness.py --sample-run outputs/background_sample_20261111_v5 --full-run outputs/background_full_20261111_v1
```

`reports/BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md`를 실제 산출물에서 갱신한다. 전체가 미완료이면 300장 표본 해석으로 명시하며 전체 결과로 추정하지 않는다. 보고서는 제품과 배경의 평균뿐 아니라 선택률·분포·paired 비교·배경별 비교·국소 대비·증강 후보의 한계를 포함한다. 모델 학습은 수행하지 않는다.


## 새 팀원의 통합 입력 폴더 준비

source-run은 완료한 메타데이터·측정된 brightness_per_image.csv/.jsonl·검증된 mask_policy.json을 함께 가진 실행이다. 여러 단계 출력이 나뉘어 있다면 다음 명령으로 새 입력 묶음을 만든다. 원본/이전 결과는 보존하고 측정된 밝기를 재사용한다.

```bash
uv run --locked python scripts/restore_windows_analysis_split.py --source outputs/my_full_image_run --output outputs/my_regional_source --verified-split outputs/my_full_image_run/image_metadata_with_split.csv --policy outputs/my_spatial_run/mask_policy.json --skip-heatmap
```

my_full_image_run은 처음부터 --split-policy windows-project-v1을 사용해 전체 metadata/brightness를 완료한 실행이다. 기존 분할이 유지됐는지 manifest와 비교하고, 표본이 아니라151,050장인지 확인한다. --skip-heatmap은 이미 완료한 공간 분석을 반복하지 않고 영역 밝기 입력만 묶는다. 정상 실행 시 restoration_validation.json에 처리 규모와 heatmap_deferred=true를 기록한다. metadata/split 불일치나 기존 출력 폴더가 있으면 중단한다. 이후 regional-brightness의 --source-run에 이 새 폴더를 지정한다. 원래 데이터와 JSONL은 삭제하지 않는다.
