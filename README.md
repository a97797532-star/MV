# MV — Real-IAD 5시점 제조 외관검사

WSL2 Ubuntu, Python 3.12, uv, CPU PyTorch를 기본으로 메타데이터·밝기·불량 위치·객체 라벨·원본 JPG 해상도 손실을 분석한다. 원본은 읽기 전용으로 사용하고 결과는 실행별 outputs 폴더에 보관한다. 모델 학습, GAN 학습, 데이터/가중치 다운로드 기능은 포함하지 않는다.

```bash
# WSL2 Ubuntu 터미널, clone한 MV 루트
bash scripts/setup.sh
export REALIAD_DATA_ROOT="/실제/데이터셋"
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 validate-data
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 metadata --limit 20
uv run --locked python -m mv_analysis.cli --split-policy windows-project-v1 run-all --limit 100
```

설치와 독립적인 파일 구조 검사:

```bash
python3 scripts/inventory_dataset.py --data-root "$REALIAD_DATA_ROOT"
```

실제 대상은 JPG 151,050장(OK 72,840 / NG 78,210), PNG 51,329장이다. NG 26,881장에 위치 마스크가 없다는 사실은 오류가 아니다. 전체 NG를 영상 분석에 사용하고 has_mask=True인 NG만 위치 분석에 사용한다. 미주석 NG의 빈 마스크/빈 YOLO 라벨을 만들지 않는다. PNG 회색조는 threshold 민감도와 overlay를 확인한 후 정책을 정하며, 정책 미확정 시 위치 분석만 보류한다. 최신 완료/실행 중/미검증 상태는 [최종 보고서](reports/REAL_IAD_FINAL_ANALYSIS.md)와 [실행 로그](reports/ANALYSIS_EXECUTION_LOG.md)를 확인한다.

- [Ubuntu 설치](docs/INSTALL_LINUX.md), [Ubuntu 검증](docs/ENVIRONMENT_VALIDATION.md), [이전 감사](docs/MIGRATION_AUDIT.md)
- [데이터 경로·검증](docs/DATASET_SETUP.md), [CLI·산출물·Notebook](docs/ANALYSIS_PIPELINE.md)
- [Git/GitHub 초보 실습](docs/GIT_GITHUB_BEGINNER_GUIDE.md), [4명 협업 규칙](docs/TEAM_GIT_WORKFLOW.md), [팀원 설치 실습](docs/TEAM_ONBOARDING.md)
- [마스크 임계값 검증](reports/MASK_THRESHOLD_VALIDATION.md), [환경 이전 보고서](reports/ENVIRONMENT_MIGRATION_REPORT.md)

단계별 실행은 같은 `--output`에 `--resume`으로 이어간다. CLI 전역 옵션은 단계 이름 앞에 둔다. 새 출력 디렉터리와 원본 디렉터리는 서로 포함할 수 없다. 설정·lock·소스가 다른 실행은 그대로 재사용하지 않는다. 전체 실행은 환경/합성 테스트/실제 표본 preflight 및 복사 완료 확인이 필요하다. 상세 명령은 분석 가이드를 따른다.

기존 루트 Windows 검증 문서와 docs/archive 설정은 역사 기록으로 보존했다. 추가 조사에서 마운트된 Windows 원본 소스/Notebook 60개를 legacy/windows_snapshot에 보존했다. 기존 split은 151,050장 모두 동일하게 재현했고, 실제 Windows JPG/PNG 경로 집합도 현재와 일치한다. 같은 방법의 밝기150장/해상도50장 재실행 비교는 reports/WINDOWS_RESULT_COMPARISON.md를 참조한다. 데이터·가중치·.env·대용량 결과·Notebook 출력은 GitHub에 올리지 않는다. 최신 지시에 따라 GitHub에는 코드·문서만 업로드 후보로 검수하며 Push는 수행하지 않는다. 원본 데이터/가중치는 포함하지 않는다. 팀원 4명의 개별 설치/PR 실습은 각자 실행하기 전까지 미검증이다.


추가 내용 감사에서 전검정 JPG 2장의 동일 바이트 중복을 확인했다. 초기 hash 탐색 분할에서는 Train/Test에 나뉘지만 보존한 Windows 분할에서는 두 장 모두 Train이며, 이 분할의 정확한 바이트 교차 중복은0이다. 선언된 제품 키의 분할 검사와 실제 물리 제품 identity 확인은 구분한다. NG 쪽은 전영역 마스크로 특정 위치 집계에 큰 영향을 준다. 원본 전체 분석을 보존하고 quality_review에 모델 입력 보류 후보와 위치 선행분포 대조를 남겼다. 검수 전 모델 학습 준비 완료로 판단하지 않는다.


배경·제품·결함 국소 밝기 확장: [실행 가이드](docs/BACKGROUND_BRIGHTNESS.md), [근거 보고서](reports/BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md). 전체 실행 상태는 보고서 상단을 확인한다.


해상도 전수 결과의 재집계: [회의용 최종 PDF](reports/RESOLUTION_TEAM_MEETING_FINAL.pdf), [상세 Markdown](reports/RESOLUTION_DETAILED_ANALYSIS.md), [파일 목록·한계·회의 결정 사항](reports/RESOLUTION_DELIVERY_GUIDE.md). 기존 151,050장 결과를 재사용했으며 전체 해상도 계산을 반복하지 않았다. 그래프·집계 CSV는 Git에서 제외된 outputs/resolution_detail_20261111_v2/에 있다. PDF는 그림을 내장한다.
