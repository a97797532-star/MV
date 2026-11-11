# 데이터 경로와 이전 검증

원본 파일 복사는 사용자가 수행한다. 분석기는 원본을 읽기만 한다. 데이터셋을 clone하거나 다운로드하지 않는다. 프로젝트 루트에서:

```bash
export REALIAD_DATA_ROOT="/home/본인/MV/dataset"
test -d "$REALIAD_DATA_ROOT" && echo "dataset directory exists"
uv run --locked python -m mv_analysis.cli validate-data
```

export는 현재 터미널에 경로를 설정한다. 팀원마다 경로가 달라도 코드 수정이 필요 없다. 새 터미널에서는 다시 설정한다. 권한 오류는 `ls -ld "$REALIAD_DATA_ROOT"`로 소유자/접근 권한을 확인한다. 무작정 chmod -R 하지 않는다. `--data-root /실제/경로`는 환경변수보다 우선한다.

기대 구조는 `category/OK/Sxxxx/<category>_<serial>_OK_C1_<timestamp>.jpg`, `category/NG/<defect>/Sxxxx/<category>_<serial>_NG_<defect>_C1_<timestamp>.jpg` 및 같은 stem의 PNG다. C1~C5가 capture 단위다. `Zone.Identifier` 부가 파일은 무시한다.

검증 명령은 전체 JPG를 decode하여 크기·접근·파싱·짝·5시점·분할을 검사한다. 출력 첫 줄의 새 outputs 폴더에 metadata_validation_report.json과 CSV가 생긴다. `--inventory-only`는 빠른 목록 검사이며 손상 decode 검증을 대체하지 않는다. 중복 상대 경로와 실제 내용 중복은 다르며 내용 중복은 미검증으로 표시한다.

과거 146,060 JPG/50,115 PNG는 참고치다. 현재 원본과의 manifest 대조가 없으면 개수 차이가 복사 누락인지 다른 버전인지 확정할 수 없다. 사용자가 복사 완료를 확정하고, 실제 파일 손상·고아 마스크를 조사한 뒤 전체 분석한다. NG–PNG 개수 차이는 오류가 아니다. 파일 개수가 2회 같아도 복사 완료를 증명하지 않는다.

```bash
uv run --locked python -m mv_analysis.cli --output outputs/본인실행 --resume mask-audit
```

위 명령은 기존 실행의 설정(특히 --limit/--inventory-only)과 같아야 한다. mask-audit는 선택 manifest의 모든 마스크를 읽고 픽셀 분포·채널·형식·짝 크기를 확인한다. 값이 정확히 {0,255} 또는 {0,1}인 경우에만 nonzero 임계 정책을 확정한다. 그 외는 임의 127/128 threshold를 쓰지 않고 중단한다. 정책 변경에는 원본 주석 규약과 실제 overlay 검수가 필요하다.


## NG/마스크 구분 정책 (2026-11-11 수정)

NG는 불량 제품의 촬영 이미지이며 모든 시점에 위치 마스크가 제공된다고 가정하지 않는다. has_mask는 실제 연결 여부이고 NG 원래 상태는 유지한다. 전체 NG를 메타데이터·밝기·해상도에 포함한다. 마스크 기반 위치 분석은 연결된 NG만 사용하며 미주석 NG에 빈 마스크/빈 YOLO 라벨을 만들지 않는다. 정상 OK의 빈 YOLO 라벨과 구분한다. ng_without_mask.csv에서 경로·대체 stem 후보를 조사하며 파일 부재만으로 의도적 미제공과 유실을 확정할 수 없다. 제공된 PNG의 연결 성공률·decode 오류를 별도 기록한다. 회색조 PNG는 손상으로 판정하지 않고 mask-thresholds의 민감도/overlay 검증 뒤 정책을 정한다.


## 최신 실행 정책 정정

회색조 PNG를 파일 손상으로 간주하지 않는다. mask-audit는 파일 decode/짝 크기 검증과 threshold 확정을 구분한다. 정확한 이진 인코딩이면 자동 정책을 도출할 수 있으나, 회색조면 mask-thresholds의 비교/overlay 검수 결과를 남기고 최종 정책을 보류한다. 이 경우 run-all은 밝기·해상도를 계속 실행하고 mask_stages_deferred.json에 위치 단계 보류를 남긴다. 미주석 NG는 개수 차이 때문에 실행을 차단하지 않는다. 현재 확정 수는 OK 72,840 / NG 78,210 / 위치 정답 NG 51,329 / 미제공 NG 26,881이다. fire_hood의 HS/QS 충돌 10장은 영상 분석에 포함하되 유형 라벨은 UNRESOLVED로 기록한다.


## 회색조 마스크 정책 검증 완료 (2026-11-11)

실제 30품목×112 품목/유형 조합에서 336장, 6개 임계값을 비교했고 overlay 30개를 만들었다. 전체 PNG 51,329장의 decode/짝 크기 검증은 0오류였다. [공식 Real-IAD EvalPerPixelAUC](https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249)의 양수 마스크 처리와 실제 경계 수축/분절 관측을 함께 근거로, 본 프로젝트 위치 분석은 grayscale >0, 면적 필터 없음으로 고정했다. 이는 모든 결함 경계의 의미적 정확도 증명이 아니다. 초기 보류 상태는 이 검증으로 갱신되었다. 원본 회색조 마스크는 그대로 보존한다.

다른 실행에서 재현하려면 전체 metadata/decode 실행의 mask-audit와 mask-thresholds 결과를 먼저 만든 뒤 새 공간 분석 실행을 만든다. 아래 경로는 본인 실제 출력으로 바꾼다.

```bash
uv run --locked python -m mv_analysis.cli --output outputs/full-metadata --resume mask-audit
uv run --locked python -m mv_analysis.cli --output outputs/full-metadata --resume mask-thresholds
uv run --locked python scripts/continue_image_analysis.py --metadata-run outputs/full-metadata --output outputs/spatial-analysis
uv run --locked python scripts/approve_mask_policy.py --integrity outputs/full-metadata --study outputs/full-metadata --run outputs/spatial-analysis
uv run --locked python -m mv_analysis.cli --output outputs/spatial-analysis --resume heatmap
uv run --locked python -m mv_analysis.cli --output outputs/spatial-analysis --resume bbox
```

최초 전체 metadata는 validate-data 명령으로 끝나야 한다. 승인 스크립트는 전체 무결성/30품목 민감도 비교 증거가 없거나 기존 policy가 있으면 실패한다. 정책 파일을 덮어쓰지 않는다. run-all은 미검증 회색조를 자동 threshold 처리하지 않으므로 image 단계 완료 후 위 검증/위치 단계를 이어서 실행한다. root/limit/class-policy/lock/source 설정을 동일하게 유지한다.


제공된 PNG가 전부 0인 경우는 mask absence와 다르다. 파일은 정상적으로 읽히는 annotation이며 has_mask=True, 분류 status=NG를 유지한다. 박스는 0개이며 annotation_status=provided_empty로 별도 집계하고, 해당 빈 YOLO 라벨은 실제 제공된 주석을 표현한다. 이를 정상 제품으로 재분류하지 않는다. has_mask=False인 NG에는 여전히 라벨을 생성하지 않는다.
