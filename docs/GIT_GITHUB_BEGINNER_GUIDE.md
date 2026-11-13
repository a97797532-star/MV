# MV 프로젝트 Git·GitHub 첫 실습

> 개인 Fork를 사용하는 팀원은 새 [Fork 협업 절차](team/GITHUB_FORK_WORKFLOW.md)와 [현재 진행 상태](team/PROJECT_STATUS.md)를 먼저 확인하세요. 이 문서의 원본 직접 Clone 예시는 관리자/직접 접근 방식이며, Fork 팀원은 origin=개인 Fork, upstream=원본으로 설정합니다.

이 문서는 Ubuntu 터미널을 처음 쓰는 팀원도 명령을 한 줄씩 실행하도록 작성했다. `본인이름`, 이메일, 브랜치명은 자기 정보로 바꾼다. `$` 프롬프트는 입력하지 않는다. 데이터셋과 비밀정보를 실습 파일에 쓰지 않는다.

## A. 개념을 프로젝트에 연결하기

Git은 내 컴퓨터에서 파일 변경 이력을 관리하는 도구다. GitHub는 Git 저장소를 서버에 보관하고 팀이 리뷰하는 서비스다. 내 Ubuntu의 `~/projects/MV`가 로컬 저장소이고 `https://github.com/whrjsdnr/MV`가 원격 저장소다.

Commit은 선택한 변경을 설명과 함께 로컬 이력에 기록한다. 아직 GitHub에 올라가지 않는다. Push는 로컬 커밋을 원격 브랜치로 보낸다. Pull은 원격 변경을 가져와 현재 로컬 브랜치에 반영한다. Branch는 다른 팀원의 안정 코드와 분리해 작업하는 이력의 이름이다. Pull Request(PR)는 “내 브랜치 변경을 main에 합쳐 주세요”라는 GitHub 리뷰 요청이다. Merge는 두 브랜치 변경을 합치는 작업이다. MV 밝기 분석을 수정한다면 개인 feature 브랜치에서 commit→push→PR→리뷰→main merge 순서다.

## B. 설치 — Ubuntu 어디서나

```bash
sudo apt update
sudo apt install git -y
git --version
```

첫 줄은 Ubuntu 패키지 목록 갱신, 둘째는 Git 설치(-y는 설치 질문에 yes), 셋째는 설치 확인이다. `git version 2.x.y` 형태면 성공이다. sudo 비밀번호 입력은 화면에 표시되지 않는다. `command not found`이면 설치 완료/터미널 종류를 확인한다. 인터넷 오류면 네트워크·배포판 설정을 확인한다.

## C. 최초 설정 — Ubuntu 어디서나 한 번

```bash
git config --global user.name "본인 GitHub 이름"
git config --global user.email "본인 이메일"
git config --global --list
```

커밋에 기록할 작성자 정보를 지정한다. `user.name=...`, `user.email=...`가 표시되는지 확인한다. 이메일 공개가 걱정되면 GitHub Settings → Emails에서 제공하는 본인 noreply 주소를 사용한다. 이 설정은 GitHub 로그인·권한 인증과 다르다. 잘못 입력했으면 같은 명령으로 수정한다. 기존 커밋 작성자가 자동 변경되지는 않는다.

## D. Clone — 프로젝트를 담을 상위 폴더

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/whrjsdnr/MV.git
cd MV
pwd
```

clone은 서버의 코드와 Git 이력을 내려받는다. 실행한 `~/projects` 안에 MV 폴더가 생긴다. `Cloning into 'MV'...`와 완료 메시지를 확인한다. `cd MV`는 Git 명령을 실행할 프로젝트 안으로 이동한다. pwd는 `/home/본인/projects/MV`를 보여야 한다. 이미 복제했다면 `cd ~/projects/MV`만 한다. 그 안에서 다시 clone하면 중첩 폴더나 이름 충돌을 만들 수 있다. `Repository not found`는 아래 오류 절차를 따른다.

## E. 상태 확인 — 이후 명령은 전부 MV 루트

```bash
git status
git branch
git remote -v
```

예시:

```text
On branch main
nothing to commit, working tree clean
* main
origin https://github.com/whrjsdnr/MV.git (fetch)
origin https://github.com/whrjsdnr/MV.git (push)
```

status의 `modified`는 추적 파일 수정, `Untracked files`는 아직 Git에 추가하지 않은 파일, `Changes to be committed`는 다음 commit에 포함할 파일이다. branch의 별표가 현재 브랜치다. remote의 fetch/push는 내려받기/올리기 주소이며 주소가 보이는 것만으로 접근 권한이 확인되지는 않는다. 현재 main에서 직접 수정하지 않는다.

## F. 브랜치 — 작업 시작 전

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c feature/brightness-analysis
```

