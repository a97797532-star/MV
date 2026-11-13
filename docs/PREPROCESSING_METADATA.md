# 저장된 Crop CSV로 전처리하기

현재 팀 공유 대상은 `outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv`입니다. 파일별 해시와 수령 방법은 [공통 코드 배포 안내](team/CODE_RELEASE.md)를 따릅니다. 아래의 `preprocessing_metadata.csv`는 수동 검수 이전 기준본에 대한 기록이므로 현재 최종본과 혼동하지 않습니다.

## 기준 CSV 생성 시점의 기록

최종 파일: `outputs/adaptive_crop_full_v1/preprocessing_metadata.csv`

**151,050행이며 현재 전부 정책 C, 원본 전체 `[0,0,1024,1024]`다.** 제품 GT 평가에서 GrabCut/CenterCrop/Gate의 제품 외곽 손실이 확인돼 확대 Crop을 승인하지 않았다. 좌표 생성 완료와 적응형 Crop 안전성 입증은 다르다. 현재 확대 이득은 없다.

원본 이미지 파일은 별도로 필요하다. CSV를 소비하는 전처리 코드는 정책 JSON, GT Ledger, 다른 분석 CSV를 읽을 필요가 없다. 같은 내용의 요청된 원본 이름은 `final_crop_manifest.csv`, 압축본은 `final_crop_manifest.parquet`다.

## 바로 사용

프로젝트 루트 `~/MV`에서 실행한다.

```python
from mv_analysis.crop_manifest import iter_metadata, load_crop_rgb

metadata = "outputs/adaptive_crop_full_v1/preprocessing_metadata.csv"
for row in iter_metadata(metadata, split="train"):
    rgb = load_crop_rgb(row)  # 원본 로딩 → CSV 좌표 Crop → RGB HWC uint8
    # 선택한 모델의 Resize / ToTensor / Normalize를 여기서 한 번 적용한다.
    # 이번 정책에서는 추가 CenterCrop을 조용히 적용하지 않는다.
```

`iter_metadata()`는 CSV를 5,000행 단위로 읽고 이미지를 메모리에 모두 적재하지 않는다. `split`을 생략하면 전체를 순회한다. 입력 파일의 stat fingerprint나 원본 크기가 달라졌으면 오류를 내므로 원본을 임의로 수정한 상태에서 계속 처리하지 않는다. 데이터 루트가 바뀌면 `load_crop_rgb(row, data_root="/새/데이터루트")`로 상대 경로를 사용하되 새 복사본의 fingerprint를 별도 검증해야 한다.

첫 행 실제 이미지 Smoke Test는 RGB `(1024,1024,3)`, `uint8`로 통과했다. 이 과정에서 Crop 이미지 파일을 저장하지 않았다.

## 필드 해석

| 필드 | 의미 |
|---|---|
| image_id | 원본 상대 경로에서 생성한 고유 ID |
| product_id, category, view, split | 기존 선언 제품·품목·C1~C5·Train/Validation/Test 유지 |
| original_path | 원본 이미지의 Ubuntu 절대 경로 |
| source_relative_path | 데이터 루트 기준 상대 경로 |
| original_width, original_height | 실제 원본 헤더로 확인한 픽셀 크기 |
| crop_x0, crop_y0, crop_x1, crop_y1 | 원본 좌표 XYXY, 끝 좌표 exclusive |
| crop_width, crop_height | Crop 크기, `x1-x0`, `y1-y0` |
| selected_policy | A GrabCut90+10%, B Center896, C 원본 전체. 현재 C만 사용 |
| quality_status | 현재 UNVERIFIED. 제품 안전성이 전수 검증됐다는 뜻이 아님 |
| risk_codes | JSON 문자열 배열. `json.loads()`로 읽는다 |
| fallback_reason | 현재 검증 범위 부족에 따른 원본 유지 이유 |
| geometric_gain, full_frame | 현재 1배·True |
| policy_version, policy_sha256 | 고정된 정책 식별 정보. 소비 시 정책 파일을 열 필요는 없음 |
| source_fingerprint | `stat-v1:파일크기:mtime_ns`. 새 JPEG SHA-256 재검증이 아님 |
| source_size_bytes, source_mtime_ns | 생성 시 원본 파일 식별 정보 |
| source_header_verified, source_error | 원본 헤더 확인 여부와 입력 오류 메시지 |
| processing_status | 정상 좌표 생성 또는 오류 Fallback 상태 |
| image_features_reused | 기존 이미지 특징 캐시를 진단에 재사용했는지 여부 |
| image_gate_status | 기존 2,550장 진단 상태. 나머지는 NOT_EVALUATED_POLICY_BLOCKED |
| coordinate_format, schema_version | exclusive 원본 픽셀 좌표 및 CSV 스키마 버전 |
| crop_saved, resize_applied, normalization_applied | 모두 False. 좌표만 생성했고 Resize/Normalize하지 않음 |
| additional_center_crop_allowed | False. 추가 CenterCrop에는 별도 감사가 필요 |
| augmentation_allowed | 기존 split이 train인 경우만 True |
| loaded_image_contract, adapter_rule | RGB HWC uint8 → 모델별 Resize/Normalize, 암묵적 두 번째 Crop 금지 |

