# Real-IAD 전체 해상도 정보 손실 상세 분석

작성 시각: 2026-11-11T11:05:03.869000+00:00. 기존 산출물 재집계만 수행했다. 전체 해상도 계산·모델 학습·Push는 수행하지 않았다.

## 1. 회의용 핵심 결론

전체 151,050장, 30품목, C1~C5, OK 72,840장·NG 78,210장을 해상도별 동일 가중치로 비교했다. 각 해상도 151,050행, 합계 453,150행과 단계별 151,050행의 유일성과 기존 검증을 확인했다.

| target | psnr_db | ssim | edge_recall | edge_f1 | local_contrast_retention | high_frequency_proxy_retention | rgb_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 256 | 35.632282 | 0.943659 | 0.178240 | 0.243461 | 0.604359 | 0.066472 | 4.642593 |
| 512 | 40.984954 | 0.975989 | 0.473716 | 0.570144 | 0.761417 | 0.165695 | 2.514565 |
| 1024 | 120.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |

1024는 자기 자신과 비교하는 기준점이다. PSNR 120 dB는 무손실 비교의 저장 상한이며 카메라의 실측 품질이 아니다. 512와 256의 낮아진 SSIM·경계 일치는 복원 영상 변화이며 결함 검출 정확도의 감소량이 아니다.

## 2. 범위·분모·재현 정책

원본 계산 CSV: `outputs/windows_preserved_20261111_v1/per_view_information_loss.csv`. 전체 NG를 포함하고 마스크 없는 NG를 제거하지 않았다. 제공 마스크 51,329장과 NG 78,210장은 다른 분모다. 마스크 미제공 NG 26,881장을 정상으로 바꾸거나 빈 마스크를 만들지 않았다.

영상마다 하나의 관측값으로 집계한다. 전체 평균은 영상 가중치이며 품목 균등 평균이 아니다. 동일 제품의 5시점은 상호 독립 표본이 아니므로 본 보고서는 통계적 유의성·인과관계를 주장하지 않는다.

## 3. 지표 정의와 해석

INTER_AREA로 1024→512/256 축소 후 INTER_LINEAR로 원본 1024 좌표에 복원했다. 전체 원본은 1024×1024이므로 이번 입력에 비정사각형 변형 사례는 없다.

PSNR은 전체 BGR 채널 MSE와 255 범위 기준이다. RGB 채널 순서 변경은 채널 전체 MSE를 바꾸지 않는다. SSIM은 그레이스케일 Gaussian 11×11, sigma 1.5, data range 255다. Edge Recall/F1은 Canny 100/200의 같은 픽셀 위치 일치이며 미세한 경계 이동에도 민감하다.

국소 대비 보존율은 11×11 국소 표준편차 평균의 복원/원본 비율이다. 고주파 보존 대리값은 Laplacian 제곱 에너지 비율이며 FFT 대역별 에너지의 직접 측정이 아니다. 1−비율을 대리 손실로 읽을 수 있으나 의미 있는 결함 정보의 손실률로 해석할 수 없다. 비율의 분모가 0인 두 검은 이미지의 3해상도 결과 6행은 결측으로 유지했다.

## 4. 전체 분포·중앙값·분위수·극단값

[전체 통계 CSV](../outputs/resolution_detail_20261111_v2/overall_statistics.csv)는 n/유효 n/결측/평균/표준편차/최소/P01/P05/P25/중앙값/P75/P95/P99/최대를 제공한다. 세 해상도와 모든 지표를 포함한다.

