# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read-only human GT audit, product-group calibration/validation/frozen final evaluation."""
import os,sys,json,hashlib,random
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np,pandas as pd
from PIL import Image
from review_product_bboxes import ReviewStore,DEFAULT_PROPOSALS,ROOT
from mv_analysis.adaptive_crop_gate import decide,contains,FULL,CENTER
B=ROOT/'outputs/adaptive_crop_full_v1';M=B/'metrics';SEED=20261116

# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
# savej: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def savej(p,v):
 p=Path(p)
 if p.exists():raise RuntimeError(f'Preserve existing {p}')
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf8');tmp.replace(p)
# cp: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def cp(p):return {r['image_path']:r for r in map(json.loads,Path(p).read_text().splitlines())}
# prep: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def prep():
 B.mkdir(exist_ok=True);M.mkdir(exist_ok=True);(B/'figures').mkdir(exist_ok=True);(B/'checkpoints').mkdir(exist_ok=True)
 if (B/'gt_split_manifest.csv').exists():return pd.read_csv(B/'gt_split_manifest.csv')
 primary=DEFAULT_PROPOSALS.with_name('human_approved_gt.jsonl');other=ROOT/'outputs/adaptive_crop_gate_v1/review/review_events.jsonl';store=ReviewStore(DEFAULT_PROPOSALS,ROOT/'dataset',extra_ledgers=[other]);states=store.snapshot();rows=[]
 meta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv').set_index('image_path')
 for r in store.rows:
  e=states.get(r['image_path'],{})
  if e.get('status')!='VERIFIED_GT':continue
  path=store.path(r)
  with Image.open(path) as im:width,height=im.size
  assert width==height==1024
  a=meta.loc[r['image_path']];assert a.product_id==r['product_id'] and a.split==r['split']
  rows.append({k:r[k] for k in ['case_id','image_path','product_id','category','view','status','split','background_type']}|dict(verified_gt_bbox=json.dumps(e['bbox']),reviewer=e['reviewer'],reviewed_utc=e['reviewed_utc'],source_sha256=e['source_sha256'],original_width=width,original_height=height))
 d=pd.DataFrame(rows);assert not d.image_path.duplicated().any();groups=d.groupby('product_id').agg(split=('split','first'),category=('category','first'),status=('status','first'),n=('image_path','size'),views=('view','nunique'));assert groups.n.eq(5).all() and groups.views.eq(5).all()
 # Never fit current gate on Test product GT. Prior exposure is disclosed separately.
 pool=groups[groups.split.eq('validation')].reset_index();rng=np.random.default_rng(SEED);cal=[]
 for cat,g in pool.groupby('category'):
  cal.append(rng.choice(sorted(g.product_id)))
 remaining=pool[~pool.product_id.isin(cal)].product_id.tolist();rng.shuffle(remaining);cal+=remaining[:max(0,min(40,len(pool)-10)-len(cal))]
 roles={pid:('gate_calibration' if pid in cal else 'gate_validation') for pid in pool.product_id};roles.update({pid:'gate_final_evaluation' for pid in groups[groups.split.eq('test')].index})
 assert len(set(cal))==len(cal)
 d['gate_role']=d.product_id.map(roles);assert d.gate_role.notna().all();assert d.groupby('product_id').gate_role.nunique().eq(1).all();d['historical_policy_exposure']='YES_PREVIOUS_CROP_DEVELOPMENT';d.to_csv(B/'gt_split_manifest.csv',index=False)
 ledger_records=[json.loads(v) for v in primary.read_text().splitlines()];summary=dict(proposals=len(store.rows),raw_approval_records=len(ledger_records),latest_verified_gt=len(d),extra_history_records=len(ledger_records)-len(d),declared_products=d.product_id.nunique(),reviewers=d.reviewer.value_counts().to_dict(),first_approval=d.reviewed_utc.min(),last_approval=d.reviewed_utc.max(),invalid_coordinates=0,source_hash_mismatches=0,all_600_actual_source_dimensions_verified=True,coordinate_tolerances_px=[0,2],tolerance_note='0px strict primary; 2px annotation sensitivity only, not team-approved loss allowance',roles=d.groupby('gate_role').size().to_dict(),role_products=d.groupby('gate_role').product_id.nunique().to_dict(),no_current_test_gt_fit=True,historical_exposure='All reviewed groups previously used in crop exploration; final here is withheld current human-GT evaluation, NOT independently untouched data',minimum_category_view_n=20,gt_minimum_note='Reuse prior gate evidence minimum20; each category-view has only4 reviewed images total, not a proven statistical sufficiency standard',seed=SEED,ledger_hashes={str(p.relative_to(ROOT)):sha(p) for p in store.read_ledgers if p.exists()},proposal_csv_sha256=sha(DEFAULT_PROPOSALS),old_feature_checkpoint_sha256=sha(ROOT/'outputs/adaptive_crop_gate_v1/checkpoints/features.jsonl'),old_thresholds_sha256=sha(ROOT/'outputs/adaptive_crop_gate_v1/thresholds.json'))
 savej(B/'gt_audit.json',summary);return d

