"""Reports are computed from saved artifacts, with missing stages marked explicitly."""
import json
from pathlib import Path
import pandas as pd


def generate(out):
    def read(name):
        p=out/name
        return pd.read_csv(p) if p.exists() else None
    validation=json.loads((out/'metadata_validation_report.json').read_text()) if (out/'metadata_validation_report.json').exists() else {}
    run=json.loads((out/'run.json').read_text())
    full=run['config']['limit'] is None and not run['config']['inventory_only']
    text=['# Real-IAD 통합 분석 보고서', '\n## 1. Executive Summary',
          f"분석 범위: {'전체 후보' if full else '표본/목록 검사'}. JPG 목록 {validation.get('jpg_count','미검증')}, PNG 목록 {validation.get('png_count','미검증')}. 성공 메타데이터 {validation.get('success','미검증')}. 전체 분석 완료 여부는 모든 단계 결과와 실행 기록을 함께 확인해야 합니다.",
          '\n목적: 모델 학습 전 5시점 데이터 품질·밝기·결함 위치·객체 라벨·해상도 손실을 파악합니다. 현재 지표는 모델 성능이 아닙니다.',
          '\n## 2. 데이터셋 구성',
          f"근거: [metadata_validation_report.json](metadata_validation_report.json). 정상/불량: `{validation.get('status_counts',{})}`. 시점: `{validation.get('view_counts',{})}`.",
          f"품목 분포: `{validation.get('category_counts',{})}`.",
          '\n## 3. 메타데이터 분석 결과',
          f"5시점 불완전 capture {len(validation.get('incomplete_capture_groups',{}))}, 위치 정답 미제공 NG {validation.get('ng_without_mask','미검증')} (개수 차이 자체는 오류 아님), 위치 정답 제공 NG {validation.get('ng_with_mask','미검증')}, 분할 누수 {validation.get('product_split_leakage','미검증')}. [image_metadata_with_split.csv](image_metadata_with_split.csv).",
          '\n기존 split manifest가 없으므로 category/serial SHA256으로 70/15/15 분할합니다. OK/NG/불량유형별로 재사용된 serial도 보수적으로 묶습니다. 실제 물리 제품 ID 및 기존 Windows split과의 일치 여부는 미검증입니다. 동일 제품 5시점은 capture_id로 점검합니다.',
          '\n## 4. 밝기 분석 결과']
    b=read('brightness_per_image.csv');c=read('brightness_comparison.csv')
    if b is None:text.append('미완료: 밝기 결과 없음.')
    else:
        text.append(f"처리 {len(b):,}장. 상태별 평균 밝기 [0,255]: `{b.groupby('status').brightness.mean().round(4).to_dict()}`. [brightness_summary.csv](brightness_summary.csv).")
        if c is not None and len(c):text.append(f"비교 조합 {len(c)}, |d|≥0.8 조합 {int((c.cohens_d.abs()>=.8).sum())}. 평균 histogram overlap {c.histogram_overlap.mean():.4f}. 검수 후보는 [brightness_review_candidates.csv](brightness_review_candidates.csv). 조명·재질·불량 자체의 영향을 분리해 검수해야 합니다.")
        text.append('![밝기 분포](brightness_histogram.png)\n\nTrain P05/P50/P95를 증강 후보 범위의 근거로 사용하되 validation으로 강도를 결정합니다. Test 통계에 증강 정책을 맞추지 않습니다.')
    text.append('\n## 5. 불량 위치 히트맵 분석')
    h=read('heatmap_summary.csv')
    if h is None:text.append('미완료: 검증된 마스크 기반 히트맵 결과 없음.')
    else:text.append(f"그룹 {len(h)}, 관측 10장 미만 그룹 {int((h.observations<10).sum())}. 평균 상위 10% 격자 결함질량 비중 {h.top10pct_mass_share.mean():.4f}. [heatmap_summary.csv](heatmap_summary.csv).\n\n![위치](heatmap_visualization.png)\n\nGAN 위치 정책은 품목·불량·시점별 관측 수를 함께 검토해야 합니다. 미관측 영역은 정상으로 보장되지 않습니다.")
    text.append('\n## 6. Bounding Box 분석')
    boxes=read('defect_bboxes.csv')
    if boxes is None:text.append('미완료: 박스 결과 없음.')
    else:
        text.append(f"8방향 성분 박스 {len(boxes):,}개. 원본 박스 면적 <1024 px²인 박스 {int((boxes.bbox_area<1024).sum()):,}개. [bbox_validation_report.json](bbox_validation_report.json), [classes.json](classes.json). 정상 이미지는 빈 YOLO 파일이며 분류용 정상 클래스와 구분됩니다. 하나의 NG 안 모든 성분에 파일명 불량 유형을 부여하는 가정입니다.")
        text.append('![클래스](bbox_class_distribution.png)')
    text.append('\n## 7. 해상도별 정보 손실 분석')
    r=read('per_view_information_loss.csv')
    if r is None:text.append('미완료: 원본 JPG 해상도 손실 결과 없음.')
    else:
        text.append(f"해상도별 평균 SSIM: `{r.groupby('target').ssim.mean().round(5).to_dict()}`. 평균 Edge recall: `{r.groupby('target').edge_recall.mean().round(5).to_dict()}`. [category_view_loss_summary.csv](category_view_loss_summary.csv).\n\n![5시점](five_view_loss.png)\n\n![확대](detail_crop_comparison.png)\n\n[review_priority_images.csv](review_priority_images.csv)의 실제 영상을 검수해야 합니다. 이 수치를 검출 정확도·추론 속도로 해석하지 않습니다.")
    text.append('\n## 8. 분석 간 연관성')
    if b is not None and r is not None:
        merged=b[['image_path','brightness']].merge(r[r.target==256][['image_path','ssim']],on='image_path')
        value=merged.brightness.corr(merged.ssim)
        text.append(f'이미지 평균 밝기와 256 SSIM의 Pearson 상관: {value:.5f} (N={len(merged)}). 품목/촬영조건의 교란 가능성이 있으며 인과를 의미하지 않습니다.')
    else:text.append('밝기–해상도 연관성은 관련 단계 완료 전 미검증입니다.')
    if boxes is not None and r is not None and len(boxes):
        small=boxes.groupby('image_path').relative_area.min().rename('min_box_relative_area')
        merged=r[r.target==256][['image_path','ssim']].merge(small,on='image_path')
        text.append(f'NG별 최소 박스 상대면적–256 SSIM Pearson 상관 {merged.min_box_relative_area.corr(merged.ssim):.5f}, N={len(merged)}. 전체 영상 SSIM은 국소 미세 결함 손실과 다릅니다.')
    text.extend(['시점별 조명·정보 손실은 같은 품목으로 층화하여 검토합니다. 위치 집중은 촬영 정렬이나 주석 편향을 반영할 수도 있습니다. 클래스 박스 수가 아닌 물리 제품 단위 평가를 병행해야 합니다.',
                 '\n## 9. 모델 실험을 위한 권고사항',
                 '원본/512/256을 동일 제품 분할로 비교하되 작은 결함의 recall을 별도로 평가합니다. Train 전용 밝기 통계로 증강 후보를 만들고 validation으로 선택합니다. 클래스 불균형은 제품 단위 sampler와 macro 지표를 고려합니다. 5시점 입력은 시점별 encoder/late fusion을 후속 실험 후보로 두며 성능은 아직 측정하지 않았습니다. 이상탐지는 제품 AUROC/AUPRO·FPR 제한 recall, 객체탐지는 클래스 AP·소형 결함 recall을 기록합니다. 실제 모델 학습·속도 측정은 이번 범위에 없습니다.',
                 '\n## 10. 한계 및 후속 과제',
                 'Windows 결과 파일과 원래 split manifest가 없어 수치 동등성은 미검증입니다. 경로 중복 검사는 내용 중복 검사가 아닙니다. serial 재사용의 물리적 의미, 마스크의 완전 주석 여부, 촬영 배치별 차이를 확인해야 합니다. 팀원 4명의 실제 설치는 미검증입니다. 미생성 결과는 추정하지 않습니다.',
                 '\n## 재현',
                 f"입력: `{run['config']['root']}`. uv.lock SHA256: `{run['config']['lock_sha256']}`. Python 3.12, CPU. [run.json](run.json)에 실제 명령·소요시간·오류를 기록합니다.",
                 '```bash\nuv sync --locked\nuv run --locked python scripts/validate_environment.py --dummy\nuv run --locked pytest -q\n# 복사 완료 및 preflight 확인 후 새 실행:\nuv run --locked python -m mv_analysis.cli --data-root "$REALIAD_DATA_ROOT" run-all --full --transfer-complete\n```'])
    (out/'REAL_IAD_FINAL_ANALYSIS.md').write_text('\n\n'.join(text))
    return out/'REAL_IAD_FINAL_ANALYSIS.md'
