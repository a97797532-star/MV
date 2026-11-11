# 배경을 고려한 Real-IAD 밝기 재검증

갱신 UTC 2026-11-11T09:29:55.824021+00:00. 전체 실행 완료. 전체 체크포인트 151,050/151,050.

## 1. 목적과 기존 방식의 한계

기존 mv_analysis/stages.py brightness는 OpenCV BGR→GRAY 0–255의 전체 픽셀 평균을 계산한다. mv_analysis/brightness.py는 없었다. 전체 밝기는 제품·촬영 배경·제품 면적 비율이 섞인 지표다. 기존 결함 상대 밝기의 마스크 밖 전체 픽셀은 제품의 정상 표면과 배경을 모두 포함한다. 결함 PNG는 제품 전체 마스크로 사용하지 않았다.

## 2. 입력과 범위

확정 전체 JPG 151,050(OK 72,840 / NG 78,210), 제공 PNG 51,329. 기존 분할을 보존한 `outputs/windows_preserved_20261111_v1`를 사용한다. 이번 보고서 실제 측정 151,050장, 30품목·C1~C5·정상/불량 포함. [실행 설정](../outputs/background_full_20261111_v1/regional_run.json). 기존 결과/원본은 수정하지 않았다.

## 3. 배경 분포

| background_type | images | median_confidence |
| --- | --- | --- |
| BLACK | 90771 | 0.9855 |
| GRAY | 11226 | 0.7638 |
| MIXED | 10 | 0.3571 |
| UNKNOWN | 9 | 0.0000 |
| WHITE | 49034 | 1.0000 |

[전체 분류](../outputs/background_full_20261111_v1/background_classification.csv), [품목별 분포](../outputs/background_full_20261111_v1/background_distribution.csv). 분류는 경계 4% 띠의 색/연결성으로 판단하며 전체 평균으로 결정하지 않는다. WHITE/BLACK은 경계 밝기 및 HSV V/OpenCV Lab L의 기술적 구간, GRAY는 중간 명도(유채색 포함)이다. MIXED는 경계 명도 변화, UNKNOWN은 지지 부족/분할 실패다. confidence는 휴리스틱 지지 점수이며 확률 정확도가 아니다. Lab L은 OpenCV uint8 0–255 표현이다.

## 4. 분리 방법과 선택 근거

A: 경계 Lab 색의 robust 대표값 또는 경계의 2차 공간 조명 모델 → 경계 연결 배경 및 유사색 내부 구멍 → 작은 성분 정리. 색상 거리 임계값은 경계 residual median/MAD로 영상마다 추정하므로 흰/검은 배경에 하나의 고정 이진 임계값을 적용하지 않는다. B: 같은 색상 seed로 2회 GrabCut. C: 색상 seed와 watershed 경계. Canny로 제품 후보 밖 경계를 추가 점검한다. 공통 seed의 편향이 있으므로 세 방법의 일치도도 정답 정확도가 아니다. 제품/배경이 유사하거나 그림자/반사가 제품 후보로 섞이면 제외한다. 분할은 긴 변256에서 수행해 native로 nearest 복원하므로 1024 원본의 약4픽셀 경계 정밀도 한계가 있다.

## 5. 성공·실패·불확실

| state | images |
| --- | --- |
| accepted_heuristic | 78526 |
| uncertain | 72517 |
| failed | 7 |

| category | accepted_heuristic | failed | uncertain | total | accepted_fraction |
| --- | --- | --- | --- | --- | --- |
| phone_battery | 416 | 1 | 4583 | 5000 | 0.0832 |
| plastic_plug | 1771 | 0 | 3224 | 4995 | 0.3546 |
| sim_card_set | 0 | 0 | 5030 | 5030 | 0.0000 |
| toothbrush | 0 | 0 | 5005 | 5005 | 0.0000 |
| toy | 4023 | 0 | 1002 | 5025 | 0.8006 |

