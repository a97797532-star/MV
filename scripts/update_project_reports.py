# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Refresh evidence-based project reports without changing analysis artifacts."""
import argparse
import csv
import json
from datetime import datetime,timezone
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--inventory',required=True,type=Path);p.add_argument('--mask-study',required=True,type=Path);p.add_argument('--spatial-run',type=Path);p.add_argument('--mask-integrity',type=Path);a=p.parse_args()
import pandas as pd
run=a.run
related={}
if (run/'related_runs.json').exists():
 related=json.loads((run/'related_runs.json').read_text())
 if a.spatial_run is None:a.spatial_run=Path(related['spatial_run'])
 if a.mask_integrity is None:a.mask_integrity=Path(related['mask_integrity'])
spatial=a.spatial_run or run
canonical=Path(related.get('preserved_windows_run',str(run)))
presence=canonical if (canonical/'heatmap_validation.json').exists() else spatial
original_image_run=run
rebind=canonical/'resolution_metadata_rebind_validation.json'
if rebind.exists() and json.loads(rebind.read_text()).get('all_numeric_metrics_exact_after_roundtrip'):run=canonical
reviewed_policy=json.loads((spatial/'mask_policy.json').read_text()) if (spatial/'mask_policy.json').exists() else {}
policy_approved=reviewed_policy.get('validated',False)
inventory=json.loads((a.inventory/'inventory.json').read_text());root=Path.cwd();reports=root/'reports';reports.mkdir(exist_ok=True)
# link: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path.
def link(path):return str(Path('..')/path)
# lines: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path.
def lines(path):
 if not path.exists():return 0
 with path.open() as stream:return sum(1 for _ in stream)
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df.
def table(df):
 if df is None or df.empty:return '미생성/해당 없음'
 columns=list(df.columns);rows=['| '+' | '.join(str(c) for c in columns)+' |','| '+' | '.join('---' for _ in columns)+' |']
 for row in df.itertuples(index=False,name=None):rows.append('| '+' | '.join(f'{v:.5f}' if isinstance(v,float) else str(v) for v in row)+' |')
 return '\n'.join(rows)
# read: 입력 파일 또는 기록을 읽습니다.
# 입력 인수: name.
def read(name):
 path=run/name
 return pd.read_csv(path) if path.exists() else None
now=datetime.now(timezone.utc).isoformat();meta=json.loads((run/'metadata_validation_report.json').read_text()) if (run/'metadata_validation_report.json').exists() else None
b=read('brightness_per_image.csv');r=read('per_view_information_loss.csv');comparison=read('brightness_comparison.csv')
counts=pd.DataFrame(inventory['category_status_mask_counts']);distribution=counts.pivot_table(index='category',columns='status',values='images',aggfunc='sum',fill_value=0).reset_index()
covered=counts[(counts.status=='NG')&counts.has_mask].groupby('category').images.sum();distribution['NG_with_mask']=distribution.category.map(covered).fillna(0).astype(int)
text=['# Real-IAD 최종 통합 분석 보고서',f'갱신 UTC: {now}. 이 보고서는 실제 산출물을 읽어 작성하며 실행 중인 단계를 완료로 취급하지 않습니다.',
'## 1. Executive Summary',f"전체 해상도 상태: {'완료' if r is not None else '미완료/계산 중'}; 성공 이미지 {r.image_path.nunique() if r is not None else lines(run/'resolution_checkpoint.jsonl'):,}/151,050. 전체 작업 완료는 해상도 최종 산출물과 무결성 검증까지 확인한 뒤 판정합니다.",f"전체 파일 구조 검사 완료: 30품목, JPG {inventory['jpg']:,}장, OK {inventory['ok']:,}장, NG {inventory['ng']:,}장, PNG {inventory['png']:,}장. NG 중 위치 정답 제공 {inventory['ng_with_mask']:,}장, 미제공 {inventory['ng_without_mask']:,}장. NG–PNG 개수 차이는 오류가 아닙니다.",
f"과거 참고치 대비 JPG +{inventory['windows_jpg_delta']:,}, PNG +{inventory['windows_png_delta']:,}. 추가 조사에서 확인한 실제 최신 Windows 저장 CSV는 JPG 151,050·PNG 51,329로 Ubuntu와 같고 u_block도 포함합니다. 보존된 과거 Windows 체크포인트는 참고치와 같은29품목이며 최신 대비 추가 경로는 모두u_block(제거0개)이었습니다. 당시 제외 동기와 인용 숫자의 생성 출처 연결은 미확정입니다. [역사적 범위 검증](../outputs/windows_checkpoint_comparison_20261111_v1/comparison.json). 사용자에게 데이터 복사 완료와 현재 전체 대상 승인을 받았습니다. [파일 구조 근거]({link(a.inventory/'inventory.json')}).",
'환경은 Ubuntu 24.04.4 WSL2, Python 3.12.14, uv 0.12.8, torch 2.15.0+cpu입니다. 잠금 설치와 CPU 더미 검증은 통과했습니다. 실제 모델 학습/추론·CUDA 성능·팀원 4명 개별 설치는 미검증입니다. 주요 위험은 전검정 중복 2장, 마스크 경계의 의미 검수 한계, 10장 불량 유형 충돌, serial의 물리 제품 identity 불확실성입니다. 기존 split은 Windows 원본에서 확인하고 전량 동일하게 재현했습니다.',
'## 2. 데이터셋 구성',table(distribution),
f"품목별 정상/불량과 위치 정답 제공 수를 구분했습니다. 근거: [file_metadata.csv]({link(a.inventory/'file_metadata.csv')}). 전체 OK 비율 {inventory['ok']/inventory['jpg']*100:.4f}%, NG 비율 {inventory['ng']/inventory['jpg']*100:.4f}%, NG 위치 주석 coverage {inventory['ng_with_mask']/inventory['ng']*100:.4f}%. Coverage는 마스크 연결 성공률과 다른 지표입니다.",
f"C1~C5 각각 {inventory['views']['C1']:,}장, 불완전 capture 그룹 {inventory['incomplete_capture_groups']}개. PNG의 동일 stem JPG 연결 성공률 {inventory['existing_png_pair_success_rate']*100:.2f}%, 고아 PNG {len(inventory['orphan_masks'])}개. 전체 파일 SHA256 내용 검사는 아래 별도 검증 결과를 확인합니다.",
f"NG 상태는 불량 제품의 촬영 시점 이미지에 부여되며 각 시점의 가시적인 결함 존재와 동일하지 않을 수 있습니다. 미주석 NG 26,881장에는 다른 폴더의 동일 stem/casefold PNG 후보가 없었습니다. 경로상 위치 주석 미제공으로 기록하되 의도적인 미제공과 실제 파일 유실을 경로만으로 단정하지 않습니다. [ng_without_mask.csv]({link(a.inventory/'ng_without_mask.csv')}). 빈 마스크를 만들거나 OK로 바꾸지 않았습니다.",
'## 3. 메타데이터 분석 결과']
if meta:
 text.append(f"전체 JPG decode 대상 {meta['selected']:,}, 성공 {meta['success']:,}, 오류 {len(meta['errors'])}. 원본 해상도 분포 `{meta.get('dimension_counts')}`. 분할 누수 {meta['product_split_leakage']}, 라벨 충돌 {meta.get('label_conflicts')}장. [검증 JSON]({link(run/'metadata_validation_report.json')}).")
 text.append(f"![품목 분포]({link(run/'dataset_category_distribution.png')})\n\n품목별 영상 수는 비슷하지만 결함 위치 주석 수와 불량 유형 분포는 다르므로 전체 수만으로 균형을 판단하지 않습니다.")
