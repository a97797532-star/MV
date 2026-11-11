# Real-IAD 네 가지 데이터 분석 + 증강·학습 과제 v2

`analysis_guide.ipynb`를 먼저 여세요. 분석은 완성 코드로 실행하고, 밝기/OpenCV 증강과 학습은 학생이 구현합니다.
기존 데이터 입력·감사·제품 단위 분할·두 backend를 보존하면서 요청 범위에 맞게 노트북을 재구성했습니다.

## 파일 안내

| 파일 | 역할 |
|---|---|
| analysis_guide.ipynb | 시작할 학생용 노트북. 분석 실행 + 과제 단계·힌트·빈 함수·빈 결과표 |
| analysis_guide_demo_executed.ipynb | 합성 데모로 기본 셀을 실행한 결과 예시. 실제 데이터 성능 아님 |
| coursework.py | 클래스 밝기·train 위치 히트맵·박스 라벨·해상도 분석 구현 |
| core.py / backend.py | 기존 로더·감사·분할·분석 / OpenCV 또는 scikit-image 성분 구현 |
| make_demo.py | RGB·마스크 합성 데모. GAN 생성 데이터나 Real-IAD 원본이 아님 |
| test_contracts.py / test_coursework.py | 기존 및 신규 경계·누수·라벨·분모·변환 검증 |
| compare_focused.py | 두 버전의 새 분석 CSV·히트맵 배열 비교, 처리 시간 제외 |
| analysis_guide_legacy.ipynb / README_legacy.md | 이전 일반 분석 흐름 보존 |
| sample_focused_results/ | 이번 버전의 합성 예제 결과. 기존 sample_results는 제거 |
| validation.txt / parity_report.md | 실제 수행한 검증과 두 구현 일치 결과 |

## 설치·실행

권장 Python 3.12. 압축을 풀고 패키지 폴더에서 터미널을 여세요.

```bash
python -m venv .venv
# Linux/WSL
source .venv/bin/activate
# Windows PowerShell은 대신: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-notebook.txt
python -m jupyter lab
```

`analysis_guide.ipynb`에서 Python 커널을 선택하고 위에서 아래 순서로 실행합니다.
GPU·API 키·모델 가중치 없이 합성 데이터 분석이 실행됩니다.
OpenCV 증강 과제는 두 버전 모두 다음 추가 의존성을 설치합니다.

```bash
python -m pip install -r requirements-assignment.txt
```

노트북 실행이 어려운 검증 환경에서는 `python validate_notebook.py`를 실행할 수 있습니다.
이 검증기는 IPython으로 모든 코드 셀을 순서 실행하고 실행본을 저장합니다. 별도 TCP Jupyter 커널을 사용하지 않습니다.
학습 프레임워크와 사전학습 모델은 학생이 선택한 뒤 별도 버전·가중치 정보를 기록합니다. 기본 Run All은 다운로드·학습하지 않습니다.

## 완성된 분석 범위

### 1. 클래스별 밝기

category=제품 품목, anomaly_class=제품 불량 유형, view_id=촬영 시점입니다.
이 셋을 분리한 이미지별 mean·median·P05·P95·암부·포화 비율, 평균 정규화 히스토그램,
클래스별 박스플롯을 제공합니다. 각 이미지의 히스토그램을 합계 1로 정규화한 뒤 평균합니다.
제품 불량 라벨이 양성이어도 해당 시점에 불량이 보이지 않을 수 있습니다.
마스크 내부와 바깥 평균도 기록하되 바깥은 배경+제품 표면이므로 순수 배경으로 해석하지 않습니다.
기존 core.image_features의 RGB 포화 비율과 신규 grayscale 포화 비율은 정의가 다르므로 섞지 않습니다.

### 2. GAN 참고용 위치 히트맵

train의 **품목×불량 유형×시점**별 마스크만 사용합니다.
기본 64×64 격자에 양성 픽셀이 하나라도 있으면 해당 이미지의 그 칸을 1로 표시하고 평균합니다.
원본의 1픽셀 결함도 보존하며 맵 값은 격자 점유율이지 픽셀 밀도나 생성 확률이 아닙니다.
확인된 빈 마스크 포함 분모와 양성 마스크만의 조건부 분모를 각각 저장합니다.
missing/error는 분모에서 제외하고 개수를 기록합니다. n_positive=0이면 조건부 맵은 NA입니다.
정상 학습 공식 train에 불량이 없으면 히트맵이 비어 있습니다. test를 자동 보충하지 않습니다.
GAN 부위 선택에는 전경·제품 부위·마스크 크기·실제 결함 타당성 검수가 추가로 필요합니다.
선택한 개발 표본으로 만든 참고 맵이므로 실제 GAN 준비 시 train 전체로 다시 계산하세요.

### 3. 마스크 → GT 바운딩박스

