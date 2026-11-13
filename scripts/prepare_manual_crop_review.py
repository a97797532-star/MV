# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Create a separate human crop review queue; never change the production coordinates."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd
from full_crop_gt_validation import B,ROOT,sha,savej,cp

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=B/'manual_crop_review.csv'
 if p.exists():print('Reuse',p);return
 base=pd.read_parquet(B/'final_crop_manifest.parquet').set_index('image_id');allmeta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv').set_index('image_path');features=cp(ROOT/'outputs/adaptive_crop_gate_v1/checkpoints/features.jsonl');reasons={}
 # add: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: ids, reason, priority.
 def add(ids,reason,priority):
  for key in ids:
   v=reasons.setdefault(key,dict(reasons=[],priority=priority));v['priority']=min(v['priority'],priority)
   if reason not in v['reasons']:v['reasons'].append(reason)
 high=pd.read_csv(B/'high_risk_images.csv');add(high.image_id,'IMAGE_ONLY_GATE_RISK',1)
 gt=pd.read_csv(B/'metrics/verified_gt_policy_evaluation.csv');lookup=base.reset_index().set_index('source_relative_path').image_id.to_dict()
 for method,name in [('grabcut90_m10','REVIEWED_PRODUCT_BBOX_LOSS_IN_A'),('center896','REVIEWED_PRODUCT_BBOX_LOSS_IN_CENTER896'),('previous_image_gate','REVIEWED_PRODUCT_BBOX_LOSS_IN_OLD_GATE')]:add([lookup[v] for v in gt[(gt.method==method)&~gt.contained_exact].image_path],name,0)
 adapter=pd.read_csv(B/'metrics/adapter_second_crop_risk_images.csv');add([lookup[v] for v in adapter.image_path],'OPTIONAL_SECOND_CENTER_CROP_MASK_LOSS_NOT_CURRENT_FULL_FRAME_LOSS',2)
 sample=pd.read_csv(B/'manual_review_candidates.csv');add(sample.image_id,'PRIORITY_SAMPLE_FROM_PREVIOUS_AUDIT',3)
 gtbox=pd.read_csv(B/'gt_split_manifest.csv').set_index('image_path').verified_gt_bbox.to_dict();rows=[];basehash=sha(B/'preprocessing_metadata.csv')
 for imageid,why in reasons.items():
  r=base.loc[imageid];m=allmeta.loc[r.source_relative_path];f=features.get(r.source_relative_path,{}).get('features',{});current=[int(r[k]) for k in ['crop_x0','crop_y0','crop_x1','crop_y1']];proposal=f.get('proposed_crop') or current
  rows.append(dict(case_id=imageid,image_id=imageid,image_path=r.source_relative_path,original_path=r.original_path,product_id=r.product_id,category=r.category,view=r.view,split=r.split,status='CROP_REVIEW_REQUIRED',review_priority=why['priority'],review_reasons=';'.join(why['reasons']),current_policy=r.selected_policy,current_crop=json.dumps(current),proposal_bbox=json.dumps(proposal),proposal_method='CACHED_IMAGE_ONLY_GRABCUT90_M10' if f.get('proposed_crop') else 'NO_AUTO_PROPOSAL_FULL_FRAME',reference_product_bbox=gtbox.get(r.source_relative_path,''),evaluation_mask_path=m.mask_path if bool(m.has_mask) else '',mask_available=bool(m.has_mask),source_fingerprint=r.source_fingerprint,base_policy_version=r.policy_version,base_manifest_sha256=basehash))
 out=pd.DataFrame(rows).sort_values(['review_priority','category','product_id','view']).reset_index(drop=True);out.to_csv(p,index=False)
 savej(B/'manual_crop_review_queue.json',dict(images=len(out),declared_products=out.product_id.nunique(),categories=out.category.nunique(),source='Union of cached image risks, reviewed candidate product losses, optional adapter second-Crop mask loss and stratified uncomputed samples. This is a priority queue, not all151050 verified unsafe images.',production_coordinates_changed=0,human_crop_approvals=0,product_gt_ledger_changed=False,reason_counts={name:int(out.review_reasons.str.contains(name,regex=False).sum()) for name in ['IMAGE_ONLY_GATE_RISK','REVIEWED_PRODUCT_BBOX_LOSS_IN_A','REVIEWED_PRODUCT_BBOX_LOSS_IN_CENTER896','REVIEWED_PRODUCT_BBOX_LOSS_IN_OLD_GATE','OPTIONAL_SECOND_CENTER_CROP_MASK_LOSS_NOT_CURRENT_FULL_FRAME_LOSS','PRIORITY_SAMPLE_FROM_PREVIOUS_AUDIT']}));print('Human crop queue',len(out),'rows',p)
if __name__=='__main__':main()
