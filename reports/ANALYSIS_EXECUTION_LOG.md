# 분석 실행 로그

갱신 UTC: 2026-11-11T09:29:56.378710+00:00. 실제 결과가 있는 단계만 완료로 표시한다.

## 입력 및 안전

입력: /home/geonug/MV/dataset. 사용자 복사 완료 확인. 확정 대상 JPG 151,050 / PNG 51,329. 읽기 전용 사용, 원본 이동/수정/삭제 없음. outputs는 Git 제외.

## 실행 이력

### outputs/smoke_20261111_v2

```json
{
  "created": "2026-11-11T03:12:30.716596+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": 100,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "0b568929de6e0c34be6a5dddc0e80ac3340871893e5fb35ff503a210a5540251"
  },
  "commands": [
    {
      "command": "run-all",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/smoke_20261111_v2",
        "run-all",
        "--limit",
        "100"
      ],
      "elapsed_s": 20.998183012008667,
      "error": null,
      "finished": "2026-11-11T03:12:51.715531+00:00"
    }
  ]
}
```

### outputs/smoke_20261111_v4

```json
{
  "created": "2026-11-11T03:14:40.659720+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": 100,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "b7752569657350a2becc86375968b91bd53f99b79801eba177631078e7c2fc20"
  },
  "commands": [
    {
      "command": "run-all",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/smoke_20261111_v4",
        "run-all",
        "--limit",
        "100"
      ],
      "elapsed_s": 22.40325379371643,
      "error": null,
      "finished": "2026-11-11T03:15:03.063117+00:00"
    }
  ]
}
```

### outputs/smoke_20261111_v5

```json
{
  "created": "2026-11-11T03:18:46.335589+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": 100,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "c4e7c7e3cd3164e7a6616b23e75e7990d8909837e3ad9437f0efcf5ceda0f552"
  },
  "commands": [
    {
      "command": "run-all",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/smoke_20261111_v5",
        "run-all",
        "--limit",
        "100"
      ],
      "elapsed_s": 26.525953769683838,
      "error": null,
      "finished": "2026-11-11T03:19:12.861747+00:00"
    }
  ]
}
```

### outputs/smoke_20261111_v6

```json
{
  "created": "2026-11-11T03:28:17.053828+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": 100,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "91d12aa05c33461a36fda6c5da1cd0c0ae349ae1c0ceaf489a4713b12d2acc17"
  },
  "commands": [
    {
      "command": "run-all",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/smoke_20261111_v6",
        "run-all",
        "--limit",
        "100"
      ],
      "elapsed_s": 22.66536855697632,
      "error": null,
      "finished": "2026-11-11T03:28:39.719334+00:00"
    }
  ]
}
```

### outputs/full_20261111_v4

```json
{
  "created": "2026-11-11T03:15:41.341508+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": null,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "b7752569657350a2becc86375968b91bd53f99b79801eba177631078e7c2fc20"
  },
  "commands": [
    {
      "command": "validate-data",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/full_20261111_v4",
        "validate-data"
      ],
      "elapsed_s": 701.7709581851959,
      "error": null,
      "finished": "2026-11-11T03:27:23.112663+00:00"
    }
  ]
}
```

### outputs/full_20261111_v6

