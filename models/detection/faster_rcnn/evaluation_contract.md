# Faster R-CNN — 팀원 구현 계약

공식 소스: https://github.com/pytorch/vision

고정 commit: `4260301135e34180d865426765487113f84e7707`. 임의로 최신 HEAD로 바꾸지 않는다. 실제 모델 통합은 **UNVERIFIED / TODO**다. 담당자 이름은 팀에서 정한다.

## TODO(담당자): 공식 출력 → 공통 평가

- 목적: `predict_original`에서 공식 예측을 원본 좌표로 복원해 common evaluator에 전달한다.
- 입력: 실제 모델 출력, 샘플 crop_xyxy/original_size/resize_scale_xy/padding_lrtb. 출력: image_id·split·coordinate_space=original과 XYXY boxes·정규화되지 않은 원본 좌표·0기반 canonical labels·0..1 confidence.
- 참고: mv_analysis/experiments/bridge.py의 원본 GT 읽기와 역변환 helper. 원본 GT를 모델 예측에 섞지 않는다.
- GT 평가 영역은 사전에 선언한 canonical Crop 또는 원본 범위다. 모델별로 편리한 영역을 사후 선택하지 않는다. Crop 밖 미관측 점수는 정상0으로 채우지 않는다.
- Validation에서만 calibrate_detection 호출 → thresholds.json 저장 → Test에는 같은 정책으로 evaluate_detection 호출.
- NMS/최소 confidence/최대 검출 수와 적용 주체를 config에 기록한다. 공통 COCO mAP와 고정Threshold TP/FP/FN은 별개의 지표다.
- NG 미주석·빈 NG·무효 타깃의 평가 제외 사유와 수를 보고한다. 단일클래스 AUROC나 위치GT없는픽셀지표는 N/A다.

## Benchmark와 보고

model.eval() 후 같은 장비·batch·입력집합에서 benchmark를 호출한다. model-only와 전처리+모델+후처리, 로드 시간, CPU RSS/GPU VRAM을 분리한다. 미측정 GPU 수치를 만들지 않는다. Recorder에 metrics/predictions/benchmark를 저장한 뒤 generate_experiment_report(run_dir)를 호출한다.

성공 기준: 예측 ID 완전 일치, 클래스·좌표 범위·Split/제품 누수 검사, Validation Threshold 출처 검사, 원본 정합, 모델 실제출력 기반 보고서. 관련 테스트: 공통 AUROC/AUPRO/COCO/FPFN/좌표/보고서/비교 필터 테스트 및 팀원 모델 통합 테스트.
