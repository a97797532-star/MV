# Real-IAD 최종 통합 분석 보고서

갱신 UTC: 2026-11-11T09:29:56.378710+00:00. 이 보고서는 실제 산출물을 읽어 작성하며 실행 중인 단계를 완료로 취급하지 않습니다.

## 1. Executive Summary

전체 해상도 상태: 완료; 성공 이미지 151,050/151,050. 전체 작업 완료는 해상도 최종 산출물과 무결성 검증까지 확인한 뒤 판정합니다.

전체 파일 구조 검사 완료: 30품목, JPG 151,050장, OK 72,840장, NG 78,210장, PNG 51,329장. NG 중 위치 정답 제공 51,329장, 미제공 26,881장. NG–PNG 개수 차이는 오류가 아닙니다.

과거 참고치 대비 JPG +4,990, PNG +1,214. 추가 조사에서 확인한 실제 최신 Windows 저장 CSV는 JPG 151,050·PNG 51,329로 Ubuntu와 같고 u_block도 포함합니다. 보존된 과거 Windows 체크포인트는 참고치와 같은29품목이며 최신 대비 추가 경로는 모두u_block(제거0개)이었습니다. 당시 제외 동기와 인용 숫자의 생성 출처 연결은 미확정입니다. [역사적 범위 검증](../outputs/windows_checkpoint_comparison_20261111_v1/comparison.json). 사용자에게 데이터 복사 완료와 현재 전체 대상 승인을 받았습니다. [파일 구조 근거](../outputs/inventory_20261111T031532567293Z/inventory.json).

환경은 Ubuntu 24.04.4 WSL2, Python 3.12.14, uv 0.12.8, torch 2.15.0+cpu입니다. 잠금 설치와 CPU 더미 검증은 통과했습니다. 실제 모델 학습/추론·CUDA 성능·팀원 4명 개별 설치는 미검증입니다. 주요 위험은 전검정 중복 2장, 마스크 경계의 의미 검수 한계, 10장 불량 유형 충돌, serial의 물리 제품 identity 불확실성입니다. 기존 split은 Windows 원본에서 확인하고 전량 동일하게 재현했습니다.

## 2. 데이터셋 구성

| category | NG | OK | NG_with_mask |
| --- | --- | --- | --- |
| audiojack | 2585 | 2465 | 1296 |
| bottle_cap | 2555 | 2460 | 1631 |
| button_battery | 2585 | 2415 | 2150 |
| end_cap | 2600 | 2410 | 2183 |
| eraser | 2605 | 2460 | 1488 |
| fire_hood | 2520 | 2505 | 1350 |
| mint | 3635 | 1670 | 2099 |
| mounts | 2555 | 2495 | 1338 |
| pcb | 2545 | 2465 | 2289 |
| phone_battery | 2585 | 2415 | 1550 |
| plastic_nut | 2500 | 2510 | 1246 |
| plastic_plug | 2570 | 2425 | 1419 |
| porcelain_doll | 2585 | 2415 | 1255 |
| regulator | 2610 | 2490 | 1080 |
| rolled_strip_base | 2565 | 2485 | 2525 |
| sim_card_set | 2540 | 2490 | 2069 |
| switch | 2590 | 2460 | 1994 |
| tape | 2600 | 2500 | 1443 |
| terminalblock | 2615 | 2435 | 2008 |
| toothbrush | 2560 | 2445 | 2027 |
| toy | 2530 | 2495 | 2190 |
| toy_brick | 2530 | 2480 | 1536 |
| transistor1 | 2515 | 2485 | 2117 |
| u_block | 2495 | 2495 | 1214 |
| usb | 2590 | 2460 | 1754 |
| usb_adaptor | 2710 | 2305 | 1520 |
| vcpill | 2505 | 2520 | 1470 |
| wooden_beads | 2830 | 2175 | 1684 |
| woodstick | 2500 | 2505 | 1073 |
| zipper | 2500 | 2505 | 2331 |

품목별 정상/불량과 위치 정답 제공 수를 구분했습니다. 근거: [file_metadata.csv](../outputs/inventory_20261111T031532567293Z/file_metadata.csv). 전체 OK 비율 48.2224%, NG 비율 51.7776%, NG 위치 주석 coverage 65.6297%. Coverage는 마스크 연결 성공률과 다른 지표입니다.

C1~C5 각각 30,210장, 불완전 capture 그룹 0개. PNG의 동일 stem JPG 연결 성공률 100.00%, 고아 PNG 0개. 전체 파일 SHA256 내용 검사는 아래 별도 검증 결과를 확인합니다.