accepted_heuristic는 자동 품질 필터 통과이며 수작업 정답 검증 성공과 다르다. 불확실/실패의 product_mean 결측 여부: True. [품질](../outputs/background_full_20261111_v1/foreground_segmentation_metrics.csv), [제외 사례](../outputs/background_full_20261111_v1/foreground_segmentation_failures.csv). 모든 300장에 세 방법을 계산했지만 시각 검수는 표시한 30개 대표 사례 중심이며 모든 픽셀의 의미를 검수한 것이 아니다. 그림자, 반사, 잘린 물체, 제품 내부 어두운 재질과 관통 구멍의 구분은 여전히 불확실하다.

![방법별 검수](../outputs/background_sample_20261111_v5/foreground_segmentation_examples.png)

빨간 윤곽/녹색 채색은 추정 전경이다. 나머지 품목은 같은 폴더의 examples_02~06을 확인한다. 첫 시도의 plastic_nut 그림자와 toy의 배경 돌출을 방법 간 일치만으로 허용할 수 없음을 확인해 보수적인 색 유사/경계/0.95 일치 조건을 추가했다. phone_battery의 파란 배경 기울기는 2차 조명 모델로 일부 개선되지만 남은 halo/문자 구멍 문제는 검수 대상이다.

## 6. 전체 밝기와 제품 밝기

![영역별 분포와 동일 표본 비교](../outputs/background_full_20261111_v1/regional_brightness_overview.png)

자동 품질 통과 subset의 제품 밝기 분포와 같은 영상의 전체/제품 차이를 함께 확인한다. 제외율과 배경 유형을 보지 않고 전체 NG로 일반화하지 않는다.

기존 전체 밝기 재계산 151,050장, 최대 절대 차이 0 intensity. [재현 대조](../outputs/background_full_20261111_v1/whole_brightness_reproduction.csv). 배경/제품 평균·분산·P05/P50/P95·P95−P05 대비·비율은 [영역별 결과](../outputs/background_full_20261111_v1/regional_brightness_per_image.csv)에 있다. 암부≤5, 하이라이트≥250은 카메라 노출 실패의 판정이 아닌 명도 proxy다.

| status | whole_mean_count | whole_mean_mean | whole_mean_std | product_mean_count | product_mean_mean | product_mean_std | background_mean_count | background_mean_mean | background_mean_std | product_pixel_ratio_count | product_pixel_ratio_mean | product_pixel_ratio_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NG | 41025 | 84.2010 | 62.9476 | 41025 | 125.2053 | 41.6390 | 41025 | 68.9427 | 108.6583 | 41025 | 0.3357 | 0.0860 |
| OK | 37501 | 85.6610 | 64.8204 | 37501 | 121.5604 | 42.1224 | 37501 | 73.4240 | 111.0250 | 37501 | 0.3359 | 0.0881 |

## 7. 정상·불량 차이 변화

| category | defect_type | view | n_ok_product | n_ng_product | whole_all_difference | whole_paired_difference | product_difference | absolute_difference_reduction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plastic_plug | QS | C2 | 152 | 35 | -3.5111 | -5.6235 | -0.1711 | 5.4524 |
| plastic_plug | HS | C2 | 152 | 44 | -3.2669 | -4.5441 | 1.0102 | 3.5339 |
| plastic_plug | HS | C5 | 240 | 39 | 2.4297 | 4.8115 | 1.8073 | 3.0042 |
| toy_brick | HS | C3 | 392 | 112 | 4.3822 | 3.8575 | 0.8632 | 2.9944 |
| plastic_plug | ZW | C3 | 24 | 3 | -2.1427 | 3.1362 | -0.1594 | 2.9768 |
| wooden_beads | QS | C4 | 435 | 126 | -3.0531 | -3.0531 | 0.4767 | 2.5764 |
| wooden_beads | AK | C4 | 435 | 128 | -3.6973 | -3.6973 | -1.2078 | 2.4895 |
| button_battery | CH | C5 | 40 | 34 | -2.7733 | -3.7224 | -1.6140 | 2.1084 |
| wooden_beads | HS | C4 | 435 | 139 | -2.6933 | -2.6933 | 0.8535 | 1.8398 |
| plastic_plug | QS | C5 | 240 | 28 | 0.3246 | 3.5616 | 1.7418 | 1.8198 |
| button_battery | ZW | C5 | 40 | 12 | -2.3436 | -2.4859 | -0.6910 | 1.7949 |
| toy_brick | HS | C2 | 257 | 82 | 2.5523 | 2.4518 | 1.0044 | 1.4474 |

