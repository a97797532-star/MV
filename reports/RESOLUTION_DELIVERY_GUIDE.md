# 해상도 분석 최종 전달 안내

최신 사용자 지시에 따라 전체 해상도 계산은 반복하지 않았고 GitHub Push도 수행하지 않았다. 원본 영상, 기존 CSV, 기존 검증 결과와 과거 보고서는 보존했다.

## 회의 자료

- [최종 회의용 PDF](RESOLUTION_TEAM_MEETING_FINAL.pdf): 그래프와 비교 영상을 내장하여 단독으로 열람할 수 있다.
- [상세 Markdown](RESOLUTION_DETAILED_ANALYSIS.md): 전체·품목·시점·OK/NG별 해석, 극단 사례, 단위와 분모, 후속 실험 가설을 제공한다.
- [최종 PDF 독립 검증](RESOLUTION_TEAM_MEETING_FINAL.render_validation.json): PDFium 페이지 수·한글 추출·선택 페이지 렌더 검사 결과.
- [전달 범위·무결성 검사](RESOLUTION_DELIVERY_VALIDATION.json).

중간 레이아웃 PDF인 RESOLUTION_DETAILED_ANALYSIS.pdf 및 RESOLUTION_TEAM_MEETING.pdf도 보존했다. 회의에는 **RESOLUTION_TEAM_MEETING_FINAL.pdf**를 사용한다.

## 로컬 증거

`outputs/resolution_detail_20261111_v2/`에 새 집계 CSV 11개와 그래프·사례 PNG 28개를 저장했다. `overall_statistics.csv`, `category_statistics.csv`, `view_statistics.csv`, `status_statistics.csv`, `category_view_status_statistics.csv`에는 평균·표준편차·유효 수·결측 수·중앙값·P01/P05/P25/P75/P95/P99·최소·최대를 기록했다. 마지막 파일은 품목×시점×상태×해상도 900개 조합을 포함한다.

`extreme_review_images.csv`는 해상도별 손실 상·하위 각 3건씩 총 12개 선정 행이며, 동일 이미지가 두 해상도에서 선정되어 실제 고유 이미지는 8장이다. 이 8장만 비교 그림을 위해 읽었다. `existing_roi_whole_comparison.csv`는 과거 결함 ROI 표본 결과를 재사용했다. `bbox_projected_size_risk.csv`는 기존 60,629개 박스의 기하학적 축소 크기다. 임계값·연결 성분 추출을 재실행하지 않았다.

`integrity.json`의 입력 SHA-256 전후 일치와 계산 재실행 0건을 확인한다. 집계 첫 시도는 기존 단계 CSV의 category/view/status와 병합 시 열 이름이 겹쳐 중단되었다. 이 시도의 부분 집계는 `outputs/resolution_detail_20261111_v1/`에 남기고, 중복 열을 제거한 뒤 v2에서 완료했다. 첫 PDF 재배치 시 인접 Markdown 표의 경계 처리가 실패하여 부분 PDF를 로컬 출력 디렉터리의 `RESOLUTION_TEAM_MEETING_INCOMPLETE.pdf`에 보존했다. 최종 PDF는 해당 문제를 수정한 뒤 새로 생성하고 독립 검사했다. 두 실패 모두 원본 계산 CSV의 수정이나 해상도 재계산을 수반하지 않았다.

## 핵심 해석과 한계

평균 SSIM은 512에서 0.975989, 256에서 0.943659다. 중앙값은 각각 0.979586과 0.950022다. C1의 256 평균 SSIM 0.933148은 C1~C5 중 가장 낮지만 품목·촬영 구성이 섞인 기술 통계다. 256 평균 SSIM이 가장 낮은 품목은 toy_brick(0.860115), woodstick(0.871078), fire_hood(0.881590)이다. 위 수치는 새 집계 CSV를 근거로 한다.

결함 ROI 표본의 평균 RGB RMSE는 512에서 6.360019, 256에서 12.339978이며, 동일 표본의 전체 영상 평균은 2.667408과 4.909179다. 전체 이미지 평균은 국소 결함 위치 변화를 희석할 수 있다. 유효 표본은 해상도당 335장이며 전체 NG 전수에 일반화하지 않는다. 256으로 기하학적 환산한 박스 중 단변 2px 미만은 1,525/60,629개(약 2.52%)이고 512에서는 38개다. 실제 검출 실패율을 측정한 값은 아니다.

고주파는 Laplacian 에너지 대리값으로 FFT 직접 측정이 아니다. Canny 경계 일치는 위치 이동에 민감하다. 검은 이미지 두 장은 대비·에너지 비율 분모가 0이므로 세 해상도에서 총 6행의 비율을 결측으로 유지한다. 영상 유사성 결과로 모델 성능, 추론 속도 또는 최적 해상도를 확정할 수 없다.

## 회의에서 결정할 사항

1. 256/512/1024 중 첫 비교 실험의 기준 입력과 고해상도 예외 품목.
2. 작은 결함용 타일링 또는 ROI 확대 실험의 우선순위.
3. 동일 제품 단위 데이터 분할과 클래스별 평가 기준.
4. 검은 영상·경로 라벨 충돌의 학습 제외 여부.
5. 실제 운영 장치의 지연·메모리 측정 예산.

모델 학습·모델 성능 비교·실측 속도·FFT 대역 분석·전체 주석 영상의 전수 ROI 분석은 미실행이다. GitHub 업로드 대상은 코드·환경 설정·문서(PDF 포함)만 검수한다. 개별 JPG/PNG·전체 CSV/NPY·가중치·키는 제외하며 Markdown의 `outputs/` 링크는 로컬 근거다. 실제 Push는 하지 않는다.

## 실행 검증

이번 작업에서 `uv run --offline pytest -q`는 **22 passed in 11.69s**였다. 두 보고서 스크립트의 py_compile도 통과했다. 최종 PDF는 모든 페이지의 한글 텍스트 추출과 페이지 수를 검사하고, 표·그림 등 선택 페이지를 실제 렌더하여 검수한다. 선택 렌더 검수를 전 페이지 육안 검수로 표현하지 않는다.