현재 생산 Manifest에는 OK/NG, 결함 유형, 마스크 경로, 제품 GT 좌표를 넣지 않았다. 전처리 결정에 정답을 섞지 않기 위함이다. 모델 학습용 라벨 연결은 별도 작업이며, 경로 문자열에서 정답을 추정하거나 위치 GT 없는 NG를 정상 이미지로 바꾸지 않는다.

## BBox와 마스크 변환

```python
from mv_analysis.crop_manifest import transform_boxes, transform_mask

# original_boxes: 원본 픽셀 XYXY 배열. 클래스는 keep으로 같은 순서 필터링한다.
new_boxes, keep = transform_boxes(original_boxes, row, output_hw=(512, 512))
new_classes = original_classes[keep]

# 유효한 원본 마스크가 있을 때만 호출한다. 미제공 마스크를 만들지 않는다.
new_mask = transform_mask(original_mask, row, output_hw=(512, 512))
```

BBox는 원점 이동 → Crop 범위 Clip → 가로·세로별 Scale 순서다. LetterBox 등에서는 `padding_xy=(left,top)`를 명시한다. 함수는 살아남은 BBox와 원래 배열에 대응하는 keep mask를 반환한다. 제거된 NG 객체가 있다고 이미지 자체를 OK로 재분류하면 안 된다.

범주형 마스크는 NEAREST의 floor 좌표 규칙을 사용해 원래 dtype과 클래스 ID를 보존한다. RGB 이미지의 보간과 정규화는 모델별 어댑터에서 결정한다.

## 12개 모델 연결 시 주의

- PatchCore, Dinomaly, INP-Former의 기본 추가 CenterCrop은 원본896 중심 영역에 해당한다. 제공된 양성 마스크 82장을 완전히 제거하고 1,029장을 일부 자르는 기하 위험을 확인했다.
- `require_no_extra_crop(row, "PatchCore")` 등은 현재 CSV에서 명시적으로 오류를 낸다. 추가 Crop을 끄거나 별도 감사된 공식 baseline 실험을 선언해야 한다. 이 함수를 호출하지 않는 외부 모델 코드까지 자동으로 바꿔 주는 것은 아니다.
- EfficientAD-S·UniAD·HVQ-Trans 등의 입력 크기·정규화는 모델별로 유지한다. Faster R-CNN/RetinaNet 내부 Resize·Normalize와 외부 처리를 중복하지 않는다.
- YOLO11 LetterBox·/255, RT-DETRv2·YOLOS의 박스 형식과 입력 스케일, ViTDet RGB0..255 내부 정규화를 동일하게 취급하지 않는다.
- 이번 구현은 공통 기하 변환 준비이며 12개 모델 실행·학습·성능 검증은 하지 않았다. 상세 소스 근거는 `reports/MODEL_INPUT_REQUIREMENTS.md`에 있다.

## 검증 파일과 재개

`outputs/adaptive_crop_full_v1/validation.json`에 전수 행 수, 좌표, 파일 식별 정보, 선언 제품 Split 누수, 5시점 완전성, 마스크 감사 결과를 기록했다. 원본 유지이므로 양성 마스크의 기하 보존율은100%지만 후속 Resize·추가 Crop·모델 검출 성능을 보장하지 않는다.

최초 실행 단계는 다음과 같다. 이미 완료된 GT 평가와 보고서를 다시 계산하거나 덮어쓰지 않는다.

```bash
uv run --offline python scripts/full_crop_gt_validation.py
uv run --offline python scripts/generate_full_crop_manifest.py
uv run --offline python scripts/audit_full_crop_manifest.py
uv run --offline python scripts/report_full_crop_manifest.py
```

좌표 생성 도중 중단되면 `generate_full_crop_manifest.py`를 같은 명령으로 실행한다. 고정 정책·입력·코드 해시가 같을 때 완료된 Parquet 파티션을 건너뛴다. GT 평가·정책 고정 도중의 불완전 상태는 원본 이력을 보존한 채 조사하고 Final 평가를 임의로 반복하지 않는다. 정책을 수정할 때는 새 버전과 미사용 제품 평가를 만든다.

원본 JPG/PNG, 사람 승인 Ledger, 기존 Split·결과는 변경하지 않았고 Crop 이미지 파일은 만들지 않았다. CSV와 대용량 산출물은 `outputs/`에 보관하며 GitHub에 Push하지 않는다.

## 사람이 범위를 조절해야 하는 이미지

별도 목록 `manual_crop_review.csv`와 Crop 검수 웹 도구를 사용한다. 실행은 `uv run --offline python scripts/review_crop_ranges.py --port 8769`이며 자세한 순서는 [MANUAL_CROP_REVIEW.md](MANUAL_CROP_REVIEW.md)에 있다. 승인한 범위만 반영된 새 `preprocessing_metadata_reviewed_vN.csv`를 내보낸 뒤, 전처리는 해당 새 CSV 하나를 읽으면 된다. 기준 CSV와 제품 GT는 보존된다.
