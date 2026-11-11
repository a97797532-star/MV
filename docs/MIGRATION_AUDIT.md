# Windows → WSL2 Ubuntu 이전 감사

조사일: 2026-11-11. 원본 Windows 문서 `ENVIRONMENT_SETUP.md`, `ENVIRONMENT_VALIDATION.md`, `MODEL_COMPATIBILITY.md`는 수정하지 않았다.

## 실제 발견 상태

- 로컬 Git main의 기존 커밋은 `0924e40 Add Ubuntu project gitignore`, 추적 파일은 `.gitignore` 한 개였다. 원격 URL은 `https://github.com/whrjsdnr/MV.git`이다. 원격 접근 권한이나 원격 최신 내용은 확인되지 않았다.
- 초기 미추적 파일: `.env.example`, 위 Windows 문서 3개, `pyproject.toml`, `uv.lock`. `.env`는 무시 대상이며 내용은 출력하지 않았다.
- 요청된 README, AGENTS.md, scripts/validate_environment.py, 분석 Python, Notebook, 모델 소스, 테스트, Windows CSV/JSON/NPY/PNG 결과는 이 체크아웃에 없었다. 기존 소스 재사용·split 보존·535행 비교표 재현·Windows 히트맵 비교를 완료했다고 주장할 수 없다. 이 초기 판단은 Ubuntu 체크아웃만 조사한 결과이며 아래 추가 조사로 갱신한다.
- Windows 검증 문서는 Python 3.12.14, 설치 실패 및 33개 검사 실패를 기록한다. 문서의 “uv.lock 없음”은 과거 기록이다. 현재는 Windows 전용 uv.lock이 실제로 있다.
- pyproject의 `environments`가 win32/AMD64만 허용하고 잠금 wheel도 Windows 중심이었다. 첫 `uv sync --locked`는 플랫폼 불일치로 실패했다. Python 제한은 >=3.12,<3.13이다.
- 기존 Python 경로 하드코딩은 검사할 소스가 없었다. Windows 문서의 PowerShell 경로 예시는 역사 기록으로 유지했다. 새 코드는 pathlib, 환경변수/CLI로 경로를 받는다.

## 보존 및 수정

기존 설정을 `docs/archive/pyproject.windows.toml`, `docs/archive/uv.windows.lock`에 보존한 후 Linux x86_64와 Windows AMD64를 지원하도록 범위를 확장했다. `uv lock`은 upgrade 옵션 없이 수행했다. 기존 잠금 패키지 버전 변경 0건이며 pytest·Jupyter 추가에 따른 새 패키지는 `reports/lock_comparison.json`에 기록한다. CPU torch/torchvision index를 유지한다. 공식 근거: [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).

초기 Ubuntu 체크아웃에는 모델별 독립 환경이 없었으며, 아래 Windows 원본 추가 조사에서 정의 파일을 찾아 읽기 전용으로 보존했다. Windows 모델 호환성 문서는 보존한다. 루트 PyTorch 검증은 12종 모델 실행 검증이 아니다. CUDA는 별도 환경에서 확인하며 루트 CPU lock을 임의로 변경하지 않는다.

## 통합 구조

`mv_analysis/core.py`: 파일명·메타데이터·분할·마스크 검증·기본 지표. `stages.py`: 밝기·Train NG 위치·8연결 박스·원본 JPG 해상도 비교. `cli.py`: 단계 제어와 출력 보호. `report.py`: 실제 결과 기반 보고서. 새 Notebook은 CLI/모듈을 호출하고 알고리즘을 복제하지 않는다.

데이터가 확인되기 전 threshold를 가정하지 않는다. 전체 선택 마스크의 단일 채널 uint8 및 {0,255}/{0,1} 인코딩을 확인했을 때만 nonzero 정책을 도출한다. 다른 값은 실행 중단 사유다. 이 검사는 픽셀 인코딩 검증이며 주석 의미의 타당성까지 증명하지 않는다.

## 데이터·Git 안전성