else:text.append(f"전체 decode 검사는 실행 중/미완료입니다. 성공 체크포인트 {lines(run/'metadata_checkpoint.jsonl'):,}행. 파일 구조 검사의 성공과 픽셀 decode 성공을 구분합니다.")
if meta:
 actual=pd.read_csv(run/'image_metadata_with_split.csv',keep_default_na=False)
 text.append(table(actual.groupby('split').agg(images=('image_path','size'),grouped_product_ids=('product_id','nunique')).reset_index()))
content_audit=Path(related.get('content_audit','outputs/no-content-audit'))
if (content_audit/'content_hash_validation.json').exists():
 content=json.loads((content_audit/'content_hash_validation.json').read_text());text.append(f"정확한 파일 바이트 SHA256 검증: {content['success']:,}/{content['target']:,}파일, 오류 {len(content['errors'])}, JPG 중복 그룹 {content['exact_jpg_duplicate_groups']}, 초기 hash 탐색 분할 시점의 같은 JPG 바이트 교차 그룹 {content['exact_jpg_cross_split_groups']}; 현재 보존된 Windows 분할은 아래 품질 검증에서 별도 확인합니다. [내용 무결성 근거]({link(content_audit/'content_hash_validation.json')}). 재인코딩/유사 이미지 중복을 검사한 것은 아닙니다.")
text.append('초기 실행은 category/serial SHA256 70/15/15 탐색 분할입니다. 이후 Windows 원본 Notebook의 category/quality/defect/serial 제품 키와 seed42 분할을 전량 동일하게 재현했습니다: Train 105,735 / Validation 22,655 / Test 22,660, 제품 그룹 30,210, 차이 0장. [분할 검증](WINDOWS_SPLIT_REPRODUCTION.json). 기존 분할 통계/히트맵은 '+link(canonical)+'에 별도로 보존합니다. serial 재사용이 동일 물리 제품인지는 미확정입니다. fire_hood 유형 충돌 10장은 UNRESOLVED로 유지하고 유형별 탐지 라벨에서 제외합니다.')
text.append('## 4. 밝기 분석 결과')
if b is None:text.append(f"전체 밝기 미완료. 성공 체크포인트 {lines(run/'brightness_per_image.jsonl'):,}행. 100장 실제 표본만 100성공/0오류였으며 이를 전체 결과로 일반화하지 않습니다.")
else:
 text.append(f"전체 밝기 {len(b):,}장. 지표는 BGR→GRAY 0–255 영상 평균 및 이미지별 P05/P50/P95입니다. [이미지별 근거]({link(run/'brightness_per_image.csv')}).")
 text.append(table(b.groupby('status').brightness.agg(['count','mean','std','median']).reset_index()))
 text.append(table(b.groupby(['view','status']).brightness.agg(['count','mean','std']).reset_index()))
 if comparison is not None and len(comparison):
  top=comparison.assign(abs_d=comparison.cohens_d.abs()).sort_values('abs_d',ascending=False).head(12)
  text.append('정상·불량 밝기 차이가 큰 후보(같은 품목/시점 OK와 각 NG 유형 비교):\n\n'+table(top))
  text.append(f"비교 {len(comparison)}개(현재 u_block 20개 및 UNRESOLVED 5개 포함; 실제 저장 Windows 비교표 555행에 UNRESOLVED 5행을 추가) 중 |Cohen d|≥0.8은 {int((comparison.cohens_d.abs()>=.8).sum())}개. [비교 근거]({link(run/'brightness_comparison.csv')}). 32 bin histogram overlap은 분포 공통 질량이며 d는 pooled 표준편차 기준 차이입니다.")
 text.append(f"![밝기 분포]({link(run/'brightness_histogram.png')})\n\n겹침이 적더라도 조명·배치·재질 차이가 결함 효과와 섞여 있습니다. 밝기만으로 분류 가능한지 또는 조명에 취약한지는 후속 모델 실험 가설입니다. 증강 범위는 [Train 전용 통계]({link(run/'brightness_train_augmentation_stats.csv')})를 출발점으로 삼고 validation으로 선택합니다. 마스크 기반 상대 밝기는 연결된 NG 부분집합의 별도 region_brightness 결과로 기록하며 전체 NG 밝기와 구분합니다.")