NG 상태는 불량 제품의 촬영 시점 이미지에 부여되며 각 시점의 가시적인 결함 존재와 동일하지 않을 수 있습니다. 미주석 NG 26,881장에는 다른 폴더의 동일 stem/casefold PNG 후보가 없었습니다. 경로상 위치 주석 미제공으로 기록하되 의도적인 미제공과 실제 파일 유실을 경로만으로 단정하지 않습니다. [ng_without_mask.csv](../outputs/inventory_20261111T031532567293Z/ng_without_mask.csv). 빈 마스크를 만들거나 OK로 바꾸지 않았습니다.

## 3. 메타데이터 분석 결과

전체 JPG decode 대상 151,050, 성공 151,050, 오류 0. 원본 해상도 분포 `{'(1024, 1024)': 151050}`. 분할 누수 0, 라벨 충돌 10장. [검증 JSON](../outputs/windows_preserved_20261111_v1/metadata_validation_report.json).

![품목 분포](../outputs/windows_preserved_20261111_v1/dataset_category_distribution.png)

품목별 영상 수는 비슷하지만 결함 위치 주석 수와 불량 유형 분포는 다르므로 전체 수만으로 균형을 판단하지 않습니다.

| split | images | grouped_product_ids |
| --- | --- | --- |
| test | 22660 | 4532 |
| train | 105735 | 21147 |
| validation | 22655 | 4531 |

정확한 파일 바이트 SHA256 검증: 202,379/202,379파일, 오류 0, JPG 중복 그룹 1, 초기 hash 탐색 분할 시점의 같은 JPG 바이트 교차 그룹 1; 현재 보존된 Windows 분할은 아래 품질 검증에서 별도 확인합니다. [내용 무결성 근거](../outputs/content_audit_20261111_v7/content_hash_validation.json). 재인코딩/유사 이미지 중복을 검사한 것은 아닙니다.

초기 실행은 category/serial SHA256 70/15/15 탐색 분할입니다. 이후 Windows 원본 Notebook의 category/quality/defect/serial 제품 키와 seed42 분할을 전량 동일하게 재현했습니다: Train 105,735 / Validation 22,655 / Test 22,660, 제품 그룹 30,210, 차이 0장. [분할 검증](WINDOWS_SPLIT_REPRODUCTION.json). 기존 분할 통계/히트맵은 ../outputs/windows_preserved_20261111_v1에 별도로 보존합니다. serial 재사용이 동일 물리 제품인지는 미확정입니다. fire_hood 유형 충돌 10장은 UNRESOLVED로 유지하고 유형별 탐지 라벨에서 제외합니다.

## 4. 밝기 분석 결과

전체 밝기 151,050장. 지표는 BGR→GRAY 0–255 영상 평균 및 이미지별 P05/P50/P95입니다. [이미지별 근거](../outputs/windows_preserved_20261111_v1/brightness_per_image.csv).

| status | count | mean | std | median |
| --- | --- | --- | --- | --- |
| NG | 78210 | 97.56290 | 72.88941 | 64.83881 |
| OK | 72840 | 98.13740 | 72.78955 | 64.29828 |

| view | status | count | mean | std |
| --- | --- | --- | --- | --- |
| C1 | NG | 15642 | 97.02686 | 70.17602 |
| C1 | OK | 14568 | 97.12782 | 70.26380 |
| C2 | NG | 15642 | 97.41749 | 72.34482 |
| C2 | OK | 14568 | 97.46418 | 72.40294 |
| C3 | NG | 15642 | 97.97650 | 74.49015 |
| C3 | OK | 14568 | 98.39445 | 74.38421 |
| C4 | NG | 15642 | 97.83265 | 73.59812 |
| C4 | OK | 14568 | 98.61787 | 73.03175 |
| C5 | NG | 15642 | 97.56102 | 73.76465 |
| C5 | OK | 14568 | 99.08266 | 73.78717 |

정상·불량 밝기 차이가 큰 후보(같은 품목/시점 OK와 각 NG 유형 비교):