[전후 비교](../outputs/background_full_20261111_v1/brightness_before_after_comparison.csv). whole_all은 전체 대상, whole_paired/product는 동일한 품질 통과 영상만 비교한다. paired 전체 차이와 제품 차이를 비교해야 제외 효과와 배경 효과를 혼동하지 않는다. 감소는 배경 편향의 후보 근거이며 분할 오차/선택 편향이 남으므로 인과 효과로 단정하지 않는다. 충분한 비교의 감소/유지 건수는 `{'difference_persisted_or_increased': 259, 'difference_decreased': 67}`이다.

동일 영상에서의 d와 분포 겹침 비교:

| category | defect_type | view | whole_paired_cohens_d | product_cohens_d | whole_paired_overlap | product_overlap |
| --- | --- | --- | --- | --- | --- | --- |
| plastic_plug | QS | C2 | -2.2706 | -0.1053 | 0.3882 | 0.8977 |
| plastic_plug | HS | C2 | -1.8622 | 0.6108 | 0.3882 | 0.8146 |
| plastic_plug | HS | C5 | 0.6695 | 0.7900 | 0.9125 | 0.6929 |
| toy_brick | HS | C3 | 0.7522 | 0.0760 | 0.7615 | 0.8801 |
| plastic_plug | ZW | C3 | 0.4753 | -0.0530 | 0.7917 | 0.9583 |
| wooden_beads | QS | C4 | -1.3146 | 0.0787 | 0.6652 | 0.9318 |
| wooden_beads | AK | C4 | -1.6384 | -0.2073 | 0.5933 | 0.8978 |
| button_battery | CH | C5 | -2.0446 | -0.4749 | 0.2750 | 0.8162 |
| wooden_beads | HS | C4 | -1.1663 | 0.1443 | 0.7599 | 0.9115 |
| plastic_plug | QS | C5 | 0.4853 | 0.7558 | 0.9125 | 0.6655 |
| button_battery | ZW | C5 | -1.1742 | -0.1872 | 0.5250 | 0.7917 |
| toy_brick | HS | C2 | 0.5346 | 0.1008 | 0.8130 | 0.9155 |

유효 paired 비교 326/560개, 관측 부족 234개, 부호 변화 64개입니다. [해석 변화와 선택 효과 분해](../outputs/background_full_20261111_v1/brightness_interpretation_changes.csv)에서 product−whole_all 차이를 선택에 따른 whole_paired−whole_all과 영역에 따른 product−whole_paired로 구분합니다. 기술적 항등 분해이며 배경 제거의 인과 효과가 아닙니다.

## 8. 품목·시점·배경별 해석

[배경 유형을 맞춘 비교](../outputs/background_full_20261111_v1/background_stratified_comparison.csv), [품목/시점](../outputs/background_full_20261111_v1/category_view_regional_comparison.csv). 기존 최신 Windows 555조합과 새 560조합(UNRESOLVED 5개 추가)을 구분한다. 표본은 모든 결함 조합을 포함하지 않으므로 표본의 560개를 전체 560개의 재검증 완료로 표현하지 않는다. 우선 검토 5품목에서 유효 OK/NG가 각각 2장 미만인 조합은 차이/d/겹침을 결측 처리한다. 배경 영향이 있다는 이유만으로 NG 라벨 또는 데이터 분할을 변경하지 않는다.

## 9. 결함과 제품 내부 국소 주변