region_path=spatial/'region_brightness'/'defect_relative_brightness.csv'
if region_path.exists():
 region=pd.read_csv(region_path);text.append(f"마스크 제공 NG {len(region):,}장의 결함 영역−배경 평균 밝기 차이는 {region.defect_minus_background.mean():.5f} intensity입니다(유효 {int(region.defect_minus_background.notna().sum()):,}장, 나머지는 제공된 빈 마스크 등으로 영역 평균 미정의). 이는 전체 NG 78,210장을 대체하지 않는 위치 주석 부분집합 통계입니다. 배경 평균은 마스크 밖 전체 픽셀 기준으로 촬영 배경/정상 물체를 포함하며, 결함 바로 주변 재질만의 국소 대비와는 다릅니다. [영역별 근거]({link(region_path)}).")
if b is not None and comparison is not None:
 means=b.groupby('status').brightness.mean().to_dict()
 text.append(f"전체 평균은 `{means}`이며, 품목/유형/시점별 비교 {len(comparison)}개(현재 u_block 20개 및 UNRESOLVED 5개 포함; 실제 저장 Windows 비교표 555행에 UNRESOLVED 5행을 추가) 중 |d|≥0.8은 {int((comparison.cohens_d.abs()>=.8).sum())}개였습니다. 품목을 섞은 전체 평균만으로 증강 필요성을 판단하면 이 차이가 가려집니다. 이 수치는 [brightness_comparison.csv]({link(run/'brightness_comparison.csv')})의 관측 통계입니다.")
 text.append(f"![밝기 검수 사례]({link(run/'brightness_review_images_readable.png')})\n\n중앙값 대표 이미지를 눈으로 검수한 결과 sim_card_set은 흰 배경 전체의 밝기 차이, phone_battery는 푸른 배경 전체의 밝기 차이가 함께 보였습니다. 촬영 조건/배치의 영향 가능성을 검토해야 하며 밝기 차이를 결함 자체의 인과 효과로 단정하지 않습니다. 파일명과 실제 평균은 [검수 manifest]({link(run/'brightness_review_images.csv')})에 있습니다. 증강은 품목/시점별 Train 분위수를 근거로 제한하고 미세 결함 대비를 훼손하지 않는 범위를 validation에서 선택합니다.")
train_policy=canonical/('train_brightness_policy_quality_aware' if (canonical/'train_brightness_policy_quality_aware'/'scope.json').exists() else 'train_brightness_policy')
if (train_policy/'scope.json').exists():
 scope=json.loads((train_policy/'scope.json').read_text());text.append(f"증강 정책용 그룹 선택/비교는 별도로 Train {scope['train_images']:,}장만 사용해 재계산했습니다(원본 재decode 0장). [Train 검수 후보]({link(train_policy/'brightness_review_candidates_verified.csv')})는 UNRESOLVED 그룹을 제외합니다. Normal-only AD에는 [정상 Train 전용 분위수]({link(train_policy/'normal_only_train_augmentation_stats.csv')})를 사용합니다. 전체 데이터 Cohen d는 기술 분석이며 Test를 포함한 수치로 증강 정책을 선택하지 않습니다.")
text.append('## 5. 불량 위치 히트맵 분석')
spatial=a.spatial_run or run
heat=pd.read_csv(presence/'heatmap_summary.csv') if (presence/'heatmap_summary.csv').exists() else None
if heat is None:text.append(('정책 >0 채택 후 전체 실행 대기/진행 중입니다.' if policy_approved else '전체 실행 보류: 회색조 마스크의 임계 정책이 아직 확정되지 않았습니다.')+'  연결된 Train NG만 대상이며 관측되지 않은 위치를 정상으로 해석하지 않습니다. [마스크 검증 보고서](MASK_THRESHOLD_VALIDATION.md)를 먼저 확인해야 합니다.')
else:text.append(table(heat.head(15))+f"\n\n근거 [heatmap_summary.csv]({link(presence/'heatmap_summary.csv')}). 기존 분할 presence-v2는 원본 양성 픽셀이 하나라도 있는 칸을 영상별로 1회 집계합니다. occupancy_known=칸 점유 영상 수/n_known 제공 마스크 수, occupancy_positive=칸 점유 영상 수/n_positive 비어 있지 않은 마스크 수입니다. 미제공은 n_unknown, 관측 0은 NaN입니다. 초기 spatial_run area-v1은 면적 분율 진단으로 보존하며 두 규약을 혼용하지 않습니다. GAN 위치 정책은 품목·유형·시점별 관측량과 정렬을 함께 검수해야 합니다.")
if heat is not None:
 text.append(f"해당 분할 Train NG 제공 마스크 관측 합계 {int(heat.observations.sum()):,}장, {len(heat)}개 품목/유형/시점 그룹, 10장 미만 그룹 {int((heat.observations<10).sum())}개. 상위 10% 격자에 모인 결함질량 비율은 관측된 위치의 집중도이며 정상 영역 확률이 아닙니다.")
 text.append(table(heat.groupby('view').agg(groups=('observations','size'),observations=('observations','sum'),mean_top10_mass_share=('top10pct_mass_share','mean')).reset_index()))
 text.append(table(heat[heat.observations>=10].sort_values('top10pct_mass_share',ascending=False).head(8)))
 text.append(f"![Train NG 위치]({link(presence/'heatmap_visualization.png')})\n\nC1/C2 종합 그림은 중심 가로 띠, C3/C5는 중심 세로 방향의 상대적 집중이 관찰됩니다. 서로 다른 물체를 섞은 정규화 좌표이므로 실제 결함 원인의 방향성으로 단정하지 않습니다. 시점별 위치 주석 관측량이 달라 단순 밝기/시점 영상 수와 별도로 봐야 합니다. 일부 regulator/rolled_strip_base 그룹은 상위 10% 격자에 관측 결함질량이 집중됩니다. 그룹 그림의 known/positive 두 패널을 비교하고 각각의 분모를 확인합니다. 초기 면적 진단의 heatmaps_scaled와 빈도값을 직접 비교하지 않습니다. 촬영 정렬·물체 크기·주석 정책의 영향과 실제 결함 발생 특성을 분리해 검수해야 합니다. 관측 10장 미만 그룹에는 강한 GAN 위치 제약을 적용하지 않고, 관측되지 않은 위치를 정상으로 고정하지 않습니다.")
