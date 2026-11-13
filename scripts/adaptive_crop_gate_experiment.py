# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Checkpointed image-only gate fitting, frozen final evaluation and no-crop Dry Run."""
import argparse,sys,json,hashlib,time,concurrent.futures as cf
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np,pandas as pd
from mv_analysis.adaptive_crop_gate import extract_features,decide,VERSION,FULL,CENTER
B=ROOT/'outputs/adaptive_crop_gate_v1';SEED=20261114;cv2.setNumThreads(1)
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# savej: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def savej(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)))
# cp: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def cp(p):
 rows={}
 if p.exists():
  for line in p.read_text().splitlines():
   r=json.loads(line);rows[r['image_path']]=r
 return rows
# prepare: 실행에 필요한 입력과 설정을 준비합니다.
def prepare():
 B.mkdir(exist_ok=True)
 for name in ['metrics','figures','checkpoints','review']:(B/name).mkdir(exist_ok=True)
 if (B/'config.json').exists():
  cfg=json.loads((B/'config.json').read_text());assert cfg['module_sha256']==sha(ROOT/'mv_analysis/adaptive_crop_gate.py');assert cfg['runner_sha256']==sha(Path(__file__));assert cfg['manifest_sha256']==sha(B/'sample_manifest.csv');return pd.read_csv(B/'sample_manifest.csv'),cfg
 old=pd.read_csv(ROOT/'outputs/object_aware_crop_v1/sample_manifest.csv');old['gate_cohort']=old.cohort.map({'dev_general':'development_general','dev_risk':'development_risk','train_normal_prior':'train_reference','independent_validation_products':'retrospective_old_holdout'})
 meta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv');bg=pd.read_csv(ROOT/'outputs/background_full_20261111_v1/background_classification.csv',usecols=['image_path','background_type']);excluded=set(old.product_id)
 previous=pd.read_csv(ROOT/'outputs/background_sample_20261111_v5/regional_brightness_per_image.csv',usecols=['product_id']);excluded.update(previous.product_id)
 roi=pd.read_csv(ROOT/'outputs/defect_resolution_review_20261111_v7/defect_jpg_resolution_review.csv',usecols=['image_path']);excluded.update(meta.loc[meta.image_path.isin(roi.image_path),'product_id'])
 rng=np.random.default_rng(SEED);cal=[];hold=[]
 for category in sorted(meta.category.unique()):
  for status in ['OK','NG']:
   ids=sorted(meta.loc[(meta.category==category)&(meta.status==status)&meta.split.eq('train')&~meta.product_id.isin(excluded),'product_id'].unique());picked=rng.choice(ids,1,replace=False).tolist();cal+=picked;excluded.update(picked)
   ids=sorted(meta.loc[(meta.category==category)&(meta.status==status)&meta.split.eq('validation')&~meta.product_id.isin(excluded),'product_id'].unique());picked=rng.choice(ids,1,replace=False).tolist();hold+=picked;excluded.update(picked)
 frames=[old]
 for ids,name in [(cal,'calibration'),(hold,'final_holdout')]:
  frame=meta[meta.product_id.isin(ids)].merge(bg,on='image_path',validate='one_to_one');frame['gate_cohort']=name;frames.append(frame)
 out=pd.concat(frames,ignore_index=True);out['case_id']=out.image_path.map(lambda s:hashlib.sha256(s.encode()).hexdigest()[:16]);out.to_csv(B/'sample_manifest.csv',index=False)
 config=dict(version=VERSION,seed=SEED,images=2550,old_base_proposals=1950,new_images=600,
  additional_feature_reason='Old checkpoints lack full foreground boundary occupancy and foreground/background contrast. Re-extract GrabCut90 only on reused images; reuse their RGB/Lab/contour boxes. New600 compute only required methods.',
  reference='Old300 Train normal +new150 Calibration Train normal =450 image-only references. No masks used for cutoffs.',
  minimum_category_view_n=20,threshold_quantiles=[.01,.99],center_safety='Every available product proxy box plus adaptive-center proxy inside Center896 with8px guard; zero GrabCut foreground outside Center896; no fatal rule and sufficient contrast',
  actual_policy='No validated team-approved scopes: deployment default selects C. Research proposals A/B/C are evaluated separately, never called validated product preservation.',
  prohibited_inputs=['OK/NG','defect_type','has_mask','defect_mask','mask_path'],team_product_loss_tolerance=None,team_gate_false_pass_tolerance=None,scope_approvals={},targets=[256,512],
  manifest_sha256=sha(B/'sample_manifest.csv'),module_sha256=sha(ROOT/'mv_analysis/adaptive_crop_gate.py'),runner_sha256=sha(Path(__file__)),root_lock_sha256=sha(ROOT/'uv.lock'),
  old_object_checkpoint_sha256=sha(ROOT/'outputs/object_aware_crop_v1/checkpoints/proposals.jsonl'),yolo_checkpoint_sha256=sha(ROOT/'outputs/yolo11_dynamic_crop_v1/inference_checkpoint.jsonl'))
 savej(B/'config.json',config);return out,config
