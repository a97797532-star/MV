# Ubuntu 검증 기록

과거 Windows 실패 기록은 루트 `ENVIRONMENT_VALIDATION.md`에 보존한다. Ubuntu의 실제 결과는 [이전 보고서](../reports/ENVIRONMENT_MIGRATION_REPORT.md)와 outputs/environment의 실행별 JSON을 따른다.

프로젝트 루트에서 실제 실행한 결과:

- `uv sync --locked`: 최초 Windows 플랫폼 불일치 실패 → Linux 지원을 추가한 뒤 DNS 실패 → 네트워크 허용 설치 재개 → interruption 복구 후 offline 설치와 locked 재검증 성공.
- `uv run --locked python scripts/validate_environment.py --dummy`: failed=[], CPU tensor/NMS/OpenCV 성공. Python 3.12.14, torch 2.15.0+cpu. CUDA unavailable 관측.
- `uv run --locked pytest -q`: 초기 1 failed/5 passed → 수정 후 6 passed → 미주석 NG·추가 구분자 검사 포함 7 passed. 마지막 로그는 reports/ANALYSIS_EXECUTION_LOG.md 참조.
- 팀원 4명의 각 설치: 아직 미검증. 모델 12종·CUDA·학습·실데이터 모델 추론: 미검증/미실행.

검증 스크립트는 네트워크 접속을 차단하고 사전학습 가중치를 요청하지 않는다. 로그는 새 outputs/environment/<UTC>/validation.json에 저장해 기존 기록을 덮지 않는다.


최종 확장 테스트: `uv run --locked pytest -q` → **14 passed in 14.39s**. 다중 클래스 COCO/YOLO, 빈 제공 PNG의 NG 상태 유지, 미주석 NG 라벨 제외, 변경된 생산자의 기존 체크포인트 거부를 포함한다. 원문은 reports/FINAL_PYTEST_RESULTS.txt에 있다. Notebook 6개는 nbformat schema 및 출력 제거를 확인했으며 실제 노트북 6개 실행 완료로 주장하지 않는다.


최신 확장 검증: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --locked pytest -q` → **22 passed in 131.05s**. 재개 가능한 영역 밝기, 미주석 NG 유지, 결함 마스크와 독립적인 전경/제품 내부 국소 주변, 기존 분할/빈 마스크/1픽셀 위치 빈도 계약을 포함한다. `reports/latest_pytest.txt` 참조. 보존한 Windows OpenCV 원본의 별도 unittest 16개도 Linux에서 통과(50.300초)했다. 기존 14개 기록은 당시 검증 이력으로 유지한다.


최종 source253019974b36a9d4beeb580580be6b3e6cf2ed59152146d813545d4083b4acf1 검증(UTC2026-11-11 08:48): locked sync0,170개 설치상태 확인, 실제100장 smoke0,환경 dummy0, pytest **22 passed in11.29s**. 원문은 reports/FINAL_ENVIRONMENT_SYNC.txt, FINAL_REAL_SMOKE_LOG.txt, FINAL_PREFLIGHT_LOG.txt, FINAL_PYTEST_RESULTS.txt에 있다. 이전14개 결과도 reports/archive에 보존한다.