| category | defect_type | view | n_ok | n_ng | mean_difference | cohens_d | histogram_overlap | abs_d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sim_card_set | CH | C3 | 498 | 169 | 20.87715 | 11.35091 | 0.00201 | 11.35091 |
| plastic_plug | AK | C1 | 485 | 169 | -11.79964 | -9.85472 | 0.00000 | 9.85472 |
| sim_card_set | CH | C1 | 498 | 169 | 15.66914 | 9.49144 | 0.00000 | 9.49144 |
| sim_card_set | CH | C2 | 498 | 169 | 18.36167 | 9.34760 | 0.00000 | 9.34760 |
| phone_battery | HS | C4 | 483 | 127 | -38.26252 | -9.06360 | 0.04724 | 9.06360 |
| phone_battery | HS | C3 | 483 | 127 | -28.96749 | -8.81669 | 0.04724 | 8.81669 |
| sim_card_set | CH | C5 | 498 | 169 | 15.23209 | 8.33228 | 0.02367 | 8.33228 |
| sim_card_set | HS | C3 | 498 | 171 | 16.63782 | 8.21443 | 0.02924 | 8.21443 |
| sim_card_set | HS | C2 | 498 | 171 | 14.82352 | 7.98845 | 0.02924 | 7.98845 |
| phone_battery | HS | C5 | 483 | 127 | -52.78008 | -7.96151 | 0.04724 | 7.96151 |
| sim_card_set | CH | C4 | 498 | 169 | 16.62265 | 7.86498 | 0.01976 | 7.86498 |
| sim_card_set | HS | C5 | 498 | 171 | 12.97340 | 7.77994 | 0.02924 | 7.77994 |

비교 560개(현재 u_block 20개 및 UNRESOLVED 5개 포함; 실제 저장 Windows 비교표 555행에 UNRESOLVED 5행을 추가) 중 |Cohen d|≥0.8은 222개. [비교 근거](../outputs/windows_preserved_20261111_v1/brightness_comparison.csv). 32 bin histogram overlap은 분포 공통 질량이며 d는 pooled 표준편차 기준 차이입니다.

![밝기 분포](../outputs/windows_preserved_20261111_v1/brightness_histogram.png)

겹침이 적더라도 조명·배치·재질 차이가 결함 효과와 섞여 있습니다. 밝기만으로 분류 가능한지 또는 조명에 취약한지는 후속 모델 실험 가설입니다. 증강 범위는 [Train 전용 통계](../outputs/windows_preserved_20261111_v1/brightness_train_augmentation_stats.csv)를 출발점으로 삼고 validation으로 선택합니다. 마스크 기반 상대 밝기는 연결된 NG 부분집합의 별도 region_brightness 결과로 기록하며 전체 NG 밝기와 구분합니다.

마스크 제공 NG 51,329장의 결함 영역−배경 평균 밝기 차이는 6.77151 intensity입니다(유효 51,294장, 나머지는 제공된 빈 마스크 등으로 영역 평균 미정의). 이는 전체 NG 78,210장을 대체하지 않는 위치 주석 부분집합 통계입니다. 배경 평균은 마스크 밖 전체 픽셀 기준으로 촬영 배경/정상 물체를 포함하며, 결함 바로 주변 재질만의 국소 대비와는 다릅니다. [영역별 근거](../outputs/spatial_20261111_v7/region_brightness/defect_relative_brightness.csv).

전체 평균은 `{'NG': 97.56290266642773, 'OK': 98.13739528445213}`이며, 품목/유형/시점별 비교 560개(현재 u_block 20개 및 UNRESOLVED 5개 포함; 실제 저장 Windows 비교표 555행에 UNRESOLVED 5행을 추가) 중 |d|≥0.8은 222개였습니다. 품목을 섞은 전체 평균만으로 증강 필요성을 판단하면 이 차이가 가려집니다. 이 수치는 [brightness_comparison.csv](../outputs/windows_preserved_20261111_v1/brightness_comparison.csv)의 관측 통계입니다.

![밝기 검수 사례](../outputs/windows_preserved_20261111_v1/brightness_review_images_readable.png)

중앙값 대표 이미지를 눈으로 검수한 결과 sim_card_set은 흰 배경 전체의 밝기 차이, phone_battery는 푸른 배경 전체의 밝기 차이가 함께 보였습니다. 촬영 조건/배치의 영향 가능성을 검토해야 하며 밝기 차이를 결함 자체의 인과 효과로 단정하지 않습니다. 파일명과 실제 평균은 [검수 manifest](../outputs/windows_preserved_20261111_v1/brightness_review_images.csv)에 있습니다. 증강은 품목/시점별 Train 분위수를 근거로 제한하고 미세 결함 대비를 훼손하지 않는 범위를 validation에서 선택합니다.