# worker_feature: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def worker_feature(args):
 row,cached=args;cv2.setNumThreads(1);p=ROOT/'dataset'/row['image_path'];data=p.read_bytes();im=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR);assert im is not None
 t=time.perf_counter();f=extract_features(im,cached);assert f['cached_bbox_parity'] is not False
 return dict(image_path=row['image_path'],features=f,source_hash=hashlib.sha256(data).hexdigest(),elapsed_ms=(time.perf_counter()-t)*1000,error=None,cohort=row['gate_cohort'])
# features: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, stage.
def features(sample,stage):
 subset=sample[sample.gate_cohort!='final_holdout'] if stage=='development' else sample[sample.gate_cohort=='final_holdout']
 if stage=='smoke':subset=sample[sample.gate_cohort=='development_general'].groupby('category').head(1)
 if stage=='final':assert (B/'frozen_policy.json').exists()
 done=cp(B/'checkpoints/features.jsonl');old=cp(ROOT/'outputs/object_aware_crop_v1/checkpoints/proposals.jsonl');todo=[(r,old[r['image_path']]['proposals'] if r['image_path'] in old else None) for r in subset.to_dict('records') if r['image_path'] not in done]
 with (B/'checkpoints/features.jsonl').open('a') as stream,cf.ProcessPoolExecutor(max_workers=3) as pool:
  for i,r in enumerate(pool.map(worker_feature,todo),1):
   stream.write(json.dumps(r)+'\n');stream.flush();done[r['image_path']]=r
   if i%50==0:print(f'{stage} image-only features {i}/{len(todo)} saved',flush=True)
 print(f'{stage}: {len(subset)} ready,newlyprocessed{len(todo)}',flush=True)
# fit: 지정한 보정 자료로 기준값을 구성합니다.
# 입력 인수: sample, cfg.
def fit(sample,cfg):
 p=B/'frozen_policy.json'
 if p.exists():raise SystemExit('Frozen policy already exists; never retune after final holdout')
 f=cp(B/'checkpoints/features.jsonl');reference=sample[(sample.gate_cohort=='train_reference')|((sample.gate_cohort=='calibration')&sample.status.eq('OK'))]
 assert len(reference)==450 and reference.split.eq('train').all() and reference.status.eq('OK').all()
 rows=[dict(f[r['image_path']]['features'],category=r['category'],view=r['view'],image_path=r['image_path']) for r in reference.to_dict('records')];d=pd.DataFrame(rows)
 names=['grabcut_change','fg_fraction','component_count','largest_component_fraction','foreground_contrast','boundary_touch_fraction','fg_outside_crop','crop_side','box_aspect','center_x','center_y','crop_center_offset','median_method_iou','max_method_center_distance','min_method_area_ratio']
 bounds={name:dict(low=float(d[name].dropna().quantile(.01)),high=float(d[name].dropna().quantile(.99)),n=int(d[name].notna().sum())) for name in names}
 groups={cat+'/'+view:dict(n=len(g),status='INSUFFICIENT_NOT_USED') for (cat,view),g in d.groupby(['category','view'])}
 thresholds=dict(global_n=len(d),global_=bounds,category_view=groups,minimum_category_view_n=cfg['minimum_category_view_n'],quantiles=[.01,.99],note='Image normal-reference tails only; not calibrated product loss/FPR safety thresholds')
 thresholds['global']=thresholds.pop('global_');reference[['image_path','category','view']+names].to_csv(B/'metrics/normal_reference_features.csv',index=False)
 savej(B/'thresholds.json',thresholds)
 savej(p,dict(policy_version=VERSION,thresholds_sha256=sha(B/'thresholds.json'),module_sha256=cfg['module_sha256'],fit_source_count=450,source='Train normal only, no defect evaluation used',frozen_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),final_holdout_seen=False,team_loss_tolerances=None,scope_approvals={}))
# dry_run: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample, cfg.
def dry_run(sample,cfg):
 feats=cp(B/'checkpoints/features.jsonl');thresholds=json.loads((B/'thresholds.json').read_text());frozen=json.loads((B/'frozen_policy.json').read_text());assert sha(B/'thresholds.json')==frozen['thresholds_sha256'];p=B/'dry_run_manifest.jsonl'
 if p.exists():raise SystemExit('Preserve Dry Run manifest')
 rows=[]
 with p.open('x') as stream:
  for r in sample.to_dict('records'):
   entry=feats[r['image_path']];f=entry['features'];variants={v:decide(f,thresholds,r['category'],r['view'],v,cfg['scope_approvals']) for v in ['risk_full','review_center','validated_scope']};decision=variants['review_center']
   record=dict(image_id=r['case_id'],image_path=r['image_path'],product_id=r['product_id'],category=r['category'],view=r['view'],original_path='dataset/'+r['image_path'],original_width=1024,original_height=1024,
    proposed_crop_xyxy=f['proposed_crop'],selected_crop_xyxy=decision['selected_crop'],selected_policy=decision['selected_policy'],quality_status=decision['image_quality_status'],risk_codes=decision['risk_codes'],fallback_reason=decision['fallback_reason'],policy_version=VERSION,source_hash=entry['source_hash'],research_policy=decision['research_selected_policy'],research_crop=decision['research_selected_crop'],gate_variants=variants,gate_cohort=r['gate_cohort'],deployment_eligible=decision['deployment_eligible'])
   stream.write(json.dumps(record)+'\n');rows.append(record)
 pd.DataFrame([{k:v for k,v in r.items() if k!='gate_variants'} for r in rows]).to_csv(B/'metrics/dry_run_manifest.csv',index=False);savej(B/'dry_run_validation.json',dict(images=len(rows),actual_dataset_crop_images_saved=0,source_only_no_crops=True,deployment_scope_approval_count=0,selected_policy_counts=pd.Series([r['selected_policy'] for r in rows]).value_counts().to_dict()))
