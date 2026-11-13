## 작업 목적

어떤 문제를 해결하며, 실행 시 무엇이 달라지는가?

## 변경된 파일 / 주요 구현 내용

- 수정·추가 파일:
- 주요 변경사항:
- 기존 기능 및 호환성 영향:

## 데이터 계약 변경

- [ ] 공통 데이터 로더 변경 없음
- [ ] 로더 변경 있음: image/target/NG 결측/5시점/collate 영향과 회귀 테스트를 설명했음
- [ ] 전처리 Manifest 변경 없음
- [ ] Manifest 변경 있음: 기준/후보 hash·정책 버전·승인 대조·검증 상태·배포 경로를 관리자에게 별도 제출했음
- [ ] 제품 GT 승인과 Crop 승인 기록을 구분했음
- [ ] 기존 Split·product_id·원본 좌표 계약을 확인했음

## 실행 방법 및 테스트 명령어

실행 위치와 실제 프로젝트 경로를 적는다. 모델 실험이면 공식 URL/commit, 환경, 데이터 hash, train/eval entrypoint를 포함한다.

```bash
# MV 루트 예시. 실제 실행한 명령으로 수정
uv sync --locked
uv run --locked pytest -q
```

## 테스트 결과 / 실행 환경

- OS / Python / uv / CPU 또는 GPU:
- 실행 명령별 passed/failed/미실행:
- 합성 테스트 / 실제 데이터 Smoke / 전수 검증의 범위·처리 수·오류 수:
- 실모델 연결/학습/성능 평가 상태(미실행은 UNVERIFIED):
- uv.lock / pyproject 변경 목적과 버전·플랫폼 영향:

## 업로드 대상 확인

- [ ] 원본 데이터·마스크·모델 가중치·대용량 결과·승인 Ledger 미포함
- [ ] .env·API 키·토큰·인증정보·개인 데이터 경로 미포함
- [ ] 외부 소스/이미지/데이터의 라이선스·공유 권한을 확인했음
- [ ] README·팀 가이드·실행 방법을 함께 갱신했음

## 남아 있는 문제 / 미검증 사항

## 리뷰 요청 사항

특히 검토할 파일·인터페이스·재현 결과와 관련 이슈.

## 공통 실험·보고 계약(모델 결과 PR)

- [ ] SYNTHETIC/REAL·Run 상태·실제 학습 여부를 구분했음
- [ ] Manifest/주석/평가ID/protocol 해시와 Validation Threshold 출처를 기록했음
- [ ] Test로 Threshold·대표 Run을 선택하지 않았음
- [ ] 다른 GPU·batch·입력집합의 속도를 한 순위로 합치지 않았음
- [ ] 추론/연결 코드·설정·Markdown/공유 가능 그래프만 제출하고 weights/checkpoint/memory bank/index는 별도 전달함
- [ ] 가중치 파일명·크기·SHA와 수령 방법만 남기고 비밀 URL/토큰을 제외했음