증강 정책용 그룹 선택/비교는 별도로 Train 105,733장만 사용해 재계산했습니다(원본 재decode 0장). [Train 검수 후보](../outputs/windows_preserved_20261111_v1/train_brightness_policy_quality_aware/brightness_review_candidates_verified.csv)는 UNRESOLVED 그룹을 제외합니다. Normal-only AD에는 [정상 Train 전용 분위수](../outputs/windows_preserved_20261111_v1/train_brightness_policy_quality_aware/normal_only_train_augmentation_stats.csv)를 사용합니다. 전체 데이터 Cohen d는 기술 분석이며 Test를 포함한 수치로 증강 정책을 선택하지 않습니다.

## 5. 불량 위치 히트맵 분석

| category | defect_type | view | n_images | n_known | n_positive | n_empty | n_unknown | observations | max_occupancy | mean_occupancy | top10pct_mass_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| audiojack | BX | C1 | 94 | 91 | 91 | 0 | 3 | 91 | 0.23077 | 0.00760 | 0.81597 |
| audiojack | BX | C2 | 94 | 72 | 72 | 0 | 22 | 72 | 0.27778 | 0.00530 | 0.97119 |
| audiojack | BX | C3 | 94 | 93 | 93 | 0 | 1 | 93 | 0.23656 | 0.00562 | 0.92060 |
| audiojack | BX | C4 | 94 | 76 | 76 | 0 | 18 | 76 | 0.30263 | 0.00587 | 0.95624 |
| audiojack | BX | C5 | 94 | 85 | 85 | 0 | 9 | 85 | 0.18824 | 0.00577 | 0.92886 |
| audiojack | HS | C1 | 91 | 3 | 3 | 0 | 88 | 3 | 1.00000 | 0.00358 | 1.00000 |
| audiojack | HS | C2 | 91 | 33 | 33 | 0 | 58 | 33 | 0.36364 | 0.00303 | 1.00000 |
| audiojack | HS | C3 | 91 | 18 | 18 | 0 | 73 | 18 | 0.33333 | 0.00389 | 1.00000 |
| audiojack | HS | C4 | 91 | 31 | 31 | 0 | 60 | 31 | 0.22581 | 0.00265 | 1.00000 |
| audiojack | HS | C5 | 91 | 16 | 16 | 0 | 75 | 16 | 0.25000 | 0.00269 | 1.00000 |
| audiojack | QS | C1 | 84 | 36 | 36 | 0 | 48 | 36 | 0.11111 | 0.00340 | 1.00000 |
| audiojack | QS | C2 | 84 | 49 | 49 | 0 | 35 | 49 | 0.10204 | 0.00345 | 1.00000 |
| audiojack | QS | C3 | 84 | 34 | 34 | 0 | 50 | 34 | 0.14706 | 0.00289 | 1.00000 |
| audiojack | QS | C4 | 84 | 45 | 45 | 0 | 39 | 45 | 0.11111 | 0.00310 | 1.00000 |
| audiojack | QS | C5 | 84 | 57 | 57 | 0 | 27 | 57 | 0.08772 | 0.00323 | 1.00000 |

근거 [heatmap_summary.csv](../outputs/windows_preserved_20261111_v1/heatmap_summary.csv). 기존 분할 presence-v2는 원본 양성 픽셀이 하나라도 있는 칸을 영상별로 1회 집계합니다. occupancy_known=칸 점유 영상 수/n_known 제공 마스크 수, occupancy_positive=칸 점유 영상 수/n_positive 비어 있지 않은 마스크 수입니다. 미제공은 n_unknown, 관측 0은 NaN입니다. 초기 spatial_run area-v1은 면적 분율 진단으로 보존하며 두 규약을 혼용하지 않습니다. GAN 위치 정책은 품목·유형·시점별 관측량과 정렬을 함께 검수해야 합니다.

해당 분할 Train NG 제공 마스크 관측 합계 36,173장, 560개 품목/유형/시점 그룹, 10장 미만 그룹 16개. 상위 10% 격자에 모인 결함질량 비율은 관측된 위치의 집중도이며 정상 영역 확률이 아닙니다.

| view | groups | observations | mean_top10_mass_share |
| --- | --- | --- | --- |
| C1 | 112 | 6639 | 0.85087 |
| C2 | 112 | 7115 | 0.88670 |
| C3 | 112 | 7404 | 0.88947 |
| C4 | 112 | 7905 | 0.87684 |
| C5 | 112 | 7110 | 0.89096 |

