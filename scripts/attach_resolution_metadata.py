"""Attach preserved Windows folds to existing resolution metrics; no JPG recomputation/overwrite."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--target',required=True,type=Path);a=p.parse_args();dest=a.target/'per_view_information_loss.csv'
if dest.exists():raise SystemExit('Derived resolution file exists; preserve it')
meta=pd.read_csv(a.target/'image_metadata_with_split.csv',keep_default_na=False).set_index('image_path');source=a.source/'per_view_information_loss.csv';before=hashlib.sha256(source.read_bytes()).hexdigest();r=pd.read_csv(source,float_precision='round_trip');assert len(r)==151050*3 and set(r.image_path)==set(meta.index)
metrics=['target','psnr_db','ssim','edge_recall','edge_f1','laplacian_energy','laplacian_retention','gradient_energy','gradient_retention','local_contrast_retention','rgb_rmse','high_frequency_proxy_retention'];values=r[metrics].to_numpy(copy=True);old_splits=r['split'].copy();new_splits=r.image_path.map(meta.split);changed_images=r.loc[old_splits!=new_splits,'image_path'].nunique()
for column in ['split','product_id','analysis_hash_split','conservative_serial_id','windows_product_key','windows_project_split','split_origin']:
 if column in meta:r[column]=r.image_path.map(meta[column])
r.to_csv(dest,index=False);written=pd.read_csv(dest,usecols=metrics,float_precision='round_trip');assert np.array_equal(values,written[metrics].to_numpy(),equal_nan=True);assert r.groupby('product_id').split.nunique().max()==1
step=pd.read_csv(a.source/'per_image_stepwise_changes.csv',float_precision='round_trip')
for column in ['category','view','status','defect_type','split','product_id']:
 step[column]=step.image_path.map(meta[column])
step.to_csv(a.target/'per_image_stepwise_changes.csv',index=False)
for name in ['category_view_loss_summary.csv','review_priority_images.csv','resolution_loss_summary.png','five_view_loss.png','detail_crop_comparison.png','detail_crop_source.json','resolution_analysis_report.md','resolution_ssim_quantiles.csv','resolution_category_means.csv','resolution_global_distribution_summary.csv','resolution_global_quantiles.csv','resolution_undefined_metric_counts.csv','resolution_metric_distributions.png','resolution_category_heatmaps.png','resolution_metric_definitions.json','resolution_math_signature.json','resolution_cache_equivalence.json','resolution_math_binding_validation.json']:
 if (a.source/name).exists():shutil.copy2(a.source/name,a.target/name)
# Keep the review-priority list's split/product fields consistent as well.
priority=pd.read_csv(a.target/'review_priority_images.csv')
for column in ['split','product_id']:
 priority[column]=priority.image_path.map(meta[column])
priority.to_csv(a.target/'review_priority_images.csv',index=False)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
record=dict(time_utc=datetime.now(timezone.utc).isoformat(),source=str(a.source),target=str(a.target),metric_rows=len(r),images=r.image_path.nunique(),split_changed_images=int(changed_images),split_changed_metric_rows=int((old_splits!=new_splits).sum()),numeric_metric_columns=metrics,all_numeric_metrics_exact_after_roundtrip=True,new_image_decodes=0,source_csv_sha256=before,original_source_unchanged=True)
save_json(a.target/'resolution_metadata_rebind_validation.json',record);run=json.loads((a.target/'run.json').read_text());run['commands'].append(dict(command='resolution-metadata-rebind',argv=sys.argv[1:],error=None,finished=record['time_utc'],source_csv_sha256=before,success_images=int(record['images']),new_image_decodes=0));save_json(a.target/'run.json',run);print(json.dumps(record,indent=2))
