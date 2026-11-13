# 공통 코드 배포와 Canonical 파일 수령

이 문서의 코드는 Commit 준비 대상이다. GitHub 반영은 관리자가 Push한 뒤에만 완료된다. 팀원은 [Fork 동기화](GITHUB_FORK_WORKFLOW.md) 후 아래를 실행한다. 현재 배포 범위에는 12개 모델의 실제 학습 엔트리포인트가 없으며 공통 입력 Adapter만 제공한다.

## 새 Clone에서 데이터 없이 확인

WSL2 Ubuntu의 MV 루트에서:

```bash
uv python install 3.12
uv sync --locked
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked python scripts/smoke_test_shared_data.py --synthetic
uv run --locked pytest -q
```

순서대로 Python 확보, 고정 의존성 설치, CPU/import 검증, 임시 합성 데이터 로더 확인, 전체 회귀 테스트다. dummy의 failed=[], Smoke의 status=PASSED, pytest의 passed/종료0이 성공 기준이다. 합성 Smoke는 JPG/PNG를 임시 폴더에 만들고 종료 시 정리하며 원본 데이터·승인 Ledger·캐시 소스가 필요 없다. BBox/Mask 변환과 결측 NG/빈 NG 계약, `(2,5,3,256,256)` 배치 및 12개 Adapter를 확인한다. 실모델 forward/학습은 하지 않는다.

설치가 막히면 네트워크·플랫폼·디스크·wheel 오류를 구분하고 uv.lock을 임의로 재생성하지 않는다. 검사 실패 시 [문제 해결](TROUBLESHOOTING.md)을 따른다. 새 팀원의 cold install과 관리자의 캐시 기반 clean-checkout 검증은 다르다.

## 실데이터 확인

Canonical 파일은 **Git에 포함하지 않는다**. [배포 식별자](../../configs/data/canonical_manifest.release.json)의 상대 경로·크기·SHA-256을 관리자가 승인한 팀 내 제한 배포물과 비교한다. 실제 Crop CSV에는 개인 절대 경로와 검수 관련 필드가 있어 공개 권한 확인 없이 업로드하지 않는다. 전체 CSV 약113MiB는 소형 Manifest에 해당하지 않는다.

공유 코드는 [행 스키마](../../schemas/preprocessing_manifest.schema.json)와 실제 ManifestIndex 교차 필드 검증을 제공한다. 스키마만으로 중복·5시점·Split 누수 검사를 대체하지 않는다. 승인 Ledger는 실행용 배포물에 필수인 파일이 아니다. 원본 GT 승인과 Crop 승인 원장을 팀원에게 무조건 배포하지 않는다.

아래 네 파일과 원본 JPG/PNG를 적법하게 수령한 뒤, MV 루트에서 실제 경로를 지정한다.

```bash
export REALIAD_DATA_ROOT="/본인/Real-IAD/루트"
uv run --locked python scripts/smoke_test_shared_data.py \
  --manifest outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv \
  --annotations outputs/filename_class_resolution_v1/image_metadata_with_split.csv \
  --bboxes outputs/filename_class_resolution_v1/defect_bboxes.csv \
  --classes outputs/spatial_20261111_v7/classes.json \
  --data-root "$REALIAD_DATA_ROOT" --products 2
```

export는 현재 터미널의 경로만 설정한다. Smoke는 실제 최대2개 선언 제품의 전체5시점을 읽으며 저장 좌표를 변경하지 않는다. 경로가 다른 곳에 배포됐다면 인수를 변경한다. NG+MISSING을 정상으로 바꾸거나 파일 식별 검사를 자동 해제하지 않는다. `PASSED`는 이 표본의 입력 변환 성공이며 전체 실데이터·모델 학습 준비 완료 판정과 다르다.

기존 `smoke_test_data_loaders.py`와 `validate_final_preprocessing_decode.py`는 v1의 로컬 감사 체크포인트에 연결된 보존용 스크립트다. 완료된 outputs에 덮어쓰며 재실행하지 않는다. 새 팀원은 먼저 이 문서의 이식 가능한 Smoke를 사용한다. 새 v2 전체 타깃 계약/eligibility 고정은 별도 검증 단계다.

## 배포 범위와 제외 범위

- 포함: 공통 모듈, Crop/Mask/BBox 변환, 제품 검수 도구 소스·정적 UI, 검증 스크립트, 합성/회귀 테스트, 소형 스키마와 배포물 해시 식별자.
- 이미 추적: pyproject.toml, uv.lock, setup.sh, 기본 환경/데이터 검사 CLI. 변경하지 않은 파일에 중복 Commit을 만들지 않는다.
- 제외: 원본 이미지/마스크, 전체 CSV·Parquet·NPY, 승인 원장, 모델 가중치, 외부 모델 소스 캐시, 실험 결과 ZIP/PDF 및 내부 비교 이미지, .venv, .env/개인정보/키.
- 없음: 12개 모델 실학습 코드. 공식 소스 연결과 학습·평가는 [모델 실험 절차](MODEL_EXPERIMENT_WORKFLOW.md)를 따른다.

관리자는 [PR·배포 검토](MAINTAINER_GUIDE.md)와 [현재 진행 상태](PROJECT_STATUS.md)를 함께 확인한다. Push 전 검증과 실제 원격 반영을 구분한다.

## 한글 주석과 과거 체크포인트

이번 배포에서는 프로젝트 자체 소스에 한글 파일·함수·입력 안내를 보강했다. 외부 모델 소스와 Windows 보존본은 수정하지 않았다. 주석도 파일 SHA-256을 바꾸므로, 과거 분석의 소스 해시 검사를 무시하거나 기존 설정에 새 해시를 덮어쓰지 않는다. 원래 소스 사본과 변경 전후 해시는 관리자 로컬 `outputs/code_release_preparation_20261113_v1/`에 보존한다. 기존 체크포인트 재개는 원래 소스/설정 확인 후 별도 판단하며 새 팀원은 합성 Smoke부터 사용한다.

`scripts/publish_analysis_branch.py`는 과거 자동 배포 전용 코드로 Commit/Push를 수행할 수 있다. 팀원 기본 설치·검증 명령이 아니며 명시적 배포 승인 없이 실행하지 않는다. 이번 작업에서도 실행하지 않았다.