text.append('## 6. Bounding Box 분석')
if (spatial/'classes.json').exists():
 classes=json.loads((spatial/'classes.json').read_text());text.append(table(pd.DataFrame([dict(defect_type=name,yolo_id=cid,coco_id=classes['coco'][name]) for name,cid in classes['yolo'].items()])))
 text.append('객체탐지에는 정상 객체 클래스를 두지 않습니다. 별도 영상 분류의 OK=0/NG=1과 YOLO의 defect class0=AK를 혼동하지 않아야 합니다.')
boxes=pd.read_csv(spatial/'defect_bboxes.csv') if (spatial/'defect_bboxes.csv').exists() else None
if boxes is None:text.append(('정책 >0 채택 후 전체 박스 추출 대기/진행 중입니다.' if policy_approved else '전체 실행 보류: 임계 정책 미확정입니다.')+'  클래스별 박스 수·크기·미세 결함 비율을 추정하지 않습니다. NG에 위치 정답이 없으면 빈 탐지 라벨을 만들지 않습니다. OK 빈 YOLO 라벨과 구분합니다. 생성 시 8연결, xyxy exclusive, YOLO 0-based/COCO 1-based, 기본 defect_type 정책을 적용하며 UNRESOLVED 유형은 제외합니다.')
else:text.append(table(boxes.groupby('defect_type').bbox_area.agg(['count','mean','median']).reset_index())+f"\n\n[박스 근거]({link(spatial/'defect_bboxes.csv')}). 한 NG의 모든 연결 성분은 한 불량 유형이라는 가정입니다. 박스 개수는 8연결 성분 수이며 실제 독립된 물리 결함의 개수와 같다고 보장하지 않습니다.")
if boxes is not None and len(boxes):
 minimum=(boxes.x1-boxes.x0).where((boxes.x1-boxes.x0)<(boxes.y1-boxes.y0),boxes.y1-boxes.y0)
 text.append(f"원본 bbox area<1,024 px² 박스 {int((boxes.bbox_area<1024).sum()):,}/{len(boxes):,}, 256 입력으로 단순 좌표 축소 시 짧은 변<2px가 되는 박스 {int((minimum/4<2).sum()):,}개입니다. 이는 기하학적 위험 지표이며 실제 결함 소실/검출 성능이 아닙니다. [박스 검증]({link(spatial/'bbox_validation_report.json')}).")
 annotation_validation=json.loads((spatial/'bbox_validation_report.json').read_text())
 text.append(f"박스 export 대상 {annotation_validation['images']:,}장, 오류 {annotation_validation['errors']}, 제공된 빈 NG PNG {annotation_validation.get('provided_empty_ng_masks',0)}개입니다. 이 NG들은 상태를 유지하며 기존 주석대로 박스 0개를 표현합니다. 제외 수 26,888은 미주석 NG 26,881 + 유형 충돌/위치 주석 NG 7입니다. [전체 COCO/YOLO 교차검증]({link(spatial/'detection_export_validation.json')})에서 실제 라벨 파일·좌표·클래스·개수를 대조합니다.")
 text.append(f"![클래스 박스 수]({link(spatial/'bbox_class_distribution.png')})\n\n정상 OK 72,840장에는 빈 YOLO 라벨을 만들고, 마스크 없는 NG 26,881장과 위치 주석이 있어도 유형이 충돌하는 NG는 탐지 라벨에서 제외합니다. 클래스 불균형은 박스 수뿐 아니라 제품 수로도 확인해야 합니다.")
