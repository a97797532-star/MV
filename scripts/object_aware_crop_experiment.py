# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Bounded OpenCV crop development + frozen-policy independent-product validation."""
import argparse,os,sys,json,hashlib,time,concurrent.futures as cf
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np,pandas as pd
from mv_analysis.object_aware_crop import analyze_proposals,proposal_methods,centered_cover,VERSION
from mv_analysis.core import prepare_image_reference,information_loss
from mv_analysis.yolo_crop_geometry import transform_boxes
cv2.setNumThreads(1)
B=ROOT/'outputs/object_aware_crop_v1';SEED=20261112
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# writej: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def writej(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2))
# readcp: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def readcp(p):
 if not p.exists():return {}
 out={}
 for line in p.read_text().splitlines():
  r=json.loads(line);out[r['image_path']]=r
 return out
# prepare: 실행에 필요한 입력과 설정을 준비합니다.
def prepare():
 B.mkdir(exist_ok=True)
 for name in ['metrics','figures','checkpoints','review']: (B/name).mkdir(exist_ok=True)
 p=B/'config.json'
 if p.exists():
  cfg=json.loads(p.read_text());assert sha(ROOT/'mv_analysis/object_aware_crop.py')==cfg['algorithm_sha256'];assert sha(Path(__file__))==cfg['runner_sha256'];return pd.read_csv(B/'sample_manifest.csv'),cfg
 old=pd.read_csv(ROOT/'outputs/yolo11_dynamic_crop_v1/sample_manifest.csv');old['stage']='development';old['cohort']=old.cohort.replace({'general':'dev_general','mask_informed_risk':'dev_risk'})
 meta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv');bg=pd.read_csv(ROOT/'outputs/background_full_20261111_v1/background_classification.csv',usecols=['image_path','background_type']);rng=np.random.default_rng(SEED)
 excluded=set(old.product_id)
 prior_sample=pd.read_csv(ROOT/'outputs/background_sample_20261111_v5/regional_brightness_per_image.csv',usecols=['product_id']);excluded.update(prior_sample.product_id)
 # Known previous manual mask-threshold/ROI inspection samples, if available.
 roi=ROOT/'outputs/defect_resolution_review_20261111_v7/defect_jpg_resolution_review.csv'
 if roi.exists():
  paths=set(pd.read_csv(roi,usecols=['image_path']).image_path);excluded.update(meta.loc[meta.image_path.isin(paths),'product_id'])
 trainids=[];holdids=[]
 for category in sorted(meta.category.unique()):
  ids=sorted(meta.loc[(meta.category==category)&(meta.status=='OK')&(meta.split=='train')&~meta.product_id.isin(excluded),'product_id'].unique());trainids+=rng.choice(ids,2,replace=False).tolist()
  for status in ['OK','NG']:
   ids=sorted(meta.loc[(meta.category==category)&(meta.status==status)&(meta.split=='validation')&~meta.product_id.isin(excluded),'product_id'].unique());holdids+=rng.choice(ids,1,replace=False).tolist()
 train=meta[meta.product_id.isin(trainids)].merge(bg,on='image_path',validate='one_to_one');train['stage']='prior_fit';train['cohort']='train_normal_prior'
 hold=meta[meta.product_id.isin(holdids)].merge(bg,on='image_path',validate='one_to_one');hold['stage']='holdout';hold['cohort']='independent_validation_products'
 out=pd.concat([old,train,hold],ignore_index=True);out['case_id']=out.image_path.map(lambda s:hashlib.sha256(s.encode()).hexdigest()[:16]);out['seed']=SEED;out.to_csv(B/'sample_manifest.csv',index=False)
 config=dict(seed=SEED,algorithm=VERSION,segmentation_size=256,margins=[0,.1,.2,.3],targets=[256,512],
  extra_target_policy='224/392/640 resized-mask metrics for frozen candidates and full/Center896 on Holdout',
  train_prior='300 normal Train images,2products/category; q95 center-cover side with10% guard,min640,max1024; category-view n=2,UNVERIFIED safety',
  design='1350 previously explored dev +300 Train-normal prior +300 new Validation products. No new Test or YOLO inference.',
  holdout_scope='Unseen by prior YOLO crop/300 geometry/336 ROI sample. Full metadata/brightness/CenterCrop aggregates existed for dataset, so not historically untouched dataset.',
  selection_rule='Development general only: choose up to2 complete-output candidates, prioritize0 fully removed mask images &pixel retention>=.995 then greatest mean geometric magnification. If no feasible option, choose highest-retention and highest-retention/enlargement Pareto proxies; no product-GT claim.',
  product_gt='600 PROPOSAL boxes await real human review; do not replace with automatic GT',
  original_yolo_sha256=sha(ROOT/'outputs/yolo11_dynamic_crop_v1/inference_checkpoint.jsonl'),metadata_sha256=sha(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv'),sample_sha256=sha(B/'sample_manifest.csv'),algorithm_sha256=sha(ROOT/'mv_analysis/object_aware_crop.py'),runner_sha256=sha(Path(__file__)),lock_sha256=sha(ROOT/'uv.lock'))
 writej(p,config);return out,config
# worker_proposal: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: row.
def worker_proposal(row):
 cv2.setNumThreads(1);p=ROOT/'dataset'/row['image_path'];st=p.stat();image=cv2.imread(str(p));assert image is not None
 try:return dict(image_path=row['image_path'],proposals=analyze_proposals(image),error=None,bytes=st.st_size,mtime_ns=st.st_mtime_ns)
 except Exception as e:return dict(image_path=row['image_path'],proposals={},error=repr(e),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
# proposals: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, stage.
def proposals(sample,stage):
 if stage=='smoke':sub=sample[sample.stage=='development'].groupby('category',sort=True).head(1)
 else:sub=sample[sample.stage==stage]
 if stage=='holdout':assert (B/'frozen_policy.json').exists()
 p=B/'checkpoints/proposals.jsonl';done=readcp(p);todo=[r for r in sub.to_dict('records') if r['image_path'] not in done]
 with p.open('a') as f,cf.ProcessPoolExecutor(max_workers=3) as pool:
  for i,r in enumerate(pool.map(worker_proposal,todo),1):
   f.write(json.dumps(r)+'\n');f.flush();done[r['image_path']]=r
   if i%25==0:print(f'{stage} proposals {i}/{len(todo)} checkpointed',flush=True)
 assert not any(done[p]['error'] for p in sub.image_path)
 print(f'{stage}: {len(sub)} proposals available; newly decoded{len(todo)}',flush=True)
# fit_priors: 지정한 보정 자료로 기준값을 구성합니다.
# 입력 인수: sample.
def fit_priors(sample):
 p=B/'train_priors.json'
 if p.exists():raise SystemExit('Train priors already frozen')
 cp=readcp(B/'checkpoints/proposals.jsonl');rows=[]
 for r in sample[sample.stage=='prior_fit'].to_dict('records'):
  prop=cp[r['image_path']]['proposals'];box=prop['hybrid_consensus']['bbox'] or prop['border_lab']['bbox'];crop=centered_cover(box,.1) if box else [0,0,1024,1024]
  rows.append(dict(category=r['category'],view=r['view'],required_side=crop[2]-crop[0],used_missing_full=box is None))
 table=pd.DataFrame(rows);table.to_csv(B/'metrics/train_normal_prior_observations.csv',index=False);priors={};counts={}
 for keys in [['category'],['category','view']]:
  for key,g in table.groupby(keys):
   key='/'.join(key) if isinstance(key,tuple) else key;side=int(np.clip(np.ceil(g.required_side.quantile(.95)),640,1024));side+=side%2;priors[key]=side;counts[key]=len(g)
 writej(p,dict(priors=priors,counts=counts,source='Train OK only; no defect masks',safety='UNVERIFIED sparse heuristic, not validated safe ROI'))
# eval_one: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def eval_one(args):
 row,prop,priors,methods_filter,yolo=args;cv2.setNumThreads(1)
 proposals=prop['proposals'];methods=proposal_methods(proposals,priors,row['category'],row['view'])
 # Explicitly compare image-only base variants with missing-candidate full fallback.
 for base in ['border_lab','border_rgb','border_hsv','contour_canny','grabcut90']:
  for m in [10,30]:
   raw=next(r for r in methods if r['method']==f'{base}_m{m}');methods.append(dict(raw,method=raw['method']+'_fullfb',crop=raw['crop'] or [0,0,1024,1024],fallback=raw['crop'] is None))
 if yolo is not None:
  methods +=[dict(method='cached_yolo_A30_fullfb',crop=yolo['yolo'],fallback=yolo['yolo_fallback'],status='CACHED_YOLO',quality=False),dict(method='cached_yolo_center_union_fullfb',crop=yolo['union'],fallback=yolo['union']==[0,0,1024,1024],status='CACHED_YOLO_UNION',quality=False)]
 if methods_filter:methods=[r for r in methods if r['method'] in methods_filter]
 mask=None
 if row['has_mask']:
  gray=cv2.imread(str(ROOT/'dataset'/row['mask_path']),0)
  if gray is None:raise ValueError('Unreadable mask')
  mask=gray>0;total=int(mask.sum());n,labels,stats,centroids=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8);areas=stats[1:,cv2.CC_STAT_AREA]
 else:total=None;areas=[]
 records=[]
 for r in methods:
  record={**r,'has_mask':bool(row['has_mask']),'original_pixels':total,'product_bbox_iou':None,'product_recall':None,'product_occupancy':None,'product_metrics_status':'UNVERIFIED_NO_HUMAN_GT'};crop=r['crop'];record['available']=crop is not None
  if crop is None:records.append(record);continue
  x0,y0,x1,y1=crop;record.update(side=x1-x0,frame_fraction=(x1-x0)**2/1024**2,magnification=1024/(x1-x0),full_frame=crop==[0,0,1024,1024])
  if mask is not None:
   cm=mask[y0:y1,x0:x1];kept=int(cm.sum());record.update(kept_pixels=kept,retention=kept/total if total else None,mask_state='empty' if not total else 'removed' if not kept else 'partial' if kept<total else 'preserved',source_components=len(areas),small_source_components=int((areas<1024).sum()))
   source_ids=np.unique(labels[y0:y1,x0:x1]);source_ids=source_ids[source_ids>0];record['geometric_component_ids']=len(source_ids)
   targets=[256,512]+([224,392,640] if methods_filter and r['method'] in methods_filter else [])
   for t in targets:
    out=cv2.resize(cm.astype(np.uint8),(t,t),interpolation=cv2.INTER_NEAREST);ids=cv2.resize(labels[y0:y1,x0:x1].astype(np.float32),(t,t),interpolation=cv2.INTER_NEAREST).astype(np.int32);survived=np.unique(ids);survived=survived[survived>0]
    record[f't{t}_positive_pixels']=int(out.sum());record[f't{t}_source_ids']=len(survived);record[f't{t}_small_ids']=int((areas[survived-1]<1024).sum());record[f't{t}_components']=cv2.connectedComponents(out,8)[0]-1
  records.append(record)
 return {k:row[k] for k in ['image_path','case_id','category','view','product_id','status','split','stage','cohort','background_type','has_mask']}|dict(results=records,error=None,small_mask=bool(total and total<1024),outer_mask=bool(total and (mask[:128].any() or mask[-128:].any() or mask[:,:128].any() or mask[:,-128:].any())),source_process_ms=proposals.get('_total_ms'))
# evaluate: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, stage.
def evaluate(sample,stage):
 done=readcp(B/f'checkpoints/evaluation_{stage}.jsonl');proposals=readcp(B/'checkpoints/proposals.jsonl');priors=json.loads((B/'train_priors.json').read_text())['priors'];sub=sample[sample.stage==stage]
 filt=None
 if stage=='holdout':filt=json.loads((B/'frozen_policy.json').read_text())['methods']+['full','center896','center768','center640']
 # Cache only, never call YOLO.
 ycache=readcp(ROOT/'outputs/yolo11_dynamic_crop_v1/evaluation_checkpoint.jsonl');hybrid={r['image_path']:r for r in map(json.loads,(ROOT/'outputs/yolo11_dynamic_crop_v1/hybrid_extension/crop_coordinates.jsonl').read_text().splitlines()) if r['method']=='hybrid896_fullfallback'}
 work=[]
 for row in sub.to_dict('records'):
  if row['image_path'] in done:continue
  p=proposals[row['image_path']];assert not p['error'];source=ROOT/'dataset'/row['image_path'];assert source.stat().st_mtime_ns==p['mtime_ns'] and source.stat().st_size==p['bytes']
  y=None
  if row['image_path'] in ycache:
   yrow=ycache[row['image_path']];method=next(r for r in yrow['metrics'] if r['method']=='confidence_m30_fallback');y=dict(yolo=method['crop'],yolo_fallback=method['fallback'],union=hybrid[row['image_path']]['crop'])
  work.append((row,p,priors,filt,y))
 with (B/f'checkpoints/evaluation_{stage}.jsonl').open('a') as f,cf.ProcessPoolExecutor(max_workers=3) as pool:
  for i,r in enumerate(pool.map(eval_one,work),1):
   f.write(json.dumps(r)+'\n');f.flush();done[r['image_path']]=r
   if i%25==0:print(f'{stage} mask/resize evaluation {i}/{len(work)} checkpointed',flush=True)
 rows=[]
 for r in done.values():
  meta={k:v for k,v in r.items() if k!='results'};rows +=[meta|v for v in r['results']]
 pd.DataFrame(rows).to_csv(B/f'metrics/per_image_{stage}.csv',index=False)
 print(f'{stage} complete: {len(done)} images /{len(rows)} metric rows',flush=True)
# summarize_and_freeze: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def summarize_and_freeze():
 d=pd.read_csv(B/'metrics/per_image_development.csv',low_memory=False);rows=[]
 for (cohort,method),g in d.groupby(['cohort','method']):
  p=g[(g.original_pixels>0)&g.available];rows.append(dict(cohort=cohort,method=method,images=len(g),available=int(g.available.sum()),available_fraction=g.available.mean(),positive_masks=int((g.original_pixels>0).sum()),available_positive_masks=len(p),retention=p.kept_pixels.sum()/p.original_pixels.sum() if len(p) else np.nan,removed=int((p.mask_state=='removed').sum()),partial=int((p.mask_state=='partial').sum()),preserved=int((p.mask_state=='preserved').sum()),mean_magnification=g.magnification.mean(),mean_side=g.side.mean(),full_frame_fraction=g.full_frame.mean(),fallback_fraction=g.fallback.mean()))
 s=pd.DataFrame(rows);s.to_csv(B/'metrics/development_summary.csv',index=False)
 p=B/'frozen_policy.json'
 if p.exists():raise SystemExit('Already frozen; do not retune after holdout')
 cand=s[(s.cohort=='dev_general')&s.available_fraction.eq(1)&(s.method.str.endswith('_full')|s.method.str.endswith('_fullfb'))&~s.method.str.startswith('cached')]
 feasible=cand[(cand.removed==0)&(cand.retention>=.995)&(cand.mean_magnification>=1.05)]
 if len(feasible):balanced=feasible.sort_values(['mean_magnification','retention'],ascending=False).iloc[0]
 else:balanced=cand.sort_values(['retention','mean_magnification'],ascending=False).iloc[0]
 conservative=cand.sort_values(['retention','removed','mean_magnification'],ascending=[False,True,False]).iloc[0];methods=list(dict.fromkeys([balanced.method,conservative.method]))
 writej(p,dict(methods=methods,feasible_count=len(feasible),selected_from='dev_general only; dev_risk diagnostic not selection',rule=json.loads((B/'config.json').read_text())['selection_rule'],selected_rows=cand[cand.method.isin(methods)].to_dict('records'),frozen_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),development_csv_sha256=sha(B/'metrics/per_image_development.csv'),algorithm_sha256=sha(ROOT/'mv_analysis/object_aware_crop.py'),holdout_seen=False))
 print(json.dumps(json.loads(p.read_text()),indent=2),flush=True)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['smoke','train','dev','freeze','holdout']);a=p.parse_args();sample,cfg=prepare()
 if a.phase=='smoke':proposals(sample,'smoke')
 elif a.phase=='train':proposals(sample,'prior_fit');fit_priors(sample)
 elif a.phase=='dev':proposals(sample,'development');evaluate(sample,'development')
 elif a.phase=='freeze':summarize_and_freeze()
 elif a.phase=='holdout':proposals(sample,'holdout');evaluate(sample,'holdout')
if __name__=='__main__':main()