| target | metric | valid | mean | median | p05 | p95 | minimum | maximum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 256 | psnr_db | 151050 | 35.632282 | 35.969790 | 28.861206 | 40.818698 | 23.895433 | 120.000000 |
| 256 | ssim | 151050 | 0.943659 | 0.950022 | 0.878658 | 0.982811 | 0.727626 | 1.000000 |
| 256 | edge_recall | 151050 | 0.178240 | 0.167492 | 0.007054 | 0.390520 | 0.000000 | 1.000000 |
| 256 | edge_f1 | 151050 | 0.243461 | 0.244233 | 0.013902 | 0.479196 | 0.000000 | 1.000000 |
| 256 | local_contrast_retention | 151048 | 0.604359 | 0.613989 | 0.436527 | 0.763272 | 0.040885 | 0.856640 |
| 256 | high_frequency_proxy_retention | 151048 | 0.066472 | 0.060404 | 0.022240 | 0.132786 | 0.011380 | 0.277502 |
| 256 | rgb_rmse | 151050 | 4.642593 | 4.055558 | 2.320627 | 9.193479 | 0.000000 | 16.284278 |
| 512 | psnr_db | 151050 | 40.984954 | 41.285207 | 34.106223 | 46.553836 | 29.485421 | 120.000000 |
| 512 | ssim | 151050 | 0.975989 | 0.979586 | 0.949680 | 0.993725 | 0.887091 | 1.000000 |
| 512 | edge_recall | 151050 | 0.473716 | 0.492072 | 0.111134 | 0.776860 | 0.000000 | 1.000000 |
| 512 | edge_f1 | 151050 | 0.570144 | 0.594474 | 0.194022 | 0.826301 | 0.000000 | 1.000000 |
| 512 | local_contrast_retention | 151048 | 0.761417 | 0.769144 | 0.653085 | 0.869291 | 0.574961 | 0.925811 |
| 512 | high_frequency_proxy_retention | 151048 | 0.165695 | 0.157844 | 0.094950 | 0.257361 | 0.058698 | 0.413626 |
| 512 | rgb_rmse | 151050 | 2.514565 | 2.199276 | 1.199081 | 5.026076 | 0.000000 | 8.555968 |

## 5. 품목별·C1~C5별·OK/NG별 비교

아래 품목 순위는 256의 평균 SSIM이 낮은 순이다. 품목별 질감·형상·배경 복잡도를 반영하며 모델 난이도 순위로 확정할 수 없다.

| category | images | mean | median | p05 | p95 |
| --- | --- | --- | --- | --- | --- |
| toy_brick | 5010 | 0.860115 | 0.875057 | 0.760578 | 0.907058 |
| woodstick | 5005 | 0.871078 | 0.877800 | 0.799630 | 0.917123 |
| fire_hood | 5025 | 0.881590 | 0.893752 | 0.793637 | 0.917400 |
| sim_card_set | 5030 | 0.904895 | 0.909972 | 0.863139 | 0.932552 |
| usb_adaptor | 5015 | 0.921011 | 0.916412 | 0.903857 | 0.946004 |
| zipper | 5005 | 0.922767 | 0.918750 | 0.885711 | 0.953526 |
| switch | 5050 | 0.926113 | 0.925297 | 0.912729 | 0.937209 |
| pcb | 5010 | 0.926783 | 0.927561 | 0.902966 | 0.948156 |
| end_cap | 5010 | 0.943808 | 0.942033 | 0.931951 | 0.959282 |
| phone_battery | 5000 | 0.944120 | 0.940849 | 0.922624 | 0.977510 |
| rolled_strip_base | 5050 | 0.944795 | 0.945591 | 0.928781 | 0.959019 |
| mint | 5305 | 0.946267 | 0.944292 | 0.931466 | 0.968475 |
| usb | 5050 | 0.946361 | 0.947070 | 0.927901 | 0.962937 |
| u_block | 4990 | 0.949032 | 0.943580 | 0.934310 | 0.973959 |
| plastic_nut | 5010 | 0.950325 | 0.947170 | 0.937483 | 0.975000 |
| plastic_plug | 4995 | 0.951948 | 0.944190 | 0.927477 | 0.983313 |
| tape | 5100 | 0.954087 | 0.956132 | 0.937657 | 0.968478 |
| wooden_beads | 5005 | 0.956524 | 0.954948 | 0.941107 | 0.975290 |
| toy | 5025 | 0.956638 | 0.952266 | 0.942411 | 0.975641 |
| bottle_cap | 5015 | 0.956675 | 0.968883 | 0.895538 | 0.976390 |
| eraser | 5065 | 0.958243 | 0.960575 | 0.933836 | 0.973469 |
| audiojack | 5050 | 0.958564 | 0.957393 | 0.950013 | 0.967187 |
| button_battery | 5000 | 0.962143 | 0.963833 | 0.927225 | 0.982144 |
| terminalblock | 5050 | 0.966474 | 0.967747 | 0.958526 | 0.973615 |
| toothbrush | 5005 | 0.967828 | 0.973150 | 0.940879 | 0.982777 |
| regulator | 5100 | 0.968880 | 0.968540 | 0.963147 | 0.975053 |
| mounts | 5050 | 0.972130 | 0.971308 | 0.963425 | 0.979302 |
| transistor1 | 5000 | 0.977366 | 0.980913 | 0.954440 | 0.986953 |
| vcpill | 5025 | 0.978528 | 0.979086 | 0.965864 | 0.990621 |
| porcelain_doll | 5000 | 0.983700 | 0.984728 | 0.977221 | 0.987049 |

