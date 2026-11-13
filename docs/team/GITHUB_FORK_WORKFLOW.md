# GitHub Fork로 MV에 기여하기

처음 읽는 순서: [현재 진행 상태](PROJECT_STATUS.md) → 이 문서 → [설치 체크리스트](ONBOARDING_CHECKLIST.md). 모든 예시는 **WSL2 Ubuntu의 Bash**다. `origin`과 `upstream`은 GitHub의 특별한 권한이 아니라 로컬 원격 별칭이다. 관리자 PC의 origin은 원본일 수 있으므로 팀원 설정과 혼동하지 않는다.

## 저장소 관계와 용어

```text
                    원본 whrjsdnr/MV
                           │ Fork
               ┌───────────┼───────────┐
               ▼           ▼           ▼
             팀원 A       팀원 B       팀원 C
             개인 Fork    개인 Fork    개인 Fork
               │ Clone     │ Clone     │ Clone
               ▼           ▼           ▼
             로컬 PC      로컬 PC      로컬 PC
               │ Push      │ Push      │ Push
               └──→ 각자의 Fork 기능 브랜치
                           │ Pull Request
                           ▼
                 리뷰 후 원본 main에 Merge
```

| 용어 | MV에서의 의미 |
|---|---|
| Repository | 소스와 변경 이력이 있는 프로젝트 저장소 |
| Fork | GitHub 안에서 원본을 자기 계정의 저장소로 복사. PC에 파일이 생기는 작업은 아님 |
| Clone | 원격 저장소와 Git 이력을 PC의 새 폴더로 복제. Fork가 있어도 별도로 필요 |
| origin | 팀원이 Clone한 **개인 Fork**. 자신의 기능 브랜치를 Push하는 곳 |
| upstream | 팀 원본 `whrjsdnr/MV`. Fetch해서 최신 코드를 받는 곳 |
| Branch | 기능별 독립 변경 이력. 디렉터리가 복제되는 것은 아니며 현재 작업 파일이 전환됨 |
| Commit | Stage한 변경을 로컬 이력에 저장 |
| Push | 로컬 Commit을 지정한 GitHub 저장소/브랜치에 업로드 |
| Fetch | 원격 이력과 원격 추적 브랜치만 갱신. 현재 작업 파일을 합치지 않음 |
| Pull | Fetch와 현재 브랜치 통합을 함께 실행. 초보자는 아래 Fetch/Merge로 단계를 구분 |
| Pull Request(PR) | Fork의 기능 브랜치를 원본에 반영해 달라는 검토 요청 |
| Merge | 브랜치 변경을 합침. 프로젝트 관리자가 승인된 PR을 원본 main에 통합 |
| Conflict | 같은 위치를 서로 다르게 수정해 자동 통합이 안 되는 상태 |

Commit만 하면 PC 밖에 공유되지 않는다. 개인 Fork에 Push해도 원본에는 반영되지 않는다. **원본 반영은 PR → 리뷰 → 관리자 Merge** 순서다. 팀원은 `upstream`에 직접 Push하지 않는다. upstream에 push URL이 표시되어도 권한 부여나 직접 Push 지시가 아니다.

## 1. Git 설치·작성자·인증

처음 한 번 Ubuntu 터미널의 어느 디렉터리에서나 실행한다.

```bash
sudo apt update
sudo apt install git -y
git --version
git config --global user.name "본인 이름 또는 GitHub 표시명"
git config --global user.email "본인 GitHub 연결 이메일 또는 GitHub 제공 noreply 이메일"
git config --global --list
```

| 명령 | 목적/바뀌는 것 | 성공 확인 | 실패 시 |
|---|---|---|---|
| apt update / install | 패키지 목록 갱신/Git 설치 | git version 출력 | sudo 권한·인터넷·Ubuntu 저장소 확인 |
| git --version | 설치 확인, 변경 없음 | 버전 문자열 | 터미널 재실행/설치 경로 확인 |
| config user.name/email | 이후 Commit 작성자 저장 | --list의 이름/이메일 | 오타를 같은 config 명령으로 수정 |
| config --list | 설정 읽기 | 기대한 작성자 | 설정 전체를 공개 로그에 올리지 말고 필요한 항목만 확인 |

작성자 설정은 **GitHub 로그인과 별개**다. HTTPS 인증은 [GitHub CLI 또는 Git Credential Manager 공식 안내](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git?platform=linux)를 따른다. GitHub 계정 비밀번호를 HTTPS Git 비밀번호로 입력하는 방식은 사용하지 않는다.

GitHub CLI를 별도로 설치했다면 어느 폴더에서나 다음을 실행할 수 있다.

```bash
gh auth login
gh auth status
```

