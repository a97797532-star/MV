# 팀원별 Ubuntu 재현 실습

> 개인 Fork를 사용하는 팀원은 새 [Fork 협업 절차](team/GITHUB_FORK_WORKFLOW.md)와 [현재 진행 상태](team/PROJECT_STATUS.md)를 먼저 확인하세요. 이 문서의 원본 직접 Clone 예시는 관리자/직접 접근 방식이며, Fork 팀원은 origin=개인 Fork, upstream=원본으로 설정합니다.

각 팀원이 자기 WSL2 Ubuntu에서 실행한다. 4명이 같은 코드를 쓴다는 것과 실제 설치에 성공했다는 것은 다르다. 마지막 표는 본인이 실행한 증거로만 갱신한다. Ubuntu 자체가 없다면 [INSTALL_LINUX.md](INSTALL_LINUX.md)를 먼저 따른다.

## STEP 1. Ubuntu 실행

Windows 시작 메뉴에서 Ubuntu를 연다. 터미널에서 `pwd`를 실행하면 `/home/본인` 등 Linux 경로가 표시되어야 한다. PowerShell의 `C:\...`이면 Ubuntu 터미널인지 확인한다. 가능하면 Linux 홈 아래에 프로젝트를 두어 /mnt/c의 대량 파일 I/O를 피한다.

## STEP 2. Git 확인

어느 디렉터리에서나 `git --version`을 실행한다. `git version 2.x.y`면 다음 단계로 진행한다. 명령이 없으면 `sudo apt update`, `sudo apt install git -y`로 설치한다. sudo 실패는 Ubuntu 비밀번호/권한을 확인한다.

## STEP 3. 프로젝트 Clone

Ubuntu 홈 또는 프로젝트 상위 폴더에서:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/whrjsdnr/MV.git
cd MV
pwd
git status
```

clone은 코드/이력을 받으며 ~/projects/MV를 만든다. 이후 명령은 모두 MV 루트에서 실행한다. pwd가 /MV로 끝나고 status에 현재 branch가 나오면 성공이다. 이미 clone했다면 다시 받지 않고 기존 폴더로 이동한다. private 저장소 권한·인증 오류는 초보자 가이드 K 절을 확인한다.

## STEP 4. 환경 설치

MV 루트에서:

```bash
bash scripts/setup.sh
```

Python 3.12 확인, 잠금 설치, 환경 검증, pytest를 차례로 수행한다. uv가 없으면 INSTALL_LINUX의 uv 설치부터 진행한다. 정상은 마지막 pytest의 passed 및 종료 코드 0이다. Python 3.12가 없으면 `uv python install 3.12` 후 다시 실행한다. lock 불일치는 최신 코드와 lock을 함께 받았는지 확인하고 임의 삭제하지 않는다. DNS/다운로드 실패는 네트워크와 권한을 확인한다. 데이터셋·가중치를 자동 다운로드하지 않는다.

## STEP 5. 설치 검증

```bash
uv run --locked python scripts/validate_environment.py --dummy
```

MV 루트에서 CPU tensor/OpenCV/NMS/import를 확인한다. JSON failed=[] 및 outputs/environment/.../validation.json을 확인한다. CUDA false는 CPU 기본 환경의 실패가 아니다. 모델 12종 실행을 검증한 것은 아니다. 실패하면 JSON의 failed 키와 import 에러를 담당자에게 전달하되 키·토큰은 보내지 않는다.

## STEP 6. 데이터셋 경로

```bash
export REALIAD_DATA_ROOT="/home/본인/데이터폴더"
ls -ld "$REALIAD_DATA_ROOT"
```

실제 복사가 끝난 디렉터리를 지정한다. ls에 디렉터리와 소유자/권한이 나오면 성공이다. 경로에 공백이 있어도 따옴표를 유지한다. 새 터미널마다 export가 필요하다. 팀원 데이터 경로 차이는 코드에 쓰지 않는다. 데이터가 없다면 개인 Git 실습과 합성 테스트까지만 실행할 수 있다.

## STEP 7. 데이터 검증

```bash
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 validate-data
```

MV 루트에서 전체 파일을 읽어 메타데이터/짝/크기/누락을 검사한다. 진행률과 Output 경로가 표시된다. metadata_validation_report.json의 errors, ng_without_mask, orphan_masks 및 처리 수를 확인한다. 예전 참고 개수와 차이가 나면 파일을 지우지 않고 입력 버전·manifest를 확인한다. decode 오류와 권한 오류는 파일 경로를 담당자에게 알려준다.

## STEP 8. 작은 메타데이터 실행

```bash
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 metadata --limit 20
```

새 Output 폴더에 20장 대상 CSV/JSON과 표본 품목 분포 PNG가 생성된다. 전체 개수와 selected=20을 구별한다. 실제 통합 PNG까지 확인하려면 `uv run --locked python -m mv_analysis.cli run-all --limit 100`으로 표본 분석한다. 마스크 검증/Train NG 표본이 부족하면 그 단계에서 중단하며 단계별 안내를 확인한다.

## STEP 9. 결과 열기

출력 메시지의 경로를 아래 `outputs/실행폴더`에 대입한다.

```bash
ls -lh outputs/실행폴더
head -n 3 outputs/실행폴더/image_metadata.csv
cat outputs/실행폴더/metadata_validation_report.json
uv run --locked jupyter lab
```

ls로 파일 존재와 크기, head로 CSV 헤더, JSON으로 성공/오류 수를 확인한다. Jupyter에 표시된 로컬 URL을 본인 브라우저에서 열어 CSV/PNG를 확인한다. 서버 token URL은 다른 사람에게 공유하지 않는다. Windows 탐색기는 `\\wsl.localhost\Ubuntu\home\본인\projects\MV\outputs` 또는 실제 배포판 이름의 경로로 열 수 있다. metadata 단계에는 dataset_category_distribution.png가 생기며 밝기·히트맵·해상도 PNG는 해당 분석 단계가 생성한다. Notebook은 ANALYSIS_PIPELINE의 순서를 따른다.

## STEP 10. 본인 연습 PR

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c docs/practice-본인이름
mkdir -p docs/practice
nano docs/practice/본인이름.md
git add docs/practice/본인이름.md
git diff --cached
git commit -m "Document my Ubuntu onboarding"
git push -u origin docs/practice-본인이름
```

