# 최종 공유 범위와 Git 전달

최신 사용자 지시는 “GitHub에는 코드와 문서만 포함되도록 검수하고, Push는 수행하지 마라”이다. 이전 Push 요청을 대체한다. 이 작업에서는 GitHub Push, Commit, 브랜치 생성 또는 PR 생성을 수행하지 않는다.

- 분석 코드: mv_analysis/, scripts/, tests/, notebooks/.
- 환경/팀 문서: pyproject.toml, uv.lock, README, docs/, .github/PR template.
- 기존 코드 보존: legacy/windows_snapshot/과 원본 SHA256 인벤토리. Notebook은 Linux 복사본의 출력만 제거했다.
- 해상도 집계 CSV·파생 그림: 로컬 outputs/resolution_detail_20261111_v2/에 보관한다. Git 업로드 대상에서 제외한다.
- 분석 보고서: reports/의 상세 Markdown·PDF·검증 결과.

원본 dataset, 전체 outputs, .venv/.uv-cache, 가중치, .env/API키는 업로드 대상에서 제외한다. GitHub 저장소는 https://github.com/whrjsdnr/MV.git이다. 팀원의 설치/PR 실습 성공은 각자 실행하기 전까지 미검증이다. 회의용 PDF는 그래프를 내장한 문서로 제공하며, 독립적인 원본 영상·파생 그림 디렉터리는 업로드하지 않는다.

scripts/publish_analysis_branch.py는 이전 지시 때 준비했던 코드이며 이번 작업에서 실행하지 않는다. 최신 업로드 검수 결과는 reports/RESOLUTION_DELIVERY_VALIDATION.json에 기록한다. Markdown의 outputs/ 상대 링크는 로컬 증거이며 GitHub 단독 열람 시 제공되지 않는다. 회의 공유에는 그림이 내장된 PDF를 사용한다.