| view | target | images | mean | median | p05 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | 256 | 30210 | 0.933148 | 0.951794 | 0.811255 | 0.979821 |
| C1 | 512 | 30210 | 0.972091 | 0.979122 | 0.930194 | 0.991122 |
| C2 | 256 | 30210 | 0.946884 | 0.950101 | 0.895641 | 0.982789 |
| C2 | 512 | 30210 | 0.977258 | 0.980421 | 0.954711 | 0.993846 |
| C3 | 256 | 30210 | 0.946700 | 0.949712 | 0.879893 | 0.983219 |
| C3 | 512 | 30210 | 0.977185 | 0.979640 | 0.950187 | 0.993944 |
| C4 | 256 | 30210 | 0.948362 | 0.947004 | 0.895063 | 0.984396 |
| C4 | 512 | 30210 | 0.977731 | 0.979098 | 0.956291 | 0.993857 |
| C5 | 256 | 30210 | 0.943203 | 0.950792 | 0.881576 | 0.983672 |
| C5 | 512 | 30210 | 0.975678 | 0.979483 | 0.950503 | 0.994143 |

| status | target | images | mean | median | p05 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| NG | 256 | 78210 | 0.944427 | 0.951612 | 0.878223 | 0.982082 |
| NG | 512 | 78210 | 0.976295 | 0.980085 | 0.949619 | 0.993532 |
| OK | 256 | 72840 | 0.942835 | 0.948710 | 0.879020 | 0.983713 |
| OK | 512 | 72840 | 0.975660 | 0.979040 | 0.949765 | 0.993908 |

OK/NG 전체 차이에는 품목·시점·불량 유형·촬영 조건의 혼합이 포함된다. 같은 품목·시점·상태의 세부 표로 확인하며, 결함 때문에 차이가 났다고 단정하지 않는다.

## 6. 512→256의 추가 손실

| index | ssim_drop_512_to_256 | rgb_rmse_increase |
| --- | --- | --- |
| count | 151050.000000 | 151050.000000 |
| mean | 0.032329 | 2.128028 |
| std | 0.020997 | 1.155097 |
| min | 0.000000 | 0.000000 |
| 5% | 0.010169 | 1.050249 |
| 50% | 0.028063 | 1.843575 |
| 95% | 0.072320 | 4.143506 |
| max | 0.169293 | 8.673053 |

ssim_drop_512_to_256은 원본 기준 SSIM512−SSIM256이며 rgb_rmse_increase는 RMSE256−RMSE512다. per_image_stepwise_changes.csv에는 직접 512 영상을 기준으로 계산한 target256 지표도 함께 있으므로 두 기준을 구분한다.

## 7. 손실 상·하위 실제 영상 검수