MV 루트에서 실행한다. 개인 문서에는 OS/버전/테스트 결과·질문만 적고 개인 데이터 경로/키는 쓰지 않는다. 새 브랜치→1 file changed→new branch upload를 확인하고 GitHub에서 PR을 작성한다. 초보자 가이드 I/L 절의 리뷰와 merge를 따른다. 미추적 기존 파일을 무작정 add하지 않는다. 에이전트는 push하지 않으며 팀원이 직접 실행한다.

## 팀원 실제 검증 기록

| 팀원 | Ubuntu/Python/uv | 환경 JSON | pytest | 데이터 검증 | 연습 PR | 판정 |
|---|---|---|---|---|---|---|
| 팀원 1 | 미수집 | 미수집 | 미실행 | 미실행 | 미작성 | 미검증 |
| 팀원 2 | 미수집 | 미수집 | 미실행 | 미실행 | 미작성 | 미검증 |
| 팀원 3 | 미수집 | 미수집 | 미실행 | 미실행 | 미작성 | 미검증 |
| 팀원 4 | 미수집 | 미수집 | 미실행 | 미실행 | 미작성 | 미검증 |

현재 에이전트 환경의 성공을 위 네 사람의 성공으로 복사하지 않는다. 각 팀원이 직접 실행 후 실제 값과 PR URL을 넣는다.


## NG/마스크 구분 정책 (2026-11-11 수정)

NG는 불량 제품의 촬영 이미지이며 모든 시점에 위치 마스크가 제공된다고 가정하지 않는다. has_mask는 실제 연결 여부이고 NG 원래 상태는 유지한다. 전체 NG를 메타데이터·밝기·해상도에 포함한다. 마스크 기반 위치 분석은 연결된 NG만 사용하며 미주석 NG에 빈 마스크/빈 YOLO 라벨을 만들지 않는다. 정상 OK의 빈 YOLO 라벨과 구분한다. ng_without_mask.csv에서 경로·대체 stem 후보를 조사하며 파일 부재만으로 의도적 미제공과 유실을 확정할 수 없다. 제공된 PNG의 연결 성공률·decode 오류를 별도 기록한다. 회색조 PNG는 손상으로 판정하지 않고 mask-thresholds의 민감도/overlay 검증 뒤 정책을 정한다.


이번 통합 산출물은 `analysis/real-iad-full-20261111` 브랜치로 공유한다. main 병합 전에는 `git clone --branch analysis/real-iad-full-20261111 https://github.com/whrjsdnr/MV.git`으로 해당 코드를 받을 수 있다. 이미 clone했다면 작업 변경을 먼저 보존하고 `git fetch origin`, `git switch --track origin/analysis/real-iad-full-20261111`을 순서대로 실행한다. branch가 이미 있으면 `git switch analysis/real-iad-full-20261111`을 쓴다. 이 명령들은 MV 저장소 루트에서 실행하며 새 추적 브랜치가 표시되면 성공이다. 파일 덮어쓰기 경고가 나면 초보자 가이드의 변경 보존 절차부터 따른다.
