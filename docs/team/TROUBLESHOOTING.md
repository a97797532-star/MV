# 초보자용 안전한 오류 복구

실행 위치는 기본적으로 MV 루트다. 먼저 `git status`와 `git branch --show-current`로 변경 상태와 작업 브랜치를 읽는다. 예상과 다르면 원인을 파악할 때까지 Push하지 않는다. 강제 Push, 작업 파일 일괄 삭제, 파괴적인 Reset을 기본 해결책으로 사용하지 않는다.

## A. 잘못된 브랜치에서 작업했다

아직 Commit하지 않은 변경으로 새 브랜치를 만들려면:

```bash
git switch -c fix/my-preserved-work
git status
```

현재 변경을 유지한 채 새 브랜치로 이동한다. 새 브랜치 이름과 기존 수정 목록이 보이면 성공이다. 이름이 이미 있으면 다른 이름을 사용한다. 기존 브랜치로 옮겨야 한다면 먼저 보관한다.

```bash
git stash push -u -m "preserve work before branch switch"
git stash list
git switch 실제작업브랜치이름
git stash apply 'stash@{0}'
git status
```

stash는 추적·미추적 변경을 보관하지만 ignored 데이터는 포함하지 않는다. list에서 방금 보관한 항목을 확인한다. 실제작업브랜치이름은 본인 브랜치로 바꾼다. apply는 보관본을 남겨 두고 복원한다. 내용이 정상인지 확인하기 전 stash를 삭제하지 않는다. 적용 충돌은 담당자와 확인한다. **이미 Commit했다면** 그 이력을 보존하고 새 기능 브랜치를 만든 뒤 관리자와 이동 방법을 협의한다. main의 Commit을 무단으로 삭제하지 않는다.

## B. GitHub에 파일이 안 보인다

```bash
git status
git log -1 --oneline
git remote -v
git branch -vv
```

status의 ??는 미추적, Stage 전 변경은 아직 다음 Commit 대상이 아니다. log는 마지막 로컬 Commit, remote는 업로드 대상, branch -vv는 추적 브랜치와 ahead/behind를 보여 준다. 웹에서 개인 Fork의 **올바른 기능 브랜치**를 선택한다. Commit했어도 아직 Push하지 않았다면 GitHub에 없으며, 개인 Fork에 Push했어도 원본 main에는 PR Merge 후 나타난다. [Fork 가이드](GITHUB_FORK_WORKFLOW.md)에서 해당 단계를 이어 간다.

## C. Push 거절·인증·원격 설정 오류

| 메시지/상황 | 확인 명령·대상 | 안전한 해결과 성공 확인 |
|---|---|---|
| fatal: not a git repository | pwd, git status | Clone한 MV로 cd. 임의 git init으로 덮지 않음 |
| destination path already exists | 기존 MV의 status/remote | 기존 Clone 사용 또는 비어 있는 별도 위치 선택 |
| remote upstream already exists | git remote -v | URL이 맞으면 add 생략. 다르면 소유자 확인 후 set-url |
| Repository not found | Fork URL·로그인·공개/비공개 권한 | 본인 실제 Fork 주소와 접근 권한 확인 |
| Authentication failed / Permission denied(publickey) | HTTPS/SSH 구분, gh auth status | CLI/GCM 또는 승인 SSH 키를 해당 방식에 맞게 설정 |
| 403 / write access denied | git remote -v | origin이 본인 Fork인지 확인. upstream 직접 Push 금지 |
| non-fast-forward / rejected | fetch 후 추적 브랜치의 ahead/behind | 같은 기능 브랜치의 원격 변경을 Merge·테스트 후 재Push |
| local changes would be overwritten | git status | A절의 Commit/보관 후 다시 전환·통합 |

팀원이 원본을 Clone해서 origin이 원본이라면, 먼저 브라우저에서 본인의 Fork가 있는지 확인한다. MV 루트에서 `git remote set-url origin https://github.com/<내-GitHub-ID>/MV.git`의 계정 자리를 실제 본인 ID로 바꿔 실행하고 `git remote -v`로 확인한다. upstream은 별도로 등록한다. **관리자 PC의 origin이 원본인 것은 정상**이므로 이 조정을 일괄 적용하지 않는다.

