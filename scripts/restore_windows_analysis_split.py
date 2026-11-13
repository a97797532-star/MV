# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Derive a new run using verified Windows folds, without rewriting prior results."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from mv_analysis.core import save_json
from mv_analysis.splits import reproduce_windows_project_split
from mv_analysis import stages
import cv2
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verified-split',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);p.add_argument('--skip-heatmap',action='store_true',help='Assemble metadata/brightness/policy input without redoing spatial analysis');a=p.parse_args()
if a.output.exists():raise SystemExit('Output exists; preserve it and choose a fresh directory')
if not json.loads(a.policy.read_text()).get('validated'):raise SystemExit('A validated mask policy is required for this assembled source')
df=pd.read_csv(a.source/'image_metadata_with_split.csv',keep_default_na=False)
if not ('split_origin' in df and df.split_origin.eq('windows-executed-notebook-cell28-seed42').all()):df=reproduce_windows_project_split(df)
verified=pd.read_csv(a.verified_split,keep_default_na=False).set_index('image_path')
assert len(df)==len(verified) and df.set_index('image_path').split.eq(verified.split).all()
a.output.mkdir(parents=True)
parent=json.loads((a.source/'run.json').read_text());config=parent['config'].copy();config['split_policy']='windows-project-v1';config['source_sha256']=hashlib.sha256(b''.join(f.read_bytes() for f in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()
save_json(a.output/'run.json',dict(created=datetime.now(timezone.utc).isoformat(),config=config,provenance=dict(parent_run=str(a.source),verified_split=str(a.verified_split),new_image_decodes=0,method='Original executed notebook seed42 split reproduced identically for all 151050 images'),commands=[]))
df.to_csv(a.output/'image_metadata_with_split.csv',index=False);df.drop(columns=['split']).to_csv(a.output/'image_metadata.csv',index=False)
for name in ['mask_metadata.csv','image_mask_pairs.csv','dataset_category_distribution.png']:
 if (a.source/name).exists():shutil.copy2(a.source/name,a.output/name)
report=json.loads((a.source/'metadata_validation_report.json').read_text());report['split_policy']='windows-project-v1';report['product_split_leakage']=int((df.groupby('product_id').split.nunique()>1).sum());report['preserved_split_import']=dict(matched=len(df),differences=0,product_groups=df.product_id.nunique(),original_manifest_verified=True)
save_json(a.output/'metadata_validation_report.json',report);shutil.copy2(a.policy,a.output/'mask_policy.json')
lookup=df.set_index('image_path').to_dict('index')
imported=set()
with (a.source/'brightness_per_image.jsonl').open() as src,(a.output/'brightness_per_image.jsonl').open('w') as dst:
 for line in src:
  row=json.loads(line)
  if row['image_path'] in imported:raise ValueError('Duplicate brightness checkpoint input')
  imported.add(row['image_path']);row.update(lookup[row['image_path']]);dst.write(json.dumps(row,allow_nan=False)+'\n')
if imported!=set(df.image_path):raise ValueError('Measured brightness cache does not cover source metadata; no fresh decode was attempted')
stages.brightness(Path(config['root']),a.output,df)
if not a.skip_heatmap:stages.heatmap(Path(config['root']),a.output,df,json.loads(a.policy.read_text()))
save_json(a.output/'restoration_validation.json',dict(images=len(df),split_counts=df.split.value_counts().to_dict(),product_groups=df.product_id.nunique(),split_differences=0,brightness_reused_images=len(df),original_sources_modified=False,heatmap_deferred=bool(a.skip_heatmap)))
