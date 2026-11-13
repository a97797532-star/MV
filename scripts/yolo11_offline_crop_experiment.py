# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""YOLO11 offline dataset preprocessing: single inference cache, native crops, adapters."""
import argparse,os,sys,json,hashlib,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
B=ROOT/'outputs/yolo11_dynamic_crop_v1'
os.environ['YOLO_CONFIG_DIR']=str(B/'ultralytics_settings');os.environ['YOLO_AUTOINSTALL']='false';os.environ['YOLO_OFFLINE']='true';os.environ['MPLCONFIGDIR']='/tmp/mv-matplotlib'
import cv2,numpy as np,pandas as pd,torch,psutil
from mv_analysis.yolo_crop_geometry import select_box,square_crop,transform_boxes,POLICIES
from mv_analysis.core import prepare_image_reference,information_loss
cv2.setNumThreads(1);torch.set_num_threads(2)
SEED=20261112

# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
# json_write: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def json_write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))
# read_checkpoint: 입력 파일 또는 기록을 읽습니다.
# 입력 인수: path.
def read_checkpoint(path):
 done={}
 if path.exists():
  for line in path.read_text().splitlines():
   r=json.loads(line);done[r['image_path']]=r
 return done
# prepare: 실행에 필요한 입력과 설정을 준비합니다.
def prepare():
 meta=ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv'
 reg=ROOT/'outputs/background_full_20261111_v1/background_classification.csv'
 if (B/'sample_manifest.csv').exists():
  cfg=json.loads((B/'config.json').read_text());assert sha(meta)==cfg['metadata_sha256'];assert sha(B/'weights/yolo11n.pt')==cfg['weight_sha256'];assert sha(B/'sample_manifest.csv')==cfg['sample_sha256'];return pd.read_csv(B/'sample_manifest.csv'),cfg
 m=pd.read_csv(meta);rng=np.random.default_rng(SEED);selected=[]
 for category in sorted(m.category.unique()):
  for split in ['validation','test']:
   for status in ['OK','NG']:
    ids=sorted(m.loc[(m.category==category)&(m.split==split)&(m.status==status),'product_id'].unique())
    chosen=rng.choice(ids,size=2,replace=False)
    selected.extend(chosen.tolist())
 general=m[m.product_id.isin(selected)].copy();general['cohort']='general'
 # A separate mask-informed cohort is never pooled with general evaluation.
 prior=pd.read_csv(ROOT/'outputs/preprocessing_review_20261112_v2/mask_crop_per_image.csv');riskids=[]
 for i,category in enumerate(sorted(m.category.unique())):
  eligible=prior[(prior.category==category)&(prior.split.isin(['validation','test']))&(~prior.product_id.isin(selected))&(prior.crop==640)&(prior.defect_pixels>0)]
  chosen=eligible.sort_values('retention' if i%2 else 'defect_pixels').iloc[0];riskids.append(chosen.product_id)
 risk=m[m.product_id.isin(riskids)].copy();risk['cohort']='mask_informed_risk'
 out=pd.concat([general,risk],ignore_index=True)
 bg=pd.read_csv(reg,usecols=['image_path','background_type']);out=out.merge(bg,on='image_path',validate='one_to_one')
 out['seed']=SEED;out['case_id']=out.image_path.map(lambda p:hashlib.sha256(p.encode()).hexdigest()[:16])
 out=out.sort_values(['cohort','category','product_id','view']).reset_index(drop=True)
 out['image_metric_subset']=False
 # One general image per category/view, alternately OK/NG; geometric metrics use all rows.
 for i,((category,view),g) in enumerate(out[out.cohort=='general'].groupby(['category','view'])):
  status='OK' if i%2 else 'NG';ix=g[g.status==status].index[0];out.loc[ix,'image_metric_subset']=True
 out.to_csv(B/'sample_manifest.csv',index=False)
 cfg=dict(seed=SEED,design='offline dataset builder; one stored inference per image; model adapters run later',
  imgsz=640,conf=.25,iou=.7,max_det=100,agnostic_nms=False,device='cpu',batch=1,half=False,torch_threads=2,
  margins=[0,.1,.2,.3],margin_definition='m*original box width on EACH x side and m*height on EACH y side; total factor1+2m',
  square_policy='ceil max expanded side +2 integer guard pixels; cap1024, shift square inside frame',policies=list(POLICIES),
  fallback='Only missing candidate (NO_DETECTION/NO_CENTRAL_BOX) or execution error -> full native image. No GT-assisted gate; product containment UNVERIFIED.',
  primary_policy='confidence, predeclared for native cache and aligned image metrics; not claimed optimal',
  materialized_native_candidate='confidence margin30 lossless PNG when candidate exists; fallback uses original path',
  adapter_evaluation_targets=[256,512],other_requested_targets='224/392/640 geometric adapters available, not exhaustively resized',
  product_bbox_ground_truth='UNVERIFIED: no validated product GT; detector candidates are not product success',
  cohorts=dict(general=1200,mask_informed_risk=150),smoke='first general row per category,30; same inference checkpoint reused',
  metadata_sha256=sha(meta),weight_sha256=sha(B/'weights/yolo11n.pt'),sample_sha256=sha(B/'sample_manifest.csv'),
  geometry_source_sha256=sha(ROOT/'mv_analysis/yolo_crop_geometry.py'),runner_source_sha256=sha(Path(__file__)))
 json_write(B/'config.json',cfg);return out,cfg

