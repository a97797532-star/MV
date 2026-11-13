# 한글 안내: 승인 Ledger와 좌표·출처가 일치하는 전처리 CSV를 식별합니다. 수정 시각만으로 고르지 않습니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Identify final CSV by immutable base lineage and exact latest crop approval matching."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd,numpy as np
from mv_analysis.data.manifest import file_hash,geometry_errors,group_audit,ManifestIndex
from review_product_bboxes import json_bytes,reject_constant,ReviewStore,DEFAULT_PROPOSALS,ROOT
B=ROOT/'outputs/adaptive_crop_full_v1';O=ROOT/'outputs/data_loader_validation_v1'

# audit_candidate: 자료와 기록을 대조해 오류와 확인 범위를 남깁니다.
# 입력 인수: base, d, states, base_hash.
def audit_candidate(base,d,states,base_hash):
 errors=[]
 # add: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: key, msg.
 def add(key,msg):errors.append(dict(image_id=key,error=msg))
 if len(d)!=len(base) or d.image_id.duplicated().any() or set(d.image_id)!=set(base.image_id):return [dict(image_id='',error='IMAGE_SET_OR_DUPLICATE_MISMATCH')]
 raw=base.set_index('image_id');q=d.set_index('image_id');geometry=geometry_errors(d)
 errors+=geometry.to_dict('records')
 for key in ['product_id','category','view','split','source_relative_path','original_path','original_width','original_height','source_fingerprint','coordinate_format']:
  for imageid in q.index[~q[key].eq(raw.loc[q.index,key])]:add(imageid,'BASE_IDENTITY_CHANGED:'+key)
 for imageid,r in q.iterrows():
  event=states.get(imageid);approved=event and event['status']=='APPROVED_CROP';expected=event['crop_xyxy'] if approved else [raw.loc[imageid,c] for c in ['crop_x0','crop_y0','crop_x1','crop_y1']];actual=[r[c] for c in ['crop_x0','crop_y0','crop_x1','crop_y1']]
  if actual!=expected:add(imageid,'CROP_DOES_NOT_MATCH_LATEST_APPROVAL_OR_BASE')
  if approved:
   if event['base_manifest_sha256']!=base_hash or event['image_path']!=r.source_relative_path or event['source_fingerprint']!=r.source_fingerprint:add(imageid,'APPROVAL_IDENTITY_MISMATCH')
   if r.get('crop_review_status')!='APPROVED_CROP':add(imageid,'APPROVAL_NOT_REFLECTED')
   for col,value in [('crop_reviewer',event['reviewer']),('crop_reviewed_utc',event['reviewed_utc']),('manual_annotation_assisted',event['preview_evaluation']['annotation_assisted'])]:
    if r.get(col)!=value:add(imageid,'APPROVAL_PROVENANCE_MISMATCH:'+col)
   full=expected==[0,0,int(r.original_width),int(r.original_height)]
   if r.selected_policy!=('C' if full else 'HUMAN_CROP'):add(imageid,'APPROVAL_POLICY_MISMATCH')
   if r.policy_version!=str(raw.loc[imageid,'policy_version'])+'+human-override-v1':add(imageid,'APPROVAL_VERSION_MISMATCH')
   revision=hashlib.sha256(json_bytes(event)).hexdigest();expected_hash=hashlib.sha256((str(raw.loc[imageid,'policy_sha256'])+revision).encode()).hexdigest()
   if r.policy_sha256!=expected_hash:add(imageid,'APPROVAL_POLICY_HASH_MISMATCH')
  elif r.get('crop_review_status','UNREVIEWED_BASELINE')=='APPROVED_CROP' or r.selected_policy!=raw.loc[imageid,'selected_policy']:add(imageid,'UNAPPROVED_CROP_MARKED_APPROVED')
 return errors

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 O.mkdir(exist_ok=True)
 if (O/'manifest_fingerprint.json').exists():raise SystemExit('Selection already frozen; resume its checkpointed validation instead')
 basefile=B/'preprocessing_metadata.csv';base=pd.read_csv(basefile,keep_default_na=False);base_hash=file_hash(basefile);ledger=B/'manual_crop_review_ledger.jsonl';events=[json.loads(l,parse_constant=reject_constant) for l in ledger.read_text().splitlines()];states={};chain_errors=[]
 for e in events:
  old=states.get(e['case_id']);previous=hashlib.sha256(json_bytes(old)).hexdigest() if old else '0'
  if e['previous_revision']!=previous:chain_errors.append(dict(image_id=e['case_id'],error='APPROVAL_REVISION_CHAIN_MISMATCH'))
  if e['status']=='APPROVED_CROP' and (not e.get('not_product_gt') or e.get('human_ack') is not True or not isinstance(e.get('reviewer'),str) or len(e['reviewer'].strip())<2):chain_errors.append(dict(image_id=e['case_id'],error='INVALID_EXPLICIT_CROP_APPROVAL'))
  states[e['case_id']]=e
 pd.DataFrame(chain_errors,columns=['image_id','error']).to_csv(O/'approval_history_errors.csv',index=False)
 if chain_errors:raise RuntimeError('Approval chain invalid; no manifest selected')
 # Existing review reader verifies original byte hashes without writing any approvals.
 from review_crop_ranges import CropReviewStore
 reader=CropReviewStore(B/'manual_crop_review.csv',ROOT/'dataset',basefile,ledger);snapshot=reader.snapshot();assert len(snapshot)==len(states)
 outcomes=[];valid=[]
 for path in sorted(B.glob('preprocessing_metadata_reviewed_v*.csv')):
  d=pd.read_csv(path,keep_default_na=False);errors=audit_candidate(base,d,states,base_hash);pd.DataFrame(errors,columns=['image_id','error']).to_csv(O/(path.stem+'_errors.csv'),index=False);outcomes.append(dict(path=str(path),sha256=file_hash(path),rows=len(d),errors=len(errors),approved_rows=int(d.get('crop_review_status',pd.Series(dtype=str)).eq('APPROVED_CROP').sum())))
  if not errors:valid.append(path)
 if not valid:
  (O/'manifest_selection.json').write_text(json.dumps(dict(success=False,candidates=outcomes,reason='No CSV matches latest approvals; no coordinate repair or automatic export performed'),indent=2));raise RuntimeError('No reviewed CSV matches current ledger')
 # Equivalent candidates must agree in full table content; never pick by mtime.
 tables=[pd.read_csv(p,keep_default_na=False).sort_values('image_id').reset_index(drop=True) for p in valid]
 if any(not tables[0].equals(v) for v in tables[1:]):raise RuntimeError('Multiple non-equivalent valid manifests; manual resolution required')
 selected=sorted(valid,key=lambda p:p.name)[0];d=pd.read_csv(selected,keep_default_na=False);index=ManifestIndex(selected,require_complete=True);group_audit(d,True)
 product_store=ReviewStore(DEFAULT_PROPOSALS,ROOT/'dataset',extra_ledgers=[ROOT/'outputs/adaptive_crop_gate_v1/review/review_events.jsonl']);product_states=product_store.snapshot();product_gt=int(sum(e['status']=='VERIFIED_GT' for e in product_states.values()))
 approved={k:v for k,v in states.items() if v['status']=='APPROVED_CROP'};original=base.set_index('image_id');final=d.set_index('image_id');changed=(final[['crop_x0','crop_y0','crop_x1','crop_y1']]!=original.loc[final.index,['crop_x0','crop_y0','crop_x1','crop_y1']]).any(axis=1)
 rectangular=d.crop_width.ne(d.crop_height);unapproved_rect=[key for key in d.loc[rectangular,'image_id'] if key not in approved]
 if unapproved_rect:raise RuntimeError('Non-square crop without manual approval')
 analysis=[]
 for key,e in approved.items():
  p=e['preview_evaluation'];r=final.loc[key];analysis.append(dict(image_id=key,source_relative_path=r.source_relative_path,split=r.split,observed_preservation_loss=p['observed_loss'],annotation_assisted=p['annotation_assisted'],requires_evaluation_leakage_review=r.get('requires_evaluation_leakage_review',False),decision_basis='ANNOTATION_REFERENCE_RECORDED' if p['annotation_assisted'] else 'NO_REFERENCE_RECORDED_CANNOT_PROVE_NO_EXTERNAL_GT_USE',product_area_recall=p['product']['area_recall'],mask_retention=p['defect_mask']['retention']))
 review=pd.DataFrame(analysis);review.to_csv(O/'manual_review_evaluation_risks.csv',index=False)
 fingerprint=dict(selected_manifest=str(selected),manifest_sha256=file_hash(selected),base_manifest=str(basefile),base_sha256=base_hash,crop_ledger=str(ledger),crop_ledger_sha256=file_hash(ledger),product_gt_ledger_sha256=file_hash(product_store.ledger),annotation_sha256=file_hash(index.annotation_source or ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv'),bbox_sha256=file_hash(ROOT/'outputs/spatial_20261111_v7/defect_bboxes.csv'),classes_sha256=file_hash(ROOT/'outputs/spatial_20261111_v7/classes.json'),selection_reason='Exact coordinate/provenance/version match to latest valid crop approvals; base identity preserved; not mtime',policy_versions=d.policy_version.value_counts().to_dict(),rows=len(d))
 (O/'manifest_fingerprint.json').write_text(json.dumps(fingerprint,ensure_ascii=False,indent=2))
 selection=dict(success=True,candidates=outcomes,selected=str(selected),ledger_records=len(events),latest_cases=len(states),latest_approved=len(approved),pending=sum(e['status']=='PENDING' for e in states.values()),unseen_priority_cases=len(reader.rows)-len(states),reflected_approvals=int(d.crop_review_status.eq('APPROVED_CROP').sum()),changed_coordinates=int(changed.sum()),human_confirmed_original=int(sum(e['crop_xyxy']==[0,0,1024,1024] for e in approved.values())),verified_product_gt=product_gt,rectangular_crops=int(rectangular.sum()),unapproved_rectangular_crops=len(unapproved_rect),observed_loss_review_records=int(review.observed_preservation_loss.sum()),test_annotation_assisted_reviews=int(((review.split=='test')&review.annotation_assisted).sum()),decision_basis_unverified=int((~review.annotation_assisted).sum()),scope='Unapproved/PENDING rows intentionally remain frozen originalC; GT600 is not crop approval',coordinate_changes_performed=0)
 (O/'manifest_selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2));print(json.dumps(selection,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
