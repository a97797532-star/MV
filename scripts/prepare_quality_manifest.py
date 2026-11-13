# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Create review/quarantine recommendations; never drop or rewrite raw analysis/source files."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import pandas as pd
from mv_analysis.core import binary_mask,read_image,save_json
p=argparse.ArgumentParser();p.add_argument('--image-run',required=True,type=Path);p.add_argument('--spatial-run',required=True,type=Path);p.add_argument('--content-audit',required=True,type=Path);args=p.parse_args();out=args.image_run/'quality_review';out.mkdir(exist_ok=True)
meta=pd.read_csv(args.image_run/'image_metadata_with_split.csv',keep_default_na=False);b=pd.read_csv(args.image_run/'brightness_per_image.csv');hashes=pd.read_csv(args.content_audit/'content_hashes.csv');black=set(b.loc[b.brightness==0,'image_path']);root=Path(json.loads((args.image_run/'run.json').read_text())['config']['root'])
flags=[]
for row in meta.to_dict('records'):
 is_black=row['image_path'] in black;reasons=[]
 if is_black:
  im=read_image(root/row['image_path']);assert im.min()==im.max()==0;reasons.append('all_zero_JPG; capture/annotation semantics need review')
 if row['label_conflict']:reasons.append('defect_type_conflict')
 flags.append({**row,'analysis_include':True,'all_zero_jpg':is_black,'recommended_image_training_include':not is_black,'recommended_defect_classification_include':not is_black and not row['label_conflict'],'recommended_detection_include':not is_black and (row['status']=='OK' or (row['has_mask'] and not row['label_conflict'])),'review_reason':'; '.join(reasons)})
manifest=pd.DataFrame(flags);flagged_captures=set(manifest.loc[manifest.all_zero_jpg,'capture_id']);manifest['recommended_strict_five_view_include']=~manifest.capture_id.isin(flagged_captures);manifest.to_csv(out/'model_input_review_manifest.csv',index=False);manifest[manifest.all_zero_jpg].to_csv(out/'quarantine_candidates.csv',index=False)
merged=manifest.merge(hashes[hashes.kind=='jpg'][['path','sha256']],left_on='image_path',right_on='path');usable=merged[merged.recommended_image_training_include];leak=usable.groupby('sha256').split.nunique();save_json(out/'quality_aware_split_validation.json',dict(raw_images=len(meta),recommended_usable_images=len(usable),quarantine_candidates=len(black),raw_exact_cross_split_groups=int((merged.groupby('sha256').split.nunique()>1).sum()),recommended_usable_exact_cross_split_groups=int((leak>1).sum()),product_group_split_leakage=int((usable.groupby('product_id').split.nunique()>1).sum()),detection_recommended_images=int(manifest.recommended_detection_include.sum()),flagged_capture_groups=len(flagged_captures),strict_five_view_recommended_images=int(manifest.recommended_strict_five_view_include.sum()),no_sources_modified=True,scope='Recommendations pending capture/annotation semantic review; original full analysis and splits unchanged'))
# Descriptive sensitivity analysis under the source heatmap's declared units.
spatial=args.spatial_run;keys=json.loads((spatial/'heatmap_groups.json').read_text());policy=json.loads((spatial/'mask_policy.json').read_text());schema=json.loads((spatial/'heatmap_schema.json').read_text()) if (spatial/'heatmap_schema.json').exists() else {'schema':'area-v1'}
presence=schema['schema']=='presence-v2'
if presence:
 from mv_analysis.legacy_bridge import coursework
 positive=np.load(spatial/'presence_count.npy');known=np.load(spatial/'observation_count.npy');summary=pd.read_csv(spatial/'heatmap_summary.csv');positive_denominator=np.stack([np.full((64,64),n,dtype=float) for n in summary.n_positive])
else:
 positive=np.load(spatial/'occupancy_positive.npy');known=np.load(spatial/'occupancy_known.npy');positive_denominator=None
before=positive.copy();before_known=known.copy();removed=[]
for row in manifest[(manifest.split=='train')&(manifest.status=='NG')&manifest.has_mask&manifest.all_zero_jpg].to_dict('records'):
 key=[row['category'],row['defect_type'],row['view']];idx=keys.index(key);mask=binary_mask(read_image(root/row['mask_path'],True),policy)
 positive[idx]-=coursework().coarse_occupancy(mask,64) if presence else cv2.resize(mask.astype(np.float32),(64,64),interpolation=cv2.INTER_AREA)
 known[idx]-=1
 if presence:positive_denominator[idx]-=int(mask.any())
 removed.append(dict(image_path=row['image_path'],group=key,foreground_pixels=int(mask.sum())))
assert np.all(positive>=-1e-10) and np.all(positive<=known+1e-10)
prior=out/'quarantine_sensitivity_heatmap';prior.mkdir(exist_ok=True)
if presence:
 np.save(prior/'presence_count.npy',positive)
 k=np.divide(positive,known,out=np.full_like(positive,np.nan),where=known>0);v=np.divide(positive,positive_denominator,out=np.full_like(positive,np.nan),where=positive_denominator>0)
 np.save(prior/'occupancy_known.npy',k);np.save(prior/'occupancy_positive.npy',v);save_json(prior/'heatmap_schema.json',schema)
else:np.save(prior/'occupancy_positive.npy',positive);np.save(prior/'occupancy_known.npy',known)
save_json(prior/'heatmap_groups.json',keys);comparisons=[]
for i,key in enumerate(keys):
 if any(row['group']==key for row in removed):
  old=before[i]/before_known[i];new=np.divide(positive[i],known[i],out=np.full_like(positive[i],np.nan),where=known[i]>0)
  comparisons.append(dict(category=key[0],defect_type=key[1],view=key[2],raw_observations=int(before_known[i].max()),reviewed_observations=int(known[i].max()),raw_mean_occupancy=float(np.nanmean(old)),without_flagged_mean_occupancy=float(np.nanmean(new)),flagged_fraction_of_positive_mass=float((before[i]-positive[i]).sum()/before[i].sum()),occupancy_units='cell presence frequency' if presence else 'foreground area fraction'))
pd.DataFrame(comparisons).to_csv(prior/'affected_group_comparison.csv',index=False);save_json(prior/'scope.json',dict(raw_train_masks=int(((meta.split=='train')&(meta.status=='NG')&meta.has_mask).sum()),excluded_candidates=removed,heatmap_schema=schema['schema'],interpretation='Sensitivity example only. Full-white mask may be intentional; no automatic correction of source annotation or original raw heatmap.'))
print(json.dumps(json.loads((out/'quality_aware_split_validation.json').read_text()),indent=2));print(pd.DataFrame(comparisons).to_string(index=False))
