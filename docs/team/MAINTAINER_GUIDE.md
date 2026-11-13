# 원본 MV 관리자 가이드

관리 대상은 `whrjsdnr/MV`의 main이다. 팀원은 origin을 개인 Fork로 쓰지만, 관리자 PC는 origin이 원본일 수 있다. 이번 문서 작업에서는 원격 설정·Commit·Push·PR·Merge·Ruleset을 변경하지 않는다.

## PR 확인 → 리뷰 → Merge

1. 원본 저장소의 Pull requests에서 base가 원본 main, head가 팀원 Fork의 기능 브랜치인지 확인한다.
2. 목적과 Files changed를 읽는다. 데이터·권한 미확인 외부 코드·가중치·인증정보·개인 경로·실제 승인 Ledger가 포함됐는지 확인한다.
3. 실제 실행 명령, 환경, passed/failed/미실행을 확인한다. 독립 입력 Adapter 테스트를 실모델 학습 성공으로 해석하지 않는다.
4. 공통 로더 변경이면 반환값, NG 결측 주석, 클래스 ID offset, C1~C5 순서, Split, Crop/Resize 회귀 테스트를 검토하고 모델 담당자에게 영향을 알린다.
5. Manifest 변경이면 아래 별도 승인 절차를 수행한다. 제품 GT BBox 승인과 Crop 승인은 다른 기록이다.
6. uv.lock 변경은 pyproject·목적·버전·플랫폼 차이를 함께 검토한다. 모델 특수 의존성은 독립 환경을 먼저 검토한다.
7. 문제는 Request changes로 파일/라인/재현 명령을 명시한다. 팀원이 같은 PR에 수정 Commit을 추가하면 다시 검토한다.
8. 통과한 PR만 관리자가 Merge한다. Squash merge는 기능 단위 이력을 단순화하고 Merge commit은 개별 이력을 보존한다. 팀에서 기본 방식을 합의하고 초보자에게 공유 이력 재작성을 요구하지 않는다.
9. Merge 후 main의 테스트 결과를 확인하고 PR·변경 인터페이스·데이터 버전·환경 주의사항을 팀에 알린다. 팀원은 [Fork 동기화](GITHUB_FORK_WORKFLOW.md) 절차를 수행한다. 이 작업에서 공지 전송은 자동 실행하지 않는다.

## Canonical Manifest 승인과 배포

현재 전체 Crop CSV는 약113MiB이며 `outputs/`에 있어 Git 배포 대상이 아니다. 공개 저장소 Clone만으로 실제 로더가 준비되지 않는다. 주석·승인자 정보·개인 경로·원본 데이터의 공유 권한이 확인되기 전 공개 Release/PR에 첨부하지 않는다.

1. 기준/후보 Manifest hash, 정책 버전, 승인 Ledger 대조, 좌표 변경 건수, 오류 목록을 받는다.
2. 원본과 Ledger는 읽기 전용으로 두고 새 출력 버전에서 검증한다. v1 전수 증거를 v2 전수 완료로 재표시하지 않는다.
3. 좌표 범위·ID 중복·5시점·Split·승인 일치·마스크/BBox 손실·원본 동일성을 확인한다. Test 정답 참조 수정의 독립성 위험도 기록한다.
4. 팀이 승인한 버전을 배포 목록에서 Canonical로 지정한다. 미완료면 Candidate 상태를 명시하고 학습 준비 완료로 선언하지 않는다.
5. 접근 제한 팀 채널로 Manifest·annotation·BBox·classes와 각 SHA-256·스키마·버전·검증 결과를 전달한다. 코드 PR에는 배포 정책과 권리 검토된 소형 스키마/합성 예제만 넣을 수 있다.
6. 팀원은 `data_root`로 개인 경로를 매핑한다. 복사 후 mtime이 달라 source_fingerprint 검증이 실패하면 조용히 검증을 끄지 말고 해시 근거를 검토한다.
7. 다음 번 갱신도 새 버전으로 배포한다. 실제 승인 Ledger를 공개 Git이나 학습용 GT로 자동 전환하지 않는다.

읽기 전용 검수 명령의 위치는 MV 루트다.

```bash
git status --short
git diff --cached --stat
git diff --cached
git ls-files outputs dataset datasets .env
sha256sum outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv
```

status는 작업 상태, cached는 다음 Commit의 파일/내용, ls-files는 이미 추적된 제외 대상, sha256sum은 배포물 식별자를 표시한다. 예상 외 파일이 있으면 Stage를 중지하고 [복구 문서](TROUBLESHOOTING.md)를 따른다. hash가 다르면 배포 대상부터 재확인한다. ignore 검사만으로 공개 권한 확인을 대신할 수 없다.

## main 보호 설정 권장

관리자가 원본 저장소 Settings → Rules → Rulesets 또는 Branches 보호 설정에서 main을 대상으로 검토한다. UI와 이용 가능한 기능은 플랜/권한에 따라 다를 수 있다.

- PR을 통한 통합과 다른 팀원 1명 이상의 승인 요구.
- 새 Commit 후 승인 재요청 및 미해결 리뷰 대화 해소 요구 검토.
- CI가 실제 존재하고 실행되는 경우에만 해당 상태 검사를 필수로 지정. 확인하지 않은 검사 이름으로 Merge를 막지 않는다.
- 강제 Push·브랜치 삭제 제한, 관리자 우회 권한 최소화 검토.
- Fork PR의 미신뢰 코드에 배포 비밀/토큰을 노출하지 않도록 CI 권한 검토.

이 설정은 이번에 변경하지 않았다. [Ruleset 공식 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)와 [가능한 규칙](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)을 확인하고 팀 합의로 설정한다.

## 다음 작업 배정

[진행 상태](PROJECT_STATUS.md)에 따라 v2 타깃 계약/eligibility 검증, 배포 권한, 모델 통합 담당을 정한다. 구조 표준화는 코드 이동·import·명령어를 검증하는 별도 PR로 진행한다. 이번 문서 작업을 전체 구조 표준화 완료로 간주하지 않는다.
