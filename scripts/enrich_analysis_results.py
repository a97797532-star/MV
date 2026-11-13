# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Add distribution summaries and real-image brightness reviews after full analysis."""
import argparse
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import json
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('run',type=Path);args=p.parse_args();out=args.run;config=json.loads((out/'run.json').read_text())['config'];root=Path(config['root'])
bpath=out/'brightness_per_image.csv'
if bpath.exists():
 b=pd.read_csv(bpath);keys=['category','defect_type','view','status','split']
 b.groupby(keys).brightness.quantile([.05,.5,.95]).unstack().rename(columns={.05:'P05',.5:'P50',.95:'P95'}).to_csv(out/'brightness_group_quantiles.csv')
 c=pd.read_csv(out/'brightness_comparison.csv');c['abs_d']=c.cohens_d.abs();top=c.sort_values('abs_d',ascending=False).head(8)
 chosen=[];fig,axes=plt.subplots(max(1,len(top)),2,figsize=(10,max(3,len(top)*3)),squeeze=False)
 for i,row in enumerate(top.itertuples()):
  for j,status in enumerate(['OK','NG']):
   group=b[(b.category==row.category)&(b.view==row.view)&(b.status==status)]
   if status=='NG':group=group[group.defect_type==row.defect_type]
   selected=group.iloc[(group.brightness-group.brightness.median()).abs().argmin()]
   im=cv2.imread(str(root/selected.image_path));axes[i,j].imshow(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));axes[i,j].set_title(f'{row.category}/{row.defect_type}/{row.view} {status}, mean={selected.brightness:.2f}',fontsize=10);axes[i,j].axis('off')
   chosen.append(dict(category=row.category,defect_type=row.defect_type,view=row.view,status=status,image_path=selected.image_path,brightness=selected.brightness,cohens_d=row.cohens_d))
 fig.suptitle('Large brightness difference groups: representative median images');fig.tight_layout(rect=(0,0,1,.985));fig.savefig(out/'brightness_review_images_readable.png',dpi=130);plt.close(fig)
 pd.DataFrame(chosen).to_csv(out/'brightness_review_images.csv',index=False)
 category_order=b.category.unique();fig,ax=plt.subplots(figsize=(14,6))
 data=[group.brightness.to_numpy() for _,group in b.groupby('category',sort=True)];labels=sorted(b.category.unique())
 ax.boxplot(data,tick_labels=labels,showfliers=False);ax.tick_params(axis='x',rotation=90);ax.set(title='Per-category distribution of image mean brightness',ylabel='Mean grayscale intensity [0,255]');fig.tight_layout();fig.savefig(out/'brightness_category_boxplot.png');plt.close(fig)
rpath=out/'per_view_information_loss.csv'
if rpath.exists():
 r=pd.read_csv(rpath);r.groupby(['category','view','target']).ssim.quantile([.05,.5,.95]).unstack().to_csv(out/'resolution_ssim_quantiles.csv')
 r.groupby(['category','target'])[['ssim','edge_recall','local_contrast_retention']].mean().to_csv(out/'resolution_category_means.csv')
print('Enrichment complete for existing brightness/resolution CSVs')
if rpath.exists():
 metrics=['psnr_db','ssim','edge_recall','edge_f1','laplacian_energy','laplacian_retention','gradient_energy','gradient_retention','local_contrast_retention','rgb_rmse','high_frequency_proxy_retention']
 r.groupby(['target','status'])[metrics].agg(['count','mean','std','median','min','max']).to_csv(out/'resolution_global_distribution_summary.csv')
 r.groupby(['target','status'])[metrics].quantile([.05,.5,.95]).unstack().to_csv(out/'resolution_global_quantiles.csv')
 missing=r.groupby('target')[metrics].count();missing=len(r[r.target==1024])-missing;missing.to_csv(out/'resolution_undefined_metric_counts.csv')
 fig,axes=plt.subplots(2,3,figsize=(16,9));display=['ssim','edge_recall','local_contrast_retention','laplacian_retention','gradient_retention','rgb_rmse']
 for ax,metric in zip(axes.ravel(),display):
  arrays=[];labels=[]
  for (size,status),part in r[r.target!=1024].groupby(['target','status']):arrays.append(part[metric].dropna().to_numpy());labels.append(f'{size}/{status}')
  ax.boxplot(arrays,tick_labels=labels,showfliers=False);ax.set(title=metric,ylabel='Gray intensity RMSE' if metric=='rgb_rmse' else 'Dimensionless');ax.tick_params(axis='x',rotation=20)
 fig.suptitle('Full JPG resolution distributions: median, IQR, 1.5 IQR whiskers; fliers hidden');fig.tight_layout();fig.savefig(out/'resolution_metric_distributions.png',dpi=120);plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(16,12))
 for ax,metric in zip(axes,['ssim','edge_recall','local_contrast_retention']):
  data=r[r.target==256].groupby(['category','view'])[metric].mean().unstack();im=ax.imshow(data.to_numpy(),aspect='auto',vmin=0,vmax=1,cmap='viridis');ax.set_title(f'256 reconstruction: mean {metric}');ax.set_xticks(range(len(data.columns)),data.columns);ax.set_yticks(range(len(data.index)),data.index,fontsize=8);fig.colorbar(im,ax=ax,label='Dimensionless mean')
 fig.tight_layout();fig.savefig(out/'resolution_category_heatmaps.png',dpi=120);plt.close(fig)
 (out/'resolution_metric_definitions.json').write_text(json.dumps(dict(resize='INTER_AREA to square target; restore native by INTER_LINEAR',ssim='Gaussian11 sigma1.5, grayscale 0..255, local means/variances',psnr='Whole BGR MSE, identical image saved as capped120dB',edge='Canny100/200, exact same native pixel; image-level edge similarity, not detector recall',laplacian_energy='mean squared OpenCV Laplacian ksize1; proxy not Fourier spectrum',gradient_energy='mean squared Sobel x/y magnitude',local_contrast='mean local grayscale std in Gaussian11 sigma1.5',undefined='Zero reference energy/contrast yields missing ratio; see metric counts',stepwise='512-to-256 compares against the 512 image; direct1024-to256 is a separate comparison'),indent=2))
 print('Full resolution distributions and category heatmaps generated')
if rpath.exists():
 import subprocess,sys
 subprocess.run([sys.executable,str(Path(__file__).with_name('validate_resolution_results.py')),str(out)],check=True)