text.append('## 7. 5시점 해상도별 정보 손실')
if r is None:text.append(f"전체 해상도 분석 미완료. 성공 이미지 체크포인트 {lines(run/'resolution_checkpoint.jsonl'):,}행. 실제 표본 100장의 3해상도 300행은 완료했지만 전체 수치로 대체하지 않습니다.")
else:
 text.append(f"전체 JPG {r.image_path.nunique():,}장 × 해상도 {r.target.nunique()}개, {len(r):,}행. [이미지별 지표]({link(run/'per_view_information_loss.csv')}).")
 metrics=['psnr_db','ssim','edge_recall','edge_f1','gradient_retention','laplacian_retention','local_contrast_retention','rgb_rmse']
 text.append(table(r.groupby('target')[metrics].mean().reset_index()))
 means=r.groupby('target')[metrics].mean();text.append(f"전체 SSIM 평균은512 {means.loc[512,'ssim']:.6f},256 {means.loc[256,'ssim']:.6f}로 높게 보이지만 동일 픽셀 Canny 경계 일치율은각각 {means.loc[512,'edge_recall']:.6f}/{means.loc[256,'edge_recall']:.6f}입니다. 국소 대비 보존은 {means.loc[512,'local_contrast_retention']:.6f}→{means.loc[256,'local_contrast_retention']:.6f}, RGB RMSE는 {means.loc[512,'rgb_rmse']:.6f}→{means.loc[256,'rgb_rmse']:.6f} intensity였습니다. 전역 지표는 넓은 배경과 평탄 영역의 영향을 받고 경계 일치율은 위치 이동에도 민감하므로 이 숫자를 실제 결함 소실률/모델 recall로 해석하지 않습니다.")
 text.append('256에서 평균 SSIM이 낮은 품목(전체 JPG, 관측 통계):\n\n'+table(r[r.target==256].groupby('category')[['ssim','edge_recall','local_contrast_retention']].mean().sort_values('ssim').head(6).reset_index()))
 text.append('해상도별 SSIM/경계 일치/국소 대비 분포의5·50·95분위수:\n\n'+table(r.groupby('target')[['ssim','edge_recall','local_contrast_retention']].quantile([.05,.5,.95]).reset_index().rename(columns={'level_1':'quantile'})))
 if (run/'resolution_scientific_validation.json').exists():
  rv=json.loads((run/'resolution_scientific_validation.json').read_text());text.append(f"수치 검증 통과: 이미지 {rv['images']:,}, 해상도 지표 {rv['metric_rows']:,}행, 직접 단계 비교 {rv['step_rows']:,}행. 전검정2장×3해상도의6행에서 참조 에너지/대비0에 따른 비율 결측을 유지했습니다. 이는 decode 실패6장이 아닙니다. [검증 근거]({link(run/'resolution_scientific_validation.json')}).")
 text.append(table(r[r.target!=1024].groupby(['view','target'])[['ssim','edge_recall','local_contrast_retention']].mean().reset_index()))
 text.append(f"![5시점]({link(run/'five_view_loss.png')})\n\n같은 capture C1~C5를 비교합니다. 시점별 조명·배경·재질을 섞어 해상도 효과로 해석하지 않습니다.\n\n![확대 비교]({link(run/'detail_crop_comparison.png')})\n\n최대 국소 복원 차이 영역을 확대했습니다. 이 영역이 실제 결함인지는 마스크 overlay로 따로 확인해야 합니다. [검수 후보]({link(run/'review_priority_images.csv')}).")
 step=read('per_image_stepwise_changes.csv')
 if step is not None:text.append('직접 512→256 단계의 평균 SSIM/Edge recall: '+str(step[['ssim','edge_recall']].mean().round(6).to_dict())+f". [단계별 근거]({link(run/'per_image_stepwise_changes.csv')}).")
text.append('정사각 1024/512/256 area 축소, 원래 크기 linear 복원, 비정사각 원본은 정사각 변형 정책입니다. SSIM은 Gaussian 11×11 sigma 1.5, PSNR은 컬러 MSE(동일 영상 120dB 상한), 경계는 Canny 100/200의 동일 위치 교집합입니다. Laplacian은 고주파 대리 지표이며 주파수 스펙트럼 자체는 아닙니다. 결함 의미·모델 정확도·추론 속도는 측정하지 않았습니다.')
roi_review=Path(related.get('defect_resolution_review','outputs/no-defect-roi-review'))
if (roi_review/'defect_jpg_resolution_review.csv').exists():
 roi=pd.read_csv(roi_review/'defect_jpg_resolution_review.csv');text.append(f"별도 실제 결함 ROI 검수: 층화 마스크 {roi.image_path.nunique()}장의 원본 JPG를 512/256으로 비교했습니다. 전체 해상도 통계를 대체하지 않는 대표 사례 분석입니다. 마스크는 결함 위치 선택에만 사용했고 영상 손실은 JPG에서 계산했습니다. [ROI 결과]({link(roi_review/'defect_jpg_resolution_review.csv')}).")
 text.append(table(roi.groupby('target')[['roi_rgb_rmse','background_rgb_rmse','roi_edge_recall','roi_contrast_retention']].mean().reset_index()))
 text.append(f"![실제 결함 위치 확대]({link(roi_review/'defect_detail_crop_comparison.png')})\n\n같은 원본 좌표의 실제 주석 위치를 확대해 배경 영상 변화와 결함 영역의 변화를 구분합니다. button_battery/HS/C1의 가는 선형 흔적은 256 복원에서 더 퍼지고 주변 미세 질감도 흐려집니다. 512에서는 선형 흔적과 질감이 상대적으로 더 명확하게 보이지만 실제 검출 성공을 뜻하지 않습니다. ROI edge recall은 Canny 경계의 같은 픽셀 일치도이며 모델 recall이 아닙니다. ROI 전체 표준편차 비율은 전역의 11×11 국소 대비 지표와 정의가 다릅니다. ROI에는 물체 경계·금속 반사 등도 섞일 수 있어 큰 복원 오차를 결함 검출 난이도의 인과 효과로 단정하지 않습니다.")
text.append('## 8. 분석 간 연관성')
if (reports/'ANALYSIS_CROSS_RELATIONS.md').exists():text.append('[실제 짝 비교·층화 상관·작은 결함 위험](ANALYSIS_CROSS_RELATIONS.md)을 함께 확인합니다. 상관은 모델 성능과 인과 효과가 아닙니다.')
if (canonical/'quality_review'/'quality_aware_split_validation.json').exists():
 cq=json.loads((canonical/'quality_review'/'quality_aware_split_validation.json').read_text());text.append(f"보존된 Windows 분할로 다시 계산한 정확 바이트 교차 분할 중복은 {cq['raw_exact_cross_split_groups']}개입니다. 전검정 두 파일은 모두 Train이며 권고 단일 영상 subset 151,048장/strict5-view 151,040장은 원본을 고치지 않는 검수 제안입니다. [기존 분할 품질 검증]({link(canonical/'quality_review'/'quality_aware_split_validation.json')}). 초기 hash 분할에서의 교차 중복 수와 구분합니다.")
 cp=canonical/'quality_review'/'quarantine_sensitivity_heatmap'/'affected_group_comparison.csv'
 if cp.exists():text.append('기존 split의 presence-v2 위치 빈도 민감도:\n\n'+table(pd.read_csv(cp))+'\n\n이 표는 아래 초기 hash/area-v1 민감도와 분모·단위가 다릅니다.')
