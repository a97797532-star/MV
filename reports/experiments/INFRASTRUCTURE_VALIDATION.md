# 공통 실험·평가·보고 인프라 검증

구현 기준 Commit: `8ee73b4`. 실제 12개 모델 학습/추론을 구현한 작업이 아니라, 공통 인프라와 담당자 TODO를 구현·검증한 기록이다. 구현 단계에서는 Git Commit/Push를 수행하지 않았다. 이후 배포 검증과 공유 파일 범위는 [배포 기록](RELEASE_VALIDATION.md)을 참고한다.

## 구현 범위

| 영역 | 실제 구현 |
|---|---|
| 계약 | source/Manifest/주석/평가ID/Split/Crop/Adapter/프로토콜·환경·설정 식별 |
| Recorder | 고유Run, 불변config, 환경, epoch/step long CSV, Loss/LR/gradient/time, 예측sidecar, checkpoint메타, 예외·실패·중단·부분완료 |
| 이상탐지 | exact영상AUROC/AP, 고정Threshold P/R/F1, 스트리밍픽셀AUROC/AP근사·직접F1, 영역동일가중 AUPRO |
| 검출 | COCO mAP50/50-95, class AP/Recall, 고정Threshold micro P/R/F1·FP/FN, confusion |
| 원본 연결 | 기존Dataset/Adapter변경없이 GT지연읽기와 모델출력 원본좌표/격자 복원 |
| Benchmark | CPU/CUDA경로, 동기화·Warmup·반복·stage분리, p50/p95/mean/throughput, parameter·checkpoint·RSS/VRAM |
| 시각화 | 원본/GT/heatmap/overlay/binary/FPFN, GT/예측BBox, 클래스·score·Threshold·출처 표기 |
| 보고 | Loss/Validation/LR/gradient/time/ROC/PR/AUPRO/품목/시점/latency·크기·Pareto, 상대PNG링크 Markdown |
| 비교 | 동일계약·평가가능cohort끼리, Validation대표선택, 하드웨어/batch/input/dtype속도분리, 합성/실패 제외 |
| 모델 영역 | 12모델×5문서=60계약문서, 12미구현interface. 실제Train/Fine-tuning없음 |

## 테스트와 실제 실행

- 전체pytest: **185 passed**, failed0, 기존경고1. 기존145개+추가40개다.
- 경고는 기존 NumPy timedelta 사용 중단 경고다. 마지막실행29.26초. 로컬HTTP테스트는허용된환경에서임시Ledger만사용했다.
- Unit범위: Run충돌방지/복구/config변조, CSV/NaN/Inf, 지표/N/A, AUPRO수직구간, COCO/클래스/FPFN, 원본좌표/Mask, CUDA동기화·peak reset모의검사, CPU RSS/크기, 그림/링크, 비교조건/Manifest/장비/합성분리,12모델NotImplemented확인.
- 실제입력계약: **10장 / 2선언제품**, C1~C5, OK/NG, mask있음/없음. 저장Crop을그대로읽고BBox역변환과원본GT참조를확인했다. **실제모델예측/성능평가는생성하지않았다.**
- 합성Run12개 전부 SYNTHETIC / PARTIAL. 실제학습실행False. PatchCore합성예에는가짜gradientLoss를넣지않았다.
- PNG **381개**를PIL로검사하고 Markdown이미지링크 **382개**를확인했다. 깨진링크0. 모든그림을사람이검수했다고주장하지않으며대표이상탐지/검출그림을직접확인했다.
- 검출그림은imshow의기본0.5픽셀중심오프셋을원본XYXY경계0..W/H와맞췄다. 초기그림을덮지않고cases_v2·새report버전에저장했다.

## 합성 점수 — 실제 모델 성능 아님

| task/metric | 합성 계산값 |
|---|---:|
| anomaly/image_auroc | 0.640000000 |
| anomaly/image_ap | 0.740000000 |
| anomaly/image_f1 | 0.800000000 |
| anomaly/pixel_auroc | 0.777777778 |
| anomaly/pixel_ap | 0.548373780 |
| anomaly/pixel_f1 | 0.734693878 |
| anomaly/aupro | 0.664726285 |
| detection/map50 | 0.663366337 |
| detection/map50_95 | 0.663366337 |
| detection/precision | 0.666666667 |
| detection/recall | 0.666666667 |
| detection/f1 | 0.666666667 |
| detection/tp | 2.000000000 |
| detection/fp | 1.000000000 |
| detection/fn | 1.000000000 |

이값은공식모델을호출한결과가아니다. 합성FP/FN을의도적으로넣어평가·시각화실패경로를검증했다. 영상예에는TP4/FP1/FN1, 검출예에는TP2/FP1/FN1이있다. CPU지연·파라미터수는공식모델대신 **SYNTHETIC_TINY_CONV_NOT_OFFICIAL_MODEL**을측정한것이다. 이를12모델성능/속도순위로사용하면안된다.

## 바로 열어볼 보고서

