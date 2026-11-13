# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Generate all source coordinates in bounded batches; no crop images and no GT inputs."""
import os,sys,json,hashlib,time,stat,fcntl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd,numpy as np,pyarrow as pa,pyarrow.parquet as pq,psutil
from PIL import Image
from mv_analysis.adaptive_crop_gate import decide,FORBIDDEN
from full_crop_gt_validation import B,ROOT,sha,savej,cp
META=ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv';BATCH=1000
ALLOWED=['image_path','product_id','category','view','split','width','height']

# process_source: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def process_source(args):
 r,policy,policy_hash,root,cache,audit=args
 assert not (set(r)&FORBIDDEN),'No annotation labels passed to production'
 path=root/r['image_path'];width,height=int(r['width']),int(r['height']);source_error='';header=False;size=mtime=0;source_ok=True
 try:
  s=path.stat();assert stat.S_ISREG(s.st_mode);size,mtime=s.st_size,s.st_mtime_ns
  with Image.open(path) as im:w,h=im.size
  if (w,h)!=(width,height):source_error=f'HEADER_DIMENSION_MISMATCH metadata{width}x{height} actual{w}x{h}';width,height=w,h;source_ok=False
  header=True
 except Exception as exc:source_error=type(exc).__name__+': '+str(exc);source_ok=False
 risk=['PRODUCT_CONTAINMENT_UNVERIFIED'];image_gate_status='NOT_EVALUATED_POLICY_BLOCKED';reused=False
 # Frozen policy currently has no verified deployment scopes. Never guess an approval.
 assert policy['production_mode']=='FULL_FRAME_UNVERIFIED_SCOPES' and not policy['approved_scopes']
 if cache and source_ok and (size,mtime)==(audit.get('bytes'),audit.get('mtime_ns')) and cache['source_hash']==audit.get('sha256'):
  thresholds=json.loads((ROOT/'outputs/adaptive_crop_gate_v1/thresholds.json').read_text())
  q=decide(cache['features'],thresholds,r['category'],r['view']);risk+=q['image_risk_codes'];image_gate_status=q['image_quality_status'];reused=True
 if not source_ok:risk.append('SOURCE_READ_ERROR')
 return dict(image_id=hashlib.sha256(r['image_path'].encode()).hexdigest()[:16],product_id=r['product_id'],category=r['category'],view=r['view'],split=r['split'],original_path=str(path),source_relative_path=r['image_path'],original_width=width,original_height=height,
  crop_x0=0,crop_y0=0,crop_x1=width,crop_y1=height,crop_width=width,crop_height=height,selected_policy='C',quality_status='UNVERIFIED' if source_ok else 'ERROR',risk_codes=json.dumps(list(dict.fromkeys(risk))),fallback_reason='UNVERIFIED_SCOPE_FULL_FRAME' if source_ok else 'SOURCE_ERROR_FULL_FRAME',geometric_gain=1.,full_frame=True,policy_version=policy['policy_version'],policy_sha256=policy_hash,source_fingerprint=f'stat-v1:{size}:{mtime}',source_size_bytes=size,source_mtime_ns=mtime,source_header_verified=header,source_error=source_error,processing_status=('OK_CACHE_REUSED_SAFE_FULL' if reused else 'OK_FROZEN_FULL_NO_FEATURE_EXTRACTION') if source_ok else 'ERROR_SOURCE_FALLBACK',image_features_reused=reused,image_gate_status=image_gate_status,
  coordinate_format='XYXY_EXCLUSIVE_ORIGINAL_PIXELS',schema_version='crop-metadata-v1',crop_saved=False,resize_applied=False,normalization_applied=False,additional_center_crop_allowed=False,augmentation_allowed=r['split']=='train',loaded_image_contract='RGB_HWC_UINT8',adapter_rule='CROP_THEN_MODEL_RESIZE_NORMALIZE_NO_IMPLICIT_SECOND_CROP')

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 policy=json.loads((B/'policy.json').read_text());assert (B/'gt_evaluation_complete.json').exists();root=Path(os.getenv('REALIAD_DATA_ROOT',str(ROOT/'dataset'))).expanduser().resolve();policyhash=sha(B/'policy.json');frame=pd.read_csv(META,usecols=ALLOWED).sort_values(['category','product_id','view']).reset_index(drop=True);assert len(frame)==151050
 cache=cp(ROOT/'outputs/adaptive_crop_gate_v1/checkpoints/features.jsonl');ad=pd.read_csv(ROOT/'outputs/content_audit_20261111_v7/content_hashes.csv',usecols=['path','kind','sha256','bytes','mtime_ns']);audit=ad[ad.kind.eq('jpg')].set_index('path').to_dict('index')
 if (B/'run_config.json').exists():
  cfg=json.loads((B/'run_config.json').read_text());assert cfg['input_metadata_sha256']==sha(META) and cfg['policy_sha256']==policyhash and cfg['runner_sha256']==sha(__file__) and cfg['data_root']==str(root)
 else:
  cfg=dict(input_metadata_sha256=sha(META),policy_sha256=policyhash,runner_sha256=sha(__file__),input_images=len(frame),data_root=str(root),batch_size=BATCH,cpu_io_workers=3,image_features_reused_possible=2550,feature_module_sha256=sha(ROOT/'mv_analysis/adaptive_crop_gate.py'),old_gate_config_sha256=sha(ROOT/'outputs/adaptive_crop_gate_v1/config.json'),root_lock_sha256=sha(ROOT/'uv.lock'),coordinate_generation='All rows processed; full frame because product gate not validated. No full GrabCut rerun; cached features reused only for diagnostic risk codes.',source_verification='Actual stat+JPEG headers on every new row. Fingerprint is current size/mtime; not a claim of new full-content hashing.',real_crop_image_files=0)
  savej(B/'run_config.json',cfg)
 t=time.perf_counter();new=0;reused_parts=0;parts=[]
 with (B/'checkpoints/run.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with ThreadPoolExecutor(max_workers=3) as pool:
   for start in range(0,len(frame),BATCH):
    sub=frame.iloc[start:start+BATCH];dest=B/'checkpoints'/f'part_{start//BATCH:05}.parquet';parts.append(dest)
    if dest.exists():
     old=pd.read_parquet(dest);assert old.source_relative_path.tolist()==sub.image_path.tolist() and old.policy_sha256.eq(policyhash).all();reused_parts+=1;continue
    todo=[(r,policy,policyhash,root,cache.get(r['image_path']),audit.get(r['image_path'],{})) for r in sub.to_dict('records')];rows=list(pool.map(process_source,todo));result=pd.DataFrame(rows);temp=dest.with_suffix('.tmp');result.to_parquet(temp,index=False,compression='zstd');os.replace(temp,dest);new+=len(rows)
    elapsed=time.perf_counter()-t;done=min(start+BATCH,len(frame));counts=sub.category.value_counts().to_dict();print(f'{done}/{len(frame)} coordinate rows checkpointed; batch categories={counts}; elapsed={elapsed:.1f}s; RSS={psutil.Process().memory_info().rss/2**20:.0f}MiB',flush=True)
  out=pd.concat([pd.read_parquet(p) for p in parts],ignore_index=True);assert len(out)==len(frame) and not out.image_id.duplicated().any()
  for name in ['final_crop_manifest.parquet','final_crop_manifest.csv','preprocessing_metadata.csv']:
   dest=B/name
   if dest.exists():continue
   tmp=dest.with_suffix(dest.suffix+'.partial')
   if dest.suffix=='.parquet':out.to_parquet(tmp,index=False,compression='zstd')
   else:out.to_csv(tmp,index=False)
   os.replace(tmp,dest)
  completion=B/'coordinates_complete.json'
  if not completion.exists():savej(completion,dict(images=len(out),newly_processed=new,checkpoint_parts_reused=reused_parts,elapsed_seconds=time.perf_counter()-t,source_read_errors=int(out.processing_status.str.startswith('ERROR').sum()),cached_feature_rows_reused=int(out.image_features_reused.sum()),new_grabcut_feature_images=0,source_headers_checked=int(out.source_header_verified.sum()),peak_final_rss_bytes=psutil.Process().memory_info().rss,actual_crop_image_files_created=0))
  print('DONE',len(out),'metadataCSV',B/'preprocessing_metadata.csv',flush=True)
if __name__=='__main__':main()