status가 clean인지 먼저 확인한다. switch는 브랜치를 바꾸고 pull은 main을 최신화한다. `Already up to date.` 또는 `Fast-forward`가 정상 출력이다. --ff-only는 예상하지 못한 자동 merge를 막고 이력이 갈라지면 중단한다. switch -c는 새 브랜치를 만들고 이동한다. `Switched to a new branch ...`를 확인하고 `git branch`의 별표가 새 이름인지 본다. 이미 존재하는 브랜치는 `git switch 브랜치명`을 쓴다. 팀원 둘이 같은 원격 브랜치를 쓰지 않도록 필요하면 이름 접두사를 넣는다.

## G. 파일 수정 → Stage → Commit

밝기 모듈을 편집한 경우:

```bash
git status
git diff -- mv_analysis/stages.py
git add mv_analysis/stages.py
git diff --cached
git commit -m "Improve brightness comparison"
```

이 저장소의 실제 통합 구현은 `mv_analysis/stages.py`다. 기존 요청의 `src/mv_analysis/brightness.py`는 실제 경로가 아니므로 사용하지 않는다. git diff는 아직 stage하지 않은 변경을, --cached는 이번 commit 후보를 보여준다. q로 diff 화면을 닫는다. git add는 파일 복사가 아니라 현재 수정 상태를 commit 후보에 선택하는 것이다. add 뒤 다시 수정하면 다시 add해야 그 부분이 포함된다. commit 성공은 `[feature/... 짧은해시] ...`와 변경 파일 수로 확인한다. `nothing to commit`이면 수정·stage 여부를 확인한다.

초보자는 `git add .` 대신 파일을 하나씩 지정한다. `.env`, 데이터, 결과, 가중치, notebook 출력이 들어가지 않았는지 --cached에서 본다. stage에서만 빼려면 `git restore --staged 파일경로`를 사용한다. 파일 수정은 남는다. add가 경로를 못 찾으면 `pwd`, `ls`로 실제 위치를 확인한다.

## H. Push — MV 루트

```bash
git push -u origin feature/brightness-analysis
```

-u는 현재 브랜치와 원격 브랜치의 연결을 기억한다. 처음 성공하면 `[new branch]`와 tracking 설정 메시지가 나온다. 이후 같은 브랜치에서는 `git push`를 사용할 수 있다. commit은 로컬 저장, push는 원격 공유라는 차이를 기억한다. 이 실습은 팀원이 직접 실행한다. 이번 에이전트 작업은 push하지 않았다.

