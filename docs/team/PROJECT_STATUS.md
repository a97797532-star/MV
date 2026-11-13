# MV 현재 진행 상태와 다음 작업

확인일: **2026-11-13 (KST)**. 새 팀원은 이 문서 → [Fork 협업](GITHUB_FORK_WORKFLOW.md) → [설치·로더 확인](ONBOARDING_CHECKLIST.md) → [모델 실험 시작 절차](MODEL_EXPERIMENT_WORKFLOW.md) 순서로 읽는다. 이 문서는 로컬 작업 공간에서 확인한 상태다. 공통 소스·검증 코드·테스트는 이번 배포 Commit에 포함했다. 비공개 분석 결과까지 모두 GitHub에 포함되는 것은 아니며 원격 반영은 GitHub main의 Commit으로 확인한다.

상태 용어: **VERIFIED**=명시한 범위 실제 확인, **UNVERIFIED**=구현/자료는 있으나 해당 검증 미완료, **NOT_IMPLEMENTED/NOT_RUN**=아직 구현/실행 안 함. 과거 보고서는 해당 시점의 증거로 보존하고 최신 사항은 아래를 따른다.

## 지금 어디까지 완료됐나

| 영역 | 실제 완료 범위 | 상태 및 남은 일 | 근거 |
|---|---|---|---|
| Ubuntu/Python/uv | WSL2, Python3.12.14, uv0.12.8, CPU torch2.15.0, locked sync 및 dummy CPU 검사 | VERIFIED: 이번 실행 failed=[]; 다른 팀원 설치는 미검증 | scripts/validate_environment.py, outputs/environment/20261113T004142213231Z/validation.json |
| 전체 데이터 | JPG151,050, OK72,840/NG78,210, 마스크51,329, 30품목, 선언제품30,210 | 이전 v1 기준 JPG/PNG 전수 실제 디코딩 오류0. 물리 제품 동일성은 독립 검증 아님 | reports/FINAL_PREPROCESSING_VALIDATION.md |
| 분석 | 메타데이터·밝기·배경/제품밝기·해상도·마스크/BBox·Crop 비교 | 기존 결과 보존. 자동 제품 분할 품질 조건/선택편향 등 한계를 보고서와 함께 읽음 | reports/DATA_ANALYSIS_MASTER_REPORT.md, reports/ANALYSIS_EVIDENCE_INDEX.md |
| 제품 GT | 사람 승인 제품 BBox600개 | Crop 승인과 별개, 자동 제안의 GT 승격 없음 | outputs/object_aware_crop_v1/review/human_approved_gt.jsonl |
| Crop 좌표 | 전체151,050행 생성 및 수동 승인 반영 v1/v2 | 원본 Crop 이미지 전수 생성은 하지 않음 | outputs/adaptive_crop_full_v1/ |
| 이번 43장 재검수 | 검수 진행43/43, v2에서 좌표43개 변경, 최신 승인1,594건 모두 좌표 일치 | VERIFIED: 이번 변경 43장 마스크 픽셀 보존100%, 좌표 오류0, 중복ID0 | outputs/team_collaboration_docs_20261113_v1/reviewed_v2_documentation_check.json |
| 클래스 충돌 | 폴더HS/파일명QS 충돌10장 → 사용자 지시로QS | 마스크7장 BBox 복구/실제 로더 통과, 마스크없는3장 MISSING 유지 | reports/FILENAME_CLASS_RESOLUTION.md |
| 공통 로더 | Single/Five-view, 좌표/마스크/BBox 변환, 결측/검출 적격 계약, collate | VERIFIED: 합성 및 기존 실제315장 Smoke/12Adapter360입력 사례. 새 v2 전체 타깃 계약/eligibility 독립 산출은 미완료 | reports/DATA_LOADER_IMPLEMENTATION.md |
| 12모델 Adapter | 독립 입력 변환 구현 | 모델 실제 forward/학습통합은 UNVERIFIED. 이중CenterCrop/Normalize 주의 | mv_analysis/data/adapters.py, reports/MODEL_INPUT_REQUIREMENTS.md |
| 모델 학습 | 공식 소스 조사·커밋·입력 근거 수집 | NOT_RUN: 12모델 비교 학습/평가/선정 미실시. 과거 YOLO Crop 추론 실험과 구분 | MODEL_EXPERIMENT_WORKFLOW.md |
| 저장소 표준화 | 분석/로더 실제 패키지는 mv_analysis/, scripts/, tests/ | NOT_IMPLEMENTED: models/·src/·통합학습train.py 없음. 폴더 이동은 이번에 하지 않음 | 실제 디렉터리 확인 |
| Fork 공유 | README/팀 문서/PR 템플릿 추가 | 로컬 문서 VERIFIED. 각 팀원의 인증/Push/PR 실습과 관리자 보호설정은 UNVERIFIED | 이 문서 묶음 |

### 현재 Crop v2 식별자

```text
outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv
SHA-256 d1c13cae3fc352f457cb22f9955280e0ce140827a449465d5e05519fd6c9073d
151,050행 / 30,210 선언 제품 그룹 / 좌표 변경43행
정책 C(원본 전체):149,463 / HUMAN_CROP:1,587
최신 사람 Crop 승인:1,594 (원본 전체 승인 포함)
```