# measurements: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: crop, gt.
def measurements(crop,gt):
 a=np.array(crop,float);g=np.array(gt,float);inter=np.maximum(0,np.minimum(a[2:],g[2:])-np.maximum(a[:2],g[:2]));intersection=float(inter.prod());area=float((g[2]-g[0])*(g[3]-g[1]));croparea=float((a[2]-a[0])*(a[3]-a[1]));strict=bool(np.all(a[:2]<=g[:2]) and np.all(a[2:]>=g[2:]));tolerant=bool(np.all(a[:2]-2<=g[:2]) and np.all(a[2:]+2>=g[2:]));return dict(bbox_area_recall=intersection/area,contained_exact=strict,contained_tolerance2=tolerant,completely_lost=intersection==0,partial_loss=0<intersection<area,original_bbox_occupancy=area/1024**2,visible_bbox_crop_occupancy=intersection/croparea,geometric_gain=1024/(a[2]-a[0]),side=a[2]-a[0])
# research: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: features, thresholds, row, candidate.
def research(features,thresholds,row,candidate):
 r=decide(features,thresholds,row['category'],row['view']);policy=r['research_selected_policy'];crop=r['research_selected_crop'];why=[]
 if policy=='A' and (features['crop_side']<candidate['min_side'] or (candidate['require_proxy_containment'] and not all(contains(crop,q,8) for q in features['other_boxes'].values()))):
  why=['CALIBRATED_CROP_RISK'];policy='B' if r['center896_image_check'] else 'C';crop=CENTER if policy=='B' else FULL
 return policy,crop,r,why

