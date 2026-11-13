# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Reuse600 approved product BBoxes for GT-assisted crop proposals, never fake crop approval."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np,pandas as pd
from PIL import Image
from mv_analysis.yolo_crop_geometry import square_crop
from full_crop_gt_validation import B,ROOT,sha,savej,measurements

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 dest=B/'gt_reference_crop_candidates.csv'
 if dest.exists():print('Reusing',dest);return
 gt=pd.read_csv(B/'gt_split_manifest.csv');meta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv').set_index('image_path');hashes=json.loads((B/'gt_audit.json').read_text())['ledger_hashes'];assert all(sha(ROOT/p)==h for p,h in hashes.items());rows=[]
 for r in gt.to_dict('records'):
  box=json.loads(r['verified_gt_bbox']);crop=square_crop(box,.1);q=measurements(crop,box);m=meta.loc[r['image_path']];n=kept=None
  if bool(m.has_mask):
   with Image.open(ROOT/'dataset'/m.mask_path) as im:mask=np.asarray(im.convert('L'))>0
   n=int(mask.sum());x0,y0,x1,y1=crop;kept=int(mask[y0:y1,x0:x1].sum())
  retained=kept/n if n else None;maskloss=bool(n and kept<n)
  rows.append(dict(image_id=r['case_id'],image_path=r['image_path'],product_id=r['product_id'],category=r['category'],view=r['view'],split=r['split'],approved_product_bbox=json.dumps(box),proposed_crop_xyxy=json.dumps(crop),margin_each_side=.1,rounding_guard_pixels=2,product_bbox_fully_contained=q['contained_exact'],bbox_area_recall=q['bbox_area_recall'],crop_side=q['side'],geometric_gain=q['geometric_gain'],full_frame=crop==[0,0,1024,1024],mask_status='NOT_PROVIDED' if n is None else 'PROVIDED_EMPTY' if n==0 else 'PROVIDED_POSITIVE',original_mask_pixels=n,kept_mask_pixels=kept,mask_retention=retained,mask_loss=maskloss,automatic_check_status='OBSERVED_LOSS_REVIEW_REQUIRED' if not q['contained_exact'] or maskloss else 'PRODUCT_AND_PROVIDED_MASK_CHECKED' if n else 'PRODUCT_CHECKED_MASK_NA',source='REUSED_HUMAN_VERIFIED_PRODUCT_GT',crop_approval_status='PROPOSAL_NOT_HUMAN_CROP_APPROVAL',annotation_assisted=True,test_evaluation_requires_leakage_review=r['split']=='test'))
 d=pd.DataFrame(rows);d.to_csv(dest,index=False);d[d.automatic_check_status.eq('OBSERVED_LOSS_REVIEW_REQUIRED')].to_csv(B/'gt_reference_crop_failures.csv',index=False)
 summary=dict(approved_product_gt_reused=len(d),product_bbox_contained=int(d.product_bbox_fully_contained.sum()),mask_status_counts=d.mask_status.value_counts().to_dict(),observed_mask_loss=int(d.mask_loss.sum()),status_counts=d.automatic_check_status.value_counts().to_dict(),mean_side=d.crop_side.mean(),mean_geometric_gain=d.geometric_gain.mean(),full_frame_rate=d.full_frame.mean(),new_product_gt_approvals_created=0,new_crop_approvals_created=0,production_metadata_modified=False,source_gt_ledger_unchanged=True,meaning='GT-derived proposals, not out-of-sample automatic object detection; test annotations were used only for separately labeled reference proposal evaluation')
 savej(B/'gt_reference_crop_reuse_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
