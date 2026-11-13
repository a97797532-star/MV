# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""New bounded preprocessing analyses, frozen CSV reuse and checkpointed PNG-only crops."""
import argparse,concurrent.futures as cf,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
from mv_analysis.background_brightness import segment,VERSION
cv2.setNumThreads(1)
BASE=Path('outputs/preprocessing_review_20261112_v2')
RUN=Path('outputs/windows_preserved_20261111_v1')
BG=Path('outputs/background_full_20261111_v1')
SIZES=[1024,896,768,640]

# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()

# mask_crop: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: item.
def mask_crop(item):
 path=item
 try:
  m=cv2.imread(str(Path('dataset')/path),cv2.IMREAD_GRAYSCALE)
  if m is None or m.shape!=(1024,1024):raise ValueError('Unreadable or unexpected dimensions')
  m=m>0;n=int(np.count_nonzero(m));values={}
  for size in SIZES:
   lo=(1024-size)//2;hi=lo+size;inside=int(np.count_nonzero(m[lo:hi,lo:hi]));values[str(size)]=inside
  return dict(mask_path=path,pixels=n,kept=values,error=None)
 except Exception as e:return dict(mask_path=path,error=str(e))

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 BASE.mkdir(parents=True,exist_ok=True)
 complete=BASE/'complete.json'
 if complete.exists():raise SystemExit('Complete output exists; preserve it')
 source=[RUN/'image_metadata_with_split.csv',BG/'regional_brightness_per_image.csv',RUN/'per_view_information_loss.csv',Path('outputs/spatial_20261111_v7/defect_bboxes.csv')]
 before={str(p):sha(p) for p in source};(BASE/'input_fingerprints.json').write_text(json.dumps(before,indent=2))
 # Inventory all requested artifact extensions; inventory is descriptive, not a claim of numerical validity.
 inventory=[]
 for folder in ['reports','outputs','notebook_results_real','docs','mv_analysis','src','notebooks','scripts']:
  if not Path(folder).exists():continue
  for directory,subdirs,files in os.walk(folder):
   subdirs[:]=[v for v in subdirs if v not in {'__pycache__','.git','.venv'}]
   for name in files:
    p=Path(directory)/name
    if p.suffix.lower() in {'.csv','.json','.md','.pdf','.png','.npy','.npz','.log','.txt','.ipynb','.py'}:
     st=p.stat();inventory.append(dict(path=str(p),extension=p.suffix,bytes=st.st_size,mtime_utc=datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat()))
 pd.DataFrame(inventory).to_csv(BASE/'artifact_inventory.csv',index=False)
 meta=pd.read_csv(source[0]);regional=pd.read_csv(source[1]);boxes=pd.read_csv(source[3])
 assert len(meta)==151050 and len(regional)==151050 and len(boxes)==60629
 category=meta.groupby(['category','status']).agg(images=('image_path','size'),declared_products=('product_id','nunique'),with_mask=('has_mask','sum')).reset_index()
 category.to_csv(BASE/'category_status_counts.csv',index=False)
 for name,keys in [('defect_counts',['defect_type','status']),('view_mask_counts',['view','status']),('split_counts',['split','status'])]:
  meta.groupby(keys).agg(images=('image_path','size'),declared_products=('product_id','nunique'),with_mask=('has_mask','sum')).reset_index().to_csv(BASE/(name+'.csv'),index=False)
 completeness=meta.groupby('product_id').agg(images=('image_path','size'),views=('view','nunique'),splits=('split','nunique'),statuses=('status','nunique'))
 completeness.to_csv(BASE/'declared_product_completeness.csv')
 # Same declared capture, across views. Unprovided masks != absence of visible defect.
 visibility=meta[meta.status=='NG'].groupby('product_id').has_mask.agg(['sum','size']).reset_index()
 visibility.groupby('sum').size().rename('ng_declared_products').to_csv(BASE/'provided_view_count_per_ng_product.csv')
 records=[]
 for keys in [['status'],['category','status'],['view','status'],['category','view','status']]:
  g=regional.groupby(keys+['background_type']).size().rename('images').reset_index();g['scope']='/'.join(keys);records.append(g)
 pd.concat(records,ignore_index=True).to_csv(BASE/'background_label_association.csv',index=False)
 pd.crosstab([regional.category,regional.view],regional.background_type).to_csv(BASE/'background_category_view_counts.csv')
 paired=regional[['product_id','view','whole_mean','background_type']].pivot(index='product_id',columns='view',values='whole_mean')
 paired['max_minus_min']=paired.max(axis=1)-paired.min(axis=1)
 paired.to_csv(BASE/'five_view_brightness_paired.csv')
 paired.corr().to_csv(BASE/'five_view_brightness_correlation.csv')
 product_metrics=['whole_mean','background_mean','product_mean','product_pixel_ratio','defect_mean','defect_local_difference']
 regional['product_minus_background']=regional.product_mean-regional.background_mean;product_metrics+=['product_minus_background']
 for label,keys in [('global',['status']),('category',['category','status']),('view',['view','status']),('background',['background_type','status'])]:
  rows=[]
  for key,g in regional.groupby(keys):
   key=key if isinstance(key,tuple) else (key,)
   for metric in product_metrics:
    s=g[metric].dropna();rows.append(dict(zip(keys,key))|dict(metric=metric,total_images=len(g),valid=len(s),mean=s.mean(),std=s.std(),median=s.median(),p05=s.quantile(.05),p95=s.quantile(.95),minimum=s.min(),maximum=s.max()))
  pd.DataFrame(rows).to_csv(BASE/f'regional_{label}_statistics.csv',index=False)
 pd.crosstab(regional.category,regional.segmentation_status).to_csv(BASE/'segmentation_category_coverage.csv')
 # Existing per-image percentiles are retained as per-image summaries, not pooled pixels.
 percentile_columns=[c for c in regional if c.endswith(('_p05','_p50','_p95','_std','_median'))]
 regional.groupby(['category','view','status'])[percentile_columns].agg(['count','mean','median']).to_csv(BASE/'regional_per_image_percentile_summary.csv')
 comparison=pd.read_csv(BG/'brightness_interpretation_changes.csv')
 valid=comparison.dropna(subset=['product_difference','whole_paired_difference'])
 regional_summary=dict(images=len(regional),segmentation_counts=regional.segmentation_status.value_counts().to_dict(),
  background_counts=regional.background_type.value_counts().to_dict(),comparison_groups=len(comparison),valid_product_comparisons=len(valid),
  paired_abs_difference_reduced=int((valid.product_difference.abs()<valid.whole_paired_difference.abs()).sum()),
  paired_sign_changes=int(((valid.product_difference*valid.whole_paired_difference)<0).sum()),
  zero_accepted_categories=sorted(set(regional.category)-set(regional.loc[regional.segmentation_status=='accepted_heuristic','category'])),
  product_gt_available=False)
 (BASE/'regional_findings.json').write_text(json.dumps(regional_summary,indent=2))
 print('Metadata and background CSV reaggregation complete',flush=True)
 # Checkpointed exact mask cropping.
 checkpoint=BASE/'mask_crop_checkpoint.jsonl';done={}
 if checkpoint.exists():
  for line in checkpoint.read_text().splitlines():
   record=json.loads(line);done[record['mask_path']]=record
 masks=meta.loc[meta.has_mask,'mask_path'].tolist()
 todo=[p for p in masks if p not in done]
 with checkpoint.open('a') as stream,cf.ThreadPoolExecutor(max_workers=4) as pool:
  for i,record in enumerate(pool.map(mask_crop,todo),1):
   stream.write(json.dumps(record)+'\n');done[record['mask_path']]=record
   if i%1000==0:stream.flush();print(f'PNG CenterCrop {len(done):,}/{len(masks):,}',flush=True)
 errors=[r for r in done.values() if r['error']]
 rows=[]
 for path in masks:
  r=done[path]
  if r['error']:continue
  for size in SIZES:
   kept=r['kept'][str(size)];n=r['pixels'];state='provided_empty' if not n else 'removed' if not kept else 'partial' if kept<n else 'preserved'
   rows.append(dict(mask_path=path,crop=size,defect_pixels=n,kept_pixels=kept,retention=kept/n if n else np.nan,crop_state=state))
 crops=pd.DataFrame(rows).merge(meta.loc[meta.has_mask,['mask_path','image_path','category','view','defect_type','split','product_id']],on='mask_path',validate='many_to_one')
 crops.to_csv(BASE/'mask_crop_per_image.csv',index=False)
 for name,keys in [('overall',['crop']),('category',['category','crop']),('view',['view','crop']),('defect',['defect_type','crop'])]:
  result=[]
  for key,g in crops.groupby(keys):
   key=key if isinstance(key,tuple) else (key,);counts=g.crop_state.value_counts()
   result.append(dict(zip(keys,key))|dict(provided_masks=len(g),positive_masks=int((g.defect_pixels>0).sum()),empty_masks=int(counts.get('provided_empty',0)),removed=int(counts.get('removed',0)),partial=int(counts.get('partial',0)),preserved=int(counts.get('preserved',0)),pixel_weighted_retention=g.kept_pixels.sum()/g.defect_pixels.sum(),image_mean_retention=g.retention.mean(),image_median_retention=g.retention.median(),p05=g.retention.quantile(.05),minimum=g.retention.min()))
  pd.DataFrame(result).to_csv(BASE/f'mask_crop_{name}.csv',index=False)
 # Original XYXY stays authoritative. Adapters clip and resize as the last step.
 bb=[]
 for size in SIZES:
  lo=(1024-size)//2;hi=lo+size;g=boxes.copy();g['crop']=size
  xx0=np.maximum(g.x0,lo);yy0=np.maximum(g.y0,lo);xx1=np.minimum(g.x1,hi);yy1=np.minimum(g.y1,hi)
  width=np.maximum(0,xx1-xx0);height=np.maximum(0,yy1-yy0);g['intersection_area']=width*height;g['bbox_retention']=g.intersection_area/g.bbox_area
  g['crop_state']=np.where(g.intersection_area==0,'removed',np.where(g.bbox_retention<1,'partial','preserved'))
  for name,array in [('cropped_x0',np.clip(xx0-lo,0,size)),('cropped_y0',np.clip(yy0-lo,0,size)),('cropped_x1',np.clip(xx1-lo,0,size)),('cropped_y1',np.clip(yy1-lo,0,size))]:g[name]=array
  g['resize512_short_side']=np.minimum(width,height)*512/size;g['resize256_short_side']=np.minimum(width,height)*256/size
  bb.append(g)
 bbc=pd.concat(bb,ignore_index=True);bbc.to_csv(BASE/'bbox_crop_per_component.csv',index=False)
 bbc.groupby(['crop','crop_state']).size().rename('components').to_csv(BASE/'bbox_crop_counts.csv')
 bbc.groupby(['category','view','crop','crop_state']).size().rename('components').to_csv(BASE/'bbox_crop_category_view.csv')
 boxes['aspect_ratio']=(boxes.x1-boxes.x0)/(boxes.y1-boxes.y0)
 boxes['center_x']=(boxes.x0+boxes.x1)/2/1024;boxes['center_y']=(boxes.y0+boxes.y1)/2/1024
 boxes['edge_band_128']=((boxes.x0<128)|(boxes.y0<128)|(boxes.x1>896)|(boxes.y1>896))
 for name,keys in [('category',['category']),('defect',['defect_type']),('view',['view'])]:
  boxes.groupby(keys).agg(boxes=('image_path','size'),images=('image_path','nunique'),area_median=('bbox_area','median'),area_p05=('bbox_area',lambda s:s.quantile(.05)),area_p95=('bbox_area',lambda s:s.quantile(.95)),aspect_median=('aspect_ratio','median'),edge_band_count=('edge_band_128','sum')).to_csv(BASE/f'bbox_{name}_distribution.csv')
 # Only 300 pre-existing representative JPGs; foreground positions are heuristic.
 sample=pd.read_csv('outputs/background_sample_20261111_v5/regional_brightness_per_image.csv')
 geometry=[]
 for i,row in enumerate(sample.to_dict('records'),1):
  image=cv2.imread(str(Path('dataset')/row['image_path']));masks,quality=segment(image,grabcut=True)
  fg=masks['A'];accepted=quality['segmentation_status']=='accepted_heuristic'
  for size in SIZES:
   r={k:row[k] for k in ['image_path','category','status','view','product_id']};r.update(crop=size,segmentation_status=quality['segmentation_status'],matches_prior_quality=quality['segmentation_status']==row['segmentation_status'])
   if accepted:
    yy,xx=np.where(fg);lo=(1024-size)//2;kept=int(fg[lo:lo+size,lo:lo+size].sum())
    r.update(center_x=float(xx.mean()/1024),center_y=float(yy.mean()/1024),native_occupancy=float(fg.mean()),left_margin=int(xx.min()),right_margin=int(1023-xx.max()),top_margin=int(yy.min()),bottom_margin=int(1023-yy.max()),estimated_product_retention=kept/len(xx),crop_occupancy=kept/size**2)
   geometry.append(r)
  if i%50==0:print(f'Product geometry representative JPG {i}/300',flush=True)
 geom=pd.DataFrame(geometry);geom.to_csv(BASE/'product_geometry_sample.csv',index=False)
 geom.groupby(['category','view','crop']).agg(samples=('image_path','size'),accepted=('estimated_product_retention','count'),retention_mean=('estimated_product_retention','mean'),retention_min=('estimated_product_retention','min'),occupancy_mean=('crop_occupancy','mean')).to_csv(BASE/'product_geometry_summary.csv')
 after={str(p):sha(p) for p in source}
 checks=dict(source_csv_hashes_unchanged=before==after,mask_count=len(done)==51329,mask_errors=len(errors)==0,
  mask_native_identity=bool(crops[crops.crop==1024].query('defect_pixels>0').retention.eq(1).all()),
  mask_monotonic=bool((crops.groupby('mask_path').kept_pixels.apply(lambda x:bool(np.all(np.diff(x)<=0)))).all()),
  bbox_native_identity=bool(bbc[bbc.crop==1024].bbox_retention.eq(1).all()),
  product_sample_scope=geom.image_path.nunique()==300,declared_groups_5views=bool((completeness.views==5).all()),declared_split_no_leakage=bool((completeness.splits==1).all()))
 report=dict(success=all(checks.values()),checks=checks,mask_errors=errors,source_sha256_before=before,source_sha256_after=after,full_resolution_recalculations=0,original_jpg_decodes=300,png_decodes=len(todo),foreground_gt_validation='UNVERIFIED',algorithm=VERSION,counts=dict(images=len(meta),ok=int((meta.status=='OK').sum()),ng=int((meta.status=='NG').sum()),masks=int(meta.has_mask.sum()),categories=meta.category.nunique(),declared_products=meta.product_id.nunique()),completed=datetime.now(timezone.utc).isoformat())
 complete.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
 if not report['success']:raise SystemExit(1)
if __name__=='__main__':main()