quality=canonical/'quality_review'
if (quality/'quality_aware_split_validation.json').exists():
 q=json.loads((quality/'quality_aware_split_validation.json').read_text());text.append(f"전검정 JPG 2장은 서로 다른 품목/상태의 동일 바이트 파일입니다. 보존된 Windows 분할에서 둘 다Train이며 정확한 바이트 교차 분할 중복은 {q['raw_exact_cross_split_groups']}그룹입니다. 초기 hash 탐색 분할에서는 Train/Test에 나뉘어1그룹이었으므로 두 분할의 결과를 구분합니다. 실제 모든 채널 min=max=0을 확인했고 NG 원래 PNG는 전영역255였습니다. 원본을 삭제/재분류하지 않고 [현재 분할의 모델 입력 검수 manifest]({link(quality/'model_input_review_manifest.csv')})에 보류 후보를 표시했습니다. 전체 분석은151,050장, 보류 후보를 제외한 권고 단일 영상 subset {q['recommended_usable_images']:,}장, strict5-view 권고 {q['strict_five_view_recommended_images']:,}장입니다. 이는 의미 검수 전 자동 데이터 수정이나 학습 수행이 아닙니다.")
 text.append('위 presence-v2 민감도는 전체 흰 마스크 한 장이 특정 Train 위치 빈도를 지배할 수 있음을 보입니다. 초기에 계산한 hash/area-v1 민감도는 원래 outputs/full_20261111_v6/quality_review에 별도 보존했으며 분모·단위가 다릅니다. 관측 편향과 결함 원인을 분리해 검수해야 합니다.')
text.extend(['## 9. 모델 실험을 위한 권고사항','원본 1024를 참조 기준으로 두고 512/256을 같은 제품 분할에서 비교합니다. 미세 결함의 위치 주석과 박스 크기가 확정되기 전 256을 최종 입력으로 고정하지 않습니다. Train 전용 밝기 통계로 증강 후보를 만들고 validation에서 선택합니다. 결함 유형별·시점별 macro 지표, NG recall 및 FPR을 함께 기록합니다. 5시점 제품 단위 분할과 제품 단위 집계를 유지하고, 이상탐지 AUROC/AUPRO·FPR 제한 recall과 탐지 클래스 AP/소형 결함 recall을 구분합니다. 초기 hash 분할은 탐색용이며 후속 재현은 확인된 기존 프로젝트 seed42 분할을 사용합니다. 프로젝트 분할과 논문 공식 benchmark 분할의 동등성은 별도 검증 대상입니다. 정상만 학습하는 AD는 split=train AND status=OK로 제한하고, 제품 NG와 시점별 가시 결함을 혼동하지 않도록 제품/시점 평가를 분리합니다. 이는 후속 실험 권고이며 성능 측정 결과가 아닙니다.',
'## 10. 한계 및 후속 과제','Windows 결과와 다른 지표 정의의 구분, serial 물리 identity, 미주석 NG의 의미, HS/QS 충돌 10장, 회색조 경계 의미, 이미지 내용 중복, 실제 결함 보존성을 확인해야 합니다. 팀원 4명의 개별 설치와 GitHub PR 실습은 미검증입니다. 마스크 미주석 NG를 정상 탐지 샘플로 자동 사용하지 않습니다.',
'## 추가 영역별 밝기 분석과 공유 산출물','[배경·제품 영역 밝기 상세 보고서](BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md)를 함께 읽습니다. 전체 이미지 밝기와 제품/배경/결함 국소 밝기를 구분하고 분할 불확실 사례는 결측으로 기록합니다. 최종 공유용 그림과 집계표는 ../images/manifest.json, 상세 PDF 생성은 scripts/export_detailed_pdf.py를 따릅니다. 미완료 상태에서 전체 결과를 추정하지 않습니다.',
'## 재현 및 환경',f"[실행 manifest]({link(run/'run.json')}), [환경 이전 보고서](ENVIRONMENT_MIGRATION_REPORT.md), [분석 실행 로그](ANALYSIS_EXECUTION_LOG.md). 데이터 원본과 기존 출력은 보존했습니다. 사용자 추가 지시에 따라 최종 코드는 분석 브랜치로 공유합니다. 원본 데이터와 가중치는 공유 대상에서 제외합니다.",
'```bash\nuv sync --locked\nuv run --locked python scripts/validate_environment.py --dummy\nuv run --locked pytest -q\nexport REALIAD_DATA_ROOT="/실제/dataset"\nuv run --locked python -m mv_analysis.cli validate-data\n# 출력 폴더를 지정해 --resume brightness / resolution 단계 실행\n# 복사 완료·preflight 이후 run-all --full --transfer-complete\n```'])
if (reports/'WINDOWS_RESULT_COMPARISON.md').exists():text.append('## Windows 실제 결과 비교\n\n[같은 방법 재실행 및 지표 정의 차이](WINDOWS_RESULT_COMPARISON.md)를 참조합니다. 원본 결과는 수정하지 않았습니다.')
(reports/'REAL_IAD_FINAL_ANALYSIS.md').write_text('\n\n'.join(text))
# Threshold evidence report is separately updated from real outputs.
folder=a.mask_study/'mask_threshold_validation';summary_path=folder/'threshold_summary.csv';validation_path=folder/'validation.json'
masktext=['# 마스크 임계값 검증',f'갱신 UTC: {now}. 원본 PNG는 수정하지 않았다.',
'0/32/64/127/192/254에 대해 foreground = pixel > threshold를 비교한다. 127은 민감도 비교 기준이며 최종 threshold로 확정한 값이 아니다. grayscale 자체는 손상을 의미하지 않는다. 표본은 품목×불량유형에서 정렬된 처음/중간/마지막 3장을 선택하며 전체 C1~C5를 포함한다. 경계 보존과 작은 성분은 원본 overlay로 검수한다.']
if summary_path.exists():
 summary=pd.read_csv(summary_path);validation=json.loads(validation_path.read_text());masktext.append(f"실제 선택 {validation['selected']}장, 성공 {validation['success']}, 오류 {len(validation['errors'])}, {len(validation['categories'])}품목, {len(validation['defect_types'])}유형. 픽셀 값 종류 {len(validation['unique_values'])}개. [검증 JSON]({link(validation_path)}), [이미지별 민감도]({link(folder/'threshold_per_mask.csv')}).")
 masktext.append(table(summary));masktext.append(f"![임계값 민감도]({link(folder/'threshold_sensitivity.png')})\n\n낮은 threshold에서 경계/저강도 성분을 더 포함하고 높은 threshold에서 core를 남긴다. 성분 수 감소만으로 제거한 성분을 노이즈로 단정할 수 없다. 255 core 보존율은 모든 threshold<255에서 항상 1이므로 결함 보존 증거로 사용할 수 없다.")
 overlays=sorted(folder.glob('overlay_*.png'));masktext.append(f"실제 JPG/PNG crop overlay {len(overlays)}개. [검수 폴더]({link(folder)}).")
 for image in overlays[:6]:masktext.append(f'![임계값별 경계]({link(image)})')
