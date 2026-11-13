# 공통 실험 인프라 GitHub 배포 검증

검증일: 2026-11-13. 배포 기준 HEAD는 `8ee73b4`이며 시작 시 로컬 `main`과 원격 `origin/main`이 같았다. 원격 URL은 `https://github.com/whrjsdnr/MV.git`이다. 이 문서는 **Push 전 검증 기록**이다. 실제 배포 Commit은 GitHub main 이력에서 확인하며, Push 후 원격 일치와 새 Clone 결과는 작업 완료 보고에 별도로 기록한다.

## 배포 범위

| Commit 단위 | 포함 파일 |
|---|---|
| A: 공통 실험 코드 | `mv_analysis/experiments/` 13개 모듈, `scripts/experiments/` 4개 CLI, `configs/experiments/model_registry.json`, `tests/test_experiment_infrastructure.py` |
| B: 모델 계약 | `models/README.md`, 12개 모델별 계약 문서 5개씩과 미구현 `integration.py` |
| C: 문서 및 최소 예제 | README, 실험 규약, 팀원 분담·진행·실험 절차, PR 템플릿, 가중치 제외 규칙, 검증 기록, 합성 보고서 발췌 2개·그래프 6개·출처 JSON |

A의 모델 Registry는 Recorder와 합성 실행에 필요한 공통 설정이다. 테스트 중 모델별 미구현 인터페이스 검사는 B의 12개 작업 영역까지 포함한 최종 배포 상태에서 수행한다. 모델 학습 구현은 추가하지 않는다.

전체 합성 예제 약 2.5MB 대신 문서 이해에 필요한 발췌 9개 파일, **241,988 bytes**만 선별했다. 각 PNG의 원본 출처·크기·SHA-256은 [ARTIFACTS.json](release_examples/ARTIFACTS.json)에 있다. 출처 경로는 로컬 생성 기록이며 해당 중간 파일 전체를 배포한다는 의미가 아니다.

## 실제 검증 결과

| 검사 | 결과 |
|---|---|
| `uv run --locked pytest -q` | **185 passed, 1 warning**, 223.14초. 테스트 삭제·Skip 없음 |
| 최초 제한 샌드박스 실행 | 176 passed, 1 failed, 8 errors. 모두 로컬 HTTP 소켓 생성의 `PermissionError` |
| 허용된 환경에서 재실행 | 동일 전체 테스트 185개 통과. 실제 승인 Ledger 대신 임시 데이터를 사용 |
| 공통 API Import | Recorder·이상탐지·검출 평가기·Benchmark·보고서/비교 함수 Import 성공, Registry 12종 확인 |
| 신규 합성 Smoke | 12개 Run 생성, 모두 **SYNTHETIC / PARTIAL / training_executed=False** |
| 보고서·비교 CLI | 새 Markdown 버전 생성 성공, 기본 비교에서 합성 제외 확인, 명시적 합성 비교 생성 성공 |
| Smoke 산출물 | PNG 309개 파일 무결성 및 Markdown 이미지 링크 310개 확인, 깨진 링크 0 |
| 배포 문서 | 선별 배포 문서의 상대 링크 158개·Bash 블록 20개 검사, 누락 파일·Anchor·문법 오류 0 |
| 모델별 TODO | 12개 모델의 `build_model`이 명시적으로 `NotImplementedError`를 발생시키는 테스트 통과 |
| 기록·평가·시각화 | Recorder 복구, NaN/Inf, Validation Threshold, AUROC/AP/AUPRO, COCO mAP, FP/FN, 좌표 복원, 그래프·보고서 링크 테스트 통과 |
| 기존 데이터 보호 | 로더 6개·Crop 기하·uv.lock·Manifest 3개·승인 Ledger 2개의 총 13개 SHA-256 일치 |
| 공유 안전성 | 선별 후보의 크기·확장자·개인 경로·토큰/키 패턴 검사. 가중치·원본·승인 기록은 Stage 대상에서 제외 |

기존 경고 1개는 NumPy timedelta의 generic 단위 사용 중단 경고다. 샌드박스 실패를 테스트 성공으로 처리하지 않았으며 권한 제한을 해소한 환경에서 전체를 다시 실행했다.

합성 검사 원본은 로컬 `outputs/experiments/SYNTHETIC_RELEASE_CHECK_20261113_v1/`에 보관한다. 배포용 보고서는 이전에 검증한 합성 Run의 발췌이며 새 Smoke와 같은 고정 합성 지표를 사용한다. 지연 시간은 CPU의 작은 Conv 연산으로 인프라를 검사한 값일 뿐 공식 12개 모델의 속도가 아니다.

## 제외 및 보존

- 원본 Real-IAD JPG/PNG, Canonical CSV 원본, 제품 GT·Crop 승인 Ledger, 개인 데이터 경로, `.env`, 인증 정보.
- 실제 모델 가중치·체크포인트·메모리 뱅크·검색 인덱스, `.venv`, 캐시, 대용량 학습 결과.
- `outputs/experiments/` 전체 Run·예측 배열·중간 산출물.
- `reports/experiments/examples/`, 기존 비교 보고서와 그래프 묶음, 이전 미추적 분석 보고서. 로컬에 그대로 보존하고 이번 Commit에는 넣지 않는다.

GitHub 제출은 추론/연결 코드·설정·보고서·공유 가능한 그래프다. 가중치는 별도 수령하고 파일명·크기·SHA-256·수령 절차만 문서화한다. 공유 권한이 없는 원본 이미지와 비밀 URL은 제출하지 않는다. 비밀정보 패턴 검사는 수동 공유 검토를 대신하지 않는다.

## 팀원 재현

기존 작업을 먼저 Commit하거나 보관한 뒤, MV 루트에서 원격과 브랜치를 확인한다. `origin`은 개인 Fork, `upstream`은 `whrjsdnr/MV`여야 한다.

```bash
git status
git fetch upstream
git switch main
git merge --ff-only upstream/main
git push origin main
uv sync --locked
uv run --locked pytest -q
uv run --locked python scripts/experiments/smoke_test_reporting.py
```

`--ff-only`가 실패하면 이력 분기를 확인하고 [Fork 가이드](../../docs/team/GITHUB_FORK_WORKFLOW.md)를 따른다. 강제 Push·Reset으로 해결하지 않는다. 합성 Smoke는 외부 데이터셋이나 가중치가 필요 없다. 로컬 테스트 서버 생성을 허용하는 실행 환경이 필요하다.

## 미검증 범위

실제 모델 생성·학습·Fine-tuning·공식 전처리 연결·실제 GPU Benchmark는 실행하지 않았다. 팀원별 GPU/드라이버 환경, 인터넷 캐시 없는 최초 설치, 실제 가중치 수령·로딩도 별도 검증 대상이다. Pixel AUROC/AP/AUPRO는 [실험 규약](../../docs/experiments/EXPERIMENT_PROTOCOL.md)에 정의한 근사이며 실제 모델 성능 증거가 아니다.

[이상탐지 최소 예제](release_examples/SYNTHETIC_ANOMALY.md) · [객체탐지 최소 예제](release_examples/SYNTHETIC_DETECTION.md) · [이전 구현 검증 기록](INFRASTRUCTURE_VALIDATION.md)