# evaluation_worker: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def evaluation_worker(args):
 row,decision=args;cv2.setNumThreads(1);mask=None
 if row['has_mask']:
  m=cv2.imread(str(ROOT/'dataset'/row['mask_path']),0);assert m is not None;mask=m>0;n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8);areas=stats[1:,cv2.CC_STAT_AREA];total=int(mask.sum())
 else:total=None;areas=[]
 methods=[]
 for name,v in decision['gate_variants'].items():methods.append((f'research_{name}',v['research_selected_policy'],v['research_selected_crop']))
 methods +=[('deployment_default',decision['selected_policy'],decision['selected_crop_xyxy']),('fixed_full','C',FULL),('fixed_center896','B',CENTER),('fixed_grabcut10','A' if decision['proposed_crop_xyxy'] else 'C',decision['proposed_crop_xyxy'] or FULL)]
 rows=[]
 for name,policy,crop in methods:
  x0,y0,x1,y1=crop;v=dict(method=name,selected_policy=policy,crop=crop,side=x1-x0,magnification=1024/(x1-x0),full_frame=crop==FULL,original_pixels=total,kept_pixels=None,retention=None,mask_state='not_provided',source_components=len(areas),small_source_components=int((areas<1024).sum()) if len(areas) else 0,
   evaluation_risk_codes=[],product_metrics_status='UNVERIFIED')
  if mask is not None:
   cm=mask[y0:y1,x0:x1];kept=int(cm.sum());v.update(kept_pixels=kept,retention=kept/total if total else None,mask_state='empty' if not total else 'removed' if not kept else 'partial' if kept<total else 'preserved')
   if total and kept<total:v['evaluation_risk_codes']=['MASK_LOSS_EVAL_ONLY']
   for t in [256,512]:
    out=cv2.resize(cm.astype(np.uint8),(t,t),interpolation=cv2.INTER_NEAREST);ids=cv2.resize(labels[y0:y1,x0:x1].astype(np.float32),(t,t),interpolation=cv2.INTER_NEAREST).astype(np.int32);survived=np.unique(ids);survived=survived[survived>0];v.update({f't{t}_positive_pixels':int(out.sum()),f't{t}_source_ids':len(survived),f't{t}_small_ids':int((areas[survived-1]<1024).sum()),f't{t}_components':cv2.connectedComponents(out,8)[0]-1})
  rows.append(v)
 return {k:row[k] for k in ['image_path','case_id','product_id','category','view','status','split','gate_cohort','has_mask','background_type']}|dict(quality_status=decision['quality_status'],risk_codes=decision['risk_codes'],small_mask=bool(total and total<1024),outer_mask=bool(total and (mask[:128].any() or mask[-128:].any() or mask[:,:128].any() or mask[:,-128:].any())),metrics=rows,error=None)
# evaluate: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: sample.
def evaluate(sample):
 decisions=cp(B/'dry_run_manifest.jsonl');done=cp(B/'checkpoints/evaluation.jsonl');todo=[(r,decisions[r['image_path']]) for r in sample.to_dict('records') if r['image_path'] not in done]
 with (B/'checkpoints/evaluation.jsonl').open('a') as stream,cf.ProcessPoolExecutor(max_workers=3) as pool:
  for i,r in enumerate(pool.map(evaluation_worker,todo),1):
   stream.write(json.dumps(r)+'\n');stream.flush();done[r['image_path']]=r
   if i%50==0:print(f'Annotation eval only {i}/{len(todo)} saved',flush=True)
 rows=[]
 for r in done.values():rows +=[{k:v for k,v in r.items() if k!='metrics'}|v for v in r['metrics']]
 pd.DataFrame(rows).to_csv(B/'metrics/per_image_evaluation.csv',index=False);savej(B/'evaluation_complete.json',dict(images=len(done),method_rows=len(rows),source_only=True,model_training=False))
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['smoke','features','freeze','final','dry-run','evaluate']);a=p.parse_args();sample,cfg=prepare()
 if a.phase=='smoke':features(sample,'smoke')
 elif a.phase=='features':features(sample,'development')
 elif a.phase=='freeze':fit(sample,cfg)
 elif a.phase=='final':features(sample,'final')
 elif a.phase=='dry-run':dry_run(sample,cfg)
 else:evaluate(sample)
if __name__=='__main__':main()
