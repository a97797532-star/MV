# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Numerical, split, input-hash and frozen-policy validation; no retuning/inference."""
import json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
B=Path('outputs/object_aware_crop_v1')
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 cfg=json.loads((B/'config.json').read_text());sample=pd.read_csv(B/'sample_manifest.csv');dev=pd.read_csv(B/'metrics/per_image_development.csv',low_memory=False);hold=pd.read_csv(B/'metrics/per_image_holdout.csv',low_memory=False);d=pd.concat([dev,hold],ignore_index=True);frozen=json.loads((B/'frozen_policy.json').read_text())
 checks=dict(sample_count=len(sample)==1950,sample_unique=sample.image_path.nunique()==1950,sample_hash=sha(B/'sample_manifest.csv')==cfg['sample_sha256'],lock_unchanged=sha('uv.lock')==cfg['lock_sha256'],metadata_unchanged=sha('outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv')==cfg['metadata_sha256'],algorithm_unchanged=sha('mv_analysis/object_aware_crop.py')==cfg['algorithm_sha256'],runner_unchanged=sha('scripts/object_aware_crop_experiment.py')==cfg['runner_sha256'],yolo_cache_unchanged=sha('outputs/yolo11_dynamic_crop_v1/inference_checkpoint.jsonl')==cfg['original_yolo_sha256'])
 sets={stage:set(g.product_id) for stage,g in sample.groupby('stage')};checks['declared_products_disjoint']=not(sets['development']&sets['holdout'] or sets['development']&sets['prior_fit'] or sets['holdout']&sets['prior_fit'])
 checks['product_five_views']=bool(sample.groupby('product_id').view.nunique().eq(5).all());checks['same_declared_split']=bool(sample.groupby('product_id').split.nunique().eq(1).all());checks['holdout_validation_only']=bool(sample.query('stage=="holdout"').split.eq('validation').all());checks['priors_train_normal_only']=bool(sample.query('stage=="prior_fit"').split.eq('train').all() and sample.query('stage=="prior_fit"').status.eq('OK').all())
 checks['cohorts_preserved']=sample.groupby('cohort').size().to_dict()=={'dev_general':1200,'dev_risk':150,'independent_validation_products':300,'train_normal_prior':300}
 checks['development_rows']=len(dev)==1350*82;checks['holdout_only_frozen_and_baselines']=set(hold.method)==set(frozen['methods']+['full','center896','center768','center640'])
 checks['frozen_development_hash']=sha(B/'metrics/per_image_development.csv')==frozen['development_csv_sha256'];checks['frozen_algorithm_hash']=frozen['algorithm_sha256']==cfg['algorithm_sha256']
 coordinates=True
 for value in d.loc[d.available,'crop']:
  x0,y0,x1,y1=json.loads(value);coordinates &= 0<=x0<x1<=1024 and 0<=y0<y1<=1024 and x1-x0==y1-y0
 checks['all_crops_square_in_frame']=coordinates;checks['retention_range']=bool(d.retention.dropna().between(0,1).all());checks['full_frame_mask_identity']=bool(d[(d.method=='full')&(d.original_pixels>0)].retention.eq(1).all());checks['unprovided_ng_remains_na']=bool(d.loc[(d.status=='NG')&~d.has_mask,'original_pixels'].isna().all())
 checks['nearest_component_ids_bounded']=True
 for t in [224,256,392,512,640]:
  q=d[d[f't{t}_source_ids'].notna()];checks['nearest_component_ids_bounded'] &= bool((q[f't{t}_source_ids']<=q.source_components).all() and (q[f't{t}_small_ids']<=q.small_source_components).all() and (q[f't{t}_positive_pixels']<=t*t).all())
 old=pd.read_csv('outputs/yolo11_dynamic_crop_v1/metrics/per_image_crop_metrics.csv',usecols=['image_path','method','kept_pixels','geometric_defect_pixels']);old=old[old.method.isin(['full','center896','center768','center640'])];new=dev[dev.method.isin(['full','center896','center768','center640'])];paired=new.merge(old,on=['image_path','method'],validate='one_to_one',suffixes=('_new','_old'));checks['cached_baseline_exact_counts']=bool(np.allclose(paired.kept_pixels_new,paired.kept_pixels_old,rtol=0,atol=0,equal_nan=True))
 cp=[json.loads(v) for v in (B/'checkpoints/proposals.jsonl').read_text().splitlines()];checks['1950_unique_proposal_checkpoints']=len(cp)==len({r['image_path'] for r in cp})==1950;checks['proposal_execution_errors_zero']=not any(r['error'] for r in cp)
 # These stages are sequential in runner, which refuses holdout without frozen-policy file.
 order={r['image_path']:i for i,r in enumerate(cp)};first_hold=min(order[p] for p in sample.loc[sample.stage=='holdout','image_path']);last_dev=max(order[p] for p in sample.loc[sample.stage=='development','image_path']);checks['holdout_proposals_after_all_development']=first_hold>last_dev
 audit=pd.read_csv('outputs/content_audit_20261111_v7/content_hashes.csv',usecols=['path','sha256']);audit=dict(zip(audit.path,audit.sha256));source_ok=True
 for r in sample.to_dict('records'):
  for key in ['image_path']+(['mask_path'] if r['has_mask'] else []):source_ok &= sha(Path('dataset')/r[key])==audit[r[key]]
 checks['original_jpg_png_match_prior_full_hash_audit']=bool(source_ok)
 proposals=pd.read_csv(B/'review/product_bbox_proposals.csv');checks['600_proposals_not_gt']=len(proposals)==600 and proposals.bbox_status.eq('PROPOSAL').all() and proposals.category.nunique()==30
 verified={};ledger=B/'review/human_approved_gt.jsonl'
 if ledger.exists():
  for line in ledger.read_text().splitlines():
   r=json.loads(line)
   if r.get('status')=='VERIFIED_GT' and r.get('human_ack') is True:verified[r['image_path']]=r
 result=dict(success=all(checks.values()),analysis_status='COMPLETED_WITH_PRODUCT_GT_PENDING' if not verified else 'COMPLETED_WITH_PARTIAL_HUMAN_GT',checks={k:bool(v) for k,v in checks.items()},image_counts=sample.groupby('cohort').size().to_dict(),declared_product_counts=sample.groupby('cohort').product_id.nunique().to_dict(),verified_gt_images=len(verified),proposal_gt_images=600,product_iou='UNVERIFIED' if not verified else 'Reviewed subset only',foreground_pixel_occupancy='UNVERIFIED',full_dataset_reprocessing=False,additional_yolo_inferences=0,model_training=False,paid_api_calls=0,push=False,frozen_methods=frozen['methods'])
 p=B/'validation.json'
 if p.exists():raise SystemExit('Preserve existing validation')
 p.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));assert result['success']
if __name__=='__main__':main()