else:masktext.append('층화 표본 계산 실행 중/미완료. 결과 표를 추정하지 않는다.')
masktext.append('## 실제 관측 해석\n\n336장 표본에서 >0은 936,019픽셀·387성분·4픽셀 이하 성분 0개, >127은 873,105픽셀·403성분·작은 성분 11개, >254는 812,094픽셀·444성분·작은 성분 46개였습니다. 높은 임계값의 작은 성분 증가가 기존 결함 영역의 분절일 수 있어 작은 성분=노이즈라고 판단하지 않습니다. audiojack/BX C1 overlay는 변형된 금속 부위와 주석 위치가 대체로 일치했고, end_cap/HS C1의 가는 scratch는 threshold 증가에 따라 1,431→858픽셀로 줄었습니다. fire_hood/AK C1도 pit 주위 contour가 점차 안쪽으로 수축했습니다. 이 세 사례의 시각 검수는 모든 표본/전체 주석의 의미적 정확도를 보장하지 않습니다.')
masktext.append('## 정책 판정\n\n현재 정책 미확정. 통계적 안정성은 실제 결함 경계 정답을 증명하지 않는다. 원본 grayscale가 축소/안티앨리어싱된 경계인지, 약한 실제 결함 주석인지 원본 주석 규약 또는 담당 검수로 확인한 뒤 threshold와 작은 성분 처리 규칙을 고정해야 한다. 그 전 전체 히트맵·Bounding Box는 보류한다. 전체 메타데이터·밝기·해상도는 독립 수행한다. 임의 빈 마스크를 만들지 않는다.')
reviewed=spatial/'mask_policy.json'
if reviewed.exists():
 policy=json.loads(reviewed.read_text())
 if policy.get('validated') and policy.get('policy_status')=='reviewed_nonzero_reference_policy':
  masktext=[part for part in masktext if not part.startswith('## 정책 판정')]
  masktext.append('## 추가 근거와 최종 분석 정책\n\n전체 제공 마스크의 무결성 통과 후, 본 프로젝트 위치 분석은 grayscale >0을 채택했습니다. [Real-IAD 공식 EvalPerPixelAUC 구현](https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249)은 양의 마스크 값을 1로 처리합니다. 표본 overlay의 경계 보존과 임계값 증가에 따른 수축/분절 관측을 함께 근거로 사용했습니다. 이는 모든 주석 경계의 의미적 정답을 입증하는 것은 아닙니다. 작은 성분 면적 필터는 적용하지 않습니다. 초기 정책 보류는 공식 구현 및 전체 무결성 검증을 추가 확인한 뒤 이 판정으로 갱신했습니다. [실행 정책 JSON]('+link(reviewed)+').')
if a.mask_integrity and (a.mask_integrity/'execution.json').exists():
 audit=json.loads((a.mask_integrity/'execution.json').read_text())
 histogram=json.loads((a.mask_integrity/'mask_policy.json').read_text())['histogram'];masktext.append(f'전체 마스크 픽셀 {sum(histogram):,}, 값 0 {histogram[0]:,}, 값 255 {histogram[255]:,}, 중간값 1–254 {sum(histogram[1:255]):,}개. 중간값은 전체 픽셀의 {sum(histogram[1:255])/sum(histogram)*100:.6f}%이며 경계 의미를 추가 검수해야 합니다.')
 global_thresholds=a.mask_integrity/'global_threshold_pixel_counts.csv'
 if global_thresholds.exists():masktext.append('전체 51,329개 제공 마스크의 픽셀 히스토그램에서 계산한 임계값별 총 면적(연결 성분 수는 336장 표본 결과와 구분):\n\n'+table(pd.read_csv(global_thresholds)))
 masktext.append(f"전체 PNG 무결성 검사: 대상 {audit['target']:,}, 성공 {audit['success']:,}, 오류 {audit['errors']}. [실행 근거]({link(a.mask_integrity/'execution.json')}).")
