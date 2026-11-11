"""Check current preserved OpenCV component backend against stratified real bbox exports."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,pandas as pd
from mv_analysis.core import read_image,binary_mask,components,save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--image-run',required=True,type=Path);p.add_argument('--spatial-run',required=True,type=Path);p.add_argument('--study',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();root=Path(json.loads((a.image_run/'run.json').read_text())['config']['root']);meta=pd.read_csv(a.image_run/'image_metadata_with_split.csv',keep_default_na=False).set_index('image_path');boxes=pd.read_csv(a.spatial_run/'defect_bboxes.csv');boxgroups={path:group for path,group in boxes.groupby('image_path')};sample=pd.read_csv(a.study/'mask_threshold_validation'/'threshold_per_mask.csv');sample=sample[sample.threshold==0].drop_duplicates('image_path');errors=[];checked=0;skipped=0
for row in sample.to_dict('records'):
 if bool(meta.loc[row['image_path'],'label_conflict']):skipped+=1;continue
 mask=binary_mask(read_image(root/row['mask_path'],True),json.loads((a.spatial_run/'mask_policy.json').read_text()));actual=sorted(components(mask));group=boxgroups.get(row['image_path']);expected=[] if group is None else sorted((int(b.x0),int(b.y0),int(b.x1),int(b.y1),int(b.component_area)) for b in group.itertuples())
 if actual!=expected:errors.append(dict(image_path=row['image_path'],issue='saved bbox/current backend differ'))
 if sum(c[-1] for c in actual)!=int(mask.sum()):errors.append(dict(image_path=row['image_path'],issue='component area does not cover foreground'))
 checked+=1
result=dict(sampled_masks=len(sample),checked_masks=checked,unresolved_type_masks_excluded=skipped,errors=errors,success=not errors,scope='Stratified actual masks across all categories; independent pixel component re-extraction compared to saved CSV, not full mask recomputation');save_json(a.output,result);print(json.dumps(result,indent=2));sys.exit(not result['success'])
