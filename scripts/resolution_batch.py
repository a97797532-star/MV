"""Bounded full-resolution analysis worker. Reuses core metrics and append-only success rows."""
import argparse
import fcntl
import hashlib
import json
import math
import inspect
import numpy as np
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import pandas as pd
from mv_analysis.core import information_loss,prepare_image_reference,read_image,save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--batch-size',type=int,default=2000);p.add_argument('--workers',type=int,default=4);p.add_argument('--finalize',action='store_true');args=p.parse_args();out=args.run
worker_lock=(out/'.resolution_worker.lock').open('a')
try:fcntl.flock(worker_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit('Another resolution batch is active for this run; do not run concurrently')
run=json.loads((out/'run.json').read_text())
if hashlib.sha256(Path('uv.lock').read_bytes()).hexdigest()!=run['config']['lock_sha256']:raise SystemExit('Lock changed; preserve cache and use a new run')
math_fingerprint=dict(functions_sha256=hashlib.sha256('\n'.join(inspect.getsource(f) for f in [read_image,prepare_image_reference,information_loss]).encode()).hexdigest(),opencv=cv2.__version__,numpy=np.__version__)
stamp=out/'resolution_math_signature.json'
if stamp.exists() and json.loads(stamp.read_text())!=math_fingerprint:raise SystemExit('Resolution producer/math/runtime changed; preserve cache and start a new run')
root=Path(run['config']['root']);df=pd.read_csv(out/'image_metadata_with_split.csv',keep_default_na=False);rows=df.to_dict('records');cache=out/'resolution_checkpoint.jsonl';done=set();samples=[]
if cache.exists():
 with cache.open('rb+') as stream:
  while True:
   offset=stream.tell();line=stream.readline()
   if not line:break
   try:
    row=json.loads(line);done.add(row['image_path'])
    if len(samples)<3:samples.append(row)
   except json.JSONDecodeError:
    if stream.read(1):raise
    stream.seek(offset);stream.truncate();break

def calculate(row):
 path=root/row['image_path'];st=path.stat()
 if st.st_size!=row['bytes'] or st.st_mtime_ns!=row['mtime_ns']:raise ValueError('Input snapshot changed')
 im=read_image(path);reference=prepare_image_reference(im)
 return {**row,'metrics':[information_loss(im,size,reference) for size in (1024,512,256)],'step_512_to_256':information_loss(cv2.resize(im,(512,512),interpolation=cv2.INTER_AREA),256)}
# Validate numerical equivalence of imported cache before continuing; save evidence once.
equivalence=out/'resolution_cache_equivalence.json'
if (not equivalence.exists() or not stamp.exists()) and samples:
 checks=[]
 for old in samples:
  actual=calculate({k:v for k,v in old.items() if k not in ('metrics','step_512_to_256')})
  for left,right in zip(old['metrics']+[old['step_512_to_256']],actual['metrics']+[actual['step_512_to_256']]):
   for key,value in left.items():
    if value is None:assert right[key] is None
    else:assert math.isclose(value,right[key],rel_tol=1e-10,abs_tol=1e-10),(key,value,right[key])
  checks.append(old['image_path'])
 save_json(equivalence if not equivalence.exists() else out/'resolution_math_binding_validation.json',dict(checked_images=checks,tolerance=1e-10,metrics='same mv_analysis.core information_loss/prepare_image_reference; only bbox/CLI source changed',source_sha256=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()))
if not stamp.exists():save_json(stamp,math_fingerprint)
pending=[r for r in rows if r['image_path'] not in done][:args.batch_size];errors=[];start=time.time();source=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()
def process(row):
 try:return calculate(row),None
 except Exception as exc:return None,dict(image_path=row['image_path'],error=str(exc))
with cache.open('a') as stream,ThreadPoolExecutor(max_workers=max(1,min(4,args.workers))) as pool:
 for i,(result,error) in enumerate(pool.map(process,pending),1):
  if error:errors.append(error)
  else:stream.write(json.dumps(result,allow_nan=False)+'\n');stream.flush();done.add(result['image_path'])
  if i%100==0:print(f'resolution full success {len(done)}/{len(rows)}, batch {i}/{len(pending)}, errors {len(errors)}',flush=True)
status=dict(time=datetime.now(timezone.utc).isoformat(),target=len(rows),success=len(done),pending=len(rows)-len(done),batch_target=len(pending),batch_success=len(pending)-len(errors),batch_errors=errors,elapsed_s=time.time()-start,source_sha256=source,checkpoint=str(cache))
save_json(out/'resolution_batch_status.json',status)
driver_path=out/'image_analysis_driver.json'
if driver_path.exists():
 driver=json.loads(driver_path.read_text());driver['state']=('complete_resolution' if (out/'per_view_information_loss.csv').exists() and (out/'resolution_scientific_validation.json').exists() else 'resolution_calculation_complete_pending_finalization') if len(done)==len(rows) else 'resolution_running_in_bounded_batches';driver['successful_resolution_images']=len(done);driver['target_resolution_images']=len(rows);driver['latest_batch_status']='resolution_batch_status.json';save_json(driver_path,driver)
with (out/'resolution_batches.jsonl').open('a') as stream:stream.write(json.dumps(status)+'\n')
print(json.dumps({k:v for k,v in status.items() if k!='batch_errors'},indent=2),flush=True)
if errors:raise SystemExit(1)
if args.finalize:
 if len(done)!=len(rows):raise SystemExit('Finalization refused: full image count not reached')
 from mv_analysis.stages import resolution
 resolution(root,out,df)
 manifest=json.loads((out/'run.json').read_text());manifest['commands'].append(dict(command='resolution-batch-finalize',argv=sys.argv[1:],source_sha256=source,target=len(rows),success=len(done),error=None,finished=datetime.now(timezone.utc).isoformat()));save_json(out/'run.json',manifest)
 print('Full resolution CSV/figures finalized',flush=True)
