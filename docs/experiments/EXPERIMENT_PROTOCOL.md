# Real-IAD 공통 실험·평가 규약 v1

이 규약은 공통 기록·평가·그래프·보고 코드의 실행 계약이다. 실제12모델 생성·전처리 연결·Train Loop는 팀원이 구현한다. 기본 source는 `mv_analysis/experiments/`, 기존 로더는 `mv_analysis/data/`이며 수정하지 않았다. 모델별 작업 영역은 `models/anomaly/`와 `models/detection/`의 계약·TODO다.

## 1. 공정한 비교의 범위

고정: Canonical Manifest, 기존 Split, 평가 이미지 ID와 결함 주석, 원본 좌표, 클래스 매핑, 픽셀 평가 영역, 지표 구현/버전, Validation Threshold 선택 규칙, 기록 형식, 추론 측정 방식.

모델 고유: 공식 해상도·Resize/LetterBox·Normalize·Loss·epoch·batch·optimizer·learning rate·학습 일정. 이들을 억지로 같게 만들지 않는다. `comparison_track`은 OFFICIAL_BASELINE / COMMON_INPUT / OPTIMIZED로 분리한다. 현재 입력Adapter의 추가CenterCrop 비활성화는 공식 baseline과 다른 조건일 수 있다.

학습GPU가 다르면 학습시간·학습PeakVRAM을 같은 장비 순위로 해석하지 않는다. 속도는 가능하면 같은 장비에서 재측정한다. 비교기는 hardware hash·batch·입력집합·dtype가 다른 속도를 분리한다. 원본오프라인Crop 구축 비용은 모델 순수추론시간에 넣지 않는다.

## 2. Run과 메타데이터

`ExperimentRecorder.create(root,config)`는 UTC시각+UUID의 새 디렉터리를 만든다. 기존 Run을 덮지 않는다. 설정과 환경은 별도 JSON, 이력은 long CSV, 사건과 예측은 JSONL이다.

| 필드/파일 | 필수 내용 |
|---|---|
| 실험 식별 | experiment_id, run_id, model_name, model_family |
| 소스 | official_repo, official_commit, project_commit, project_dirty, infrastructure_sha256 |
| 데이터 | manifest_sha256, annotation_sha256, class_mapping_sha256, evaluation_set_sha256, evaluation_ids_sha256(validation/test 각각) |
| 정책 | split_version, crop_policy_version, model_adapter_version, protocol_sha256, comparison_track, nms_policy |
| 설정 | seed, device, batch_size, epochs, optimizer, scheduler, learning_rate, input_resolution, normalization |
| 초기 checkpoint | checkpoint_path, checkpoint_sha256(없으면null) |
| 실제 checkpoint | artifacts.json의 path·bytes·SHA-256·epoch·선택 역할 |
| 환경 | Python/torch/CUDA, GPU이름·VRAM, CPU모델·논리코어·RAM·torch threads |
| 재현 | reproduce_command, 실제 모델 환경과 고정 source commit |

`evaluation_ids_sha256`는 Split별 정렬한 image_id 목록의 digest이며, `evaluation_set_sha256`는 그2개 해시 dict의 digest다. 코드의 `digest` 함수를 그대로 사용한다. 실제 config는 체크리스트를 채운 팀원이 작성한다. `demo.example_config`는 합성 전용이며 실제 데이터 해시 대신 쓰지 않는다.

상태: CREATED → RUNNING → COMPLETED / FAILED / INTERRUPTED / PARTIAL. COMPLETED는 REAL Run이며 실제학습 실행과 근거가 있어야 한다. PatchCore의 memory bank 구축도 실제학습 단계로 근거를 남긴다. 합성·단순평가·보고 검증은 PARTIAL이다. 예외와 KeyboardInterrupt는 구분 기록한다. 프로세스 강제종료/정전은 자동 감지할 수 없으므로 남은 RUNNING을 사람이 확인하고 복구한다.

## 3. Recorder 사용