로컬 초기 목록: 30품목, JPG 151,050, PNG 51,329, 부가 Zone.Identifier 202,379, 이미지 합계 58,791,659,189 bytes, 0바이트 이미지 0. 과거 참고보다 JPG +4,990, PNG +1,214. 규모 차이의 원인은 Windows manifest가 없어 미확정이다. 복사 완료 여부도 파일 수만으로 확정하지 않는다. 원본 이동·수정·삭제는 수행하지 않는다.

`.gitignore`에 dataset/outputs/가중치/.env가 이미 있으며 실제 경로가 check-ignore에 걸리는 것을 확인했다. 기존 `.uv_cache/`와 실제 `.uv-cache/`가 달라 후자를 추가했다. 기존 Git에는 데이터·가중치·키가 추적되지 않았다. 새 결과는 outputs에 보관한다. 보고서와 교육 문서는 Git 후보이며 결과 CSV/NPY/이미지와 실행 체크포인트는 업로드하지 않는다. 마지막 업로드 후보 검사 결과는 별도 보고서에 기록한다.


## 최신 실행 정책 정정

회색조 PNG를 파일 손상으로 간주하지 않는다. mask-audit는 파일 decode/짝 크기 검증과 threshold 확정을 구분한다. 정확한 이진 인코딩이면 자동 정책을 도출할 수 있으나, 회색조면 mask-thresholds의 비교/overlay 검수 결과를 남기고 최종 정책을 보류한다. 이 경우 run-all은 밝기·해상도를 계속 실행하고 mask_stages_deferred.json에 위치 단계 보류를 남긴다. 미주석 NG는 개수 차이 때문에 실행을 차단하지 않는다. 현재 확정 수는 OK 72,840 / NG 78,210 / 위치 정답 NG 51,329 / 미제공 NG 26,881이다. fire_hood의 HS/QS 충돌 10장은 영상 분석에 포함하되 유형 라벨은 UNRESOLVED로 기록한다.


## 회색조 마스크 정책 검증 완료 (2026-11-11)

실제 30품목×112 품목/유형 조합에서 336장, 6개 임계값을 비교했고 overlay 30개를 만들었다. 전체 PNG 51,329장의 decode/짝 크기 검증은 0오류였다. [공식 Real-IAD EvalPerPixelAUC](https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249)의 양수 마스크 처리와 실제 경계 수축/분절 관측을 함께 근거로, 본 프로젝트 위치 분석은 grayscale >0, 면적 필터 없음으로 고정했다. 이는 모든 결함 경계의 의미적 정확도 증명이 아니다. 초기 보류 상태는 이 검증으로 갱신되었다. 원본 회색조 마스크는 그대로 보존한다.

다른 실행에서 재현하려면 전체 metadata/decode 실행의 mask-audit와 mask-thresholds 결과를 먼저 만든 뒤 새 공간 분석 실행을 만든다. 아래 경로는 본인 실제 출력으로 바꾼다.

```bash
uv run --locked python -m mv_analysis.cli --output outputs/full-metadata --resume mask-audit
uv run --locked python -m mv_analysis.cli --output outputs/full-metadata --resume mask-thresholds
uv run --locked python scripts/continue_image_analysis.py --metadata-run outputs/full-metadata --output outputs/spatial-analysis
uv run --locked python scripts/approve_mask_policy.py --integrity outputs/full-metadata --study outputs/full-metadata --run outputs/spatial-analysis
uv run --locked python -m mv_analysis.cli --output outputs/spatial-analysis --resume heatmap
uv run --locked python -m mv_analysis.cli --output outputs/spatial-analysis --resume bbox
```

최초 전체 metadata는 validate-data 명령으로 끝나야 한다. 승인 스크립트는 전체 무결성/30품목 민감도 비교 증거가 없거나 기존 policy가 있으면 실패한다. 정책 파일을 덮어쓰지 않는다. run-all은 미검증 회색조를 자동 threshold 처리하지 않으므로 image 단계 완료 후 위 검증/위치 단계를 이어서 실행한다. root/limit/class-policy/lock/source 설정을 동일하게 유지한다.


## Windows 참고 수량 차이의 추가 근거