v1의 상세 전수 디코딩 결과는 [기존 최종 검증 보고서](../../reports/FINAL_PREPROCESSING_VALIDATION.md)에 있다. 이번 작업에서는 **v2 전체 이미지 디코딩/모든 타깃 변환을 다시 실행하지 않았다**. 원본 좌표·그룹 무결성과 승인 대조, 바뀐43장 마스크 보존을 확인했다. 따라서 v1의 hash/eligibility 결과를 그대로 v2의 완료 증거라고 제출하지 않는다. v1 대비 새 v2에서 실제 클래스/마스크 계약을 확정한 학습 적격 테이블은 모델 학습 전 별도 고정해야 한다.

클래스 파생 파일은 `outputs/filename_class_resolution_v1/`다. 7장 클래스 오류를 해결한 v1 기반 전체 계약은 SUPERVISED_VALID51,295 / OK_NEGATIVE72,840 / MISSING_ANNOTATION26,881 / EMPTY_NG_REVIEW34다. 클래스 충돌 해결과 Crop v2 검증 버전은 서로 다른 버전 축이다.

## 팀원이 지금 할 수 있는 작업

1. Fork 동기화, CPU 환경 설치, 합성 테스트와 공통 로더 이해.
2. 관리자에게 승인된 데이터/Manifest/클래스 파일 묶음을 받고 로컬경로 매핑 Smoke Test.
3. 담당 모델 공식 소스와 고정 커밋/라이선스/환경 조사, 별도 환경 구축.
4. 실제 모델 Dataset/Trainer와 공통 로더의 연결 코드를 기능 브랜치에서 개발하고 PR 리뷰 요청.

[모델 실험 단계별 가이드](MODEL_EXPERIMENT_WORKFLOW.md)에 Clone→환경→로더→forward Smoke→Train→Validation→Test→결과 공유 조건을 적었다. 현재 없는 학습 명령을 이미 실행 가능한 것으로 취급하지 않는다.

## 학습 전 우선 해결/팀 결정

1. **Canonical 배포**: v2 및 annotation/BBox/classes 파일의 배포 권한·책임자·팀 제한 저장 위치·해시 목록 승인. Git Clone만으로 outputs 파일을 얻을 수 없다.
2. **v2 계약 확정**: 새 Manifest hash에 묶인 타깃/eligibility 검증 결과를 별도 버전에 생성. 이전 출력 덮어쓰기 금지.
3. **평가 독립성**: v1 기록에 Test의 주석 참조 수동Crop189건이 있었다. v2에서도 Test를 포함한 수정이 있으므로 평가 독립성을 자동 보장하지 않는다. 변경 근거/사용된 정답/평가 보고 방식을 팀이 결정한다.
4. **모델 통합**: 학습 엔트리포인트 경로 표준화, 모델별 격리환경, 실제 모델 forward, 손실/평가 라벨 계약 검증.
5. **전처리 실험 조건**: 공식추가CenterCrop을 끈 공통 입력 조건과 공식 baseline을 분리. 실제 성능 확인 전 최적 정책 확정 금지.
6. **협업 확인**: 4명 각자 설치·데이터 수령·로더 Smoke·Fork PR 실습 기록. 관리자 main 보호/리뷰 권한 설정은 수동으로 검토.

## 이번 문서 작업의 실행 검증

- `uv sync --locked`: 성공, lock 변경 없음.
- Python3.12.14, dummy CPU/OpenCV/import: 성공, failed=[].
- 전체pytest: **143 passed, 1 warning**. 제한 샌드박스에서 로컬소켓 테스트가 차단된 뒤, 로컬HTTP 허용 환경에서 다시 통과했다. 경고는 기존 NumPy timedelta 사용 중단 경고.
- 저장소 URL과 공개 GitHub 화면 기본 main 확인. 로컬 main도 확인했으나 origin/HEAD 캐시는 미설정. 팀원 개별 Fork 주소/권한은 추측하지 않았다.
- GitHub 인증/Clone/Push/PR/Merge, 새 Python 설치, 모델 Clone/설치/학습 명령은 이번 작업에서 실행하지 않았다.
- 원본 데이터/승인Ledger/기존Manifest/uv.lock은 문서 작업에서 수정하지 않았다.

기존 전체 진행 보고서: [분석 종합](../../reports/DATA_ANALYSIS_MASTER_REPORT.md), [로더 구현](../../reports/DATA_LOADER_IMPLEMENTATION.md), [클래스 해결](../../reports/FILENAME_CLASS_RESOLUTION.md). 일부 보고서의 대형근거파일/내부PDF는 Git에서 제외돼 로컬 관리자 환경에만 존재할 수 있다.

이번 README/협업 문서의 명령·링크·실제 로더 검증 범위는 [문서 검증 기록](DOCUMENTATION_VALIDATION.md)을 참고한다.

## 공통 코드 배포 업데이트

- 프로젝트 자체 소스133개에 한글 설명을 보강하고 신규/변경 코드를 목적별로 Commit했다.
- 별도 로컬 Clone의 새 가상환경에서 고정 의존성170개 설치, dummy 검증, 합성 Smoke, 전체145개 테스트를 통과했다. 기존 캐시 기반이며 인터넷 cold install과 팀원 개별 설치는 미검증이다.
- 새 명령: `uv run --locked python scripts/smoke_test_shared_data.py --synthetic`. 비공개 데이터가 없어도 실행할 수 있다.
- 전체 Canonical CSV/승인 Ledger/이미지/가중치는 Git 배포 대상에서 제외했다. [배포 검증 기록](../../reports/CODE_RELEASE_PREPARATION.md)과 [수령 안내](CODE_RELEASE.md)를 따른다.
- 사용자가 Push를 승인했다. 실제 원격 반영 여부는 GitHub main Commit을 확인한다.
