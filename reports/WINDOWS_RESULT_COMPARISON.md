# Windows 실제 결과와 Ubuntu 비교

원본 Windows 결과는 읽기 전용으로 사용했다. [검증 JSON](../outputs/windows_comparison_20261111_v2/comparison_validation.json).

- 실제 저장 Windows JPG 151,050 / PNG 51,329. Ubuntu와 상대 경로 집합 동일 여부: JPG True, PNG True. 과거 참고 146,060/50,115와의 차이 원인은 미확정이다. 최신 Windows 결과에도 u_block이 있다.
- 저장 split은 151,050장 모두 재현 일치했다. [분할 검증](WINDOWS_SPLIT_REPRODUCTION.json).
- 전체 밝기 151,050장 비교: 새 OpenCV 정수 회색조와 기존 float32 RGB 가중 회색조의 영상 평균 절대 차이 평균 0.01320723, 최대 0.09794903 intensity. [전체 대조](../outputs/windows_comparison_20261111_v2/brightness_full_comparison.csv). 반올림/회색조 정의 차이를 OS 차이로 보지 않는다.
- 기존 Notebook의 순수 analyze_brightness를 그대로 추출해 30품목×5시점 150장 재실행: 저장값 대비 최대 절대 차이 0. [같은 방법 재검증](../outputs/windows_comparison_20261111_v2/brightness_same_method_replay.csv).
- 기존 해상도는 50장의 3해상도 150행만 저장되어 있다. 모든 저장 입력에 보존된 loss_metrics를 다시 적용했다. [지표별 같은 방법 대조](../outputs/windows_comparison_20261111_v2/resolution_same_method_replay.csv). 이는 전체 해상도 분석 결과가 아니다.

기존 해상도는 LINEAR 축소, 경계 ±1픽셀 일치 허용, Laplacian 절댓값 평균(ksize3), Sobel magnitude 평균, 9×9 box 국소 표준편차다. 새 통합 분석은 AREA 축소, 경계 정확 위치, Laplacian 제곱 평균(ksize1), Sobel 제곱 에너지, Gaussian11 sigma1.5 국소 대비를 사용한다. PSNR 동일 영상 처리도 기존 OpenCV 약361dB와 새 상한120dB가 다르다. 따라서 서로 다른 정의의 값을 직접 OS 오차로 비교하지 않는다.

기존 multiclass Notebook에는 threshold127 예시와 나중의 None 초기화가 함께 있어 실행 순서 의존성이 있다. 새 정책은 전체 마스크 무결성/층화 overlay/공식 nonzero 평가 규칙에 근거해 >0으로 명시했다. 기존 단일 클래스 함수·backend·coarse_occupancy는 보존 및 재사용하고, 새 default defect_type 8클래스와 기존 category+type 클래스 체계를 구분한다.

초기 area-v1 히트맵은 면적 진단으로 보존한다. 기존 coursework 계약을 재사용하는 presence-v2는 영상별 cell 존재 합/n_known 또는 n_positive이며 관측 0은 NaN이다. 기존 Windows seed42 분할로 별도 재생성한다. 원본 위치별 수치와 직접 동등하다고 주장하려면 split/threshold/grid/분모가 모두 같아야 한다.


## 실제 저장 Windows 히트맵 NPY 전수 비교

기존 Windows 555개 그룹과 새 560개 그룹(UNRESOLVED 5개 추가)의 공통 555개를 실제 NPY로 비교했다. **553개 그룹에서 occupancy_known과 occupancy_positive가 모든 격자 값이 정확히 일치(허용 오차 0, NaN은 같은 미관측 상태로 비교)**했다. 같은 제품 split, >0 정책, 64×64 영상별 칸 존재 여부와 known/positive 분모를 유지한 결과다.

차이가 있는 두 그룹은 fire_hood/HS/C4(기존 known81→새80), C5(50→49)다. 폴더 HS/파일명 QS 충돌을 UNRESOLVED로 분리해 각각 한 제공 마스크가 이동한 영향이며 OS 수치 오차로 해석하지 않는다. 최대 절대 빈도 차이는 각각 1/81=0.012345679, 1/50=0.02다. [전수 대조 CSV](../outputs/windows_heatmap_comparison_20261111_v1/heatmap_same_split_comparison.csv), [검증 JSON](../outputs/windows_heatmap_comparison_20261111_v1/validation.json). 재현 코드는 scripts/compare_windows_heatmaps.py다.


## 보존된 과거 체크포인트와 535개 비교의 범위

`.ipynb_checkpoints`에서 과거 참고와 동일한 29품목/JPG146,060/PNG50,115/비교535행을 확인했다. 최신 CSV와의 경로 집합 차이는 JPG4,990개·PNG1,214개 모두 u_block이며 제거된 경로는0개다. 최신 Windows 비교555행에는 u_block20행이 있고 새560행에는 추가로 UNRESOLVED5행이 있다. 보존 체크포인트 사이의 범위 차이는 확인됐으나, 당시 u_block을 제외한 동기와 사용자가 인용한 참고 숫자의 정확한 생성 출처 연결은 미확정이다. [파일별 SHA256·경로 차이](../outputs/windows_checkpoint_comparison_20261111_v1/comparison.json).

## 기존 밝기 그룹 비교 함수의 전량 재실행

기존 Notebook compare_distributions를 추출해 저장된 RGB float 밝기로555개 그룹을 다시 계산했다. 저장 결과 대비 평균 차이/겹침 최대 오차0, Cohen d 최대1.11e-14였다. 기존과 새 비교는 모두 영상별 평균 명도의32-bin 분포와 pooled sample Cohen d를 사용한다. 픽셀 히스토그램과 영상 평균 분포는 구분한다. 동일 표본 수550개 그룹의 OpenCV 정수 명도 vs RGB float 차이는 평균 차이 최대0.044676664 intensity, d 최대0.076521615, overlap 최대0.047227926이었다. 경계 근처 명도의 bin 이동과 반올림이 겹침 변화에 영향을 줄 수 있다. 나머지5개 fire_hood/HS 시점 그룹은 NG132→130으로 유형 충돌 영상2장씩을 UNRESOLVED로 이동한 차이다. [검증](../outputs/windows_group_comparison_20261111_v1/validation.json), [같은 방법555개 재실행](../outputs/windows_group_comparison_20261111_v1/windows_group_same_method_replay.csv).