`GitHub.com → HTTPS → 브라우저 로그인`을 선택하고 Git 인증 설정 질문을 확인한다. status에 본인 계정/호스트가 나타나면 성공이다. gh가 없으면 [공식 설치 문서](https://cli.github.com/manual/installation)를 먼저 따른다. Windows GCM을 WSL Git에서 쓰는 경우에는 [공식 WSL 안내](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/wsl.md)에 맞춰 별도 연결해야 한다. 인증 실패 시 계정·Fork 소유자·조직 SSO/접근 권한을 확인한다. 비밀번호·토큰을 URL, 코드, 문서, 터미널 공유 로그에 넣지 않는다. SSH를 이미 쓰는 팀원은 기존 키 인증을 유지할 수 있다.

## 2. 이미 Fork한 팀원의 Clone

GitHub 프로필에서 본인 로그인 ID와 Fork `MV`가 있는지 확인한다. `<내-GitHub-ID>`를 **실제 ID로 치환한 뒤** 실행한다. 꺾쇠가 있는 예시를 그대로 Bash에 붙여 넣지 않는다.

```bash
# 프로젝트를 둘 상위 폴더. ~/projects는 원하면 바꿀 수 있다.
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/<내-GitHub-ID>/MV.git
cd MV
```

mkdir는 부모 폴더를 만들고, 첫 cd는 생성 위치를 정한다. clone은 그 아래 MV 폴더와 .git을 만들며 다운로드 진행 메시지가 나온다. 마지막 cd로 프로젝트 루트에 들어간다. 이미 MV가 있으면 다시 Clone하지 말고 기존 폴더에서 상태/원격을 확인한다. Repository not found는 URL·로그인·Fork 접근 권한을 확인한다.

```bash
# 이후 기본 실행 위치는 Clone한 MV 루트
git status
git branch
git remote -v
```

status에 `On branch main`, 새 Clone이면 `working tree clean`이 나타난다. branch의 `* main`은 현재 브랜치다. remote는 origin의 fetch/push URL을 보여 준다. 원본을 실수로 Clone했다면 즉시 Push하지 말고 [복구 가이드](TROUBLESHOOTING.md)의 원격 설정 절차를 확인한다.

먼저 `git remote -v`를 읽는다. **upstream이 없는 경우에만** 등록한다.

```bash
git remote add upstream https://github.com/whrjsdnr/MV.git
git remote -v
```

```text
origin    https://github.com/<내-GitHub-ID>/MV.git (fetch)
origin    https://github.com/<내-GitHub-ID>/MV.git (push)
upstream  https://github.com/whrjsdnr/MV.git (fetch)
upstream  https://github.com/whrjsdnr/MV.git (push)
```

add는 PC의 .git/config만 변경하고 GitHub를 수정하지 않는다. 이미 있으면 재등록하지 않는다. URL이 다르면 소유자 확인 후 `git remote set-url upstream https://github.com/whrjsdnr/MV.git`으로 수정하고 remote -v로 다시 확인한다. 이 안내 작업에서는 원격 설정을 실제 변경하지 않았다.

## 3. Ubuntu 환경과 데이터

[온보딩 체크리스트](ONBOARDING_CHECKLIST.md)의 Python 3.12/uv 설치, 잠금 설치, CPU 검증, 합성 테스트, 승인된 Canonical 파일 수령, 로컬 데이터 경로, 로더 Smoke Test를 순서대로 수행한다. 데이터셋과 113MB 규모 Crop CSV는 Clone으로 내려오지 않는다. `outputs/`는 Git 제외 대상이다. 단순 Clone 성공은 데이터 로더 준비 완료가 아니다.

## 4. 매일 작업 시작: 최신 원본 main

MV 루트에서, 편집기 파일을 저장한 뒤 실행한다.

```bash
git status
git fetch upstream
git switch main
git merge --ff-only upstream/main
```

| 명령 | 목적/결과 | 성공 확인 | 실패 시 |
|---|---|---|---|
| status | 현재 브랜치/미커밋 확인 | clean이면 다음 진행 | 수정이 있으면 해당 작업 브랜치에 명시적 Stage/Commit 또는 stash 보관 |
| fetch upstream | 원본의 원격 추적 이력 갱신 | 오류 없이 종료, 새 이력 있으면 출력 | 네트워크·인증·upstream URL 확인 |
| switch main | 로컬 main으로 이동 | Switched to branch main 또는 Already on main | 덮어쓰기 경고면 중단하고 미커밋 보존 |
| merge --ff-only upstream/main | 분기 이력이 없을 때만 main 앞으로 이동 | Fast-forward 또는 Already up to date | 분기 이력 확인, 강제 Reset 금지. 관리자와 복구 가이드 확인 |

개인 Fork main도 갱신하려면 이력을 먼저 읽고 팀원이 직접 Push한다.

```bash
git log --oneline --left-right main...upstream/main
git push origin main
```

첫 명령은 로컬과 원본의 서로 다른 Commit을 표시한다. 동기화 직후 아무것도 없으면 일치한다. 로컬 독자 Commit이나 Push 거절이 있으면 강제 Push하지 않는다. Push 성공은 `main -> main` 또는 `Everything up-to-date`다. 원격 개인 main이 앞섰다면 [복구](TROUBLESHOOTING.md)를 따른다.

## 5. 기능 브랜치와 파일 변경

최신 main에서 시작한다. MV 루트:

```bash
git switch main
git switch -c feature/anomaly-patchcore
```

두 번째 명령은 **현재 main Commit에서 새 브랜치를 생성하고 이동**한다. 이미 있는 이름이면 `git branch`로 확인하고 `git switch feature/anomaly-patchcore`로 기존 작업을 계속한다. 기능 브랜치를 만든 뒤 파일을 편집한다. main에서 직접 개발하지 않는다.

이름 예: `feature/anomaly-dinomaly`, `feature/detection-yolo11`, `feature/detection-vitdet`, `fix/dataloader-mask`, `docs/readme-update`. 두 사람이 같은 기능을 하면 담당 파일·반환 타입·설정 키를 먼저 공유한다.

현재 저장소에는 `models/anomaly/patchcore/`가 **없다**. 임의로 존재하는 것처럼 실행하지 않는다. 기존 공통 로더 수정의 실제 경로 예시는 다음과 같다.

```text
mv_analysis/data/adapters.py
tests/test_data_loading.py
reports/DATA_LOADER_IMPLEMENTATION.md
```

편집기에서 실제 필요한 파일을 수정/추가한 후 MV 루트:

```bash
git status
uv run --locked pytest -q
git add mv_analysis/data/adapters.py tests/test_data_loading.py
git diff --cached
git commit -m "feat: improve PatchCore input adapter"
git push -u origin feature/anomaly-patchcore
```

| 명령 | 의미/바뀌는 것 | 성공 확인 | 실패 시 |
|---|---|---|---|
| status | 새 파일/수정 파일 확인 | ??=미추적, M=수정, staged 구분 | 예상 외 파일은 내용을 먼저 확인 |
| pytest | 합성/회귀 테스트 실행 | passed와 종료 코드 0 | 실패 원인 수정. 실제 모델/전체 데이터 검증과 구분 |
| add 지정 경로 | **다음 Commit 대상**으로 변경을 Stage | diff --cached에 필요한 변경만 보임 | 경로 오타 또는 ignore 확인 |
| diff --cached | Stage된 실제 코드 검토 | 데이터·키·개인 경로 없음 | `git restore --staged 경로`로 Stage만 취소 |
| commit | Stage 내용을 로컬 이력으로 저장 | Commit hash/변경 파일 수 | 작성자 설정/빈 Stage/검사 실패 확인 |
| push -u origin 브랜치 | 개인 Fork에 업로드, 추적 브랜치 연결 | 새 브랜치 URL 출력 | 인증/권한/원격 선행 이력 구분 |

새 파일도 **저장 → Stage → Commit → Push**가 필요하다. git add .를 습관적으로 쓰지 않는다. 공식 모델 소스 Clone 및 학습 준비는 [모델 실험 시작 절차](MODEL_EXPERIMENT_WORKFLOW.md)를 따른다.

## 6. 웹에서 PR 제출

1. 개인 Fork 기능 브랜치에 Push한다.
2. GitHub에서 본인 Fork의 MV 페이지를 연다. 브랜치 선택을 확인한다.
3. Compare & pull request를 누른다. 없으면 Pull requests → New pull request → compare across forks를 선택한다.
4. **base repository = whrjsdnr/MV**, **base = main**인지 확인한다.
5. **head repository = 본인 Fork**, **compare = 기능 브랜치**인지 확인한다. 방향이 반대면 원본 반영 요청이 아니다.
6. 제목과 목적/파일/핵심 구현, 로더·Manifest·uv.lock 변경 여부를 작성한다.
7. 실제 테스트 명령, passed/failed/미실행, 환경과 제한을 기입한다. [PR 템플릿](../../.github/PULL_REQUEST_TEMPLATE.md)을 사용한다.
8. Files changed에서 의도한 코드만 있는지 다시 읽는다. 대용량 CSV·승인 기록·키가 있으면 제출 전 제거/검토한다.
9. Create pull request를 누른다. 비교 Commit이 없으면 잘못된 브랜치이거나 아직 Push하지 않은 것이다.
10. 팀원에게 리뷰를 요청한다. Fork 기여자는 리뷰어 지정 권한이 없을 수 있으므로 PR에서 관리자에게 요청한다.
11. 수정 요청은 **같은 기능 브랜치에 추가 Commit/Push**하면 기존 PR에 반영된다.
12. 관리자 승인·Merge를 기다린다. PR 생성만으로 통합되지 않는다.

실제 GitHub 인증·Push·PR·Merge 실습은 각자 실행하기 전까지 미검증이다.

## 7. PR Merge 후 다음 작업

작업 트리가 깨끗한 MV 루트에서 아래를 실행한다. 원본 변경을 받고 개인 Fork main을 따라가게 한 뒤 새 기능 브랜치를 만든다.

```bash
git status
git fetch upstream
git switch main
git merge --ff-only upstream/main
git push origin main
git switch -c fix/dataloader-mask
```

각 명령의 확인/실패 처리는 4~5절과 같다. Merge 완료된 옛 기능 브랜치를 새 기능에 재사용하지 않는다. Squash merge 후 로컬 main에 옛 기능 Commit을 다시 합치지 않는다.

## 8. 기능 작업 중 원본이 바뀐 경우

먼저 해당 작업의 파일만 Stage/Commit하거나 [stash 절차](TROUBLESHOOTING.md)로 보관한다. MV 루트에서 **기능 브랜치로 원본 main을 Merge**한다.

```bash
git status
git fetch upstream
git switch feature/anomaly-patchcore
git merge upstream/main
uv run --locked pytest -q
git push origin feature/anomaly-patchcore
```

merge는 현재 기능 브랜치를 변경한다. 충돌이 없으면 통합 Commit 또는 Already up to date가 보인다. 테스트 후 Push하면 같은 PR이 갱신된다. 인증/Push 거절은 강제로 해결하지 않는다. Rebase는 초보 기본 절차에서 제외하며, 공유 이력 재작성은 관리자와 별도 협의한다.

충돌이 나면:

1. `git status`에서 unmerged paths를 확인하고 해당 파일을 편집기로 연다.
2. `<<<<<<<`, `=======`, `>>>>>>>` 사이 양쪽 의도를 팀원과 확인한다. 무조건 한쪽 코드를 지우지 않는다.
3. 올바른 통합 코드를 남기고 구분자를 모두 지운 뒤 저장한다.
4. `git add 충돌파일경로`로 해결 표시한다. `<파일경로>` 같은 자리표시자는 실제 경로로 바꾼다.
5. `git diff --cached`를 검토하고 `git commit`으로 Merge를 마친다.
6. `uv run --locked pytest -q` 후 개인 Fork 기능 브랜치에 Push한다.

판단할 수 없으면 Merge를 시작할 때 clean이었는지 확인하고 `git merge --abort`로 시도를 취소한다. 이 명령도 기존 미커밋 보존을 보장하는 만능 복구가 아니므로 clean 상태에서 Merge를 시작한다. 자세한 [오류 해결](TROUBLESHOOTING.md)을 따른다.

## 9. 초보자 실습: 문서 한 장으로 흐름 익히기

1~4절로 Clone/upstream/환경/최신 main을 준비한 뒤 MV 루트에서 실행한다. `내ID` 부분은 실제 로그인 ID로 바꾼다.

```bash
git switch -c docs/practice-내ID
mkdir -p docs/team/practice
```

편집기로 `docs/team/practice/내ID.md`를 만들어 본인 역할과 설치 확인 결과 한 줄을 저장한다. mkdir는 연습 폴더만 만들며 `git status`에 새 파일이 보여야 한다.

```bash
git status
git add docs/team/practice/내ID.md
git diff --cached
git commit -m "docs: practice fork workflow"
git push -u origin docs/practice-내ID
```

상태→Stage→내용 확인→로컬 Commit hash→Fork 브랜치 표시 순서가 성공 기준이다. 각 단계 오류는 앞 표와 복구 문서를 따른다. 웹에서 PR의 base/head를 선택해 비교 화면까지 확인한다. 관리자 합의 전에는 Create pull request를 누르지 않아도 된다. 실제 PR을 만들면 제목에 `[연습·병합 금지]`를 붙이고 리뷰 후 **Merge 없이 Close**하는 것을 기본으로 한다. 연습 파일을 원본에 불필요하게 합치지 않는다.

## 공식 근거

- [Fork 원격 설정](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/configuring-a-remote-repository-for-a-fork)
- [Fork 동기화](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/syncing-a-fork)
- [GitHub CLI 인증](https://docs.github.com/en/github-cli/github-cli/authenticating-with-github-cli)

이 문서는 명령 안내다. 문서 작성 에이전트는 Commit/Push/PR/Merge나 GitHub 설정 변경을 실행하지 않는다.
