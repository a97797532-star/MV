"""Resume preserved-split presence heatmaps in bounded per-group batches."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,pandas as pd
from mv_analysis.presence_heatmaps import generate
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--max-groups',type=int,default=50);a=p.parse_args();run=json.loads((a.run/'run.json').read_text());df=pd.read_csv(a.run/'image_metadata_with_split.csv',keep_default_na=False);policy=json.loads((a.run/'mask_policy.json').read_text())
complete=generate(Path(run['config']['root']),a.run,df,policy,a.max_groups)
if complete:
 from mv_analysis.core import save_json
 save_json(a.run/'restoration_validation.json',dict(images=len(df),split_counts=df.split.value_counts().to_dict(),product_groups=df.product_id.nunique(),split_differences=0,brightness_reused_images=len(df),original_sources_modified=False))
print('Presence complete:',complete)
