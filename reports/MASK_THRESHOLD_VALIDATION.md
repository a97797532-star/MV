# 마스크 임계값 검증

갱신 UTC: 2026-11-11T09:29:56.378710+00:00. 원본 PNG는 수정하지 않았다.

0/32/64/127/192/254에 대해 foreground = pixel > threshold를 비교한다. 127은 민감도 비교 기준이며 최종 threshold로 확정한 값이 아니다. grayscale 자체는 손상을 의미하지 않는다. 표본은 품목×불량유형에서 정렬된 처음/중간/마지막 3장을 선택하며 전체 C1~C5를 포함한다. 경계 보존과 작은 성분은 원본 overlay로 검수한다.

실제 선택 336장, 성공 336, 오류 0, 30품목, 9유형. 픽셀 값 종류 256개. [검증 JSON](../outputs/mask_study_20261111_v4/mask_threshold_validation/validation.json), [이미지별 민감도](../outputs/mask_study_20261111_v4/mask_threshold_validation/threshold_per_mask.csv).

| threshold | images | foreground_pixels | components | tiny_components_le4 | bbox_area_sum | median_area_ratio | median_iou_to_127 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 336 | 936019 | 387 | 0 | 2406884 | 1.12316 | 0.89053 |
| 32 | 336 | 909606 | 388 | 0 | 2373444 | 1.07269 | 0.93228 |
| 64 | 336 | 895271 | 389 | 0 | 2353366 | 1.04328 | 0.95901 |
| 127 | 336 | 873105 | 403 | 11 | 2318091 | 1.00000 | 1.00000 |
| 192 | 336 | 849964 | 401 | 11 | 2279863 | 0.95646 | 0.95658 |
| 254 | 336 | 812094 | 444 | 46 | 2192650 | 0.88308 | 0.88329 |

![임계값 민감도](../outputs/mask_study_20261111_v4/mask_threshold_validation/threshold_sensitivity.png)

낮은 threshold에서 경계/저강도 성분을 더 포함하고 높은 threshold에서 core를 남긴다. 성분 수 감소만으로 제거한 성분을 노이즈로 단정할 수 없다. 255 core 보존율은 모든 threshold<255에서 항상 1이므로 결함 보존 증거로 사용할 수 없다.

실제 JPG/PNG crop overlay 30개. [검수 폴더](../outputs/mask_study_20261111_v4/mask_threshold_validation).

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0000_audiojack_BX.png)

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0012_bottle_cap_AK.png)

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0024_button_battery_AK.png)

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0036_end_cap_HS.png)

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0048_eraser_AK.png)

![임계값별 경계](../outputs/mask_study_20261111_v4/mask_threshold_validation/overlay_0060_fire_hood_AK.png)

## 실제 관측 해석

336장 표본에서 >0은 936,019픽셀·387성분·4픽셀 이하 성분 0개, >127은 873,105픽셀·403성분·작은 성분 11개, >254는 812,094픽셀·444성분·작은 성분 46개였습니다. 높은 임계값의 작은 성분 증가가 기존 결함 영역의 분절일 수 있어 작은 성분=노이즈라고 판단하지 않습니다. audiojack/BX C1 overlay는 변형된 금속 부위와 주석 위치가 대체로 일치했고, end_cap/HS C1의 가는 scratch는 threshold 증가에 따라 1,431→858픽셀로 줄었습니다. fire_hood/AK C1도 pit 주위 contour가 점차 안쪽으로 수축했습니다. 이 세 사례의 시각 검수는 모든 표본/전체 주석의 의미적 정확도를 보장하지 않습니다.

## 추가 근거와 최종 분석 정책

전체 제공 마스크의 무결성 통과 후, 본 프로젝트 위치 분석은 grayscale >0을 채택했습니다. [Real-IAD 공식 EvalPerPixelAUC 구현](https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249)은 양의 마스크 값을 1로 처리합니다. 표본 overlay의 경계 보존과 임계값 증가에 따른 수축/분절 관측을 함께 근거로 사용했습니다. 이는 모든 주석 경계의 의미적 정답을 입증하는 것은 아닙니다. 작은 성분 면적 필터는 적용하지 않습니다. 초기 정책 보류는 공식 구현 및 전체 무결성 검증을 추가 확인한 뒤 이 판정으로 갱신했습니다. [실행 정책 JSON](../outputs/spatial_20261111_v7/mask_policy.json).

전체 마스크 픽셀 53,822,357,504, 값 0 53,638,078,165, 값 255 162,966,915, 중간값 1–254 21,312,424개. 중간값은 전체 픽셀의 0.039598%이며 경계 의미를 추가 검수해야 합니다.

전체 51,329개 제공 마스크의 픽셀 히스토그램에서 계산한 임계값별 총 면적(연결 성분 수는 336장 표본 결과와 구분):

| threshold | foreground_pixels | fraction_all_mask_pixels | ratio_to_127 |
| --- | --- | --- | --- |
| 0 | 184279339 | 0.00342 | 1.06233 |
| 32 | 179805191 | 0.00334 | 1.03654 |
| 64 | 177341677 | 0.00329 | 1.02234 |
| 127 | 173467175 | 0.00322 | 1.00000 |
| 192 | 169499394 | 0.00315 | 0.97713 |
| 254 | 162966915 | 0.00303 | 0.93947 |

전체 PNG 무결성 검사: 대상 51,329, 성공 51,329, 오류 0. [실행 근거](../outputs/mask_integrity_20261111_v6/execution.json).