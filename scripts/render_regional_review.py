"""Render full-result failure/priority examples without treating automatic masks as ground truth."""
import argparse,json,os,sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mv_analysis.core import read_image,save_json
from mv_analysis.background_brightness import segment
from mv_analysis.regional_cli import overlay,render_review
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False);run=json.loads((a.run/'regional_run.json').read_text());root=Path(run['config']['root']);df=pd.read_csv(a.run/'regional_brightness_per_image.csv',keep_default_na=True);policy=json.loads((Path(run['config']['source'])/'mask_policy.json').read_text());render_review(root,a.output,df,policy)
selected=[]
for category in ['phone_battery','sim_card_set','plastic_plug','toothbrush','toy']:
 part=df[(df.category==category)&(df.status=='NG')]
 accepted=part[part.segmentation_status=='accepted_heuristic'].assign(whole_product_gap=lambda x:(x.whole_mean-x.product_mean).abs()).sort_values('whole_product_gap',ascending=False)
 uncertain=part[(part.segmentation_status!='accepted_heuristic')&(part.whole_mean>0)].sort_values('background_confidence')
 for label,candidates in [('accepted_extreme_gap',accepted),('uncertain_low_border_confidence',uncertain)]:
  if len(candidates):selected.append(dict(candidates.iloc[0],review_selection=label))
for start in range(0,len(selected),5):
 rows=selected[start:start+5];fig,axes=plt.subplots(len(rows),4,figsize=(14,3.3*len(rows)),squeeze=False)
 for axesrow,row in zip(axes,rows):
  image=read_image(root/row['image_path']);masks,quality=segment(image,True);axesrow[0].imshow(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));product=row['product_mean'];axesrow[0].set_title(f'{row["category"]}/{row["view"]}: {row["segmentation_status"]}\nwhole={row["whole_mean"]:.1f}, product={product:.1f}' if pd.notna(product) else f'{row["category"]}/{row["view"]}: uncertain\nwhole={row["whole_mean"]:.1f}, product=missing',fontsize=9)
  for ax,method in zip(axesrow[1:],['A','B','C']):
   if method in masks:ax.imshow(overlay(image,masks[method]))
   ax.set_title(f'Method {method}: candidate mask')
  for ax in axesrow:ax.axis('off')
 fig.tight_layout();fig.savefig(a.output/f'priority_foreground_examples_{start//5+1:02}.png',dpi=110);plt.close(fig)
pd.DataFrame(selected).to_csv(a.output/'priority_review_manifest.csv',index=False);save_json(a.output/'scope.json',dict(source_run=str(a.run),full_images=len(df),category_representatives=30,priority_images=len(selected),selection='Lowest-confidence per category plus accepted extreme whole-product gap/uncertain cases from five priority categories',ground_truth_available=False,visual_review_completed=False));print('Review figures generated; inspect before recording visual review complete')
