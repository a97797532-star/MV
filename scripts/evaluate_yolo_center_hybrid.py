# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Post-hoc hybrid: use cached YOLO crops, no further YOLO inference."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd,cv2
from mv_analysis.yolo_crop_geometry import transform_boxes
from mv_analysis.yolo_center_hybrid import anchor_union_square
B=Path('outputs/yolo11_dynamic_crop_v1');cv2.setNumThreads(1)
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 out=B/'hybrid_extension'
 if out.exists():raise SystemExit('Preserve existing hybrid extension')
 out.mkdir();before=sha(B/'inference_checkpoint.jsonl');records=[json.loads(v) for v in (B/'evaluation_checkpoint.jsonl').read_text().splitlines()]
 rows=[];coords=[];bb=pd.read_csv('outputs/spatial_20261111_v7/defect_bboxes.csv');lookup={p:g for p,g in bb.groupby('image_path')}
 manifests=pd.read_csv(B/'sample_manifest.csv').set_index('image_path')
 for i,r in enumerate(records,1):
  base=next(x for x in r['metrics'] if x['method']=='confidence_m30');candidate=base['crop'];anchor=[64,64,960,960]
  union=anchor_union_square(anchor,candidate);m=None
  if r['has_mask']:m=cv2.imread(str(Path('dataset')/manifests.loc[r['image_path'],'mask_path']),0)>0
  xyxy=lookup[r['image_path']][['x0','y0','x1','y1']].to_numpy() if r['image_path'] in lookup else np.empty((0,4))
  for name,crop in [('hybrid896',union),('hybrid896_fullfallback',[0,0,1024,1024] if candidate is None else union)]:
   x0,y0,x1,y1=crop;assert x0<=64 and y0<=64 and x1>=960 and y1>=960
   row={k:r[k] for k in ['image_path','case_id','category','cohort','view','status','has_mask']};row.update(method=name,available=True,native_side=x1-x0,frame_fraction=(x1-x0)**2/1024**2,no_yolo_candidate=candidate is None)
   coords.append({k:r[k] for k in ['image_path','case_id']}|dict(method=name,crop=crop,anchor=anchor,yolo_candidate=candidate,model_calls=0,posthoc=True))
   transformed,keep=transform_boxes(xyxy,crop);row.update(original_boxes=len(xyxy),removed_boxes=int((~keep).sum()))
   if m is not None:
    total=int(m.sum());kept=int(m[y0:y1,x0:x1].sum());row.update(original_pixels=total,kept_pixels=kept,pixel_retention=kept/total if total else None,crop_state='provided_empty' if not total else 'removed' if not kept else 'partial' if kept<total else 'preserved')
    centerkept=int(m[64:960,64:960].sum());assert kept>=centerkept
    for t in [256,512]:
     resized=cv2.resize(m[y0:y1,x0:x1].astype(np.uint8),(t,t),interpolation=cv2.INTER_NEAREST);row[f't{t}_positive_pixels']=int(resized.sum());row[f't{t}_components']=cv2.connectedComponents(resized,8)[0]-1
   rows.append(row)
  if i%200==0:print(f'Hybrid coordinates/masks {i}/{len(records)}; no YOLO calls',flush=True)
 d=pd.DataFrame(rows);d.to_csv(out/'per_image_metrics.csv',index=False);(out/'crop_coordinates.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in coords))
 result=[]
 for (cohort,method),g in d.groupby(['cohort','method']):
  pos=g[g.original_pixels>0];result.append(dict(cohort=cohort,method=method,images=len(g),positive_masks=len(pos),pixel_weighted_retention=pos.kept_pixels.sum()/pos.original_pixels.sum(),removed=int((pos.crop_state=='removed').sum()),partial=int((pos.crop_state=='partial').sum()),preserved=int((pos.crop_state=='preserved').sum()),mean_native_side=g.native_side.mean(),full_frame_fraction=float((g.native_side==1024).mean()),t256_mask_pixels_median=pos.t256_positive_pixels.median(),t512_mask_pixels_median=pos.t512_positive_pixels.median()))
 summary=pd.DataFrame(result);summary.to_csv(out/'summary.csv',index=False)
 validation=dict(success=sha(B/'inference_checkpoint.jsonl')==before,additional_yolo_calls=0,images=1350,methods=2,posthoc=True,guarantee='Contains Center896 AND available A30 candidate in native coordinates; no guarantee for pixels outside both',product_gt='UNVERIFIED',warning='Follow-up proposed after seeing initial evaluation; requires independent holdout validation',inference_checkpoint_sha256=before)
 (out/'validation.json').write_text(json.dumps(validation,indent=2));print(summary.to_string(index=False));assert validation['success']
if __name__=='__main__':main()