# summarize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: d, keys.
def summarize(d,keys):
 out=[]
 for key,g in d.groupby(keys,dropna=False):
  key=key if isinstance(key,tuple) else (key,);out.append(dict(zip(keys,key))|dict(images=len(g),products=g.product_id.nunique(),mean_bbox_area_recall=g.bbox_area_recall.mean(),min_bbox_area_recall=g.bbox_area_recall.min(),complete_exact_rate=g.contained_exact.mean(),complete_tolerance2_rate=g.contained_tolerance2.mean(),partial_loss=int(g.partial_loss.sum()),complete_loss=int(g.completely_lost.sum()),mean_side=g.side.mean(),mean_geometric_gain=g.geometric_gain.mean(),mean_visible_bbox_occupancy=g.visible_bbox_crop_occupancy.mean()))
 return pd.DataFrame(out)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 d=prep();features=cp(ROOT/'outputs/adaptive_crop_gate_v1/checkpoints/features.jsonl');thresholds=json.loads((ROOT/'outputs/adaptive_crop_gate_v1/thresholds.json').read_text());assert set(d.image_path)<=set(features)
 if (B/'policy.json').exists():raise SystemExit('Policy already frozen; reuse outputs, do not re-evaluate final')
 # Only Calibration and Validation product boxes are used before freeze.
 pre=d[d.gate_role.ne('gate_final_evaluation')];candidates=[dict(name=f'min{s}_proxy{int(p)}',min_side=s,require_proxy_containment=p) for s in [0,768,896,960,1024] for p in [False,True]];pre_rows=[]
 for r in pre.to_dict('records'):
  f=features[r['image_path']]['features'];gt=json.loads(r['verified_gt_bbox'])
  for c in candidates:
   policy,crop,_,_=research(f,thresholds,r,c);pre_rows.append({k:r[k] for k in ['image_path','product_id','category','view','gate_role','background_type']}|dict(candidate=c['name'],selected_policy=policy,crop=json.dumps(crop))|measurements(crop,gt))
 pre_eval=pd.DataFrame(pre_rows);pre_eval.to_csv(M/'calibration_validation_candidate_evaluation.csv',index=False);cs=summarize(pre_eval,['gate_role','candidate']);cs.to_csv(M/'calibration_validation_candidate_summary.csv',index=False)
 ca=cs[cs.gate_role.eq('gate_calibration')];va=cs[cs.gate_role.eq('gate_validation')];eligible=ca[ca.complete_exact_rate.eq(1)].candidate.tolist();v=va[va.candidate.isin(eligible)].sort_values(['complete_exact_rate','mean_geometric_gain','candidate'],ascending=[False,False,True]);selected=v.iloc[0].candidate if len(v) else 'min1024_proxy1';chosen=next(c for c in candidates if c['name']==selected)
 # Preserve research candidate, but never invent approval or acceptable product loss rate.
 policy=dict(policy_version='adaptive-full-v1-safe',research_candidate=chosen,thresholds_sha256=sha(ROOT/'outputs/adaptive_crop_gate_v1/thresholds.json'),gt_split_manifest_sha256=sha(B/'gt_split_manifest.csv'),calibration_uses_test=False,rule_frozen_utc=datetime.now(timezone.utc).isoformat(),final_metrics_seen=False,production_mode='FULL_FRAME_UNVERIFIED_SCOPES',approved_scopes={},team_product_loss_tolerance=None,team_false_pass_tolerance=None,minimum_category_view_n=20,reason='600 GT=4 images/category-view total; fewer per role; historical development exposure; no independently verified scopes or team loss tolerance. Final cannot authorize unverified scopes.',gt_inputs_for_production=False,gt_inputs_for_candidate_selection='Calibration/Validation aggregate only; never per-image selection',feature_module_sha256=sha(ROOT/'mv_analysis/adaptive_crop_gate.py'),extractor_implementation='existing extract_features; no retuning image feature extraction')
 savej(B/'policy.json',policy)
 eval_rows=[];risk=[]
 for r in d.to_dict('records'):
  f=features[r['image_path']]['features'];gt=json.loads(r['verified_gt_bbox']);pol,crop,gate,why=research(f,thresholds,r,chosen);base=[('grabcut90_m10',f['proposed_crop'] or FULL),('center896',CENTER),('full1024',FULL),('previous_image_gate',gate['research_selected_crop']),('calibrated_research_gate',crop),('production_safe_policy',FULL)]
  for method,a in base:eval_rows.append({k:r[k] for k in ['image_path','product_id','category','view','split','background_type','gate_role']}|dict(method=method,crop=json.dumps(a),quality_status=gate['image_quality_status'],risk_codes=';'.join(gate['image_risk_codes']),selected_policy=pol if method=='calibrated_research_gate' else None)|measurements(a,gt))
  raw=measurements(f['proposed_crop'] or FULL,gt);risk.append({k:r[k] for k in ['image_path','product_id','category','view','background_type','gate_role']}|dict(raw_A_product_loss=not raw['contained_exact'],gate_PASS=gate['image_quality_status']=='PASS',gate_blocked=gate['image_quality_status']!='PASS',risk_codes=';'.join(gate['image_risk_codes'])))
 e=pd.DataFrame(eval_rows);e.to_csv(M/'verified_gt_policy_evaluation.csv',index=False);summarize(e,['gate_role','method']).to_csv(M/'verified_gt_policy_summary.csv',index=False)
 for key in ['category','view','background_type']:summarize(e,['gate_role',key,'method']).to_csv(M/f'gt_summary_by_{key}.csv',index=False)
 rr=pd.DataFrame(risk);rr.to_csv(M/'gate_risk_per_image.csv',index=False)
 # risk_summary: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: keys.
 def risk_summary(keys):
  out=[]
  for key,g in rr.groupby(keys,dropna=False):
   key=key if isinstance(key,tuple) else (key,);lost=g.raw_A_product_loss;passed=g.gate_PASS;blocked=~passed;safe=~lost;missed=int((lost&passed).sum());tp=int((lost&blocked).sum());out.append(dict(zip(keys,key))|dict(images=len(g),raw_A_loss=int(lost.sum()),PASS=int(passed.sum()),blocked=int(blocked.sum()),loss_blocked=tp,loss_PASS=missed,loss_given_actual_loss=missed/lost.sum() if lost.sum() else None,loss_given_PASS=missed/passed.sum() if passed.sum() else None,false_reject_rate=int((safe&blocked).sum())/safe.sum() if safe.sum() else None,risk_recall=tp/lost.sum() if lost.sum() else None,risk_precision=tp/blocked.sum() if blocked.sum() else None))
  return pd.DataFrame(out)
 for keys,name in [(['gate_role'],'gate_risk_summary'),(['gate_role','category'],'gate_risk_by_category'),(['gate_role','view'],'gate_risk_by_view'),(['gate_role','background_type'],'gate_risk_by_background')]:risk_summary(keys).to_csv(M/(name+'.csv'),index=False)
 savej(B/'gt_evaluation_complete.json',dict(images=len(d),policy_rows=len(e),test_gt_used_for_calibration=False,final_evaluation_frozen_before_metrics=True,final_role_images=int(d.gate_role.eq('gate_final_evaluation').sum()),independent_final_status='UNVERIFIED_HISTORICAL_POLICY_EXPOSURE',production_scopes_approved=0,original_ledger_unchanged=all(sha(ROOT/p)==h for p,h in json.loads((B/'gt_audit.json').read_text())['ledger_hashes'].items())))
 print(pd.read_csv(M/'verified_gt_policy_summary.csv').to_string(index=False));print(pd.read_csv(M/'gate_risk_summary.csv').to_string(index=False));print('FROZEN',policy['production_mode'],chosen)
if __name__=='__main__':main()