| category | defect_type | view | n_images | n_known | n_positive | n_empty | n_unknown | observations | max_occupancy | mean_occupancy | top10pct_mass_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| woodstick | HS | C5 | 94 | 15 | 15 | 0 | 79 | 15 | 0.20000 | 0.00742 | 1.00000 |
| bottle_cap | QS | C4 | 86 | 55 | 55 | 0 | 31 | 55 | 0.18182 | 0.00337 | 1.00000 |
| bottle_cap | QS | C3 | 86 | 38 | 38 | 0 | 48 | 38 | 0.21053 | 0.00315 | 1.00000 |
| bottle_cap | QS | C2 | 86 | 29 | 29 | 0 | 57 | 29 | 0.20690 | 0.00351 | 1.00000 |
| audiojack | QS | C3 | 84 | 34 | 34 | 0 | 50 | 34 | 0.14706 | 0.00289 | 1.00000 |
| woodstick | QS | C5 | 85 | 47 | 47 | 0 | 38 | 47 | 0.40426 | 0.00330 | 1.00000 |
| audiojack | QS | C1 | 84 | 36 | 36 | 0 | 48 | 36 | 0.11111 | 0.00340 | 1.00000 |
| audiojack | QS | C2 | 84 | 49 | 49 | 0 | 35 | 49 | 0.10204 | 0.00345 | 1.00000 |

![Train NG 위치](../outputs/windows_preserved_20261111_v1/heatmap_visualization.png)

C1/C2 종합 그림은 중심 가로 띠, C3/C5는 중심 세로 방향의 상대적 집중이 관찰됩니다. 서로 다른 물체를 섞은 정규화 좌표이므로 실제 결함 원인의 방향성으로 단정하지 않습니다. 시점별 위치 주석 관측량이 달라 단순 밝기/시점 영상 수와 별도로 봐야 합니다. 일부 regulator/rolled_strip_base 그룹은 상위 10% 격자에 관측 결함질량이 집중됩니다. 그룹 그림의 known/positive 두 패널을 비교하고 각각의 분모를 확인합니다. 초기 면적 진단의 heatmaps_scaled와 빈도값을 직접 비교하지 않습니다. 촬영 정렬·물체 크기·주석 정책의 영향과 실제 결함 발생 특성을 분리해 검수해야 합니다. 관측 10장 미만 그룹에는 강한 GAN 위치 제약을 적용하지 않고, 관측되지 않은 위치를 정상으로 고정하지 않습니다.

## 6. Bounding Box 분석

| defect_type | yolo_id | coco_id |
| --- | --- | --- |
| AK | 0 | 1 |
| BX | 1 | 2 |
| CH | 2 | 3 |
| HS | 3 | 4 |
| PS | 4 | 5 |
| QS | 5 | 6 |
| YW | 6 | 7 |
| ZW | 7 | 8 |

객체탐지에는 정상 객체 클래스를 두지 않습니다. 별도 영상 분류의 OK=0/NG=1과 YOLO의 defect class0=AK를 혼동하지 않아야 합니다.

| defect_type | count | mean | median |
| --- | --- | --- | --- |
| AK | 7107 | 1925.31828 | 980.00000 |
| BX | 2649 | 16070.52171 | 7446.00000 |
| CH | 4232 | 19938.64225 | 5781.50000 |
| HS | 9266 | 9984.25610 | 5328.00000 |
| PS | 2192 | 5738.46943 | 3122.00000 |
| QS | 14019 | 7758.16977 | 4347.00000 |
| YW | 2215 | 1852.50158 | 658.00000 |
| ZW | 18949 | 3640.98222 | 1540.00000 |

[박스 근거](../outputs/spatial_20261111_v7/defect_bboxes.csv). 한 NG의 모든 연결 성분은 한 불량 유형이라는 가정입니다. 박스 개수는 8연결 성분 수이며 실제 독립된 물리 결함의 개수와 같다고 보장하지 않습니다.

원본 bbox area<1,024 px² 박스 16,297/60,629, 256 입력으로 단순 좌표 축소 시 짧은 변<2px가 되는 박스 1,525개입니다. 이는 기하학적 위험 지표이며 실제 결함 소실/검출 성능이 아닙니다. [박스 검증](../outputs/spatial_20261111_v7/bbox_validation_report.json).

