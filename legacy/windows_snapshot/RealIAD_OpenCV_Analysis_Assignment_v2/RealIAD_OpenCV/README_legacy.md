# Real-IAD 데이터 분석 가이드 코드셋 — OpenCV

첨부 「Real-IAD 5시점 제조 외관검사 통합 실행 가이드」의 **1장 / 1주차 데이터 분석(문서 2~6페이지)**을 실행 가능한 코드로 옮겼습니다. `sci-image`는 **scikit-image**로 해석했습니다. 이 패키지의 영상 처리 backend는 **OpenCV**입니다. GPU·Ollama·API 키 없이 CPU에서 실행합니다.

## 1. 먼저 실행하기

Python **3.12** 권장. 각 ZIP을 별도 폴더로 풉니다. 아래 명령은 패키지 루트에서 실행합니다.

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest -v test_contracts
python make_demo.py --out demo_data
python core.py manifest --root demo_data/images --json-dir demo_data/jsons --out work
python core.py analyze --root demo_data/images --manifest work/manifest.csv --out results_demo --max-products 20
```

같은 경로에 합성 데이터를 다시 만들면 덮어쓰지 않고 멈춥니다. 다른 `--out` 경로를 쓰거나 기존 합성 데이터로 진행하세요. 합성 데이터는 2개 가상 제품 유형 × 3개 코드 × 6개 제품 × 5개 시점입니다. 실제 Real-IAD의 분포나 결함 형상을 재현한 데이터가 아닙니다. 데모의 HS 코드는 배열 검증용으로 두 제품에 사용하며 실제 칫솔 결함 코드에 관한 주장이 아닙니다.

수업·분석용은 `analysis_guide.ipynb`를 여세요. Jupyter가 없다면 다음 명령을 추가합니다.

```bash
python -m pip install -r requirements-notebook.txt
python -m ipykernel install --user --name realiad-opencv --display-name "Real-IAD OpenCV"
jupyter lab analysis_guide.ipynb
```

VS Code에서는 위 가상환경을 노트북 커널로 선택하면 됩니다. 노트북은 `make_demo.py`가 만드는 작은 데이터로 처음부터 실행되며, 별도 설치 명령을 셀 안에서 자동 실행하지 않습니다. 아래 실제 데이터 설정으로 바꿔 사용할 수 있습니다.

## 2. 폴더와 읽을 순서

| 파일 | 역할 |
|---|---|
| `analysis_guide.ipynb` | 0~9단계 설명·코드·표·그림. 가장 먼저 볼 파일 |
| `core.py` | 공통 입력, JSON 어댑터, 감사, 표본 선택, EDA, 그림, 속도 측정 CLI |
| `backend.py` | 이 버전의 Laplacian과 연결 성분 구현. 두 버전 비교 핵심 |
| `make_demo.py` | 같은 seed에서 같은 합성 입력 생성 |
| `compare_results.py` | 양쪽 결과 정합성 검사. 한쪽 라이브러리만 설치해도 CSV 비교 가능 |
| `validate_notebook.py` | Jupyter 서버 없이 IPython으로 노트북의 코드 셀을 순서대로 검증 |
| `test_contracts.py` | 대각선 연결·빈 마스크·경계·누수·읽기 오류 검사 |
| `REFERENCE.md` | 가이드 항목 대응표, 공식 문서, 수식·좌표 계약 |
| `sample_results/` | 제작 환경에서 실행한 합성 예제 결과. 실제 데이터 결과 아님 |
| `validation.txt` | 제작 환경 테스트·노트북 코드 셀 실행 기록 |

두 코드셋은 독립 실행 가능합니다. 공통 입력 및 표·그림 구현은 의도적으로 같고, `backend.py`와 의존성만 다릅니다. 이는 가이드에서 요구한 같은 RGB·같은 분할·같은 좌표 계약을 보장합니다. OpenCV 버전은 scikit-image를 import하지 않으며, scikit-image 버전은 OpenCV를 import하지 않습니다.

## 3. 실제 Real-IAD로 바꾸기

데이터 다운로드와 접근 조건 동의는 사용자가 공식 배포처에서 진행합니다. 코드가 대용량 데이터를 자동 다운로드하지는 않습니다. 공식 다중 시점 분할 `realiad_jsons`를 사용하고, 단일 시점 `_sv` 등 다른 실험 분할과 섞지 마세요.

예상 구조:

```text
Real-IAD/
  realiad_1024/
    toothbrush/ ... image and mask files ...
    toy/ ... image and mask files ...
  realiad_jsons/
    toothbrush.json
    toy.json
