# 4명 협업 규칙

main은 검증된 코드만 유지한다. 모든 팀원은 개인 작업 브랜치를 만들고 기능 단위로 commit, push, PR을 작성한다. 가능하면 작성자 외 1명이 리뷰하고 main에 합친다. 테스트가 실패한 PR은 원인과 영향이 합의되기 전 merge하지 않는다. 저장소 관리자가 main 보호/PR 필수/리뷰 1명 설정을 검토한다. 이 작업에서 GitHub 설정을 변경하지 않았다.

```text
main
feature/metadata-analysis
feature/brightness-analysis
feature/bbox-labeling
feature/resolution-analysis
docs/git-beginner-guide
fix/linux-path
```

동일 기능을 두 명이 다루면 담당자 이름을 추가한다. 동시에 같은 파일을 고칠 작업은 PR 범위를 먼저 합의한다. 통합 분석 stages.py는 공통 파일이므로 겹치는 작업을 미리 조율한다. 역할 예시는 1명 환경/통합, 1명 metadata/밝기, 1명 mask/box, 1명 해상도/검수이며 실제 담당 배정은 팀이 결정한다. Git 초보 두 명은 첫 PR을 숙련자와 짝으로 진행한다.

모델 소스는 향후 models/ 또는 독립 environments/에서 관리하고 분석 모듈과 분리한다. 현재 모델 소스와 독립 환경이 없으므로 설치 완료로 취급하지 않는다. 환경 변경 PR에는 pyproject와 lock을 함께 검토하고 불필요한 upgrade를 하지 않는다. Python 3.12/CPU 기본 환경과 CUDA 실험을 분리한다.

데이터셋·가중치·.env·API 키·대용량 CSV/NPY/PNG는 Git에 넣지 않는다. 분석 결과는 outputs의 로컬 실행 디렉터리에 두고, 작은 텍스트 보고서와 재현 명령만 리뷰한다. 원본 경로나 개인 식별자가 있는 로그를 외부 공개하기 전 확인한다. README·설치·분석 가이드를 코드와 함께 갱신한다. 기존 결과를 덮어쓰지 않는다.

## 작업 시작/종료

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c feature/작업-본인
# 편집 후
git add 수정파일1 수정파일2
git diff --cached
uv run --locked pytest -q
git commit -m "Describe the behavior change"
# 팀원이 직접 실행:
git push -u origin feature/작업-본인
```

PR 설명은 `.github/pull_request_template.md`를 채우고 테스트 실제 결과와 입력 범위를 적는다. 리뷰어는 split 누수·train 전용 통계·마스크 정책·좌표·원본 보호·수치 근거를 확인한다. main으로 합친 후 각자 pull한다. 작업 중 수정이 있으면 초보자 가이드 J/K 절을 먼저 따른다.

## 비공개 저장소와 인증

저장소 소유자가 GitHub 저장소 → Settings → Collaborators(조직 저장소는 Collaborators and teams) → Add people에서 각 팀원의 GitHub 계정을 초대한다. 팀원은 초대 알림/이메일에서 수락하고 로그인한 브라우저로 저장소를 연다. 관리자 메뉴명/초대 권한은 계정 유형에 따라 다를 수 있다. 조직 정책/SSO가 있으면 관리자 지침을 따른다. 현재 4명 초대 여부와 권한은 미검증이다.

HTTPS는 GitHub 비밀번호 대신 공식 credential 로그인 또는 적절히 제한된 token, SSH는 등록한 본인 키를 사용한다. 커밋 user.name/email은 로그인 수단이 아니다. 토큰을 remote URL에 넣거나 문서·스크립트·로그에 출력하지 않는다. [GitHub 공식 인증](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)을 참고한다.

## 업로드 전 확인

```bash
git status --short
git diff --cached --stat
git diff --cached
git ls-files dataset outputs
```

첫 세 명령으로 commit 후보를 확인하고 마지막 명령에 데이터/결과 파일이 나오면 추적 여부를 조사한다. ignore 검증과 비밀정보 검사는 push 직전에 다시 수행한다. GitHub push는 사용자가 직접 한다.