박스 export 대상 124,162장, 오류 0, 제공된 빈 NG PNG 34개입니다. 이 NG들은 상태를 유지하며 기존 주석대로 박스 0개를 표현합니다. 제외 수 26,888은 미주석 NG 26,881 + 유형 충돌/위치 주석 NG 7입니다. [전체 COCO/YOLO 교차검증](../outputs/spatial_20261111_v7/detection_export_validation.json)에서 실제 라벨 파일·좌표·클래스·개수를 대조합니다.

![클래스 박스 수](../outputs/spatial_20261111_v7/bbox_class_distribution.png)

정상 OK 72,840장에는 빈 YOLO 라벨을 만들고, 마스크 없는 NG 26,881장과 위치 주석이 있어도 유형이 충돌하는 NG는 탐지 라벨에서 제외합니다. 클래스 불균형은 박스 수뿐 아니라 제품 수로도 확인해야 합니다.

## 7. 5시점 해상도별 정보 손실

전체 JPG 151,050장 × 해상도 3개, 453,150행. [이미지별 지표](../outputs/windows_preserved_20261111_v1/per_view_information_loss.csv).

| target | psnr_db | ssim | edge_recall | edge_f1 | gradient_retention | laplacian_retention | local_contrast_retention | rgb_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 256 | 35.63228 | 0.94366 | 0.17824 | 0.24346 | 0.39444 | 0.06647 | 0.60436 | 4.64259 |
| 512 | 40.98495 | 0.97599 | 0.47372 | 0.57014 | 0.62468 | 0.16569 | 0.76142 | 2.51457 |
| 1024 | 120.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 0.00000 |

전체 SSIM 평균은512 0.975989,256 0.943659로 높게 보이지만 동일 픽셀 Canny 경계 일치율은각각 0.473716/0.178240입니다. 국소 대비 보존은 0.761417→0.604359, RGB RMSE는 2.514565→4.642593 intensity였습니다. 전역 지표는 넓은 배경과 평탄 영역의 영향을 받고 경계 일치율은 위치 이동에도 민감하므로 이 숫자를 실제 결함 소실률/모델 recall로 해석하지 않습니다.

256에서 평균 SSIM이 낮은 품목(전체 JPG, 관측 통계):

| category | ssim | edge_recall | local_contrast_retention |
| --- | --- | --- | --- |
| toy_brick | 0.86011 | 0.02778 | 0.47661 |
| woodstick | 0.87108 | 0.19726 | 0.47512 |
| fire_hood | 0.88159 | 0.09160 | 0.40669 |
| sim_card_set | 0.90489 | 0.00600 | 0.45387 |
| usb_adaptor | 0.92101 | 0.16217 | 0.53688 |
| zipper | 0.92277 | 0.21127 | 0.59209 |

해상도별 SSIM/경계 일치/국소 대비 분포의5·50·95분위수:

| target | quantile | ssim | edge_recall | local_contrast_retention |
| --- | --- | --- | --- | --- |
| 256 | 0.05000 | 0.87866 | 0.00705 | 0.43653 |
| 256 | 0.50000 | 0.95002 | 0.16749 | 0.61399 |
| 256 | 0.95000 | 0.98281 | 0.39052 | 0.76327 |
| 512 | 0.05000 | 0.94968 | 0.11113 | 0.65309 |
| 512 | 0.50000 | 0.97959 | 0.49207 | 0.76914 |
| 512 | 0.95000 | 0.99372 | 0.77686 | 0.86929 |
| 1024 | 0.05000 | 1.00000 | 1.00000 | 1.00000 |
| 1024 | 0.50000 | 1.00000 | 1.00000 | 1.00000 |
| 1024 | 0.95000 | 1.00000 | 1.00000 | 1.00000 |

수치 검증 통과: 이미지 151,050, 해상도 지표 453,150행, 직접 단계 비교 151,050행. 전검정2장×3해상도의6행에서 참조 에너지/대비0에 따른 비율 결측을 유지했습니다. 이는 decode 실패6장이 아닙니다. [검증 근거](../outputs/windows_preserved_20261111_v1/resolution_scientific_validation.json).

| view | target | ssim | edge_recall | local_contrast_retention |
| --- | --- | --- | --- | --- |
| C1 | 256 | 0.93315 | 0.19334 | 0.58536 |
| C1 | 512 | 0.97209 | 0.50341 | 0.74892 |
| C2 | 256 | 0.94688 | 0.17618 | 0.61045 |
| C2 | 512 | 0.97726 | 0.46928 | 0.76592 |
| C3 | 256 | 0.94670 | 0.18124 | 0.60963 |
| C3 | 512 | 0.97718 | 0.47057 | 0.76407 |
| C4 | 256 | 0.94836 | 0.16805 | 0.61253 |
| C4 | 512 | 0.97773 | 0.46609 | 0.76730 |
| C5 | 256 | 0.94320 | 0.17240 | 0.60383 |
| C5 | 512 | 0.97568 | 0.45923 | 0.76087 |