# infer: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, cfg, smoke.
def infer(sample,cfg,smoke=False):
 from ultralytics import YOLO,__version__
 checkpoint=B/'inference_checkpoint.jsonl';done=read_checkpoint(checkpoint)
 subset=sample[(sample.cohort=='general')].groupby('category',sort=True).head(1) if smoke else sample
 todo=[r for r in subset.to_dict('records') if r['image_path'] not in done]
 if not todo:print('Inference cache complete; 0 YOLO calls',flush=True);return
 start=time.perf_counter();model=YOLO(str(B/'weights/yolo11n.pt'));load_s=time.perf_counter()-start
 # Warmup uses synthetic pixels; no evaluation image is inferred twice.
 warm=[]
 for _ in range(3):
  start=time.perf_counter();model.predict(np.zeros((1024,1024,3),np.uint8),imgsz=cfg['imgsz'],conf=cfg['conf'],iou=cfg['iou'],max_det=cfg['max_det'],device='cpu',verbose=False,save=False);warm.append(time.perf_counter()-start)
 json_write(B/('smoke_runtime.json' if smoke else 'runtime.json'),dict(ultralytics=__version__,torch=torch.__version__,opencv=cv2.__version__,numpy=np.__version__,gpu_available=torch.cuda.is_available(),cpu=psutil.cpu_count(),model_load_s=load_s,warmup_s=warm,warmup_input='synthetic black only',rss_after_load_mb=psutil.Process().memory_info().rss/2**20))
 with checkpoint.open('a') as stream:
  for i,row in enumerate(todo,1):
   r={k:row[k] for k in ['image_path','case_id','category','status','view','cohort','split','product_id','background_type']};path=ROOT/'dataset'/row['image_path'];stat=path.stat();r.update(input_bytes=stat.st_size,input_mtime_ns=stat.st_mtime_ns,detections=[],error=None)
   try:
    t=time.perf_counter();im=cv2.imread(str(path));r['decode_ms']=(time.perf_counter()-t)*1000
    if im is None:raise ValueError('IMAGE_DECODE_FAILED')
    t=time.perf_counter();result=model.predict(im,imgsz=cfg['imgsz'],conf=cfg['conf'],iou=cfg['iou'],max_det=cfg['max_det'],agnostic_nms=False,device='cpu',half=False,verbose=False,save=False)[0];r['wall_predict_ms']=(time.perf_counter()-t)*1000;r['ultralytics_speed_ms']=result.speed
    for box in result.boxes:
     class_id=int(box.cls.item());r['detections'].append(dict(xyxy=box.xyxy[0].cpu().tolist(),confidence=float(box.conf.item()),coco_class=class_id,coco_name=model.names[class_id]))
    r['inference_status']='DETECTIONS_PRESENT_UNVERIFIED' if r['detections'] else 'NO_DETECTION'
   except Exception as e:r.update(error=repr(e),inference_status='EXECUTION_ERROR')
   r['rss_mb']=psutil.Process().memory_info().rss/2**20;r['peak_rss_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
   stream.write(json.dumps(r)+'\n');stream.flush();done[r['image_path']]=r
   if i%25==0:print(f'YOLO cached {len(done)}/{len(sample)}; detections={sum(bool(x["detections"]) for x in done.values())}; errors={sum(bool(x["error"]) for x in done.values())}',flush=True)
 json_write(B/('smoke_validation.json' if smoke else 'inference_validation.json'),dict(images=len(subset),cached=sum(p in done for p in subset.image_path),errors=sum(bool(done[p]['error']) for p in subset.image_path),detections=sum(bool(done[p]['detections']) for p in subset.image_path),one_cached_record_per_image=len(done)==len(set(done))))

# evaluate: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, cfg.
def evaluate(sample,cfg):
 detections=read_checkpoint(B/'inference_checkpoint.jsonl');assert set(sample.image_path)==set(detections)
 boxes=pd.read_csv(ROOT/'outputs/spatial_20261111_v7/defect_bboxes.csv');boxgroups={k:g for k,g in boxes.groupby('image_path')}
 checkpoint=B/'evaluation_checkpoint.jsonl';done=read_checkpoint(checkpoint);native=B/'native_crops/confidence_margin30';native.mkdir(parents=True,exist_ok=True)
 with checkpoint.open('a') as stream:
  for i,row in enumerate(sample.to_dict('records'),1):
   if row['image_path'] in done:continue
   det=detections[row['image_path']];path=ROOT/'dataset'/row['image_path'];assert path.stat().st_mtime_ns==det['input_mtime_ns'] and path.stat().st_size==det['input_bytes']
   im=cv2.imread(str(path));mask=cv2.imread(str(ROOT/'dataset'/row['mask_path']),0)>0 if row['has_mask'] else None
   npositive=int(mask.sum()) if mask is not None else None
   labels=None;areas=None
   if mask is not None:
    _,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8);areas=stats[1:,cv2.CC_STAT_AREA]
   original_boxes=boxgroups.get(row['image_path']);xyxy=original_boxes[['x0','y0','x1','y1']].to_numpy() if original_boxes is not None else np.empty((0,4))
   methods=[dict(method='full',crop=[0,0,1024,1024],fallback=False,policy='baseline',margin=None,gate='BASELINE')]
   methods +=[dict(method=f'center{s}',crop=[(1024-s)//2]*2+[(1024+s)//2]*2,fallback=False,policy='baseline',margin=None,gate='BASELINE') for s in [896,768,640]]
   for policy in POLICIES:
    selected,gate=select_box(det['detections'],policy)
    for m in cfg['margins']:
     crop=square_crop(selected,m);name=f'{policy}_m{int(m*100)}'
     methods.append(dict(method=name,crop=crop,fallback=False,policy=policy,margin=m,gate=gate))
     methods.append(dict(method=name+'_fallback',crop=crop or [0,0,1024,1024],fallback=crop is None,policy=policy,margin=m,gate=gate))
   metrics=[];image_metrics=[];offline=None
   for method in methods:
    record={**method,'geometric_defect_pixels':npositive,'has_mask':bool(row['has_mask']),'mask_state':'provided_empty' if npositive==0 else 'provided_positive' if npositive is not None else 'not_provided'}
    crop=method['crop']
    if crop is None:record.update(available=False);metrics.append(record);continue
    x0,y0,x1,y1=crop;native_image=im[y0:y1,x0:x1];record.update(available=True,crop_width=x1-x0,crop_area=(x1-x0)*(y1-y0),frame_occupancy=(x1-x0)*(y1-y0)/1024**2,product_occupancy=None,product_occupancy_status='UNVERIFIED_NO_PRODUCT_GT')
    transform_t=time.perf_counter();transformed,keep=transform_boxes(xyxy,crop);record['box_count']=len(xyxy);record['remaining_boxes']=int(keep.sum());record['removed_boxes']=int((~keep).sum())
    if len(xyxy):
     a=(xyxy[:,2]-xyxy[:,0])*(xyxy[:,3]-xyxy[:,1]);b=(transformed[:,2]-transformed[:,0])*(transformed[:,3]-transformed[:,1]);record['bbox_area_retention']=float(b.sum()/a.sum())
    if mask is not None:
     cropmask=mask[y0:y1,x0:x1];kept=int(cropmask.sum());record.update(kept_pixels=kept,pixel_retention=kept/npositive if npositive else None,crop_state='provided_empty' if not npositive else 'removed' if not kept else 'partial' if kept<npositive else 'preserved')
     surviving_native_ids=np.unique(labels[y0:y1,x0:x1]);surviving_native_ids=surviving_native_ids[surviving_native_ids>0]
     record.update(original_components=len(areas),geometric_components_remaining=len(surviving_native_ids),small_native_components=int((areas<1024).sum()))
     for target in cfg['adapter_evaluation_targets']:
      t=time.perf_counter();resized=cv2.resize(cropmask.astype(np.uint8),(target,target),interpolation=cv2.INTER_NEAREST);labelmap=cv2.resize(labels[y0:y1,x0:x1].astype(np.float32),(target,target),interpolation=cv2.INTER_NEAREST).astype(np.int32);ids=np.unique(labelmap);ids=ids[ids>0]
      ncomponents=cv2.connectedComponents(resized,8)[0]-1
      record[f't{target}_positive_pixels']=int(resized.sum());record[f't{target}_components']=ncomponents;record[f't{target}_original_component_ids_survived']=len(ids);record[f't{target}_small_component_ids_survived']=int((areas[ids-1]<1024).sum());record[f't{target}_mask_resize_ms']=(time.perf_counter()-t)*1000
    record['geometry_eval_ms']=(time.perf_counter()-transform_t)*1000
    # Actual image resize is a downstream adapter test, not materialized training input.
    if row['image_metric_subset'] and method['method'] in ['full','center896','center768','center640','confidence_m0','confidence_m30','confidence_m30_fallback']:
     ref=prepare_image_reference(native_image)
     for target in cfg['adapter_evaluation_targets']:
      t=time.perf_counter();small=cv2.resize(native_image,(target,target),interpolation=cv2.INTER_AREA);resize_ms=(time.perf_counter()-t)*1000
      loss=information_loss(native_image,target,ref);image_metrics.append(dict(method=method['method'],target=target,edge_recall=loss['edge_recall'],local_contrast_retention=loss['local_contrast_retention'],rgb_rmse=loss['rgb_rmse'],adapter_image_resize_ms=resize_ms,native_crop_side=x1-x0,alignment='same native crop region restored to that region'))
    if method['method']=='confidence_m30_fallback':
     offline=dict(case_id=row['case_id'],image_path=row['image_path'],crop_xyxy=crop,fallback=method['fallback'],source_sha256=sha(path),source_status=row['status'],has_mask=bool(row['has_mask']),resize_applied=False,normalize_applied=False,coordinate_format='absolute original XYXY exclusive')
     outbox,keep=transform_boxes(xyxy,crop);offline['valid_cropped_defect_boxes']=outbox[keep].tolist();offline['removed_defect_boxes']=int((~keep).sum())
     if method['fallback']:offline.update(image_file=str(path.relative_to(ROOT)),storage='original reference, no duplicate')
     else:
      destination=native/(row['case_id']+'.png')
      if not destination.exists():assert cv2.imwrite(str(destination),native_image,[cv2.IMWRITE_PNG_COMPRESSION,3])
      offline.update(image_file=str(destination.relative_to(ROOT)),storage='lossless native crop PNG',image_sha256=sha(destination))
      assert np.array_equal(cv2.imread(str(destination)),native_image)
      if mask is not None:
       destination=native/(row['case_id']+'_mask.png')
       if not destination.exists():assert cv2.imwrite(str(destination),(mask[y0:y1,x0:x1]*255).astype(np.uint8))
       offline['mask_file']=str(destination.relative_to(ROOT))
    metrics.append(record)
   record={k:row[k] for k in ['image_path','case_id','category','status','view','product_id','split','cohort','background_type','has_mask']};record.update(metrics=metrics,image_metrics=image_metrics,offline=offline,original_defect_pixels=npositive,outer_defect=bool(mask is not None and npositive and (mask[:128].any() or mask[-128:].any() or mask[:,:128].any() or mask[:,-128:].any())),small_defect_image=bool(npositive is not None and 0<npositive<1024))
   stream.write(json.dumps(record)+'\n');stream.flush();done[row['image_path']]=record
   if i%25==0:print(f'Offline Crop/adapter evaluation {i}/{len(sample)} (cached rows={len(done)})',flush=True)
 # Flatten cached evidence; each distinct image was inferred just once.
 rows=[];imgs=[];offline=[]
 for record in done.values():
  meta={k:v for k,v in record.items() if k not in ['metrics','image_metrics','offline']}
  rows +=[meta|r for r in record['metrics']];imgs +=[meta|r for r in record['image_metrics']];offline.append(record['offline'])
 pd.DataFrame(rows).to_csv(B/'metrics/per_image_crop_metrics.csv',index=False);pd.DataFrame(imgs).to_csv(B/'metrics/aligned_adapter_image_metrics.csv',index=False);pd.DataFrame(offline).to_csv(B/'metrics/offline_native_dataset_manifest.csv',index=False)
 flat=[]
 for r in detections.values():
  row={k:v for k,v in r.items() if k!='detections'};row['detection_count']=len(r['detections']);flat.append(row)
 pd.DataFrame(flat).to_csv(B/'metrics/inference_per_image.csv',index=False)
 json_write(B/'evaluation_complete.json',dict(images=len(done),metric_rows=len(rows),aligned_image_metric_rows=len(imgs),native_dataset_candidate='confidence margin30 + missing-candidate fallback, exploratory not approved product containment',yolo_calls=len(detections),product_gt='UNVERIFIED'))

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['smoke','infer','evaluate']);a=p.parse_args();sample,cfg=prepare()
 if cfg['geometry_source_sha256']!=sha(ROOT/'mv_analysis/yolo_crop_geometry.py'):raise RuntimeError('Changed geometry: use new run')
 if a.phase in ['smoke','infer']:infer(sample,cfg,a.phase=='smoke')
 elif a.phase=='evaluate':evaluate(sample,cfg)
if __name__=='__main__':main()