현재 u_block은 JPG 4,990장·PNG 1,214장이며 과거 참고와의 차이(+4,990/+1,214)에 정확히 일치한다. 비교 조합은 전체 560개 중 u_block 20개, UNRESOLVED 5개다. 이는 기존 약 535행과의 구성 차이를 조사할 근거이지만 Windows manifest/CSV가 없어 u_block 누락 또는 범위 제외를 확정하지 않는다. 수치 근거는 reports/WINDOWS_COUNT_DIFFERENCE_EVIDENCE.json과 현재 전체 메타데이터다.


## 마운트된 Windows 원본 추가 조사 — 초기 판단 갱신

`/mnt/c/Users/user1/jogeonug/MV`에 보존된 원본을 읽기 전용으로 조사했다. OpenCV/ScikitImage 분석 패키지, 기존 Notebook, scripts, configs, 모델별 environments 정의 파일을 확인했다. 실제 12종 모델 구현은 찾지 못했다. 선택된 소스·설정·Notebook 60개를 `legacy/windows_snapshot/`에 복사했고 원본은 수정하지 않았다. Linux 복사본 Notebook 출력만 제거했다. 파일별 원본 SHA256과 복사 방식은 [인벤토리](../reports/WINDOWS_SOURCE_INVENTORY.json)에 있다. 원본 데이터·대용량 분석 결과·가중치·가상환경은 복사하지 않았다. 역사적 Windows 경로는 보존본에 남겨 두고 새 공식 CLI는 환경변수와 pathlib로 실행한다.

실제 저장된 Windows 최종 CSV는 JPG 151,050장·PNG 51,329장으로 현재 Ubuntu 파일 수와 같고 u_block도 포함한다. 과거 참고 146,060/50,115와의 차이 원인은 여전히 미확정이며, 최신 Windows 결과와 Ubuntu가 서로 다른 규모라고 표현하지 않는다. 기존 brightness 비교표는 555행이며 새 결과의 560행에는 유형 충돌을 보존한 UNRESOLVED 5개 조합이 추가된다.

기존 실행 Notebook Cell28의 제품 키(category/quality/defect/serial), seed42의 두 번 train_test_split을 재사용해 151,050장 모두 기존 split과 동일하게 재현했다. Train 105,735 / Validation 22,655 / Test 22,660, 제품 그룹 30,210이다. [검증](../reports/WINDOWS_SPLIT_REPRODUCTION.json). 초기 category/serial hash 분할 결과는 탐색 결과로 보존하고, 기존 분할 기반 통계/히트맵을 별도 `outputs/windows_preserved_20261111_v1`에 생성한다. category/serial은 다른 상태/유형 폴더에서 재사용될 수 있으므로 이 alias만으로 동일 물리 제품이라고 확정하지 않는다.

기존 OpenCV 8연결 backend와 1픽셀도 보존하는 coursework.coarse_occupancy를 새 모듈에서 재사용한다. canonical occupancy_known=영상별 cell presence 합/n_known, occupancy_positive=합/n_positive이며 분모 0은 NaN이다. 초기 면적 기반 area-v1은 별도 진단으로 보존한다. 해상도 계산 함수는 현재 실행 중 변경하지 않았다. 기존 Windows 해상도 지표는 LINEAR 축소, 경계 ±1픽셀 허용, 절댓값 에너지 등으로 새 AREA/정확 위치/제곱 에너지와 정의가 다르므로 같은 이름만으로 OS 차이라고 해석하지 않는다.


추가 역사 검증: Windows .ipynb_checkpoints의 실제29품목/JPG146,060/PNG50,115/밝기535행과 최신30품목/JPG151,050/PNG51,329/밝기555행을 전수 비교했다. 추가된 상대 경로는 전부u_block이며 제거0개다. 참조 수치와 같은 규모의 보존 중간 결과를 확인했으므로 단순 수량 우연의 후보를 넘어 이 두 결과 사이의 범위 차이는 확인됐다. 제외한 이유나 인용한 참고치의 정확한 출처 연결은 별도 미확정이다. reports/WINDOWS_HISTORICAL_CHECKPOINT_COMPARISON.json 및 outputs/windows_checkpoint_comparison_20261111_v1/comparison.json을 참조한다.