![5시점](../outputs/windows_preserved_20261111_v1/five_view_loss.png)

같은 capture C1~C5를 비교합니다. 시점별 조명·배경·재질을 섞어 해상도 효과로 해석하지 않습니다.

![확대 비교](../outputs/windows_preserved_20261111_v1/detail_crop_comparison.png)

최대 국소 복원 차이 영역을 확대했습니다. 이 영역이 실제 결함인지는 마스크 overlay로 따로 확인해야 합니다. [검수 후보](../outputs/windows_preserved_20261111_v1/review_priority_images.csv).

직접 512→256 단계의 평균 SSIM/Edge recall: {'ssim': 0.964342, 'edge_recall': 0.529029}. [단계별 근거](../outputs/windows_preserved_20261111_v1/per_image_stepwise_changes.csv).

정사각 1024/512/256 area 축소, 원래 크기 linear 복원, 비정사각 원본은 정사각 변형 정책입니다. SSIM은 Gaussian 11×11 sigma 1.5, PSNR은 컬러 MSE(동일 영상 120dB 상한), 경계는 Canny 100/200의 동일 위치 교집합입니다. Laplacian은 고주파 대리 지표이며 주파수 스펙트럼 자체는 아닙니다. 결함 의미·모델 정확도·추론 속도는 측정하지 않았습니다.

별도 실제 결함 ROI 검수: 층화 마스크 336장의 원본 JPG를 512/256으로 비교했습니다. 전체 해상도 통계를 대체하지 않는 대표 사례 분석입니다. 마스크는 결함 위치 선택에만 사용했고 영상 손실은 JPG에서 계산했습니다. [ROI 결과](../outputs/defect_resolution_review_20261111_v7/defect_jpg_resolution_review.csv).

| target | roi_rgb_rmse | background_rgb_rmse | roi_edge_recall | roi_contrast_retention |
| --- | --- | --- | --- | --- |
| 256 | 12.33998 | 4.86995 | 0.14532 | 0.77665 |
| 512 | 6.36002 | 2.64824 | 0.42000 | 0.88604 |

![실제 결함 위치 확대](../outputs/defect_resolution_review_20261111_v7/defect_detail_crop_comparison.png)

같은 원본 좌표의 실제 주석 위치를 확대해 배경 영상 변화와 결함 영역의 변화를 구분합니다. button_battery/HS/C1의 가는 선형 흔적은 256 복원에서 더 퍼지고 주변 미세 질감도 흐려집니다. 512에서는 선형 흔적과 질감이 상대적으로 더 명확하게 보이지만 실제 검출 성공을 뜻하지 않습니다. ROI edge recall은 Canny 경계의 같은 픽셀 일치도이며 모델 recall이 아닙니다. ROI 전체 표준편차 비율은 전역의 11×11 국소 대비 지표와 정의가 다릅니다. ROI에는 물체 경계·금속 반사 등도 섞일 수 있어 큰 복원 오차를 결함 검출 난이도의 인과 효과로 단정하지 않습니다.

## 8. 분석 간 연관성

보존된 Windows 분할로 다시 계산한 정확 바이트 교차 분할 중복은 0개입니다. 전검정 두 파일은 모두 Train이며 권고 단일 영상 subset 151,048장/strict5-view 151,040장은 원본을 고치지 않는 검수 제안입니다. [기존 분할 품질 검증](../outputs/windows_preserved_20261111_v1/quality_review/quality_aware_split_validation.json). 초기 hash 분할에서의 교차 중복 수와 구분합니다.

기존 split의 presence-v2 위치 빈도 민감도:

| category | defect_type | view | raw_observations | reviewed_observations | raw_mean_occupancy | without_flagged_mean_occupancy | flagged_fraction_of_positive_mass | occupancy_units |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phone_battery | HS | C5 | 11 | 10 | 0.09504 | 0.00454 | 0.95656 | cell presence frequency |

이 표는 아래 초기 hash/area-v1 민감도와 분모·단위가 다릅니다.