| category | status | view | target | selection | rank | ssim | rgb_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| toy_brick | OK | C1 | 512 | high_loss | 1 | 0.887091 | 7.092183 |
| toy_brick | OK | C1 | 512 | high_loss | 2 | 0.890372 | 6.161109 |
| toy_brick | NG | C1 | 512 | high_loss | 3 | 0.890379 | 7.182306 |
| button_battery | OK | C3 | 512 | low_loss_nonconstant | 1 | 0.999989 | 0.023485 |
| button_battery | OK | C4 | 512 | low_loss_nonconstant | 2 | 0.999961 | 0.047297 |
| button_battery | OK | C5 | 512 | low_loss_nonconstant | 3 | 0.999904 | 0.065556 |
| toy_brick | OK | C1 | 256 | high_loss | 1 | 0.727626 | 11.270516 |
| toy_brick | OK | C1 | 256 | high_loss | 2 | 0.728347 | 12.461349 |
| toy_brick | OK | C1 | 256 | high_loss | 3 | 0.728967 | 13.483536 |
| button_battery | OK | C3 | 256 | low_loss_nonconstant | 1 | 0.999968 | 0.032374 |
| button_battery | OK | C4 | 256 | low_loss_nonconstant | 2 | 0.999912 | 0.068269 |
| button_battery | OK | C5 | 256 | low_loss_nonconstant | 3 | 0.999841 | 0.077927 |

각 해상도에서 SSIM 손실 상위 3개와 비상수 영상 중 손실 하위 3개를 선정했다. 완전 검은 영상 등 SSIM=1 사례는 저손실 검수 후보에서 제외했다. 이는 눈으로 확인할 극단 사례 선정이며 임의 추출된 대표 표본이 아니다. 아래 원본·축소·복원·고정 범위 차이맵과 동일 영역 확대를 함께 본다.

## 8. 기존 마스크·Bounding Box 연결

| target | boxes | images | short_under2 | short_under4 | area_under16 | short_median |
| --- | --- | --- | --- | --- | --- | --- |
| 1024 | 60629 | 51288 | 0 | 38 | 26 | 38.000000 |
| 512 | 60629 | 51288 | 38 | 1525 | 816 | 19.000000 |
| 256 | 60629 | 51288 | 1525 | 8667 | 5025 | 9.500000 |

박스 60,629개는 8방향 연결 성분과 검증된 >0 마스크 정책으로 이미 생성된 결과를 읽었다. NG 전체가 아니라 제공 마스크와 확정 클래스가 있는 영상에 한한다. 길이를 target/1024, 면적을 그 제곱으로 환산했다. 박스 단변 2px 미만은 검토 우선순위 신호이지 실제 결함 소실·검출 실패 판정이 아니다.

기존 결함 ROI 검수는 336이미지×2해상도=672행, 빈 마스크 1이미지를 제외한 670개 유효 관측이다. 마스크는 JPG의 결함 위치를 지정하는 용도다. ROI RGB 복원 오차와 전체 영상 오차를 비교해 전체 평균이 작은 영역의 변화를 희석할 수 있는지 살펴본다.

## 9. 해상도별 장단점과 실험 가설

1024는 원본 세부 정보를 유지하지만 영상당 픽셀 수가 512의 4배, 256의 16배다. 이는 입력 픽셀 수 비율이며 실제 메모리·추론 시간 측정값이 아니다. 512는 픽셀 수와 세부 정보 보존의 중간 후보이며, 256은 더 적은 입력 픽셀을 쓰지만 경계·고주파 변화와 작은 박스 위험을 함께 검토해야 한다.

검증할 가설: (1) 작은 결함 클래스는 256보다 512/1024 또는 타일링에서 검출·분할 지표가 나을 수 있다. (2) SSIM이 낮은 질감 품목은 고해상도 유지의 이득이 클 수 있다. (3) 배경 변화가 전체 지표를 지배하는 품목은 제품·결함 ROI 지표가 모델 결과와 더 관련될 수 있다. (4) 5시점 결합이 한 시점의 세부 손실을 보완할 수 있으나 실제 제품 단위 평가가 필요하다.