```json
{
  "created": "2026-11-11T03:28:29.704909+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": null,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "91d12aa05c33461a36fda6c5da1cd0c0ae349ae1c0ceaf489a4713b12d2acc17"
  },
  "commands": [
    {
      "command": "metadata-import",
      "argv": [
        "--metadata-run",
        "outputs/full_20261111_v4",
        "--output",
        "outputs/full_20261111_v6"
      ],
      "error": null,
      "finished": "2026-11-11T03:28:29.704909+00:00",
      "success": 151050,
      "source_run": "outputs/full_20261111_v4",
      "snapshot_verified": true
    },
    {
      "command": "brightness",
      "argv": [
        "--data-root",
        "dataset",
        "--output",
        "outputs/full_20261111_v6",
        "--resume",
        "brightness"
      ],
      "elapsed_s": 1038.4623329639435,
      "error": null,
      "finished": "2026-11-11T03:45:49.228684+00:00"
    },
    {
      "command": "resolution-batch-finalize",
      "argv": [
        "--run",
        "outputs/full_20261111_v6",
        "--batch-size",
        "1",
        "--finalize"
      ],
      "source_sha256": "253019974b36a9d4beeb580580be6b3e6cf2ed59152146d813545d4083b4acf1",
      "target": 151050,
      "success": 151050,
      "error": null,
      "finished": "2026-11-11T08:04:52.653974+00:00"
    }
  ],
  "provenance": {
    "created": "2026-11-11T03:15:41.341508+00:00",
    "config": {
      "root": "/home/geonug/MV/dataset",
      "limit": null,
      "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
      "class_policy": "defect_type",
      "inventory_only": false,
      "source_sha256": "b7752569657350a2becc86375968b91bd53f99b79801eba177631078e7c2fc20"
    },
    "commands": [
      {
        "command": "validate-data",
        "argv": [
          "--data-root",
          "dataset",
          "--output",
          "outputs/full_20261111_v4",
          "validate-data"
        ],
        "elapsed_s": 701.7709581851959,
        "error": null,
        "finished": "2026-11-11T03:27:23.112663+00:00"
      }
    ]
  }
}
```

### outputs/windows_preserved_20261111_v1

```json
{
  "created": "2026-11-11T06:00:13.494434+00:00",
  "config": {
    "root": "/home/geonug/MV/dataset",
    "limit": null,
    "lock_sha256": "1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32",
    "class_policy": "defect_type",
    "inventory_only": false,
    "source_sha256": "68b93d7317baf4b0aa0e440f011844b62f3d31d2046c62b8122aabf162018001",
    "split_policy": "windows-project-v1"
  },
  "provenance": {
    "parent_run": "outputs/full_20261111_v6",
    "verified_split": "outputs/windows_parity_20261111_v1/image_metadata_with_preserved_windows_split.csv",
    "new_image_decodes": 0,
    "method": "Original executed notebook seed42 split reproduced identically for all 151050 images"
  },
  "commands": [
    {
      "command": "resolution-metadata-rebind",
      "argv": [
        "--source",
        "outputs/full_20261111_v6",
        "--target",
        "outputs/windows_preserved_20261111_v1"
      ],
      "error": null,
      "finished": "2026-11-11T09:14:29.442479+00:00",
      "source_csv_sha256": "fa1c0d662e986dd0fab9f2a64405ef052405333d50909e3319803d382f4377ec",
      "success_images": 151050,
      "new_image_decodes": 0
    }
  ]
}
```

## 전체 데이터 처리 상태

표준 라이브러리 구조 검사: 151,050 JPG, 51,329 PNG, parse 오류 0, 고아 PNG 0.

전체 메타데이터: 완료, 성공 151050, 오류 0.

전체 밝기: 완료, 성공 151050, 오류는 brightness_per_image_execution.json의 최종 값을 확인.

전체 해상도: 완료, 성공 이미지 151050, 오류는 resolution_checkpoint_execution.json의 최종 값을 확인.

전체 히트맵: 560개 그룹 CSV; 전체 박스: 60629개 박스 CSV. 정책 상태: reviewed_nonzero_reference_policy. 최종 성공/오류는 해당 run.json과 검증 JSON을 확인.

## 실행 시간·디스크 예상

실제 100장 표본 run-all은 약 22초였다. 전체 151,050장의 단순 비례 추정은 약 9.4시간이며 첫 그림/초기화 비용과 병렬도·품목별 JPEG 내용에 따라 달라진다. 이는 완료 시간 약속이 아니다. 해상도 계산은 참조 통계를 재사용하고 최대 4 worker를 사용한다. 실행별 체크포인트를 보존한다. 설치 후 약 740GiB 여유를 확인했으며 결과는 CSV/JSONL 중심이고 원본 복사본을 만들지 않는다.

