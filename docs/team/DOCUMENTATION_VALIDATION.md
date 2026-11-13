# Fork 협업 문서 검증 기록

확인일: 2026-11-13. 이번 범위는 README/팀 협업·모델 시작 절차·PR 템플릿이다. 코드 디렉터리 이동, 새 모델 실행, 기존 Crop 변경은 하지 않았다.

## 실행 및 결과

| 항목 | 결과 | 범위/제한 |
|---|---|---|
| 원본 GitHub URL/main | VERIFIED | 공개 저장소 화면 main과 로컬 main 확인. 원격 설정 변경 없음 |
| 개인 Fork/인증 | UNVERIFIED | 팀원 계정 추측하지 않음. Clone/로그인/Push/PR/Merge 미실행 |
| uv sync --locked | VERIFIED | 설치 확인 성공. uv.lock SHA 변경 없음 |
| Python/uv | VERIFIED | Python3.12.14, uv0.12.8 |
| 환경 dummy | VERIFIED | CPU 텐서/NMS/OpenCV/import, failed=[] |
| pytest | VERIFIED | 143 passed, 경고1. 로컬HTTP 차단 환경의 실패 후 허용 환경에서 재실행 통과 |
| 온보딩 실제 로더 예제 | VERIFIED | v2, 실제1제품5장. float32, (3,256,256), 배치(1,5,3,256,256), C1〜C5 순 |
| 상대 링크 | VERIFIED | 최초 README+7개 팀 문서+템플릿의79개 검사, 깨진 링크0. 이후 이 기록 링크도 추가 확인 |
| Bash 블록 | VERIFIED_SYNTAX_ONLY | 최초37블록 bash -n 통과. ID 자리표시자 치환 후 검사. 모든 Git 작업을 실제 실행했다는 뜻 아님 |
| setup.sh | VERIFIED_SYNTAX_ONLY | bash -n 통과. 이번에는 setup 자체를 다시 실행하지 않고 구성 단계별 검사 |
| git diff --check | VERIFIED | 공백 오류 없음 |
| 원본 Manifest/승인Ledger/lock 보호 | VERIFIED | 문서 작업 전후6파일 SHA 동일 |
| 원본 JPG/PNG | 쓰기 미수행 | 마스크43개·실제5장 읽기 확인. 이번에 전체 원본 해시를 다시 계산하지 않음 |
| 12모델 학습/추가Clone | NOT_RUN | 기존 고정 소스 근거를 문서에 연결. 실런타임 통합은 UNVERIFIED |
| 새 Python 설치/팀원 cold install | NOT_RUN | 기존 환경 확인. 팀원 설치 성공으로 일반화 금지 |
| 전체 데이터 CLI 재분석 | NOT_RUN | help와 경로 확인. 해상도 전수/전체Crop 재실행 없음 |

## 실제 재검수 반영 상태

이번에는 사용자 보고만으로 완료 판단하지 않고 승인 Ledger와 v2를 읽었다.

- 재검수43/43 완료, v1 대비 좌표43개 변경.
- v2 151,050행, 중복image_id0, 좌표오류0, 완전한 선언제품30,210그룹.
- 최신 Crop 승인1,594건과 v2 좌표 불일치0.
- 변경43장 마스크를 실제 읽어 결함픽셀 보존율 모두100% 확인.
- v2의 모든 이미지/타깃을 다시 디코딩한 것은 아님. 학습적격 계약과 hash 고정은 다음 검증 단계.

기존 상세 검증 출력은 덮어쓰지 않고 `outputs/team_collaboration_docs_20261113_v1/`에 이번 문서 검사와 재검수 확인을 별도 기록했다. 이 outputs는 Git 제외 대상이다.

## 문서 파일과 보존

- README: Fork 시작, 현재지점, 매일 Git 표, 기존 분석 링크 보존.
- team/CONTRIBUTING, GITHUB_FORK_WORKFLOW, MAINTAINER_GUIDE, ONBOARDING_CHECKLIST, TROUBLESHOOTING, PROJECT_STATUS, MODEL_EXPERIMENT_WORKFLOW, 이 검증 기록.
- `.github/pull_request_template.md`의 기존 내용을 확장해 요청한 `.github/PULL_REQUEST_TEMPLATE.md`로 이름을 통일했다. Windows 체크아웃의 대소문자 중복을 피하기 위해 두 파일을 동시에 두지 않았다. 아직 Stage하지 않아 Git status에는 이전 경로 D와 새 경로 ??로 보일 수 있다.
- 기존 초보 Git/협업/온보딩 문서는 유지하고 새 Fork 안내 링크만 앞에 덧붙였다.
- `.gitignore`는 기존 규칙을 읽고 사용했다. 이번 작업에서 규칙을 더 추가하거나 기존 산출물을 강제로 추적하지 않았다. git ls-files로 확인한 데이터/outputs/가중치/.env 추적은 없었다. 전체 공개 후보 내용의 비밀·권리 검토는 관리자 PR 검수에서 다시 해야 한다.

## 근거 링크

- [프로젝트 상태](PROJECT_STATUS.md), [모델 시작 단계](MODEL_EXPERIMENT_WORKFLOW.md), [관리자 배포](MAINTAINER_GUIDE.md)
- [GitHub Fork 원격 공식 안내](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/configuring-a-remote-repository-for-a-fork)
- [GitHub 인증 공식 안내](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git?platform=linux)
- [uv 설치 공식 안내](https://docs.astral.sh/uv/getting-started/installation/)