```

이것은 설명용 트리입니다. 실제 제품 유형 이름은 내려받은 JSON 파일명을 확인하세요. 이미지 이름을 임의로 변경하지 마세요.

```bash
python core.py manifest --root /data/Real-IAD/realiad_1024 --json-dir /data/Real-IAD/realiad_jsons --categories toothbrush toy --out work_real
python core.py audit --root /data/Real-IAD/realiad_1024 --manifest work_real/manifest.csv --out audit_real
python core.py analyze --root /data/Real-IAD/realiad_1024 --manifest work_real/manifest.csv --out results_real_20 --max-products 20
# 제품 20개 수동 검수 후 같은 분할을 전수 분석
python core.py analyze --root /data/Real-IAD/realiad_1024 --manifest work_real/manifest.csv --out results_real_all
```

`--root`는 JSON 경로를 해석할 이미지 릴리스 루트입니다. 경로를 찾으면 category 접두사가 있는 경우와 없는 경우를 처리하고, 둘 다 실제 파일로 존재하면 모호한 입력으로 중단합니다. 없는 경로를 파일 검색으로 억지로 맞추지 않고 감사에서 `image_error`로 기록합니다.

기본 기대 시점은 **C1~C5**입니다. 번호와 물리적 위/사선 시점은 별개이므로 샘플을 확인해 기록하세요. 다른 토큰을 쓰는 릴리스는 `--expected-views C0 C1 C2 C3 C4` 등으로 **audit와 analyze 양쪽에 같은 값**을 명시합니다.

### 메타데이터 어댑터

지원 형식은 `{"train": [...], "val": [...], "test": [...]}` JSON과 이미지 행 목록 JSON, 한 줄 한 이미지 JSONL입니다. 행 필수 필드는 `image_path`, `anomaly_class`, 선택 필드는 `category`, `mask_path`, `sample_key`, `view_id`, `official_split`입니다. split 딕셔너리 형태라면 바깥의 split 이름이 우선합니다. 정의되지 않은 구조는 명시적으로 멈춥니다. 알 수 없는 필드는 버리지 않도록 원본 JSON을 보관하세요. 분석 매니페스트에는 필요한 표준 필드를 저장합니다.

파일명에서 공식 ADEval 패턴의 제품 키와 `C숫자` 토큰을 추출합니다. 파싱할 수 없는 릴리스는 `sample_key/view_id`를 직접 입력하거나 아래 공통 매니페스트를 작성하세요. 시점마다 다른 sample_key를 만들면 제품 분할이 깨집니다.

```csv
category,sample_key,view_id,image_path,mask_path,anomaly_class,official_split,project_split,split_version
sample,sample_0001_OK,C1,sample/image.png,,OK,train,train,official-v1
```

이 CSV는 열 형식 설명용 한 행입니다. 실제 실행에는 각 제품 시점마다 한 행이 있어야 합니다. 상대 경로를 사용하고 마스크 미제공은 빈 칸으로 둡니다. `--manifest my_manifest.csv`로 사용하면 JSON 로더를 건너뜁니다. `category=OK/NG`처럼 제품 유형을 뜻하지 않는 필드가 있는 자체 JSON은 CSV 변환 시 제품 유형으로 명시적으로 매핑하세요.

## 4. 시험 데이터 보호와 개발용 불량 분석

- **audit는 전수 검사**입니다. 이미지·마스크 디코딩, 크기, 제품 키, 시점 집합, 파일 및 디코딩 픽셀 해시만 확인합니다.
- **analyze는 기본 `project_split=train/val/validation`만 선택**합니다. test는 통계·그림에서 제외됩니다.
- 공식 정상 학습 트랙에서는 개발 데이터에 정상만 있을 수 있습니다. 이때 결함 가시율·성분 그림이 비어 있는 것이 정상입니다. 실제 불량을 본 분석을 하려면 별도 검증 자료 또는 아래 지도학습용 프로젝트 분할이 필요합니다.

가이드의 지도 판정기/GAN 실험 트랙을 선택한 경우에만, 다음 명령으로 **공식 분할을 보존한 별도 프로젝트 분할**을 생성합니다.

```bash
python core.py split --manifest work_real/manifest.csv --out work_real/manifest_supervised.csv --seed 42
# 미학습 결함 ZW를 학습/검증에서 완전히 제외하는 예
python core.py split --manifest work_real/manifest.csv --out work_real/manifest_holdout_ZW.csv --seed 42 --holdout-defects ZW
python core.py analyze --root /data/Real-IAD/realiad_1024 --manifest work_real/manifest_supervised.csv --out results_supervised
```

분할은 category·결함 코드별 제품 그룹을 섞어 약 60/20/20으로 배치합니다. 유형별 제품이 3개 미만이면 시험에만 두고 경고합니다. 실제 비율과 표본 수는 결과로 확인합니다. 이 분할은 공식 성능 비교와 구분해 보고해야 합니다. 근접 중복이나 동일 물체의 재촬영까지 자동 판단하지는 못하므로 감사와 수동 검수를 먼저 완료하세요. 동결한 CSV를 두 팀이 그대로 공유하세요.

최종 설정을 고정한 후에만 명시적으로 `--splits test`를 사용해 별도 출력 경로에 시험 통계를 만드세요. test의 결함 마스크를 GAN 원본·ROI 후보 선택·임계값 튜닝에 사용하지 않습니다.

## 5. 산출물과 해석

| 산출물 | 확인 질문 / 해석 |
|---|---|
| `audit/manifest.csv` | width/height/status/mask_state, SHA256 포함 전체 파일 감사 |
| `audit/split_manifest.csv` | 제품 단위 공식·프로젝트 분할 및 버전 |
| `audit/integrity_issues.csv` | 시점 누락·중복·파싱·이미지/마스크 오류·제품 및 해시 누수 |
| `selected_manifest.csv` | 양쪽이 실제 분석한 고정 표본 목록 |
| `image_metrics.csv` | 밝기·대비·포화·초점, 양성 픽셀 비율·성분 수·NA 사유 |
| `product_summary.csv` | 제품당 시점 수·양성 표시 시점 수·전체 마스크 판정 가능 여부 |
| `counts.csv` | category·split·결함별 제품 수와 이미지 수를 따로 집계 |
| `visibility.csv` | 시점 가시율 분자/분모/미판정 수 |
| `components.csv` | 8이웃 성분 면적·박스·중심·정규화 중심 |
| `resolution_sensitivity.csv` | 원본 성분마다 1024/512/256 변환 후 생존 픽셀 수 |
| `resolution_summary.csv` | 해상도·제품 유형별 소실 성분 수와 소실률 |
| `normal_quality_by_view.csv` | 정상 개발 이미지에 한정한 시점별 품질 분포 통계 |
| `figures/` | 개수·가시율·로그 면적·시점별 위치 지도·품질·소실률·5시점 오버레이 |
| `decisions.md` | 확인된 표본 수와 해상도·융합·보정·GAN 후속 실험 리뷰 양식 |
| `run_info.json` | 라이브러리 버전, 표본·매니페스트 해시, 선택 분할, 크기 |

`mask_state`는 `positive` / `empty` / `not_provided` / `error`입니다. **미제공·오류는 음성으로 채우지 않습니다.** 실제 빈 마스크는 0으로 집계하며, 제품 불량 라벨은 그대로 유지합니다. 마스크가 색상형이면 임의 gray 변환 대신 검수한 바이너리 변환을 요구합니다. 모든 값이 0보다 큰 픽셀을 양성으로 정의하므로 다른 인코딩은 미리 명시적으로 변환하세요.

가시율 분모는 **그 시점이 존재하며 마스크를 읽고 판정할 수 있는 결함 제품 수**입니다. 실제 결함 존재 확률이 아닌 정답 표시율입니다. `n_positive_views`는 미판정 마스크가 있을 때 하한이며, `all_masks_known=1`인 제품만 정확한 '한 시점 양성' 분석에 씁니다.

시점 집합 오류는 자동 복원하지 않습니다. 파싱 실패·키 중복·제품 라벨 충돌·제품/해시 분할 누수·정상 라벨/양성 마스크 충돌은 상세 EDA를 중단합니다. 이미지/마스크 읽기 실패와 시점 누락은 오류 표와 NA로 남기며 부분 분석을 허용합니다. 결과 발표 전 이를 검수하고 `readable_images`, 분모, 제외 사유를 함께 보고하세요.

## 6. 두 버전 비교하기

두 폴더가 이웃해 있고 같은 데이터·동일 매니페스트를 사용했다고 가정합니다. 각각 실행한 결과 폴더를 CSV 비교기에 전달합니다.

```bash
python compare_results.py --left ../RealIAD_OpenCV/sample_results --right ../RealIAD_ScikitImage/sample_results --out parity_report.md
```

실제 데이터 비교에는 두 팀이 **한 manifest CSV를 공유**하고, `--splits`, `--max-products`, `--seed`, `--sizes`, `--expected-views`를 같게 설정하세요. 비교기는 입력/표본 해시와 설정을 확인하며 성분 ID는 면적·박스·중심 기준으로 정규화합니다. 이미지 크기·픽셀 수·성분 수와 실수 지표(절대 1e-8, 상대 1e-10)를 비교합니다. FAIL이면 종료 코드 1을 반환합니다.

표본 선택은 category·결함별 목록을 고정 seed로 섞어 round-robin으로 제품을 고릅니다. 20개로 모든 유형을 담을 수 없는 경우 전체를 포함한다고 보장하지 않습니다. 먼저 `counts.csv`와 표본 목록을 확인하세요. 라이브러리·파이썬 버전이 다르면 CSV 해시 표현이 달라질 수 있으므로 공통 버전을 맞추세요.

## 7. 속도 비교

```bash
python core.py benchmark --root demo_data/images --manifest work/manifest.csv --out benchmark_demo --max-products 20 --repeats 5
```

같은 장비에서 같은 데이터와 입력 순서로 실행하세요. 이미지 품질+마스크 성분 연산만 측정하며 전체 EDA·해시·그림·해상도 민감도 시간과 구분합니다. 제품별 워밍업 후 5회 반복하고 `decode_and_process_ms` / `array_only_ms`를 분리합니다. 제품별 반복 중앙값을 모아 제품 간 중앙값과 p95를 기록합니다. 누락 시점이 있으면 `n_views`를 보고 완전한 5시점 제품만 별도로 비교하세요. OS 캐시를 강제로 비우지 않으므로 디코딩 시간은 warm-cache 환경의 결과입니다. OpenCV 스레드는 1로 고정합니다. 실제 버전은 `pip freeze`도 함께 보관하세요.

## 8. 1주차 실습 진행

1. 전체 `audit` → 오류 목록 검수 → 기대 시점·물리적 시점 대응표 기록.
2. 공통 개발 제품 20개 선정 → 모든 시점 오버레이를 수동 검수. `figures/07_*`는 대표 6개까지만 자동 출력하므로 나머지는 노트북의 `figures()`에 넘기는 표본을 바꾸거나 직접 확인.
3. 두 backend로 같은 표본 실행 → parity PASS와 불일치 원인 기록.
4. 전체 개발 분할 분석 → 작은 결함 소실·희소 결함·시점 편차 확인.
5. `decisions.md`에 근거 CSV/그림과 후속 실험을 적고 모델팀에 인수.

초점 지표는 촬영 초점뿐 아니라 표면 질감/노이즈/해상도에도 영향을 받습니다. 밝기·초점 숫자만으로 자동 불량 판정을 하지 않습니다. 2D 카메라 위치 지도는 category/view별로 분리하며 여러 카메라의 좌표를 같은 물리 위치로 합치지 않습니다.

## 9. 검증 범위와 한계

제작 환경에서 합성 배열 계약 테스트, 전체 합성 파이프라인, 양쪽 parity와 노트북의 모든 코드 셀을 IPython에서 순서대로 실행해 검증했습니다. 기록은 `validation.txt`, 예제 결과는 `sample_results/`에 있습니다. **실제 Real-IAD 이미지·실제 배포 JSON은 첨부되지 않아 실제 릴리스에 대한 실행 검증은 하지 못했습니다.** JSON 구조가 다르면 명시적 CSV 어댑터를 사용하세요. GAN 학습·모델 학습·에이전트 구현은 후속 장의 범위이며 이 데이터 분석 코드셋에는 포함하지 않습니다.

노트북 코드 셀 재검증(노트북 의존성 설치 후): `python validate_notebook.py`. 이는 Jupyter 화면/커널 전송 계층의 검증과 구분됩니다.