```python
from mv_analysis.experiments import ExperimentRecorder
# config는 담당자가 실제 source/data/환경 계약에 맞춰 작성한다.
with ExperimentRecorder.create("outputs/experiments", config) as recorder:
    recorder.log(epoch=0, step=10, phase="train", metrics={
        "loss_total": measured_loss,
        "learning_rate": measured_lr,
        "gradient_norm": measured_gradient_norm,
        "epoch_seconds": measured_epoch_seconds,
    })
    # 실제 모델이 제공한 Loss 구성요소만 추가한다.
    # validation/test 예측→평가는 아래 계약을 사용한다.
```

없는 Loss는 보내지 않는다. None은 N/A이며 NaN/Inf는 빈 CSV값과 NONFINITE_METRIC 사건으로 기록한다. 가짜0으로 만들지 않는다. PatchCore에는 gradient Loss를 생성하지 않는다. 학습종료가 확인되지 않으면 context가 PARTIAL로 마친다. 실제 종료 시 `finalize("COMPLETED",training_executed=True,evidence=...)`를 담당자가 호출한다.

`resume(run_dir,expected_config_sha256)`는 같은 설정과 중단/부분/실패 상태에서만 명시적으로 재개한다. 과거 설정을 바꾸거나 결과를 덮지 않는다. DDP에서는 rank0 한 writer만 Recorder를 소유한다. flock로 쓰기를 직렬화하지만 서로 다른 학습 프로세스가 같은 Run을 소유하는 설계는 지원하지 않는다. 체크포인트 저장 자체와 학습 재개는 팀원 trainer가 구현한다.

예측 NumPy 배열은 run내 `arrays/*.npy`에 저장하고 JSONL에는 상대경로·SHA를 넣는다. `load_predictions(run_dir,lazy=True)`와 평가기의 지연복원을 사용하면 모든 heatmap을 한 번에 읽지 않는다. sidecar는 allow_pickle=False, 경로 이탈/해시 변경을 검사한다. 상태/config/event/파일들은 전체분산트랜잭션이 아니므로 정전 후 손상 파일을 성공으로 무시하지 않는다.

## 4. 공통 예측과 원본 GT

GT와 예측은 **별도 자료**다. 모든 평가 대상 image_id의 예측 레코드가 있어야 한다. 누락예측을 점수0/빈정상으로 채우지 않는다.

공통GT: image_id, product_id, category, C1~C5 view, split, OK/NG status, original_hw, mask_status, 원본binary mask/None, 원본XYXY boxes, canonical labels, detection_status. 필요하면 고정 evaluation_mask를 포함한다.

공통예측: image_id, split, coordinate_space="original". 이상탐지는 score(높을수록NG)와 원본격자 score_map(없으면위치평가N/A). 검출은 boxes XYXY, 0기반정수 labels, 0..1 scores다. 좌표·클래스·confidence·ID를 검증한다.

기존Dataset과의 연결은 `bridge.ground_truth_records`, `restore_anomaly_prediction`, `restore_detection_prediction`을 참고한다. 예측 클래스 offset/좌표형식/정규화 여부는 팀원이 **실제 모델 출력**을 보고 명시한다. Adapter의 GT형식으로 예측형식을 추측하지 않는다. BBox는 역Normalize→형식변환→Pad제거→Scale역변환→Crop원점복원→Clip 순서다. 제거된박스와 keep을 기록한다.

연속 score map은 BILINEAR, 범주형 예측mask는 NEAREST로 복원한다. 실제원본GT는 별도로 읽고 Crop된GT를 원본전체GT로 부르지 않는다. Crop밖은 NaN/observed=False다. 모델 featuremap이 입력보다작으면 먼저담당자가 명시적격자정렬을 수행해야 한다. 크기가다른지도를암묵적으로원본으로인정하지않는다.

## 5. 픽셀 평가 영역과 누락 주석