명시적으로 검증한 bool/0-1/0-255 마스크에 8연결 성분을 적용합니다.
분리 영역은 별도 박스, 최소 면적 제거 없음. GT에는 dilation/closing/padding을 넣지 않습니다.
`[x0,y0,x1,y1]`의 오른쪽/아래 끝점을 제외하고 원본 픽셀 좌표를 저장합니다.
CSV와 single-class defect의 split별 COCO·YOLO 라벨을 제공합니다.
COCO category_id는 1, YOLO class_id는 0이며 COCO box-only area는 박스 면적입니다.
마스크 누락·오류를 빈 정상 라벨로 바꾸지 않습니다.

**YOLO 내보내기는 라벨만**입니다. detection_images.csv의 원본 image_path와 숫자 yolo_stem을 사용해
`images/<split>/<yolo_stem>.png`를 준비하는 단계는 학생 과제입니다.
라벨과 이미지가 같은 stem인지 확인하고 data.yaml을 작성해야 학습할 수 있습니다.
COCO의 file_name은 ROOT 기준 원본 상대 경로입니다.

### 4. 모델 입력 해상도 1024 / 512 / 256

RGB bilinear, 성분 ID 맵은 공통 pixel-center nearest로 비교합니다.
성분별 잔존 픽셀·소실·박스 크기와 RGB 밝기·전처리 시간·입력 텐서 메모리만 산출합니다.
이 수치는 모델 성능·추론 지연·피크 GPU 메모리 결과가 아닙니다.
5뷰 FP32 입력만 계산하면 1024=60MiB, 512=15MiB, 256=3.75MiB입니다.
데모 원본은 512×640이므로 1024는 업샘플이며 square resize는 종횡비를 바꿉니다.
실제 모델의 내부 resize와 letterbox·좌표 역변환은 과제로 구현·확인합니다.

## 남겨 둔 학생 과제

| 과제 | 구현할 부분 | 힌트·확인 기준 |
|---|---|---|
| A | student_brightness | float에서 계산·clip·uint8, gamma/alpha-beta 후보, 포화·결함 대비·동일 좌표 |
| B | student_opencv_augment | RGB·mask 같은 기하 변환, mask nearest, 변환 후 박스 재추출·오버레이 |
| C | student_prepare_input | 3해상도·채널·정규화·resize/letterbox·실제 백본 입력 크기 |
| D | student_train_and_evaluate | 모델 1개부터 사전학습·헤드·학습·검증·결과표, 내장증강 통제 |

기본 스위치는 모두 False입니다. 함수를 구현하지 않고 True로 바꾸면 NotImplementedError로 명확히 멈춥니다.
정답 증강 코드·GAN 생성기·완성 학습 루프·모델 가중치는 포함하지 않습니다.
512에서 증강 없음/밝기/OpenCV/결합 4조건을 비교하고, 선정 정책을 1024/256에 추가해
최소 6조건을 비교하세요. 충분한 자원이 있으면 전체 12조건으로 확대합니다.
고정된 원본 제품 split, 학습 step·유효 batch·seed를 기록하고 랜덤 증강은 train에만 적용합니다.
제품 Recall/FPR·박스 AP50/AP@[.50:.95]·작은 불량 Recall·5뷰 지연·메모리는 직접 측정해 작성합니다.

## 실제 데이터로 전환

1. Real-IAD 공식 사용 조건에 동의해 필요한 품목·JSON·마스크를 내려받습니다.
2. USE_DEMO=False로 바꾸고 ROOT, JSON_DIR, CATEGORIES를 설정합니다.
3. 새 OUTPUT 경로를 정합니다. 선택 표본이나 변환 정책을 바꿀 때도 새 결과 폴더를 사용하세요.
4. 공식 train 정상-only 실험과 지도 탐지/GAN용 프로젝트 분할을 구분합니다.
   필요할 때만 USE_SUPERVISED_PROJECT_SPLIT=True를 명시적으로 설정합니다.
5. category/sample_key/view_id, mask encoding과 camera token을 수동 표본으로 확인합니다.
6. 공식 분할·원본 제품 키·파생 계보와 split_version을 보존합니다. holdout 유형은 GAN에도 넣지 않습니다.
7. 잠근 test는 분석 설계·임계값·GAN 소스에 사용하지 않습니다.
8. 전체 분석은 MAX_PRODUCTS=0으로 실행합니다. 실험 설정과 선택 목록·해시를 기록합니다.

다중 클래스/ignore mask는 core.read_mask가 무조건 양성으로 바꾸지 않고 멈춥니다.
릴리스 정의에 맞는 명시적 매핑을 검수해 추가하세요. 색 마스크도 임의 이진화하지 않습니다.

## 검증과 비교

```bash
python -m unittest -v test_contracts test_coursework
python validate_notebook.py
python compare_focused.py ../RealIAD_OpenCV/notebook_results_demo/focused_analysis ../RealIAD_ScikitImage/notebook_results_demo/focused_analysis
```

검증은 합성 데모와 경계 사례에 한합니다. 실제 Real-IAD 전수 실행·증강 학습·탐지 모델 성능은 미실행입니다.
기존 core.py CLI는 그대로 사용 가능하며 README_legacy.md를 참고하세요.
