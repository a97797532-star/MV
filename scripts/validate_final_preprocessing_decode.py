# 한글 안내: 원본 이미지·마스크를 배치 단위로 디코딩하고 체크포인트를 남기는 보존용 전수 감사입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Checkpointed full actual JPEG/PNG decoding and saved-coordinate target audit; no repair."""
import sys,json,hashlib,time,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd,psutil
from mv_analysis.data.manifest import ManifestIndex,file_hash,ROOT
from mv_analysis.data.targets import read_mask,crop_targets
cv2.setNumThreads(1);O=ROOT/'outputs/data_loader_validation_v1';BATCH=1000

# worker: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def worker(args):
 row,path,maskpath,boxes,labels,expected_hash,approved_hash=args
 base=dict(image_id=row['image_id'],image_path=row['source_relative_path'],product_id=row['product_id'],category=row['category'],view=row['view'],split=row['split'],status=row['status'],source_fingerprint_match=False,image_decoded=False,image_error='',mask_status='MISSING',mask_error='',native_bbox_mask_match=None,source_sha256='',annotation_hash_match=True)
 try:
  stat=path.stat();fp=f'stat-v1:{stat.st_size}:{stat.st_mtime_ns}';base['source_fingerprint_match']=fp==row['source_fingerprint']
  if not base['source_fingerprint_match']:raise ValueError('Source stat fingerprint changed')
  if path.suffix.lower() not in ['.jpg','.jpeg']:raise ValueError('Expected JPG source extension')
  data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();base['source_sha256']=digest
  if expected_hash and digest!=expected_hash:raise ValueError('Source JPG content differs from previous dataset audit')
  if approved_hash and digest!=approved_hash:raise ValueError('Manual approval image bytes changed')
  image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
  if image is None:raise ValueError('JPG decode failed')
  if image.shape[:2]!=(row['original_height'],row['original_width']):raise ValueError('Actual source dimensions disagree with manifest')
  base['image_decoded']=True;mask,state,error=read_mask(maskpath,image.shape[:2]);t=crop_targets(row,boxes,labels,mask,state,error)
  if mask is not None:
   _,_,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8);native=Counter(tuple(v) for v in boxes.tolist());actual=Counter((int(x),int(y),int(x+w),int(y+h)) for x,y,w,h,_ in stats[1:]);base['native_bbox_mask_match']=native==actual
   if native!=actual:t['detection_status']='INVALID_TARGET';t['detection_trainable']=False
  base.update({k:v for k,v in t.items() if k not in ['boxes','labels','mask','source_class_ids','box_keep']});base['final_box_count']=len(t['boxes']);base['final_class_ids']=json.dumps(t['labels'].tolist());base['target_xyxy_valid']=bool(not len(t['boxes']) or ((t['boxes']>=0).all() and (t['boxes'][:,[0,2]]<=row['crop_width']).all() and (t['boxes'][:,[1,3]]<=row['crop_height']).all()));base['validation_status']='VALID' if not error and base['native_bbox_mask_match'] is not False else 'ANNOTATION_INVALID'
 except Exception as exc:base.update(image_error=type(exc).__name__+': '+str(exc),validation_status='IMAGE_INVALID',detection_status='INVALID_TARGET',detection_trainable=False)
 return base

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--max-batches',type=int);a=p.parse_args();finger=json.loads((O/'manifest_fingerprint.json').read_text());index=ManifestIndex(finger['selected_manifest'],require_complete=True);assert index.sha256==finger['manifest_sha256'];parts=O/'decode_checkpoints';parts.mkdir(exist_ok=True)
 ledger=[json.loads(v) for v in Path(finger['crop_ledger']).read_text().splitlines()];latest={v['case_id']:v for v in ledger};audit=pd.read_csv(ROOT/'outputs/content_audit_20261111_v7/content_hashes.csv',usecols=['path','kind','sha256']);hashes=audit[audit.kind.eq('jpg')].set_index('path').sha256.to_dict()
 config=dict(manifest_sha256=index.sha256,runner_sha256=file_hash(__file__),target_module_sha256=file_hash(ROOT/'mv_analysis/data/targets.py'),index_module_sha256=file_hash(ROOT/'mv_analysis/data/manifest.py'),mask_threshold='>0 same as original validated analysis; no new threshold',cpu_io_workers=3,batch_size=BATCH,full_jpg_decode=True,full_provided_mask_decode=True)
 cfg=O/'decode_config.json'
 if cfg.exists():assert json.loads(cfg.read_text())==config,'Changed decoder version; do not mix checkpoints'
 else:cfg.write_text(json.dumps(config,indent=2))
 start=time.perf_counter();new=0;paths=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  for i in range(0,len(index.data),BATCH):
   path=parts/f'part_{i//BATCH:05}.parquet';paths.append(path);sub=index.data.iloc[i:i+BATCH]
   if path.exists():old=pd.read_parquet(path);assert old.image_id.tolist()==sub.image_id.tolist();continue
   args=[]
   for row in sub.to_dict('records'):
    boxes,labels=index.boxes.get(row['source_relative_path'],(np.empty((0,4),np.float32),np.empty(0,np.int64)));event=latest.get(row['image_id']);approved_hash=event.get('source_sha256') if event and event['status']=='APPROVED_CROP' else None;args.append((row,index.source_path(row),index.source_path(row,True) if row['has_mask'] else None,boxes,labels,hashes.get(row['source_relative_path']),approved_hash))
   result=pd.DataFrame(pool.map(worker,args));tmp=path.with_suffix('.tmp');result.to_parquet(tmp,index=False,compression='zstd');os.replace(tmp,path);new+=len(result);print(f'DECODE {min(i+BATCH,len(index.data))}/{len(index.data)} {sub.category.value_counts().to_dict()} elapsed{time.perf_counter()-start:.1f}s RSS{psutil.Process().memory_info().rss/2**20:.0f}MiB',flush=True)
   if a.max_batches and new//BATCH>=a.max_batches:print('Checkpoint smoke complete; resume command without --max-batches');return
 allrows=pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True);assert len(allrows)==len(index.data)
 for name in ['per_image_decode_validation.csv','annotation_contract.csv']:
  target=O/name
  if not target.exists():tmp=target.with_suffix('.partial');allrows.to_csv(tmp,index=False);os.replace(tmp,target)
 for name,select in [('image_decode_errors',allrows.validation_status.eq('IMAGE_INVALID')),('annotation_errors',allrows.validation_status.eq('ANNOTATION_INVALID')),('crop_defect_losses',allrows.crop_mask_loss.eq(True)),('all_defects_cropped_out',allrows.all_defects_cropped_out.eq(True)),('detection_ineligible',~allrows.detection_trainable.eq(True))]:
  dest=O/(name+'.csv')
  if not dest.exists():allrows[select].to_csv(dest,index=False)
 grouped=allrows.groupby('source_sha256').agg(images=('image_id','size'),splits=('split','nunique'));content_leaks=grouped[(grouped.index!='')&grouped.splits.gt(1)]
 summary=dict(images=len(allrows),full_jpg_decoded=int(allrows.image_decoded.sum()),image_errors=int(allrows.validation_status.eq('IMAGE_INVALID').sum()),mask_states=allrows.mask_status.value_counts().to_dict(),annotation_errors=int(allrows.validation_status.eq('ANNOTATION_INVALID').sum()),native_bbox_mask_mismatches=int(allrows.native_bbox_mask_match.eq(False).sum()),detection_statuses=allrows.detection_status.value_counts().to_dict(),crop_mask_loss_images=int(allrows.crop_mask_loss.eq(True).sum()),all_defects_removed_images=int(allrows.all_defects_cropped_out.eq(True).sum()),crop_clipped_boxes=int(allrows.crop_clipped_boxes.fillna(0).sum()),crop_removed_boxes=int(allrows.crop_removed_boxes.fillna(0).sum()),bbox_without_mask_support=int(allrows.boxes_without_mask_support.fillna(0).sum()),jpeg_hash_cross_split_duplicates=len(content_leaks),seconds=time.perf_counter()-start,new_decodes_this_invocation=new,source_and_crop_coordinates_changed=0)
 dest=O/'decode_summary.json'
 if not dest.exists():dest.write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