- OK + mask미제공은 정당한 정상영역 GT0으로 평가할 수 있다.
- NG + MISSING/INVALID/PRESENT_EMPTY는 픽셀평가에서 제외하고 사유/수를 남긴다. 영상NG는 그대로평가한다.
- 기본규약은 사전에GT에 선언한 원본공간 evaluation_mask다. canonical_crop이면 저장Crop을 사용한다. 모델score를보고범위를조정하지않는다.
- GT평가영역 안의 score가 미관측/NaN/Inf면 해당이미지픽셀평가를 제외한다. Crop밖을 정상0으로채우지않는다.
- 평가영역밖양성픽셀수도 별도로 기록한다. 좁은영역에서높은지표가나왔다고 전체결함보존을주장하지않는다.
- 모델간 동일영역은 annotation/Manifest/평가집합 해시와 설정으로 고정한다.

## 6. 이상탐지 지표와 Threshold

영상 AUROC/AP는 sklearn을 사용한 exact score ranking이다. 단일GT클래스 AUROC, 양성없는AP, 유효픽셀없는지표는 null/N/A다. F1의 빈예측 분모는 운영계수정책에따라0으로정의하지만 평가불가능한GT자체를0점으로채우지않는다.

Validation 영상 F1 최대 Threshold, 동률이면 높은값을선택한다. 픽셀은 아래히스토그램 경계중 Validation F1 최대값을선택한다. 정한 Threshold·Validation ID/제품해시·protocol hash·data_kind를 `ThresholdPolicy`와 thresholds.json으로동결한다. Test에서다시calibrate하지않는다. Validation/Test 선언제품중복을검사한다.

### 전수 픽셀의 메모리 제한

기본 Pixel AUROC/AP는 **2048-bin 히스토그램 근사**다. Validation 유효score의 min/max로 구간을고정하고 Test에서재조정하지않는다. 원본유효픽셀을한영상씩누적하므로전체픽셀목록을메모리에쌓지않는다. Test구간밖score는끝bin에묶으며그건수를보고한다. 큰포화/타이로정확도가낮아질수있어exact pixel metric과동일하다고부르지않는다. Pixel F1은고정Threshold로실제픽셀 TP/FP/FN을직접누적한다.

### AUPRO

마스크의8연결영역각각의 recall을같은가중치로평균해PRO를구한다. 정상픽셀전체를분모로FPR을계산한다. FPR0~0.3구간을선형보간적분하고0.3으로나눈다. 기본실행은Validation 고정2048-bin에서256개Threshold를선언해계산하는근사다. 영역/정상픽셀이없으면N/A다. 동일FPR의수직구간을순서대로유지하며최대PRO로합쳐면적을과대평가하지않는다. 별도 `aupro()` 진단함수는 명시적표본의원점수를사용하며 기본평가의히스토그램방식과구분한다. 둘의알고리즘/구간/Threshold조건이같지않으면직접비교하지않는다.

## 7. 객체탐지 지표

pycocotools.COCOeval bbox: IoU0.50~0.95(0.05간격), recall101지점, maxDets1/10/100, area=all. class별GT없는AP는N/A이며COCO의정의대로평균에서제외한다. 내부COCO ID는 canonical+1이고외부라벨은0기반을유지한다.

mAP는최종고정confidenceThreshold로잘라계산하지않고최대100개의score순위예측을사용한다. 미리공식모델에서잘린confidence/NMS는복구할수없으므로 최소score·NMS IoU·최대검출수와적용위치를실제config에추가기록한다. 공통evaluator는NMS를두번적용하지않는다. `nms_policy=already_applied_upstream_declared_per_run` 계약이다.

운영Precision/Recall/F1과TP/FP/FN은Validation에서0~1,0.01간격으로microF1을최대화한Threshold를Test에고정해계산한다. 동률이면높은Threshold. IoU0.5·동일클래스·score순greedy one-to-one이다. ConfusionMatrix는클래스무관IoU매칭의GT행/예측열이며마지막BACKGROUND행은FP·열은FN이다. 두매칭목적을혼동하지않는다.

OK_NEGATIVE는정당한빈GT다. SUPERVISED_VALID NG만위치평가하고 MISSING_ANNOTATION/EMPTY_NG_REVIEW/INVALID_TARGET NG는제외한다. Crop에서사라진NG를OK로변경하지않는다. 유효양성GT없는mAP는N/A다.