인증은 SSH 또는 HTTPS의 지원 방식으로 한다. HTTPS에서는 일반 GitHub 비밀번호로 Git 인증할 수 없다. GitHub CLI의 브라우저 로그인/credential manager 또는 필요한 저장소에만 권한을 부여한 토큰을 사용한다. 토큰은 비밀번호 입력란에만 입력하고 URL·명령 인수·문서·메신저에 붙여 넣지 않는다. SSH는 자신의 키를 GitHub 계정에 등록하고 remote를 SSH 주소로 바꿔 사용한다. 비공개 저장소는 collaborator 권한도 필요하다. 공식 안내: [GitHub 인증](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github), [원격 저장소](https://docs.github.com/en/get-started/git-basics/about-remote-repositories).

## I. PR — GitHub 웹 브라우저

1. Push 성공 후 `https://github.com/whrjsdnr/MV`에 로그인한다. 브랜치 선택 목록에 자기 브랜치가 있는지 확인한다.
2. 상단 알림의 **Compare & pull request**를 누른다. 알림이 없으면 Pull requests → New pull request를 누른다.
3. base가 main, compare가 자기 feature 브랜치인지 확인한다. 반대면 변경 방향이 틀린다.
4. Files changed에서 의도한 파일만 있는지 확인한다. 데이터·키·가중치가 있으면 PR 작성보다 해당 노출 정리와 키 폐기를 먼저 담당자와 처리한다.
5. 제목에 바뀐 행동을 쓴다. 설명 템플릿에 목적, 수정 파일, 실행 명령, 테스트 실제 결과, 영향과 검수 항목을 채운다. 미실행 테스트는 미실행이라고 쓴다.
6. 우측 Reviewers에서 다른 팀원 1명을 선택한다. 메뉴가 없으면 권한/저장소 참여 여부를 관리자에게 확인한다.
7. **Create pull request**를 누르고 리뷰 요청이 표시되는지 본다. Review comment에 수정 요구가 있으면 같은 브랜치에서 수정→commit→push한다. PR은 자동 갱신된다.
8. 승인과 필요한 테스트 통과를 확인한 뒤 담당자가 **Merge pull request** 또는 팀의 정해진 merge 방식→Confirm merge를 누른다. 보라색 Merged 표시가 성공이다. Merge 버튼이 비활성이면 충돌·리뷰·권한·보호 규칙을 확인한다. 초보자는 보호 규칙을 우회하지 않는다.

## J. 최신 코드 — 작업 변경을 먼저 확인

```bash
git status
git switch main
git pull --ff-only origin main
```

PR merge 뒤 로컬 main도 갱신한다. 작업 중 변경이 있으면 무작정 pull하지 않는다. 자신의 작업 브랜치에서 필요한 파일을 검토해 commit하거나 별도 안전 복사 후 팀원에게 확인한다. 임시 보관이 필요하면 `git stash push -m "WIP before update"` → `git stash list`로 확인하고 나중에 해당 브랜치에서 `git stash apply`한다. apply 후 내용 확인 전 stash를 지우지 않는다. stash가 untracked 파일을 기본 포함하지 않는 점도 확인한다.

## K. 오류별 안전한 해결

| 오류 | 원인 | 먼저 확인 | 안전한 다음 행동 |
|---|---|---|---|
| fatal: not a git repository | 저장소 밖에서 실행 | `pwd`, `ls -a` | `cd ~/projects/MV` 후 `git status`; 임의 git init으로 덮지 않기 |
| fatal: destination path already exists | clone 대상 폴더 이미 존재 | `ls -la MV`, `git -C MV status` | 기존 저장소면 `cd MV`; 다른 파일이면 삭제하지 말고 다른 이름으로 clone |
| Permission denied (publickey) | SSH 키 미등록/다른 계정 | `git remote -v`, `ssh -T git@github.com` | 본인 공개키 등록·ssh-agent 상태 확인; private key 공유 금지 |
| Authentication failed | HTTPS 인증 만료/비밀번호 사용 | `git remote -v`, 로그인 계정 확인 | 공식 credential 로그인 갱신; 토큰을 로그에 쓰지 않기 |
| Repository not found | URL 오타 또는 비공개 권한 없음 | `git remote -v`, 로그인한 브라우저에서 저장소 열기 | 소유자에게 본인 계정 collaborator 초대 요청 |
| non-fast-forward | 원격에 내 로컬이 모르는 커밋 존재 | `git fetch origin`, `git log --oneline --graph --all -12` | main이면 직접 commit 여부 확인 후 팀원과 분리; 작업 브랜치는 아래 merge 절차. force 금지 |
| Your local changes would be overwritten | 이동/pull이 현재 수정과 충돌 | `git status`, `git diff` | 작업 브랜치에서 검토 후 commit 또는 설명 있는 stash, 다시 시도 |
| Merge conflict | 같은 부분을 두 브랜치가 수정 | `git status`, 충돌 파일 열기 | 아래 수동 충돌 절차; 이해 못하면 리뷰어와 해결 |
| git push 권한 부족 / 403 | 계정/협업 권한/보호 브랜치 문제 | remote, 로그인 계정, 저장소 접근 확인 | 관리자 초대 수락 후 개인 브랜치 push; main 직접 push 금지 |
| gitignore에 있어도 계속 추적 | ignore는 이미 추적된 파일에 소급 적용 안 됨 | `git ls-files -- 파일경로`, `git check-ignore -v --no-index 파일경로` | 팀 확인 후 `git rm --cached -- 파일경로`, ignore commit. 로컬 파일은 유지됨. 노출된 비밀은 이력에 남으므로 즉시 폐기/재발급 협의 |

원격 작업 브랜치의 새 커밋을 가져오는 예시(작업이 clean이고 해당 브랜치에서만):

```bash
git fetch origin
git merge origin/feature/brightness-analysis
```

충돌 파일에는 `<<<<<<<`, `=======`, `>>>>>>>` 표시가 있다. 두 내용을 읽고 필요한 최종 코드로 편집한 뒤 표시를 제거한다. 원래 의도를 모르겠으면 담당자와 같이 확인한다.

```bash
git status
git diff
git add 충돌해결한파일
uv run --locked pytest -q
git commit
git push
```

git commit 편집기가 열리면 메시지를 저장하고 종료한다. nano는 Ctrl+O→Enter→Ctrl+X다. 시작 전 clean이었다면 `git merge --abort`로 진행 중 merge를 중단할 수 있다. 오류 해결을 위해 reset --hard, clean -fd, push --force를 사용하지 않는다.

## L. 첫 PR 실습 — 각 팀원 개인 파일

아래는 Ubuntu의 `~/projects`에서 시작한다. 브랜치/파일의 `myname`을 본인 영문 이름으로 바꾼다. 이미 clone했다면 clone 단계는 건너뛴다.

| 단계 | 실행 명령 | 기대 출력·성공 확인 | 실패 시 확인 |
|---|---|---|---|
| 1 Clone | `git clone https://github.com/whrjsdnr/MV.git` 후 `cd MV` | Cloning 완료, pwd 끝이 /MV | D/K 절 |
| 2 환경 | `bash scripts/setup.sh` | 검증 failed=[], pytest passed | INSTALL_LINUX, 환경 JSON |
| 3 Branch | `git switch main`, `git pull --ff-only origin main`, `git switch -c docs/practice-myname` | Switched to a new branch | status clean 여부 |
| 4 연습 파일 | `mkdir -p docs/practice` 후 `nano docs/practice/myname.md` | 자기 이름·설치 상태·질문 1개 저장 | ls로 파일 확인; 민감정보 금지 |
| 5 상태 | `git status` | Untracked에 자기 파일 | pwd/저장 여부 |
| 6 Stage | `git add docs/practice/myname.md` 후 `git diff --cached` | 자기 파일 내용만 표시 | 경로/오타 확인 |
| 7 Commit | `git commit -m "Add my onboarding practice"` | 1 file changed와 commit hash | 작성자 설정/Stage 확인 |
| 8 Push | `git push -u origin docs/practice-myname` | new branch와 tracking | 인증/권한 확인 |
| 9 PR | 웹에서 base main / compare docs/practice-myname | 열린 PR URL 생성 | I 절 |
| 10 리뷰/Merge | 다른 팀원 승인 후 담당자가 Merge | Merged 표시 후 로컬 main pull | 보호 규칙/충돌 확인 |

실습 완료 증거는 PR URL, 설치 검증 JSON의 성공 여부, 본인 환경 버전이다. 문서를 읽었다는 것만으로 팀원 설치 성공이라고 기록하지 않는다.


## 줄바꿈과 보존 소스

.gitattributes가 유지보수 코드의 줄바꿈을LF로 통일한다. legacy/windows_snapshot과 docs/archive는 원본 바이트 보존 대상으로 변환하지 않는다. 파일 전체가 변경된 것처럼 보이면 프로젝트 루트에서 `git diff --stat`과 `git diff -- 파일경로`로 확인하고, 에디터의 줄바꿈 설정을LF로 맞춘다. 보존 스냅샷을 일괄 포맷하거나 줄바꿈 변환하지 않는다. 실제 수정한 줄만 diff에 나타나면 정상이다.
