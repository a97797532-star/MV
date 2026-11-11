# 분석 간 관계와 결함 해상도 위험

모든 결과는 관측 자료의 기술 분석이다. 전체 영상 SSIM과 밝기/박스 크기의 관계는 결함 검출 성능이나 인과 효과가 아니다.

## 작은 결함과 해상도

| target | boxes | short_side_under2 | scaled_area_under16 |
| --- | --- | --- | --- |
| 256 | 60629 | 1525 | 5025 |
| 512 | 60629 | 38 | 816 |

원본1024 박스 좌표를512/256으로 선형 스케일한 기하학적 위험이다. 2픽셀 미만의 짧은 변은 미세 결함 검수 우선순위이며 실제 결함 소실 비율이 아니다. 연결 성분 bbox는 독립 물리 결함의 개수와 다를 수 있다.

## 품목·시점·상태를 고정한 상관

| category | view | status | feature | metric | available_pairs | group_images | spearman_rho |
| --- | --- | --- | --- | --- | --- | --- | --- |
| eraser | C2 | OK | background_mean | ssim | 439 | 492 | -0.93250 |
| transistor1 | C4 | NG | background_mean | ssim | 471 | 503 | 0.91679 |
| transistor1 | C4 | OK | background_mean | ssim | 283 | 497 | 0.91528 |
| vcpill | C5 | OK | product_mean | ssim | 482 | 504 | -0.90746 |
| phone_battery | C2 | NG | whole_mean | ssim | 517 | 517 | -0.90537 |
| eraser | C4 | OK | background_mean | ssim | 372 | 492 | -0.90095 |
| phone_battery | C5 | NG | whole_mean | edge_recall | 517 | 517 | 0.89286 |
| toy | C1 | OK | whole_mean | edge_recall | 499 | 499 | 0.87825 |
| plastic_plug | C5 | OK | background_mean | ssim | 240 | 485 | -0.87603 |
| bottle_cap | C3 | OK | product_mean | ssim | 492 | 492 | -0.87227 |
| bottle_cap | C3 | OK | whole_mean | ssim | 492 | 492 | -0.87143 |
| plastic_plug | C3 | NG | whole_mean | ssim | 514 | 514 | -0.86785 |
| bottle_cap | C4 | OK | whole_mean | ssim | 492 | 492 | -0.86242 |
| transistor1 | C4 | OK | product_pixel_ratio | ssim | 283 | 497 | -0.86191 |
| phone_battery | C4 | NG | whole_mean | edge_recall | 517 | 517 | 0.86104 |
| plastic_plug | C5 | NG | whole_mean | ssim | 514 | 514 | -0.85199 |
| bottle_cap | C4 | OK | product_mean | ssim | 492 | 492 | -0.84941 |
| phone_battery | C1 | NG | whole_mean | edge_recall | 517 | 517 | 0.84612 |
| phone_battery | C2 | NG | whole_mean | edge_recall | 517 | 517 | 0.84492 |
| transistor1 | C4 | NG | product_mean | ssim | 471 | 503 | -0.84326 |

단순 전체 상관은 배경/품목 구성에 좌우되므로 품목×시점×OK/NG 내부에서 Spearman rank 상관을 계산했다. 최소10개 유효 쌍, 표에는30개 이상만 보인다. 분산0/관측부족은 결측이다. 다중 비교의 탐색 결과이며 유의성 검정/원인 판정으로 사용하지 않는다. product/background 관련 쌍은 자동 품질 통과 subset이라 선택 편향이 남는다. min bbox 관련 쌍은 제공 마스크의 유효 탐지 라벨이 있는 NG 부분집합이다.

## 실제 결함 ROI와 전역 영상 변화

| target | roi_rgb_rmse | rgb_rmse | roi_minus_whole_rgb_rmse | roi_edge_recall | edge_recall |
| --- | --- | --- | --- | --- | --- |
| 256 | 12.33998 | 4.90918 | 7.42666 | 0.14532 | 0.18161 |
| 512 | 6.36002 | 2.66741 | 3.69023 | 0.42000 | 0.47686 |

동일336장·동일 해상도에서 전역 JPG 복원 오차와 마스크 위치 JPG 복원 오차를 짝지어 비교했다. ROI가 빈 마스크면 ROI 통계는 결측이며 전체 계산을 대체하지 않는다. 그림의 대각선 위는 ROI 복원 오차가 전체 평균보다 크다는 뜻이다. Canny ROI recall과 전역 recall은 영상 경계 일치도이며 모델 recall이 아니다.

![분석 간 관계](../outputs/cross_analysis_20261111_v1/cross_analysis_associations.png)

그림 왼쪽은 배경별 기술 산점도로 가독성을 위해 최대 약3,000장/배경으로 간격 표본화했다. 숫자 상관은 전체 유효 행에서 계산했다. 가운데는 품목별 짧은 변 위험, 오른쪽은 동일 ROI/전역 오차다.

## 계산 근거

[기하학적 위험](../outputs/cross_analysis_20261111_v1/small_defect_resolution_risk.csv), [전체 그룹 상관](../outputs/cross_analysis_20261111_v1/within_group_associations.csv), [ROI 짝 비교](../outputs/cross_analysis_20261111_v1/defect_roi_vs_whole_image_loss.csv). 재현: scripts/analyze_cross_relations.py.