## 8. Benchmark

`model.eval()`·torch.inference_mode·Warmup후측정. CUDA는타이머앞뒤동기화, mode별peak memory reset. 실제CPU/GPU하드웨어·batch·dtype·입력집합해시·shape·Warmup·반복수를기록한다. 모델로드는load_timed로별도측정한다.

model-only와preprocess+model+postprocess를분리하고stage별지연도기록한다. p50/p95/mean은 **배치당ms**, throughput/FPS는batch_size×반복/총초다. parameter/trainable count, checkpoint bytes/SHA, memory bank/search index bytes도기록한다. 일반callable의parameter는모르면N/A다.

CPU메모리는5ms간격프로세스RSS표본peak와baseline/delta이며정확한모델메모리나순간시스템peak가아니다. GPU는allocated/reserved peak를구분한다. CPU에서는GPU값N/A. CUDA동기화모의테스트는실제GPU벤치마크성공이아니다. 실제12모델속도는같은GPU/CPU에서재측정해야한다.

## 9. 그래프와 보고

```bash
uv run --locked python scripts/experiments/smoke_test_reporting.py
uv run --locked python scripts/experiments/generate_report.py --run-dir outputs/experiments/실제run_id
uv run --locked python scripts/experiments/compare_models.py --runs-root outputs/experiments/
```

실행위치MV루트. 첫명령은SYNTHETIC만생성하고PARTIAL로끝난다. 두번째는저장된Run의새버전report.md/report_2.md와figures/report_N을만든다. 세번째는기본REAL·COMPLETED만비교한다. `--include-synthetic --allow-partial`은인프라검토용으로만명시한다. 기존보고서/비교파일은덮지않는다.

그래프는Loss·구성요소·LR·gradient·epoch시간·Validation곡선·ROC/PR·AUPRO·점수분포·confusion·품목/시점·latency와비교scatter/Pareto다. 미측정GPU/모델크기등은생성하지않고사유를기록한다. 작은표본은일반화근거부족을기재한다. Loss자동진단은관측/가설을나누고Loss감소만으로모델성능을판정하지않는다.

대표Run은Validation ImageAUROC 또는mAP50-95 최대,동률run_id사전순이다. Test로선정하지않는다. 비교그룹은data_kind·family·track·Manifest/annotation/classes/평가ID/Split/Crop/Adapter/protocol/인프라소스해시가같아야한다. failed/미완료/자료누락과SYNTHETIC을별도기록한다. 속도는그룹내에서도하드웨어·batch·입력집합·dtype별로나눈다.

## 10. GitHub 결과 제출과 가중치 별도 전달

**추론/연결 코드·실행설정·결과Markdown·공유가능그래프만PR로제출한다. 가중치·checkpoint·memory bank·검색index는GitHub에올리지않는다.** 별도팀채널로전달하고파일명·크기·SHA-256·권한있는수령방법만보고서에적는다. 접근토큰/비밀URL/개인절대경로는공개하지않는다. 원본/파생실제이미지는공유권한을검토하고내부검토와외부공개를구분한다. 합성그림은SYNTHETIC표시를유지한다.

## 근거와 한계

- [COCO 공식 평가 코드](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py)
- [sklearn AP 정의](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)
- [Anomalib 지표/AUPRO 참고](https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/metrics/index.html)

기본픽셀/AUPRO의명시적근사는저자구현과비트단위동일성을보장하지않는다. 이규약을바꾸면새protocol version과새Run으로평가하고이전결과를덮지않는다. 실제학습·공식출력/손실·GPU성능은팀원이별도검증한다.

## 확장 메모

`ground_truth_records(...,lazy=True)`는 GT 마스크와 평가 영역을 지연참조로 유지한다. `load_predictions`도 기본지연복원이며 큰score map을 한 번에적재하지 않는다. 비교기는실제픽셀/검출평가가능ID집합해시까지그룹에넣어, 누락지도때문에평가표본이다른결과를직접비교하지않는다. 이런보수적그룹분리때문에영상지표가같은범위여도픽셀지도제공범위가다르면별도그룹일수있다.