## 검증 및 미검증

환경 dummy 성공, 합성 테스트 결과는 reports/preflight_pytest.txt 및 최신 테스트 로그 참조. 표본 영상 분석 100/100 성공, 0오류. 팀원 4명 개별 설치/원격 쓰기 권한/모델 성능은 미검증. Windows split 재현은 전량 일치, 영상 지표는 정의 차이와 같은 방법 재실행을 구분해 검증한다.

## 추가 통합 실행 · 보존된 Windows 분할과 영역별 밝기

### outputs/windows_preserved_20261111_v1/restoration_validation.json

```json
{
  "images": 151050,
  "split_counts": {
    "train": 105735,
    "test": 22660,
    "validation": 22655
  },
  "product_groups": 30210,
  "split_differences": 0,
  "brightness_reused_images": 151050,
  "original_sources_modified": false
}
```

### outputs/windows_preserved_20261111_v1/heatmap_validation.json

```json
{
  "train_ng_images": 54805,
  "provided_masks": 36173,
  "success": 36173,
  "errors": 0,
  "groups": 560,
  "groups_no_known": 6,
  "groups_no_positive": 6,
  "split_policy": "source metadata split, preserved in run.json"
}
```

### outputs/spatial_20261111_v7/bbox_validation_report.json

```json
{
  "images": 124162,
  "expected_images": 124162,
  "unannotated_ng_skipped": 26888,
  "boxes": 60629,
  "errors": 0,
  "classes": 8,
  "normal_empty_labels": 72840,
  "provided_empty_ng_masks": 34,
  "coordinate_format": "xyxy, exclusive x1/y1",
  "small_box_definition": "bbox area < 32^2 native pixels",
  "small_box_count": 16297
}
```

### outputs/spatial_20261111_v7/detection_export_validation.json

```json
{
  "metadata_images": 151050,
  "eligible_images": 124162,
  "normal_empty_labels": 72840,
  "provided_empty_ng_annotations": 34,
  "unannotated_ng_excluded": 26881,
  "masked_class_conflicts_excluded": 7,
  "boxes": 60629,
  "classes": 8,
  "validated_coco_images": 124162,
  "validated_coco_annotations": 60629,
  "validated_yolo_boxes": 60629,
  "errors": []
}
```

### outputs/windows_preserved_20261111_v1/resolution_scientific_validation.json

```json
{
  "images": 151050,
  "metric_rows": 453150,
  "step_rows": 151050,
  "success": true,
  "checks": {
    "full_scope": true,
    "one_record_per_image_target": true,
    "native_identity": true,
    "psnr_db_finite": true,
    "ssim_finite": true,
    "rgb_rmse_finite": true,
    "edge_recall_finite": true,
    "edge_f1_finite": true,
    "ssim_range": true,
    "edge_recall_range": true,
    "edge_f1_range": true,
    "rgb_rmse_nonnegative": true,
    "laplacian_energy_nonnegative": true,
    "gradient_energy_nonnegative": true,
    "laplacian_retention_nonnegative": true,
    "gradient_retention_nonnegative": true,
    "local_contrast_retention_nonnegative": true,
    "high_frequency_proxy_is_declared_laplacian_ratio": true,
    "full_step_scope": true,
    "ssim_drop_matches_direct_targets": true,
    "rmse_increase_matches_direct_targets": true
  },
  "failed": [],
  "nonmonotonic_rmse_images": 0,
  "nonmonotonic_ssim_images": 0,
  "undefined_ratio_counts": {
    "laplacian_retention": 6,
    "gradient_retention": 6,
    "local_contrast_retention": 6
  },
  "notes": "Nonmonotonic metrics are recorded, not automatically errors. Exact edge agreement is not model recall; high frequency is a Laplacian proxy, not FFT."
}
```