동일 제품 단위 분할·시드·증강·모델·학습 예산을 고정하고 256/512/1024를 비교한다. 이상탐지는 image/pixel AUROC와 AUPRO, 객체탐지는 클래스별 AP와 작은 객체 recall을 함께 평가한다. 운영 장치에서 실제 지연·최대 메모리도 측정한다. 이번 작업에서 모델을 학습하거나 최적 해상도를 결정하지 않았다.

## 10. 한계·미완료·회의 결정 항목

고주파는 Laplacian 대리값이며 주파수 대역별 FFT 분석은 하지 않았다. ROI 표본은 전체 주석 영상의 전수 ROI 분석이 아니다. 자동 마스크는 제공 정답의 경계 정책에 의존하고 물리적 결함의 완전성을 독립 검증하지 않았다. 검은 영상 두 장은 에너지 비율 분모가 0이며 추후 학습 사용 여부를 결정해야 한다.

회의에서 결정할 사항: ① 초기 기준 입력 해상도와 고해상도 예외 품목 ② 작은 결함용 타일링/ROI 전략 ③ 제품 단위 평가와 클래스별 최소 recall 기준 ④ 검은 영상·라벨 경로 충돌의 학습 제외 정책 ⑤ 제한된 장치에서 비교할 속도·메모리 예산. 모델 성능·추론 속도·최적 해상도는 미검증이다.

## 11. 시각화와 해석

### distribution psnr db