유효 추정 국소 대비 22,411장. 전체 NG 중 마스크가 있고 제공된 결함 영역의 90% 이상이 추정 제품 내부이며, 제품 내부 annulus가 20픽셀 이상인 경우만 계산한다. 반경은 1024에서12픽셀, 제품 경계1픽셀 erosion으로 배경 혼입을 줄인다. 결함 자체 밝기는 유효 PNG에 대해 별도로 기록하되 제품 불확실이면 국소 차이는 결측이다. [국소 대비](../outputs/background_full_20261111_v1/defect_local_contrast.csv). 이웃 결함까지 제외하기 위해 전체 결함 마스크를 annulus에서 뺀다. 가까운 정상 재질의 진짜 정답이라고 보장하지 않는다.

| category | count | mean | std | median |
| --- | --- | --- | --- | --- |
| audiojack | 357 | 34.7480 | 36.9752 | 26.8986 |
| bottle_cap | 1341 | -12.6252 | 39.9783 | -8.4872 |
| button_battery | 1282 | 39.8438 | 39.9581 | 32.8378 |
| end_cap | 1928 | 14.4825 | 22.7381 | 9.7108 |
| eraser | 1076 | -4.6615 | 27.1900 | 3.3645 |
| fire_hood | 1101 | -15.1070 | 22.3696 | -9.5531 |
| mint | 1689 | -23.3093 | 21.4383 | -20.3536 |
| mounts | 959 | -20.1566 | 40.3756 | -1.7194 |
| phone_battery | 47 | 10.6811 | 19.7486 | 6.6294 |
| plastic_nut | 723 | 4.2515 | 31.8440 | -5.5986 |
| plastic_plug | 389 | 2.3388 | 19.9195 | -1.2012 |
| porcelain_doll | 185 | -16.7881 | 19.9630 | -16.1321 |
| regulator | 465 | -6.2824 | 37.2148 | 6.0698 |
| rolled_strip_base | 2250 | -21.4913 | 41.7479 | 1.5843 |
| switch | 797 | 6.7335 | 34.2695 | -5.9069 |
| terminalblock | 1692 | -10.6170 | 31.2645 | -0.5428 |
| toy | 1274 | -17.2212 | 20.2805 | -15.6817 |
| toy_brick | 1060 | -17.7435 | 34.0736 | -19.4362 |
| transistor1 | 855 | 18.9021 | 29.9917 | 10.6202 |
| usb | 147 | 14.6090 | 27.2946 | 12.5091 |
| vcpill | 1257 | -9.9209 | 31.2702 | -0.2749 |
| wooden_beads | 1531 | -21.3338 | 34.1598 | -10.1623 |
| woodstick | 6 | 18.3977 | 19.1390 | 23.8185 |

## 10. 편향과 제외의 영향

| segmentation_status | status | count | mean | std | median |
| --- | --- | --- | --- | --- | --- |
| accepted_heuristic | NG | 41025 | 84.2010 | 62.9476 | 61.5562 |
| accepted_heuristic | OK | 37501 | 85.6610 | 64.8204 | 59.2023 |
| failed | NG | 1 | 0.0000 | nan | 0.0000 |
| failed | OK | 6 | 3.9798 | 9.7405 | 0.0042 |
| uncertain | NG | 37184 | 112.3077 | 79.9278 | 87.2632 |
| uncertain | OK | 35333 | 111.3954 | 78.2354 | 95.8296 |

품질 통과율과 OK/NG 비율이 다르면 제품 밝기 통계 자체도 선택 편향을 갖는다. [품목별 선택률](../outputs/background_full_20261111_v1/segmentation_selection_by_category.csv), [더 엄격한 0.98 일치 민감도](../outputs/background_full_20261111_v1/strict_selection_sensitivity_comparison.csv). 제외된 영상을 통과 영상 평균으로 대체하지 않았다. 실패·불확실의 전체 밝기는 유지했다. 그림자가 제품으로 들어가는 공통 오차는 숫자만으로 제거되지 않는다.

## 11. 증강 후보와 시각 검증

