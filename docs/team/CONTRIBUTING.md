# MV 기여 규칙

시작은 [README](../../README.md), 실제 조작은 [Fork 절차](GITHUB_FORK_WORKFLOW.md), 현재 작업 상태는 [진행 상태](PROJECT_STATUS.md)를 참고한다. 기존 [4명 협업 규칙](../TEAM_GIT_WORKFLOW.md)은 보존하며, Fork 사용자의 origin/upstream 관계는 새 가이드를 따른다.

## 팀에서 지킬 계약

- main에는 안정된 코드만 유지한다. 개인 Fork 기능 브랜치 → PR → 다른 팀원 1명 이상 리뷰 → 관리자 Merge를 기본으로 한다.
- 같은 파일을 수정하기 전에 담당을 공유한다. 모델 담당, 공통 로더 담당, Canonical 데이터 관리자, 리뷰 역할을 합의하며 임의로 개인에게 배정하지 않는다.
- `mv_analysis/data/`의 반환값, BBox 클래스 ID·좌표, NG 결측 주석, 5시점 순서, Split을 바꾸면 호출 코드와 테스트도 함께 변경한다.
- 로더는 저장된 Crop을 읽는다. 학습 중 Crop을 다시 추정하거나 결함 라벨·마스크로 Crop을 선택하지 않는다.
- 기존 선언 product_id와 Split을 유지한다. Train 통계로 설정하고 Test에 맞춰 조정하지 않는다. Test의 주석을 참고한 수동 수정의 평가 독립성 위험을 기록한다.
- 공식 구현과 공통 Adapter의 Resize·Normalize·CenterCrop 중복 적용을 방지한다. 12개 모델 실제 런타임 연결은 아직 UNVERIFIED다.
- 실험 추가 시 [모델 실험 단계](MODEL_EXPERIMENT_WORKFLOW.md)와 실행 README를 함께 갱신한다.

## PR 전 확인

모든 명령은 MV 루트에서 실행한다.

```bash
git status
uv run --locked pytest -q
git diff
# 실제 변경한 파일만 지정하는 예시
git add mv_analysis/data/adapters.py tests/test_data_loading.py
git diff --cached
git diff --cached --check
```

status는 변경 파일, pytest는 테스트, diff는 수정 내용, add는 다음 Commit 대상 지정, cached는 Stage된 내용을 보여 준다. check 성공은 출력 없이 종료 코드0이다. 문제를 수정한 뒤 해당 파일을 다시 Stage한다. Commit·Push의 목적, 성공 확인과 오류 대응은 [Fork 가이드](GITHUB_FORK_WORKFLOW.md)를 따른다.

## 공유 범위

| 대상 | 기본 방침 |
|---|---|
| Python·모델 설정·테스트·README·팀 문서·pyproject·uv.lock | 리뷰 후 코드 PR에 포함 |
| 소형 스키마·합성 Manifest | 실제 이미지·개인 경로·주석이 없는지 확인 후 공유 후보 |
| 전체 Crop CSV·승인 Ledger·데이터에서 파생된 라벨 | Git 밖의 접근 제한 배포. 권한·hash·버전·승인 필요 |
| Real-IAD JPG/PNG·원본에서 파생된 내부 비교 그림·가중치 | 자동 공개 금지 |
| .venv·.env·개인 설정·캐시·학습 로그·인증정보/API 키 | Git에 포함 금지 |

현재 `.gitignore`는 outputs/·데이터·가중치·환경·비밀 파일을 제외한다. ignore는 **이미 추적된 파일을 제외하지 않는다**. 전체 CSV 약113MiB는 소형 Manifest가 아니다. ignore를 대량 해제하거나 `git add -f`로 넣지 않는다. 외부 코드 라이선스와 데이터 공유 권한도 별도로 확인한다.

문법 확인·합성 테스트·실데이터 Smoke·전수 디코딩·실모델 학습은 서로 다른 검증이다. 실제 실행 범위만 VERIFIED로 기록하고 나머지는 미실시/UNVERIFIED로 남긴다.