![distribution psnr db](../outputs/resolution_detail_20261111_v2/distribution_psnr_db.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. psnr_db는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution ssim

![distribution ssim](../outputs/resolution_detail_20261111_v2/distribution_ssim.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. ssim는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution edge recall

![distribution edge recall](../outputs/resolution_detail_20261111_v2/distribution_edge_recall.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. edge_recall는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution edge f1

![distribution edge f1](../outputs/resolution_detail_20261111_v2/distribution_edge_f1.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. edge_f1는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution local contrast retention

![distribution local contrast retention](../outputs/resolution_detail_20261111_v2/distribution_local_contrast_retention.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. local_contrast_retention는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution high frequency proxy retention

![distribution high frequency proxy retention](../outputs/resolution_detail_20261111_v2/distribution_high_frequency_proxy_retention.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. high_frequency_proxy_retention는 영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.

### distribution rgb rmse

![distribution rgb rmse](../outputs/resolution_detail_20261111_v2/distribution_rgb_rmse.png)

전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. rgb_rmse는 작을수록 복원 오차가 작다.

### category comparison

![category comparison](../outputs/resolution_detail_20261111_v2/category_comparison.png)

category별 동일 영상 가중 평균. 각 그룹의 표본 수를 표시한다. 품목 구성·촬영 배경·결함 유형이 섞여 있으므로 그룹 차이로 결함 검출 성능을 추정할 수 없다.

### view comparison

![view comparison](../outputs/resolution_detail_20261111_v2/view_comparison.png)

view별 동일 영상 가중 평균. 각 그룹의 표본 수를 표시한다. 품목 구성·촬영 배경·결함 유형이 섞여 있으므로 그룹 차이로 결함 검출 성능을 추정할 수 없다.

### status comparison

![status comparison](../outputs/resolution_detail_20261111_v2/status_comparison.png)

status별 동일 영상 가중 평균. 각 그룹의 표본 수를 표시한다. 품목 구성·촬영 배경·결함 유형이 섞여 있으므로 그룹 차이로 결함 검출 성능을 추정할 수 없다.

### stepwise distribution

![stepwise distribution](../outputs/resolution_detail_20261111_v2/stepwise_distribution.png)

원본 대비 두 해상도 지표의 차이다. 별도로 저장된 512 영상을 기준으로 한 직접 단계별 PSNR/SSIM과 혼동하지 않는다. 양수이면 256에서 추가 손실이 증가한다.

### case 01 full

![case 01 full](../outputs/resolution_detail_20261111_v2/case_01_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 01 crop

![case 01 crop](../outputs/resolution_detail_20261111_v2/case_01_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 02 full

![case 02 full](../outputs/resolution_detail_20261111_v2/case_02_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 02 crop

![case 02 crop](../outputs/resolution_detail_20261111_v2/case_02_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 03 full

![case 03 full](../outputs/resolution_detail_20261111_v2/case_03_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 03 crop

![case 03 crop](../outputs/resolution_detail_20261111_v2/case_03_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 04 full

![case 04 full](../outputs/resolution_detail_20261111_v2/case_04_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 04 crop

![case 04 crop](../outputs/resolution_detail_20261111_v2/case_04_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 05 full

![case 05 full](../outputs/resolution_detail_20261111_v2/case_05_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 05 crop

![case 05 crop](../outputs/resolution_detail_20261111_v2/case_05_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 06 full

![case 06 full](../outputs/resolution_detail_20261111_v2/case_06_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 06 crop

![case 06 crop](../outputs/resolution_detail_20261111_v2/case_06_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 07 full

![case 07 full](../outputs/resolution_detail_20261111_v2/case_07_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 07 crop

![case 07 crop](../outputs/resolution_detail_20261111_v2/case_07_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### case 08 full

![case 08 full](../outputs/resolution_detail_20261111_v2/case_08_full.png)

기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.

### case 08 crop

![case 08 crop](../outputs/resolution_detail_20261111_v2/case_08_crop.png)

192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.

### defect roi and bbox risk

![defect roi and bbox risk](../outputs/resolution_detail_20261111_v2/defect_roi_and_bbox_risk.png)

ROI는 기존 336개 마스크 연결 이미지 표본(해상도당 유효 335개)이며 전체 NG의 대표성을 보장하지 않는다. 박스 위험은 제공 위치 정답이 있고 클래스가 확정된 전체 60,629개 박스의 기하학적 축소값이며 실제 검출 실패율이 아니다.

## 12. 전체 결과 파일과 재현

- [bbox_projected_size_risk.csv](../outputs/resolution_detail_20261111_v2/bbox_projected_size_risk.csv)

- [category_statistics.csv](../outputs/resolution_detail_20261111_v2/category_statistics.csv)

- [category_view_status_statistics.csv](../outputs/resolution_detail_20261111_v2/category_view_status_statistics.csv)

- [existing_roi_summary.csv](../outputs/resolution_detail_20261111_v2/existing_roi_summary.csv)

- [existing_roi_whole_comparison.csv](../outputs/resolution_detail_20261111_v2/existing_roi_whole_comparison.csv)

- [extreme_review_images.csv](../outputs/resolution_detail_20261111_v2/extreme_review_images.csv)

- [overall_statistics.csv](../outputs/resolution_detail_20261111_v2/overall_statistics.csv)

- [status_statistics.csv](../outputs/resolution_detail_20261111_v2/status_statistics.csv)

- [stepwise_distribution.csv](../outputs/resolution_detail_20261111_v2/stepwise_distribution.csv)

- [stepwise_group_statistics.csv](../outputs/resolution_detail_20261111_v2/stepwise_group_statistics.csv)

- [view_statistics.csv](../outputs/resolution_detail_20261111_v2/view_statistics.csv)

집계·시각화 재현 명령(새 출력 이름 필요):

```bash
uv run --offline python scripts/report_resolution_detail.py --run outputs/windows_preserved_20261111_v1 --data-root dataset --output outputs/resolution_detail_NEW --report reports/RESOLUTION_DETAILED_NEW.md
```

실행 환경: Python 3.12 + 기존 uv.lock 고정 의존성. PNG/CSV/선정 이미지 파생물은 로컬 outputs/에 보관하며 GitHub 대상에는 코드·문서(PDF 포함)만 남긴다. PDF에는 그래프가 내장되어 단독 회의 자료로 사용할 수 있다. Push는 수행하지 않았다.

무결성 근거: [integrity.json](../outputs/resolution_detail_20261111_v2/integrity.json). 입력 5개 파일의 SHA-256을 집계 전후 비교한다. 원본 JPG/PNG는 선택 사례 시각화에서 읽기만 했다.