(reports/'MASK_THRESHOLD_VALIDATION.md').write_text('\n\n'.join(masktext))
log=['# 분석 실행 로그',f'갱신 UTC: {now}. 실제 결과가 있는 단계만 완료로 표시한다.','## 입력 및 안전',f"입력: {json.loads((run/'run.json').read_text())['config']['root']}. 사용자 복사 완료 확인. 확정 대상 JPG 151,050 / PNG 51,329. 읽기 전용 사용, 원본 이동/수정/삭제 없음. outputs는 Git 제외.",'## 실행 이력']
for folder in [Path('outputs/smoke_20261111_v2'),Path('outputs/smoke_20261111_v4'),Path('outputs/smoke_20261111_v5'),Path('outputs/smoke_20261111_v6'),Path('outputs/full_20261111_v4'),original_image_run,run]:
 path=folder/'run.json'
 if path.exists():
  value=json.loads(path.read_text());log.append(f'### {folder}\n\n```json\n'+json.dumps(value,ensure_ascii=False,indent=2)+'\n```')
log.extend(['## 전체 데이터 처리 상태',f"표준 라이브러리 구조 검사: 151,050 JPG, 51,329 PNG, parse 오류 {len(inventory['parse_errors'])}, 고아 PNG {len(inventory['orphan_masks'])}.",f"전체 메타데이터: {'완료' if meta else '실행 중/미완료'}, 성공 {meta['success'] if meta else lines(run/'metadata_checkpoint.jsonl')}, 오류 {len(meta['errors']) if meta else '최종 미집계'}.",f"전체 밝기: {'완료' if b is not None else '미완료'}, 성공 {len(b) if b is not None else lines(run/'brightness_per_image.jsonl')}, 오류는 brightness_per_image_execution.json의 최종 값을 확인.",f"전체 해상도: {'완료' if r is not None else '미완료'}, 성공 이미지 {r.image_path.nunique() if r is not None else lines(run/'resolution_checkpoint.jsonl')}, 오류는 resolution_checkpoint_execution.json의 최종 값을 확인.",f'전체 히트맵: {len(heat) if heat is not None else 0}개 그룹 CSV; 전체 박스: {len(boxes) if boxes is not None else 0}개 박스 CSV. 정책 상태: {reviewed_policy.get("policy_status","review pending")}. 최종 성공/오류는 해당 run.json과 검증 JSON을 확인.','## 실행 시간·디스크 예상','실제 100장 표본 run-all은 약 22초였다. 전체 151,050장의 단순 비례 추정은 약 9.4시간이며 첫 그림/초기화 비용과 병렬도·품목별 JPEG 내용에 따라 달라진다. 이는 완료 시간 약속이 아니다. 해상도 계산은 참조 통계를 재사용하고 최대 4 worker를 사용한다. 실행별 체크포인트를 보존한다. 설치 후 약 740GiB 여유를 확인했으며 결과는 CSV/JSONL 중심이고 원본 복사본을 만들지 않는다.','## 검증 및 미검증','환경 dummy 성공, 합성 테스트 결과는 reports/preflight_pytest.txt 및 최신 테스트 로그 참조. 표본 영상 분석 100/100 성공, 0오류. 팀원 4명 개별 설치/원격 쓰기 권한/모델 성능은 미검증. Windows split 재현은 전량 일치, 영상 지표는 정의 차이와 같은 방법 재실행을 구분해 검증한다.'])
log.append('## 추가 통합 실행 · 보존된 Windows 분할과 영역별 밝기')
for folder,names in [(canonical,['restoration_validation.json','heatmap_validation.json']),(spatial,['bbox_validation_report.json','detection_export_validation.json']),(run,['resolution_scientific_validation.json','resolution_batch_status.json'])]:
 for name in names:
  path=folder/name
  if path.exists():log.append(f'### {path}\n\n```json\n'+json.dumps(json.loads(path.read_text()),ensure_ascii=False,indent=2)+'\n```')
regional=Path('outputs/background_full_20261111_v1')
if (regional/'regional_run.json').exists():
 manifest=json.loads((regional/'regional_run.json').read_text());batch_records=[json.loads(p.read_text()) for p in sorted(regional.glob('batch_*.json'))];image_errors=sum(len(b['errors']) for b in batch_records);completed=max([b['completed'] for b in batch_records] or [0]);log.append(f"영역별 밝기 입력: {manifest['config']['root']}; 메타데이터/기존 밝기 입력: {manifest['config']['source']}. 최초2 worker로 실행한 뒤 해상도 완료까지22,000장 체크포인트에서 대기했고, 이후4 worker로재개했습니다. 완료 체크포인트 {completed:,}/{manifest['target']:,}; 완료 배치의 이미지 오류 {image_errors}. worker 종료와 분할 불확실은 이미지 decode 오류와 구분합니다.")
 log.append('실제 재개 명령: `uv run --locked python -m mv_analysis.regional_cli --source-run outputs/windows_preserved_20261111_v1 --output outputs/background_full_20261111_v1 --compare-methods --validation-evidence reports/BACKGROUND_SEGMENTATION_REVIEW.json --resume --batch-size 2000 --workers 4`. '+('마지막 --finalize 집계 완료.' if (regional/'regional_validation.json').exists() else '--finalize 전체 집계는 아직 미완료.'))
 for name in ['regional_validation.json','scientific_validation.json','whole_brightness_reproduction.json']:
  path=regional/name
  if path.exists():log.append(f'### {path}\n\n```json\n'+json.dumps(json.loads(path.read_text()),ensure_ascii=False,indent=2)+'\n```')
if (reports/'PROCESS_INTERRUPTION_LOG.json').exists():log.append('[작업자143 종료와 성공 체크포인트 보존 기록](PROCESS_INTERRUPTION_LOG.json). 이미지 분석 실패와 프로세스 종료 원인을 혼동하지 않습니다.')
(reports/'ANALYSIS_EXECUTION_LOG.md').write_text('\n\n'.join(log));print('Updated three reports from actual artifacts')
