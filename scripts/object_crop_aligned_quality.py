# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Evaluate only frozen policies on a bounded aligned image sample, no retuning."""
import json,sys,concurrent.futures as cf
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
from mv_analysis.core import prepare_image_reference,information_loss
B=Path('outputs/object_aware_crop_v1');cv2.setNumThreads(1)
# work: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: args.
def work(args):
 row,entries=args;cv2.setNumThreads(1);image=cv2.imread(str(Path('dataset')/row['image_path']));mask=cv2.imread(str(Path('dataset')/row['mask_path']),0)>0 if row['has_mask'] else None;out=[]
 for entry in entries:
  if not entry['available']:continue
  x0,y0,x1,y1=entry['crop'];im=image[y0:y1,x0:x1];ref=prepare_image_reference(im)
  for target in [256,512]:
   metrics=information_loss(im,target,ref);r={k:row[k] for k in ['image_path','cohort','category','view','status']};r.update(method=entry['method'],target=target,edge_recall=metrics['edge_recall'],local_contrast_retention=metrics['local_contrast_retention'],rgb_rmse=metrics['rgb_rmse'],defect_local_context_status='UNVERIFIED_PRODUCT_BOUNDARY')
   if mask is not None:
    m=mask[y0:y1,x0:x1];ring=(cv2.dilate(m.astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(25,25)))>0)&~m
    if m.sum()>0 and ring.sum()>=20:
     gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY);recon=cv2.resize(cv2.resize(im,(target,target),interpolation=cv2.INTER_AREA),(im.shape[1],im.shape[0]),interpolation=cv2.INTER_LINEAR);g=cv2.cvtColor(recon,cv2.COLOR_BGR2GRAY)
     native=float(gray[m].mean()-gray[ring].mean());r.update(kept_defect_pixels=int(m.sum()),local_ring_pixels=int(ring.sum()),native_defect_minus_ring=native,restored_defect_minus_ring=float(g[m].mean()-g[ring].mean()))
   out.append(r)
 return dict(image_path=row['image_path'],metrics=out)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=B/'checkpoints/aligned_quality.jsonl';done={}
 if p.exists():
  for line in p.read_text().splitlines():
   r=json.loads(line);done[r['image_path']]=r
 sample=pd.read_csv(B/'sample_manifest.csv');selected=[]
 for cohort in ['dev_general','independent_validation_products']:
  for i,(_,g) in enumerate(sample[sample.cohort==cohort].groupby(['category','view'])):selected.append(g[g.status==('NG' if i%2 else 'OK')].iloc[0].to_dict())
 frozen=json.loads((B/'frozen_policy.json').read_text())['methods'];lookup={}
 for stage in ['development','holdout']:
  for line in (B/f'checkpoints/evaluation_{stage}.jsonl').read_text().splitlines():
   r=json.loads(line);lookup[r['image_path']]=[v for v in r['results'] if v['method'] in frozen+['full','center896']]
 todo=[(r,lookup[r['image_path']]) for r in selected if r['image_path'] not in done]
 with p.open('a') as f,cf.ProcessPoolExecutor(max_workers=3) as pool:
  for i,r in enumerate(pool.map(work,todo),1):
   f.write(json.dumps(r)+'\n');f.flush();done[r['image_path']]=r
   if i%25==0:print(f'Aligned same-region quality {i}/{len(todo)}',flush=True)
 rows=[]
 for r in done.values():rows+=r['metrics']
 pd.DataFrame(rows).to_csv(B/'metrics/aligned_image_quality.csv',index=False);print('Aligned sample300 complete',flush=True)
if __name__=='__main__':main()