전검정 JPG 2장은 서로 다른 품목/상태의 동일 바이트 파일입니다. 보존된 Windows 분할에서 둘 다Train이며 정확한 바이트 교차 분할 중복은 0그룹입니다. 초기 hash 탐색 분할에서는 Train/Test에 나뉘어1그룹이었으므로 두 분할의 결과를 구분합니다. 실제 모든 채널 min=max=0을 확인했고 NG 원래 PNG는 전영역255였습니다. 원본을 삭제/재분류하지 않고 [현재 분할의 모델 입력 검수 manifest](../outputs/windows_preserved_20261111_v1/quality_review/model_input_review_manifest.csv)에 보류 후보를 표시했습니다. 전체 분석은151,050장, 보류 후보를 제외한 권고 단일 영상 subset 151,048장, strict5-view 권고 151,040장입니다. 이는 의미 검수 전 자동 데이터 수정이나 학습 수행이 아닙니다.

위 presence-v2 민감도는 전체 흰 마스크 한 장이 특정 Train 위치 빈도를 지배할 수 있음을 보입니다. 초기에 계산한 hash/area-v1 민감도는 원래 outputs/full_20261111_v6/quality_review에 별도 보존했으며 분모·단위가 다릅니다. 관측 편향과 결함 원인을 분리해 검수해야 합니다.

## 9. 모델 실험을 위한 권고사항

원본 1024를 참조 기준으로 두고 512/256을 같은 제품 분할에서 비교합니다. 미세 결함의 위치 주석과 박스 크기가 확정되기 전 256을 최종 입력으로 고정하지 않습니다. Train 전용 밝기 통계로 증강 후보를 만들고 validation에서 선택합니다. 결함 유형별·시점별 macro 지표, NG recall 및 FPR을 함께 기록합니다. 5시점 제품 단위 분할과 제품 단위 집계를 유지하고, 이상탐지 AUROC/AUPRO·FPR 제한 recall과 탐지 클래스 AP/소형 결함 recall을 구분합니다. 초기 hash 분할은 탐색용이며 후속 재현은 확인된 기존 프로젝트 seed42 분할을 사용합니다. 프로젝트 분할과 논문 공식 benchmark 분할의 동등성은 별도 검증 대상입니다. 정상만 학습하는 AD는 split=train AND status=OK로 제한하고, 제품 NG와 시점별 가시 결함을 혼동하지 않도록 제품/시점 평가를 분리합니다. 이는 후속 실험 권고이며 성능 측정 결과가 아닙니다.

## 10. 한계 및 후속 과제

Windows 결과와 다른 지표 정의의 구분, serial 물리 identity, 미주석 NG의 의미, HS/QS 충돌 10장, 회색조 경계 의미, 이미지 내용 중복, 실제 결함 보존성을 확인해야 합니다. 팀원 4명의 개별 설치와 GitHub PR 실습은 미검증입니다. 마스크 미주석 NG를 정상 탐지 샘플로 자동 사용하지 않습니다.

## 추가 영역별 밝기 분석과 공유 산출물

[배경·제품 영역 밝기 상세 보고서](BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md)를 함께 읽습니다. 전체 이미지 밝기와 제품/배경/결함 국소 밝기를 구분하고 분할 불확실 사례는 결측으로 기록합니다. 최종 공유용 그림과 집계표는 ../images/manifest.json, 상세 PDF 생성은 scripts/export_detailed_pdf.py를 따릅니다. 미완료 상태에서 전체 결과를 추정하지 않습니다.

## 재현 및 환경

[실행 manifest](../outputs/windows_preserved_20261111_v1/run.json), [환경 이전 보고서](ENVIRONMENT_MIGRATION_REPORT.md), [분석 실행 로그](ANALYSIS_EXECUTION_LOG.md). 데이터 원본과 기존 출력은 보존했습니다. 사용자 추가 지시에 따라 최종 코드는 분석 브랜치로 공유합니다. 원본 데이터와 가중치는 공유 대상에서 제외합니다.

```bash
uv sync --locked
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked pytest -q
export REALIAD_DATA_ROOT="/실제/dataset"
uv run --locked python -m mv_analysis.cli validate-data
# 출력 폴더를 지정해 --resume brightness / resolution 단계 실행
# 복사 완료·preflight 이후 run-all --full --transfer-complete
```

## Windows 실제 결과 비교

[같은 방법 재실행 및 지표 정의 차이](WINDOWS_RESULT_COMPARISON.md)를 참조합니다. 원본 결과는 수정하지 않았습니다.