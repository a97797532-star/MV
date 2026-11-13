# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Validate and reuse completed PNG crops; compute only missing 300-image geometry."""
import sys,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mv_analysis.background_brightness import segment,VERSION
cv2.setNumThreads(1)
B=Path('outputs/preprocessing_review_20261112_v2')
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# save: 결과를 지정한 출력 위치에 기록합니다.
# 입력 인수: df, name.
def save(df,name):
 p=B/name
 if p.exists():raise RuntimeError('Preserve existing '+str(p))
 df.to_csv(p,index=False)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 sources=json.loads((B/'input_fingerprints.json').read_text())
 assert all(sha(Path(p))==h for p,h in sources.items())
 cp=[json.loads(v) for v in (B/'mask_crop_checkpoint.jsonl').read_text().splitlines()]
 assert len(cp)==51329 and len({r['mask_path'] for r in cp})==51329 and not any(r['error'] for r in cp)
 assert sha(B/'mask_crop_checkpoint.jsonl')==sha(Path('outputs/preprocessing_review_20261112_v1/mask_crop_checkpoint.jsonl'))
 print('All 51,329 PNG checkpoints valid; no PNG decoding',flush=True)
 sample=pd.read_csv('outputs/background_sample_20261111_v5/regional_brightness_per_image.csv')
 checkpoint=B/'geometry_checkpoint.jsonl';done={}
 if checkpoint.exists():
  for line in checkpoint.read_text().splitlines():
   row=json.loads(line);done[row['image_path']]=row
 with checkpoint.open('a') as stream:
  for i,row in enumerate(sample.to_dict('records'),1):
   if row['image_path'] in done:continue
   im=cv2.imread(str(Path('dataset')/row['image_path']));assert im is not None
   masks,quality=segment(im,grabcut=True);fg=masks['A'];yy,xx=np.where(fg)
   record={k:row[k] for k in ['image_path','category','status','view','product_id']}
   record.update(segmentation_status=quality['segmentation_status'],matches_prior_quality=quality['segmentation_status']==row['segmentation_status'],candidate_native_occupancy=float(fg.mean()),candidate_center_x=float(xx.mean()/1024) if len(xx) else None,candidate_center_y=float(yy.mean()/1024) if len(xx) else None,crops=[])
   for size in [1024,896,768,640]:
    r=dict(crop=size)
    if quality['segmentation_status']=='accepted_heuristic':
     lo=(1024-size)//2;kept=int(fg[lo:lo+size,lo:lo+size].sum())
     r.update(center_x=float(xx.mean()/1024),center_y=float(yy.mean()/1024),native_occupancy=float(fg.mean()),left_margin=int(xx.min()),right_margin=int(1023-xx.max()),top_margin=int(yy.min()),bottom_margin=int(1023-yy.max()),estimated_product_retention=kept/len(xx),crop_occupancy=kept/size**2)
    record['crops'].append(r)
   stream.write(json.dumps(record)+'\n');stream.flush();done[row['image_path']]=record
   if i%50==0:print(f'Product geometry {i}/300 checkpointed',flush=True)
 rows=[]
 for r in done.values():
  for crop in r['crops']:rows.append({k:v for k,v in r.items() if k!='crops'}|crop)
 geom=pd.DataFrame(rows)
 if not (B/'product_geometry_sample.csv').exists():save(geom,'product_geometry_sample.csv')
 if not (B/'product_geometry_summary.csv').exists():
  save(geom.groupby(['category','view','crop']).agg(samples=('image_path','size'),accepted=('estimated_product_retention','count'),retention_mean=('estimated_product_retention','mean'),retention_min=('estimated_product_retention','min'),occupancy_mean=('crop_occupancy','mean')).reset_index(),'product_geometry_summary.csv')
 # Distribution of missingness/selection across all available image-level attributes.
 regional=pd.read_csv('outputs/background_full_20261111_v1/regional_brightness_per_image.csv',low_memory=False)
 regional['quality_group']=np.where(regional.segmentation_status=='accepted_heuristic','accepted','not_accepted')
 for key in ['category','status','view','background_type']:
  table=regional.groupby(['quality_group',key]).size().rename('images').reset_index();table['within_quality_fraction']=table.images/table.groupby('quality_group').images.transform('sum')
  if not (B/f'selection_{key}.csv').exists():save(table,f'selection_{key}.csv')
 reasons=regional[regional.quality_group=='not_accepted'].assign(reason=lambda d:d.segmentation_reason.fillna('unspecified').str.split(';')).explode('reason').groupby('reason').size().rename('images').reset_index().sort_values('images',ascending=False)
 if not (B/'selection_failure_reasons.csv').exists():save(reasons,'selection_failure_reasons.csv')
 # Candidate shape is a diagnostic only, NOT measured product shape for rejected images.
 numeric=['foreground_candidate_fraction','foreground_border_fraction','border_sector_spread','background_confidence','near_background_foreground_fraction','outside_product_edge_fraction']
 if not (B/'selection_candidate_diagnostics.csv').exists():
  result=regional.groupby('quality_group')[numeric].agg(['count','mean','median','std',lambda s:s.quantile(.05),lambda s:s.quantile(.95)]);result.columns=['_'.join(v) for v in result.columns];save(result.reset_index(),'selection_candidate_diagnostics.csv')
 crops=pd.read_csv(B/'mask_crop_per_image.csv');boxes=pd.read_csv(B/'bbox_crop_per_component.csv')
 crops['defect_size']=pd.cut(crops.defect_pixels,[-1,0,16,256,1024,4096,np.inf],labels=['empty','1-16','17-256','257-1024','1025-4096','4097+'])
 if not (B/'mask_crop_by_size.csv').exists():
  save(crops.groupby(['crop','defect_size'],observed=True).agg(masks=('mask_path','size'),removed=('crop_state',lambda s:int((s=='removed').sum())),partial=('crop_state',lambda s:int((s=='partial').sum())),mean_retention=('retention','mean'),median_retention=('retention','median'),kept_pixels=('kept_pixels','sum'),native_pixels=('defect_pixels','sum')).reset_index(),'mask_crop_by_size.csv')
 projected=[]
 for crop,g in crops.groupby('crop'):
  for size in [256,512,1024]:
   pixels=g.kept_pixels*(size/crop)**2
   projected.append(dict(crop=crop,target=size,positive_masks=int((g.defect_pixels>0).sum()),removed=int((g.crop_state=='removed').sum()),equivalent_area_median=float(pixels[g.defect_pixels>0].median()),equivalent_area_p05=float(pixels[g.defect_pixels>0].quantile(.05)),equivalent_area_under1=int(((pixels<1)&(g.defect_pixels>0)).sum()),note='continuous geometric area proxy, not actual resized binary support'))
 if not (B/'mask_crop_resize_area_proxy.csv').exists():save(pd.DataFrame(projected),'mask_crop_resize_area_proxy.csv')
 projected=[]
 for crop,g in boxes.groupby('crop'):
  valid=g[g.intersection_area>0]
  for target in [256,512]:
   col=f'resize{target}_short_side';projected.append(dict(crop=crop,target=target,remaining_boxes=len(valid),removed=len(g)-len(valid),short_side_under2=int((valid[col]<2).sum()),short_side_median=float(valid[col].median()),short_side_p05=float(valid[col].quantile(.05))))
 if not (B/'bbox_crop_resize_risk.csv').exists():save(pd.DataFrame(projected),'bbox_crop_resize_risk.csv')
 checks=dict(input_sources_unchanged=all(sha(Path(p))==h for p,h in sources.items()),checkpoint_unique_masks=len(cp)==51329,
  checkpoint_errors_zero=not any(r['error'] for r in cp),v1_v2_checkpoint_identical=sha(B/'mask_crop_checkpoint.jsonl')==sha(Path('outputs/preprocessing_review_20261112_v1/mask_crop_checkpoint.jsonl')),
  mask_native_identity=bool(crops.query('crop==1024 and defect_pixels>0').retention.eq(1).all()),
  mask_retention_range=bool(crops.retention.dropna().between(0,1).all()),
  mask_crop_monotonic=bool((crops.pivot(index='mask_path',columns='crop',values='kept_pixels').diff(axis=1).iloc[:,1:]>=0).all().all()),
  bbox_native_identity=bool(boxes.query('crop==1024').bbox_retention.eq(1).all()),
  geometry_300_images=geom.image_path.nunique()==300,
  prior_geometry_quality_matches=bool(geom.matches_prior_quality.all()))
 report=dict(success=all(checks.values()),checks=checks,source_sha256=sources,full_resolution_recalculations=0,additional_png_decodes=0,original_jpg_decodes=300,algorithm=VERSION,foreground_gt_validation='UNVERIFIED',recovery='v1/v2 identical mask checkpoint reused; only missing geometry and selection audit added')
 p=B/'complete.json'
 if p.exists():raise RuntimeError('Preserve complete marker')
 p.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
 if not report['success']:raise SystemExit(1)
if __name__=='__main__':main()
