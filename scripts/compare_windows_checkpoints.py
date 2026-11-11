"""Explain observed scope differences between preserved Windows checkpoint/latest inventories."""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('--windows',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False);records={}
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  while chunk:=stream.read(1024*1024):h.update(chunk)
 return h.hexdigest()
for name in ['image_metadata','mask_metadata','brightness_comparison']:
 prior=a.windows/'.ipynb_checkpoints'/(name+'-checkpoint.csv');latest=a.windows/(name+'.csv');columns=['category']+(['relative_path'] if name!='brightness_comparison' else []);old=pd.read_csv(prior,usecols=columns);new=pd.read_csv(latest,usecols=columns);r=dict(checkpoint_rows=len(old),latest_rows=len(new),checkpoint_categories=sorted(old.category.unique()),latest_categories=sorted(new.category.unique()),checkpoint_u_block_rows=int(old.category.eq('u_block').sum()),latest_u_block_rows=int(new.category.eq('u_block').sum()),source_checkpoint=str(prior),source_latest=str(latest),checkpoint_sha256=digest(prior),latest_sha256=digest(latest))
 if 'relative_path' in old:
  before=set(old.relative_path.str.replace('\\','/',regex=False));after=set(new.relative_path.str.replace('\\','/',regex=False));added=after-before;r.update(added_paths=len(added),removed_paths=len(before-after),added_categories=sorted({v.split('/')[0] for v in added}),all_added_are_u_block=all(v.startswith('u_block/') for v in added))
 records[name]=r
(a.output/'comparison.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps({k:{f:r[f] for f in ['checkpoint_rows','latest_rows','checkpoint_u_block_rows','latest_u_block_rows']} for k,r in records.items()},indent=2))