영역별 밝기 입력: /home/geonug/MV/dataset; 메타데이터/기존 밝기 입력: outputs/windows_preserved_20261111_v1. 최초2 worker로 실행한 뒤 해상도 완료까지22,000장 체크포인트에서 대기했고, 이후4 worker로재개했습니다. 완료 체크포인트 151,050/151,050; 완료 배치의 이미지 오류 0. worker 종료와 분할 불확실은 이미지 decode 오류와 구분합니다.

실제 재개 명령: `uv run --locked python -m mv_analysis.regional_cli --source-run outputs/windows_preserved_20261111_v1 --output outputs/background_full_20261111_v1 --compare-methods --validation-evidence reports/BACKGROUND_SEGMENTATION_REVIEW.json --resume --batch-size 2000 --workers 4`. 마지막 --finalize 집계 완료.

### outputs/background_full_20261111_v1/regional_validation.json

```json
{
  "processed": 151050,
  "segmentation_status_counts": {
    "accepted_heuristic": 78526,
    "uncertain": 72517,
    "failed": 7
  },
  "background_counts": {
    "BLACK": 90771,
    "WHITE": 49034,
    "GRAY": 11226,
    "MIXED": 10,
    "UNKNOWN": 9
  },
  "accepted_product_statistics": 78526,
  "uncertain_product_values_missing": true,
  "defect_status_counts": {
    "not_provided": 99721,
    "segmentation_uncertain": 24130,
    "estimated_product_local_context": 22411,
    "insufficient_or_uncertain_product_context": 4754,
    "provided_empty": 34
  },
  "comparison_groups": 560,
  "ground_truth_foreground_available": false,
  "method_agreement_is_not_ground_truth_iou": true,
  "source_run": "outputs/windows_preserved_20261111_v1"
}
```

### outputs/background_full_20261111_v1/scientific_validation.json

```json
{
  "images": 151050,
  "success": true,
  "checks": {
    "unique_images": true,
    "scope": true,
    "all_statuses_preserved": true,
    "uncertain_product_missing": true,
    "uncertain_background_missing": true,
    "accepted_product_finite": true,
    "complement_region_mean_identity": true,
    "local_context_valid": true,
    "unprovided_ng_kept": true,
    "whole_reproduced": true,
    "whole_mean_range": true,
    "product_mean_range": true,
    "background_mean_range": true,
    "defect_mean_range": true
  },
  "max_complement_mean_error": 1.4210854715202004e-14,
  "failed": [],
  "ground_truth_accuracy_measured": false
}
```

### outputs/background_full_20261111_v1/whole_brightness_reproduction.json

```json
{
  "images": 151050,
  "max_absolute_difference": 0.0
}
```

[작업자143 종료와 성공 체크포인트 보존 기록](PROCESS_INTERRUPTION_LOG.json). 이미지 분석 실패와 프로세스 종료 원인을 혼동하지 않습니다.

## 해상도 상세 집계·회의 PDF 후속 작업

UTC 2026-11-11T11:08:58.530478+00:00. 기존 해상도 CSV 453,150행/151,050이미지와 단계별 151,050행 재사용. 전체 해상도 계산 재실행 0건. 신규 집계 CSV 11개, PNG 28개, 최종 회의 PDF 51쪽 생성. 입력 SHA-256 전후 일치 및 기존 raw CSV SHA 일치. pytest 22 passed in 11.69s. PDFium 전 페이지 한글 추출/페이지 수 검사 통과, 선택 페이지 육안 검수. Git 후보 코드·설정·문서만 확인, 개별 영상/집계 CSV/PNG는 outputs에서 제외. Commit/Push 미수행. 상세 근거: RESOLUTION_DELIVERY_VALIDATION.json 및 RESOLUTION_DELIVERY_GUIDE.md.