[Train 제품 분위수](../outputs/background_full_20261111_v1/train_product_augmentation_candidates.csv), [정상 Train만의 AD 후보](../outputs/background_full_20261111_v1/train_normal_only_augmentation_candidates.csv). 정책 계산은 원래 split=train 중 품질 통과 영상만 사용한다. 배경 타입으로 전체 영상을 일괄 밝게/어둡게 하지 않는다. 제품 내부 gain 후보는 그룹 밝기 변동에서 2~10%로 제한하고 경계를 안쪽으로 부드럽게 처리하며 배경 픽셀은 유지한다. 정상/불량, 흰/검은 배경의 실제 Train 사례로 비교했다. [후보별 국소/제품-배경 대비](../outputs/background_full_20261111_v1/augmentation_visual_checks.csv). 대비 비율 0.85~1.15는 검수용 조건이며 모델 최적 정책이 아니다. 국소 대비 미정의는 보존 검증 완료로 보지 않는다. Validation/Test 원본을 바꾸지 않았다.

![증강 후보](../outputs/background_full_20261111_v1/augmentation_review.png)

원본·약한 음/양 gain을 비교한다. 배경·국소 대비 검수를 통과하지 못한 후보는 보류한다. 모델 학습/성능 측정은 수행하지 않았다.

## 12. 파이프라인 반영

기존 전체 밝기는 조명/촬영 편향 진단으로 보존하고 product_mean을 별도 필드로 추가한다. has_mask=False NG도 전부 포함한다. 자동 전경은 GT로 재사용하지 않고 segmentation_status와 algorithm/version/hash를 함께 저장한다. 체크포인트의 성공 이미지별 기록과 배치 오류 로그를 이용해 재개한다. 원본 검증 당시 bytes/mtime이 바뀌면 해당 영상은 오류로 중단한다.

## 13. 한계 및 회의 의사결정

사람이 그린 제품 정답이 없으므로 GT 기반 IoU/Dice를 계산하지 않았다. method_A_B/C_agreement는 자동 후보끼리의 교집합/합집합 비율이다. 권고 의사결정: 우선 5품목에서 그림자·구멍·반사·잘림을 포함한 수작업 제품 마스크 표본을 확보하고, 현재 제외율/배경별 성능을 점검한 뒤 제품 통계를 학습 전처리에 적용한다. 제품 영역에서 관통 구멍과 검은 재질을 구별하려면 추가 의미 정보가 필요하다. 본 표본을 검수해 정한 휴리스틱의 평가는 독립 검수 표본에서 다시 해야 한다. 관측 분포나 제품 대비 변화는 모델 성능 개선의 검증이 아니다.

병렬 재현성: 동일한 실제 층화 표본300장의107개 필드는 worker1/4에서 결측을 포함해 정확히 일치했습니다. [실제 검증](REGIONAL_PARALLEL_REPRODUCIBILITY.json). 이는 이 환경의 표본 검증이며 다른 팀원4명 설치/모든 하드웨어의 bit 동일성을 확인한 것은 아닙니다.

## 14. 재현

산출물 `outputs/background_full_20261111_v1`. 표본 검수 `outputs/background_sample_20261111_v5`. 전체 실행 `outputs/background_full_20261111_v1`. [검증 JSON](../outputs/background_full_20261111_v1/regional_validation.json).

```bash
uv run --locked python -m mv_analysis.cli --output outputs/new_bg_sample regional-brightness --source-run outputs/windows_preserved_20261111_v1 --sample --compare-methods
# 실제 오버레이 검수 후 동일 버전의 validation-evidence를 지정한다.
uv run --locked python -m mv_analysis.cli --output outputs/new_bg_full regional-brightness --source-run outputs/windows_preserved_20261111_v1 --full --compare-methods --validation-evidence reports/BACKGROUND_SEGMENTATION_REVIEW.json --batch-size 2000 --workers 2
# 같은 옵션에 전역 --resume을 추가해 반복하고 마지막 배치에 --finalize를 지정한다.
```