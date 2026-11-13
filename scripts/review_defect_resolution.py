# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Representative JPG defect-ROI review; does not measure mask image quality or model accuracy."""
import argparse
import json
import os
import sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mv_analysis.core import read_image,binary_mask,save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--image-run',required=True,type=Path);p.add_argument('--spatial-run',required=True,type=Path);p.add_argument('--study',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
root=Path(json.loads((args.image_run/'run.json').read_text())['config']['root']);policy=json.loads((args.spatial_run/'mask_policy.json').read_text());sample=pd.read_csv(args.study/'mask_threshold_validation'/'threshold_per_mask.csv');sample=sample[sample.threshold==0].drop_duplicates('image_path');results=[]
for i,row in enumerate(sample.to_dict('records')):
 im=read_image(root/row['image_path']);mask=binary_mask(read_image(root/row['mask_path'],True),policy).astype(bool);h,w=mask.shape;gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY);ea=cv2.Canny(gray,100,200)>0
 for size in (512,256):
  recon=cv2.resize(cv2.resize(im,(size,size),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR);err=np.mean((im.astype(np.float32)-recon)**2,axis=2);rb=cv2.cvtColor(recon,cv2.COLOR_BGR2GRAY);eb=cv2.Canny(rb,100,200)>0
  ratio=lambda x,y:float(x/y) if y>1e-10 else None
  results.append(dict(image_path=row['image_path'],mask_path=row['mask_path'],category=row['category'],defect_type=row['defect_type'],view=row['view'],target=size,roi_pixels=int(mask.sum()),roi_rgb_rmse=float(np.sqrt(err[mask].mean())) if mask.any() else None,background_rgb_rmse=float(np.sqrt(err[~mask].mean())) if (~mask).any() else None,roi_edge_recall=ratio((ea&eb&mask).sum(),(ea&mask).sum()),roi_contrast_retention=ratio(rb[mask].std(),gray[mask].std()) if mask.any() else None))
 if (i+1)%50==0:print(f'Defect JPG ROI review {i+1}/{len(sample)}',flush=True)
df=pd.DataFrame(results);df.to_csv(args.output/'defect_jpg_resolution_review.csv',index=False);df.groupby(['category','target'])[['roi_rgb_rmse','background_rgb_rmse','roi_edge_recall','roi_contrast_retention']].mean().to_csv(args.output/'category_roi_loss_summary.csv')
priority=df[(df.target==256)&(df.roi_pixels>0)].sort_values('roi_rgb_rmse',ascending=False);row=priority.iloc[0];im=read_image(root/row.image_path);mask=binary_mask(read_image(root/row.mask_path,True),policy);h,w=mask.shape;recon=cv2.resize(cv2.resize(im,(256,256),interpolation=cv2.INTER_AREA),(w,h));err=np.mean((im.astype(float)-recon)**2,axis=2);inside=np.where(mask>0,cv2.blur(err,(9,9)),-1);y,x=np.unravel_index(np.argmax(inside),inside.shape);x0=min(max(0,x-64),w-128);y0=min(max(0,y-64),h-128)
fig,axes=plt.subplots(1,4,figsize=(15,4))
for ax,size in zip(axes[:3],[1024,512,256]):
 image=im if size==1024 else cv2.resize(cv2.resize(im,(size,size),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
 ax.imshow(cv2.cvtColor(image[y0:y0+128,x0:x0+128],cv2.COLOR_BGR2RGB));ax.set_title(f'JPG {size} reconstruction');ax.axis('off')
axes[3].imshow(mask[y0:y0+128,x0:x0+128],cmap='gray',vmin=0,vmax=1);axes[3].set_title('Annotation: ROI location only');axes[3].axis('off');fig.suptitle(f'{row.category}/{row.defect_type}/{row.view}, crop x={x0}, y={y0}, size=128');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(args.output/'defect_detail_crop_comparison.png',dpi=150);plt.close(fig)
save_json(args.output/'scope.json',dict(sampled_masks=len(sample),rows=len(df),source='same 336 stratified masks as threshold sensitivity study',input='Original JPG; masks only locate ROI',policy=str(args.spatial_run/'mask_policy.json'),limitation='Representative ROI study only, not full-dataset statistics or model performance',example_image=row.image_path,crop=[int(x0),int(y0),128,128]));print('Defect ROI resolution review completed')