- [이상탐지 합성 예제 발췌](release_examples/SYNTHETIC_ANOMALY.md): 주요 수치·Loss·ROC·heatmap/overlay·FN 예제.
- [객체탐지 합성 예제 발췌](release_examples/SYNTHETIC_DETECTION.md): COCO mAP·confusion·GT/예측·FP/FN 예제.
- 전체 12개 합성 Run과 비교 보고서는 Smoke 명령으로 로컬에서 생성한다. 실제 모델 비교가 아니며 anomaly/detection 그룹을 분리한다. 기존 `reports/experiments/MODEL_COMPARISON.md`와 전체 예제 디렉터리는 로컬에 보존하고 이번 배포에서는 제외한다.
- 원본Run/추가그래프/검사JSON: `outputs/experiments/SYNTHETIC_INFRASTRUCTURE_V2/`, `outputs/experiments/infrastructure_validation_v1.json`, `outputs/experiments/real_input_contract_v1.json`.

## 미검증과 한계

1. 실제12모델생성·공식전처리/Trainer연결·forward/backward·학습·Validation/Test·weights수령은팀원TODO다. 미구현함수는NotImplementedError를낸다.
2. 실제GPU·CUDA시간/VRAM은미측정이다. CUDA단위테스트는mock이며GPU성공으로보고하지않는다. 팀원GPU환경에서실측한다.
3. PixelAUROC/AP는Validation구간고정2048-bin근사, AUPRO는동일bin의256Threshold와FPR0~0.3적분이다. exactpixel지표와동일하지않다. Test구간밖포화건수·평가범위밖양성픽셀수를기록한다.
4. NG미주석/빈NG/손상GT는위치평가에서제외하며영상NG는유지한다. Crop밖미관측score는정상0이아니다. 평가cohort가다르면별도비교그룹이다.
5. CPU RSS는5ms프로세스표본peak이며정확한모델메모리가아니다. memory bank/search index는실제모델실행시담당자가추가측정한다.
6. 실제v2전체타깃계약/학습eligibility최종고정과Test수동주석참조독립성검토는이전과동일하게별도과제다. 이번에Manifest를변경하지않았다.
7. Run파일은rank0단일writer기준이다. 정전후손상파일은수동확인하고, 과거설정/Metric을덮어복구하지않는다.
8. 다른장비학습시간/PeakVRAM·다른조건지표·SYNTHETIC을한순위로합치지않는다. 성능향상/최적모델을선언하지않았다.

## 팀원과 GitHub 공유

README와 [역할 안내](../../docs/team/MODEL_EXPERIMENT_ASSIGNMENT_GUIDE.md), [실험 규약](../../docs/experiments/EXPERIMENT_PROTOCOL.md)을따른다. GitHub제출은추론/연결코드·설정·Markdown·공유가능그래프다. **weights/checkpoint/memory bank/index는별도전달**하며파일명·bytes·SHA·수령방법만기록한다. 접근토큰/비밀URL/원본이미지무단공개는제외한다. 이문서의예제자료는전부합성이다.

## 재현 명령

```bash
uv run --locked python scripts/experiments/smoke_test_reporting.py
uv run --locked python scripts/experiments/generate_report.py --run-dir outputs/experiments/실제run_id
uv run --locked python scripts/experiments/compare_models.py --runs-root outputs/experiments/
uv run --locked pytest -q
```

합성비교를명시적으로검토할때만 `--include-synthetic --allow-partial`을추가한다. 실제모델Train명령은아직없다.

## 구현 파일

- `mv_analysis/experiments/__init__.py`
- `mv_analysis/experiments/anomaly.py`
- `mv_analysis/experiments/benchmark.py`
- `mv_analysis/experiments/bridge.py`
- `mv_analysis/experiments/contracts.py`
- `mv_analysis/experiments/demo.py`
- `mv_analysis/experiments/detection.py`
- `mv_analysis/experiments/geometry.py`
- `mv_analysis/experiments/integration.py`
- `mv_analysis/experiments/pixels.py`
- `mv_analysis/experiments/recorder.py`
- `mv_analysis/experiments/reports.py`
- `mv_analysis/experiments/visualization.py`
- `scripts/experiments/compare_models.py`
- `scripts/experiments/generate_report.py`
- `scripts/experiments/smoke_test_reporting.py`
- `scripts/experiments/validate_real_input_contract.py`
- `tests/test_experiment_infrastructure.py`
- `configs/experiments/model_registry.json`
- `models/<family>/<model>/`의5개계약과integration.py

## 보호와 Git 상태

구현 단계에서 기존 로더 6개·Crop 기하·uv.lock·기준/v1/v2 Manifest·두 승인 Ledger의 총 13개 파일 SHA-256이 작업 전후 같았다. 기존 미추적 보고서도 보존했고 당시 HEAD는 기준 `8ee73b4`였다. 이후 Commit/Push는 별도 배포 작업이며 최신 검증 범위는 [배포 기록](RELEASE_VALIDATION.md)을 따른다.
