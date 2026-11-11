"""Read-only exact-byte duplicate and input fingerprint audit with resumable hashes."""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
run=json.loads((args.run/'run.json').read_text());root=Path(run['config']['root']);images=pd.read_csv(args.run/'image_metadata_with_split.csv',keep_default_na=False);masks=pd.read_csv(args.run/'mask_metadata.csv',keep_default_na=False)
items=[dict(path=r['image_path'],kind='jpg',split=r['split'],product_id=r['product_id']) for r in images.to_dict('records')]+[dict(path=r['mask_path'],kind='png',split='',product_id='') for r in masks.to_dict('records')]
cache=args.output/'content_hashes.jsonl';done={};errors=[];started=time.time()
if cache.exists():
 for line in cache.open():
  try:r=json.loads(line);done[r['path']]=r
  except json.JSONDecodeError:raise SystemExit('Interrupted hash tail requires review before reuse')
def compute(item):
 try:
  path=root/item['path'];before=path.stat();digest=hashlib.sha256()
  with path.open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
  after=path.stat()
  if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Input changed during hashing')
  return {**item,'sha256':digest.hexdigest(),'bytes':before.st_size,'mtime_ns':before.st_mtime_ns},None
 except Exception as exc:return None,dict(path=item['path'],error=str(exc))
pending=[r for r in items if r['path'] not in done]
with cache.open('a') as stream,ThreadPoolExecutor(max_workers=2) as pool:
 for start in range(0,len(pending),1000):
  for result,error in pool.map(compute,pending[start:start+1000]):
   if error:errors.append(error)
   else:done[result['path']]=result;stream.write(json.dumps(result)+'\n');stream.flush()
  print(f'Input content hashes {len(done)}/{len(items)} errors={len(errors)}',flush=True)
all_rows=pd.DataFrame(list(done.values()));all_rows.to_csv(args.output/'content_hashes.csv',index=False)
jpg=all_rows[all_rows.kind=='jpg'];duplicate=jpg[jpg.sha256.duplicated(keep=False)];duplicate.to_csv(args.output/'exact_jpg_duplicates.csv',index=False);png=all_rows[all_rows.kind=='png'];png[png.sha256.duplicated(keep=False)].to_csv(args.output/'exact_png_duplicates.csv',index=False)
leak=duplicate.groupby('sha256').split.nunique();groups=int(duplicate.sha256.nunique());save_json(args.output/'content_hash_validation.json',dict(target=len(items),success=len(done),errors=errors,jpg=len(jpg),png=len(png),exact_jpg_duplicate_groups=groups,exact_jpg_duplicate_files=len(duplicate),exact_jpg_cross_split_groups=int((leak>1).sum()),exact_png_duplicate_groups=int(png.loc[png.sha256.duplicated(keep=False),'sha256'].nunique()),fingerprint=hashlib.sha256('\n'.join(r['path']+' '+r['sha256'] for r in sorted(done.values(),key=lambda r:r['path'])).encode()).hexdigest(),elapsed_s=time.time()-started,scope='exact file bytes, not perceptual or re-encoding-invariant duplicates'))
print('Exact byte content audit completed');raise SystemExit(bool(errors))