기능 브랜치 Push가 non-fast-forward로 거절된 예시다. 이름을 실제 브랜치로 바꾸고, 같은 기능 브랜치의 clean 상태에서 실행한다.

```bash
git status
git fetch origin
git log --oneline --left-right HEAD...origin/feature/anomaly-patchcore
git merge origin/feature/anomaly-patchcore
uv run --locked pytest -q
git push origin feature/anomaly-patchcore
```

fetch로 원격 이력을 받고 log로 차이를 읽은 뒤 merge로 선행 Commit을 통합한다. 테스트 후 Push한다. 충돌은 다음 절을 따른다. 다른 사람의 변경을 이해할 수 없으면 담당자에게 확인한다. Fork main의 독자 Commit 때문에 ff-only가 실패해도 강제로 초기화하지 말고, 작업 이력을 기능 브랜치에 보존한 뒤 관리자와 main 복구를 협의한다.

## D. Merge conflict / uv.lock 충돌

[Fork 가이드의 충돌 절차](GITHUB_FORK_WORKFLOW.md)를 따른다. status로 충돌 파일 확인 → 양쪽 코드 검토 → 구분자 제거 → 저장 → 지정 파일 Stage → Merge Commit → 테스트 → 개인 Fork Push 순서다. `git merge --abort`는 clean 상태에서 시작한 Merge를 취소할 때 사용한다. 기존 미커밋 변경의 만능 복구 명령은 아니다.

uv.lock 충돌은 양쪽 pyproject·모델 의존 변경을 함께 확인한다. 임의의 lock 조각 선택, lock 삭제·재생성, 전체 의존성 업데이트로 해결하지 않는다. 담당자가 요구사항을 합의한 뒤 필요한 최소 변경을 리뷰하고 `uv sync --locked`와 테스트를 수행한다. 충돌하는 모델 의존성은 별도 환경을 검토한다.

## E. 데이터셋이 열리지 않는다

```bash
printenv REALIAD_DATA_ROOT
test -d "$REALIAD_DATA_ROOT"
```

로컬에서만 경로를 확인한다. test 성공은 무출력·종료0이다. 개인 경로를 공개 로그에 붙이지 않는다. Git Clone은 데이터나 Canonical CSV를 받는 과정이 아니다. 원본 CSV의 절대 경로를 고치지 말고 ManifestIndex의 data_root를 지정한다. 필요한 파일은 [온보딩](ONBOARDING_CHECKLIST.md)을 확인한다. 마스크 없는 NG는 MISSING_ANNOTATION이며 정상 Negative가 아니다.

## F. PR에 불필요한 파일이 포함됐다

아직 Stage만 했다면:

```bash
git diff --cached --name-only
git restore --staged 실제불필요파일경로
git status
```

첫 명령으로 대상을 확인하고 실제 경로로 바꿔 Stage만 해제한다. 로컬 파일이 남았는지 status와 편집기에서 확인한다. Commit한 일반 코드라면 내용을 수정해 **추가 정정 Commit**으로 남긴다. 불필요한 데이터의 추적을 해제해야 하면 관리자와 대상을 확인한 후 `git rm --cached 실제파일경로`를 사용하면 로컬 파일은 남지만, **과거 Commit의 내용은 사라지지 않는다**.

비밀·원본 이미지·공유 권한 미확인 데이터를 Commit했다면 Push하지 말고 관리자에게 알린다. 이미 Push된 비밀은 먼저 폐기·재발급과 관리자의 누출 대응이 필요하다. 추가 Commit만으로 이전 이력의 노출을 해결했다고 판단하지 않는다.

ignore 등록 후에도 추적되면 `git ls-files -- 실제파일경로`로 추적 여부, `git check-ignore -v -- 실제파일경로`로 ignore 규칙을 확인한다. 의도한 코드까지 제외됐다면 규칙을 검토한다. 전체 데이터에 git add -f를 사용하지 않는다.
