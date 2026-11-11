# 상세 PDF 및 공유 이미지 생성

분석 완료 후 `scripts/build_analysis_gallery.py`로 품목별 분포/동일 제품5시점/Train 위치 빈도 및 주요 전체 그림을 만든다. 공유 대상은 `images/`, 소규모 집계표는 `images/tables/`다. `images/manifest.json`에 출처·범위·선정 이미지 경로를 기록한다. 원본 JPG/PNG 및 전체 per-image 결과와 체크포인트는 로컬 dataset/outputs에 보존한다.

```bash
uv run --locked python scripts/build_analysis_gallery.py --image-run outputs/full_20261111_v6 --spatial-run outputs/spatial_20261111_v7 --preserved-run outputs/windows_preserved_20261111_v1 --background-run outputs/background_full_20261111_v1 --output images
uv run --locked python scripts/export_detailed_pdf.py --gallery images --output reports/REAL_IAD_DETAILED_ANALYSIS.pdf --image-run outputs/full_20261111_v6 --background-run outputs/background_full_20261111_v1 --sample-run outputs/background_sample_20261111_v5 --mask-study outputs/mask_study_20261111_v4
```

Ubuntu 프로젝트 루트에서 실행한다. 새 출력만 허용하므로 이미 있는 산출물은 보존하고 새 실행명을 사용한다. PDF 최종 출력은 전체 해상도453,150행과 영역 분석151,050장, 성공한 검증 JSON 및 완료된 gallery를 확인한 후 허용한다. `--draft`는 초안이며 표지/쪽 번호에 DRAFT를 표시한다. 초안을 완료본으로 공유하지 않는다.

Matplotlib의 PDF backend와 설치된 한글 글꼴을 사용한다. 우선 `/usr/share/fonts/truetype/nanum/NanumGothic.ttf`, 대체로 WSL의 Windows Malgun을 탐색한다. 글꼴이 없으면 중단한다. Ubuntu에서 필요한 경우 `sudo apt install fonts-nanum`을 설치한 뒤 다시 실행한다. 글꼴 파일 자체는 저장소에 포함하지 않는다. PDF에는 필요한 글꼴을 subset으로 포함한다.

독립적인 실제 PDF 렌더 검증은 임시 PDFium 도구를 사용한다. 주 프로젝트 의존성과 uv.lock을 변경하지 않는다.

```bash
UV_CACHE_DIR=.uv-cache uv pip install --target /tmp/mv-pdf-tools pypdfium2==5.15.2
uv run --locked python scripts/validate_pdf_report.py reports/REAL_IAD_DETAILED_ANALYSIS.pdf --render-dir images/pdf_review
```

검증은 페이지 수·한글 텍스트 추출·선택 페이지 실제 렌더/빈 페이지 여부를 확인한다. 표지·표·그림·중간/마지막 페이지를 PNG로 만들어 직접 검수한다. `*.validation.json`, `*.render_validation.json`, `*.pages.json`은 구조/렌더 결과와 페이지별 출처다. 검사 통과와 모든 그림의 의미적 정답 검수 완료는 구분한다.

최종 PDF는 보고서의 계산 근거와 품목별 그림을 포함하고, 파일 크기와 렌더 검증을 거친 뒤 Git 공유 대상에 포함한다. 입력 데이터·가중치·비밀정보는 업로드 대상이 아니다. 전체 raw CSV/NPY는 로컬 산출물이며 공유 집계표와 출처를 통해 재현한다.
