# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Aggregate frozen OpenCV crop experiment, visualize, and write INTERNAL research report."""
import os,sys,json,hashlib,re
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib');sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path('outputs/object_aware_crop_v1');M=B/'metrics';F=B/'figures';P=Path('reports')
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# j: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def j(p):return json.loads(Path(p).read_text())
# savej: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def savej(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)))
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: d.
def table(d):
 # val: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: x.
 def val(x):return 'NA' if pd.isna(x) else f'{x:.6g}' if isinstance(x,(float,np.floating)) else str(x).replace('|','/')
 return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(val(v) for v in r)+' |' for r in d.itertuples(index=False,name=None)])
# link: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def link(p):return f'[{Path(p).name}](../{p})'
# summarize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: d, keys.
def summarize(d,keys):
 rows=[]
 for key,g in d.groupby(keys,dropna=False):
  key=key if isinstance(key,tuple) else (key,);positive=g[g.original_pixels>0];p=positive[positive.available];rows.append(dict(zip(keys,key))|dict(images=len(g),available=int(g.available.sum()),candidate_rate=g.available.mean(),candidate_failures=int((~g.available).sum()),quality_pass_rate=g.quality.mean(),fallback_rate=g.fallback.mean(),full_frame_rate=g.full_frame.mean(),positive_masks=len(positive),available_positive_masks=len(p),retention=p.kept_pixels.sum()/p.original_pixels.sum() if len(p) else np.nan,removed=int((p.mask_state=='removed').sum()),partial=int((p.mask_state=='partial').sum()),preserved=int((p.mask_state=='preserved').sum()),image_mean_retention=p.retention.mean(),image_median_retention=p.retention.median(),p05_retention=p.retention.quantile(.05),side_mean=g.side.mean(),side_median=g.side.median(),side_p05=g.side.quantile(.05),side_p95=g.side.quantile(.95),linear_gain=g.magnification.mean()))
 return pd.DataFrame(rows)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if (P/'OBJECT_AWARE_CROP_COMPARISON_REPORT.md').exists():raise SystemExit('Preserve previous report; choose new version')
 cfg=j(B/'config.json');frozen=j(B/'frozen_policy.json');primary=frozen['methods'][0];sample=pd.read_csv(B/'sample_manifest.csv');dev=pd.read_csv(M/'per_image_development.csv',low_memory=False);hold=pd.read_csv(M/'per_image_holdout.csv',low_memory=False);d=pd.concat([dev,hold],ignore_index=True)
 s=summarize(d,['cohort','method']);s.to_csv(M/'all_method_summary.csv',index=False)
 for name,key in [('category','category'),('view','view'),('background','background_type'),('small_mask','small_mask'),('outer_mask','outer_mask')]:summarize(d,['cohort',key,'method']).to_csv(M/f'summary_by_{name}.csv',index=False)
 resize=[]
 for (cohort,method),g in d.groupby(['cohort','method']):
  p=g[(g.original_pixels>0)&g.available]
  for t in [224,256,392,512,640]:
   col=f't{t}_positive_pixels'
   if col not in p or not p[col].notna().any():continue
   q=p[p[col].notna()];resize.append(dict(cohort=cohort,method=method,target=t,positive_masks=len(q),median_output_pixels=q[col].median(),p05_output_pixels=q[col].quantile(.05),zero_support_images=int(q[col].eq(0).sum()),source_id_survival=q[f't{t}_source_ids'].sum()/q.source_components.sum() if q.source_components.sum() else np.nan,small_id_survival=q[f't{t}_small_ids'].sum()/q.small_source_components.sum() if q.small_source_components.sum() else np.nan,output_components=int(q[f't{t}_components'].sum())))
 resize=pd.DataFrame(resize);resize.to_csv(M/'actual_resize_summary.csv',index=False)
 # Per-declared-product properties retain annotation missingness across five views.
 products=[]
 for (cohort,method,pid),g in d.groupby(['cohort','method','product_id']):
  positive=g[g.original_pixels>0];products.append(dict(cohort=cohort,method=method,product_id=pid,views=len(g),any_no_candidate=not g.available.all(),any_fallback=bool(g.fallback.any()),mixed_fallback=0<int(g.fallback.sum())<5,all_five_quality_pass=bool(g.quality.all()),crop_side_range=g.side.max()-g.side.min(),provided_mask_views=int(g.has_mask.sum()),positive_mask_views=len(positive),all_observed_defect_views_preserved=bool((positive.mask_state=='preserved').all()) if len(positive) else None))
 product=pd.DataFrame(products);product.to_csv(M/'five_view_product_metrics.csv',index=False)
 ps=product.groupby(['cohort','method']).agg(products=('product_id','size'),any_no_candidate_rate=('any_no_candidate','mean'),any_fallback_rate=('any_fallback','mean'),mixed_fallback_rate=('mixed_fallback','mean'),all_five_quality_pass_rate=('all_five_quality_pass','mean'),mean_side_range=('crop_side_range','mean'),observed_positive_products=('all_observed_defect_views_preserved','count'),all_observed_defects_preserved=('all_observed_defect_views_preserved','mean')).reset_index();ps.to_csv(M/'five_view_product_summary.csv',index=False)
 cp={r['image_path']:r for r in map(json.loads,(B/'checkpoints/proposals.jsonl').read_text().splitlines())};diag=[]
 lookup=sample.set_index('image_path')
 for path,r in cp.items():
  for name,v in r['proposals'].items():
   if name.startswith('_'):continue
   diag.append(dict(image_path=path,cohort=lookup.loc[path,'cohort'],category=lookup.loc[path,'category'],view=lookup.loc[path,'view'],method=name,status=v['status'],quality=v.get('quality',False),reason=v.get('reason',''),last_iteration_change=v.get('last_iteration_change_fraction'),elapsed_ms=v.get('elapsed_ms'),total_pipeline_ms=r['proposals'].get('_total_ms')))
 diag=pd.DataFrame(diag);diag.to_csv(M/'proposal_diagnostics.csv',index=False)
 ledger=B/'review/human_approved_gt.jsonl';gt={}
 if ledger.exists():
  for line in ledger.read_text().splitlines():
   r=json.loads(line)
   if r.get('status')=='VERIFIED_GT' and r.get('human_ack') is True and r.get('reviewer'):gt[r['image_path']]=r
 # BBox-only GT measures box intersection, not actual foreground pixel occupancy.
 gt_rows=[]
 from mv_analysis.object_aware_crop import box_iou
 for r in d[d.image_path.isin(gt)].to_dict('records'):
  if not r['available']:continue
  q=gt[r['image_path']]['bbox'];a=json.loads(r['crop']);inter=max(0,min(a[2],q[2])-max(a[0],q[0]))*max(0,min(a[3],q[3])-max(a[1],q[1]));area=(q[2]-q[0])*(q[3]-q[1]);gt_rows.append(dict(image_path=r['image_path'],method=r['method'],cohort=r['cohort'],box_area_recall=inter/area,gt_box_crop_occupancy=inter/((a[2]-a[0])*(a[3]-a[1])),gt_box_fully_contained=inter==area,crop_box_iou=box_iou(a,q),note='BBox area proxy, not pixel foreground occupancy'))
 pd.DataFrame(gt_rows,columns=['image_path','method','cohort','box_area_recall','gt_box_crop_occupancy','gt_box_fully_contained','crop_box_iou','note']).to_csv(M/'human_product_bbox_metrics.csv',index=False)
 savej(B/'review/gt_snapshot_status.json',dict(proposals=600,verified_gt_images=len(gt),product_metrics='UNVERIFIED' if not gt else 'VERIFIED only reviewed boxes; foreground pixel occupancy still UNVERIFIED'))
 # Pareto only complete-output methods on identical positive-mask image sets.
 dg=s[s.cohort=='dev_general'].copy();complete=dg[dg.candidate_rate==1].copy();front=[]
 for i,r in complete.iterrows():
  dominated=((complete.retention>=r.retention)&(complete.linear_gain>=r.linear_gain)&((complete.retention>r.retention)|(complete.linear_gain>r.linear_gain))).any();front.append(not dominated)
 complete['pareto_proxy']=front;complete.to_csv(M/'development_pareto.csv',index=False)
 main_methods=['full','center896','center768','center640','border_lab_m10','border_rgb_m10','border_hsv_m10','background_difference_m10','contour_otsu_m10','contour_adaptive_m10','contour_canny_m10','contour_closing_m10','grabcut90_m10','grabcut80_m10','grabcut_bbox_m10','adaptive_center_m10','adaptive_shift_m10','prior_category','prior_category_view','hybrid_m10_center896','hybrid_m10_full','hybrid_m10_trainprior',primary,'cached_yolo_A30_fullfb','cached_yolo_center_union_fullfb'];main_methods=list(dict.fromkeys(main_methods));primary_dev=dg[dg.method==primary].iloc[0];hh=s[s.cohort=='independent_validation_products'];primary_hold=hh[hh.method==primary].iloc[0]
 figures=[]
 # save: 결과를 지정한 출력 위치에 기록합니다.
 # 입력 인수: fig, name, caption.
 def save(fig,name,caption):
  fig.tight_layout();dest=F/(name+'.png');fig.savefig(dest,dpi=145,bbox_inches='tight');plt.close(fig);figures.append(dict(path=str(dest),name=name,caption=caption))
 chart=dg[dg.method.isin(main_methods)]
 fig,axes=plt.subplots(2,1,figsize=(15,10));axes[0].bar(chart.method,chart.retention);axes[0].set(ylabel='Conditional pixel weighted retention (ratio)',ylim=(0,1.02));axes[1].bar(chart.method,chart.candidate_rate,label='candidate available');axes[1].bar(chart.method,chart.quality_pass_rate,alpha=.5,label='image-only QC pass');axes[1].set(ylabel='Fraction of images',xlabel='Method');axes[1].legend()
 for ax in axes:ax.tick_params(axis='x',rotation=90,labelsize=7)
 fig.suptitle('Development general n=1,200, positive masks409; availability is NOT product success');save(fig,'methods_preservation_availability','동일일반표본이다. 원시방법의실패는NA로보존율분모에서빠지므로후보율을함께표시한다. 품질조건통과도제품정답정확도가아니다.')
 fig,ax=plt.subplots(figsize=(13,5));ax.scatter(complete.linear_gain,complete.retention,s=28,c='gray',alpha=.5,label='Complete-output development methods');p=complete[complete.pareto_proxy].sort_values('linear_gain');ax.plot(p.linear_gain,p.retention,'o-',label='Proxy Pareto');ax.scatter([primary_dev.linear_gain],[primary_dev.retention],s=100,marker='*',label='Frozen policy');ax.set(xlabel='Mean1024/native crop side (geometric linear gain)',ylabel='Pixel weighted defect retention (ratio)');ax.legend();fig.suptitle('Pareto: general1,200 / positive409; product containment NOT VERIFIED');save(fig,'pareto','제품점유율이아닌원본프레임축소로얻는기하확대대리지표다. 원본전체는보존100%이지만gain1.0이다. 일부결함손실과확대효과의동시교환관계를본다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5));
 for stage,g in [('development',dev[dev.cohort=='dev_general']),('holdout',hold)]:
  x=g[g.method==primary];axes[0].hist(x.side,bins=30,alpha=.45,label=f'{stage} n={len(x)}');axes[1].bar(stage,float(x.full_frame.mean()))
 axes[0].set(xlabel='Native crop side (pixels)',ylabel='Images (count)');axes[0].legend();axes[1].set(xlabel='Frozen policy stage',ylabel='Full1024 frame used (fraction)',ylim=(0,1));fig.suptitle(primary+' / original pixels preserved before model adapters');save(fig,'frozen_crop_size','크기가작아졌다는것은제품확대가능성의대리지표다. 제품외곽이빠졌는지는제품GT검수전미확인이다. 전체프레임복귀를성공확대로표현하지않는다.')
 fig,ax=plt.subplots(figsize=(14,5));by=pd.read_csv(M/'summary_by_category.csv');g=by[(by.cohort=='dev_general')&(by.method.isin([primary,'center896','cached_yolo_A30_fullfb']))];pivot=g.pivot(index='category',columns='method',values='retention');pivot.plot(ax=ax,marker='o');ax.set_xticks(range(len(pivot)),pivot.index,rotation=90,fontsize=7);ax.set(ylabel='Pixel weighted retention (ratio)',xlabel='Category');fig.suptitle('General40images/category / positive mask counts differ by category');save(fig,'category_retention','마스크표본수는summary_by_category에있다. 동일품목·동일표본에서사전학습YOLO캐시와비교했으며원본제품검출정확도는아니다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5))
 for key,ax in zip(['view','background_type'],axes):
  name='summary_by_view.csv' if key=='view' else 'summary_by_background.csv';g=pd.read_csv(M/name);g=g[(g.cohort=='dev_general')&g.method.isin([primary,'center896','cached_yolo_A30_fullfb'])];g.pivot(index=key,columns='method',values='retention').plot.bar(ax=ax);ax.set(ylabel='Defect pixel retention (ratio)',xlabel=key);ax.tick_params(axis='x',rotation=15)
 fig.suptitle('Same general1,200/positive409; background is previous automatic classification');save(fig,'view_background','흰색·검은색배경을나눠보고시점도분리한다. 품목구성과배경예측오류가섞여있으므로인과효과를주장하지않는다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5))
 for name,key,ax in [('small_mask',True,axes[0]),('outer_mask',True,axes[1])]:
  g=pd.read_csv(M/f'summary_by_{name}.csv');g=g[(g.cohort=='dev_general')&(g[name]==key)&g.method.isin(main_methods)];ax.bar(g.method,g.retention);ax.tick_params(axis='x',rotation=90,labelsize=6);ax.set(ylabel='Conditional pixel retention (ratio)',xlabel='Method');ax.set_title(name+' subset; counts in companion CSV')
 fig.suptitle('Small mask<1024px2 / outer128px defect band; within general1,200');save(fig,'small_outer_defects','small은이미지전체주석면적기준,성분small은원본성분면적1024미만으로별개다. 외곽양성픽셀은원본128px테두리에있는지로정의한다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 for metric,ax in zip(['median_output_pixels','small_id_survival'],axes):
  g=resize[(resize.cohort=='independent_validation_products')&resize.method.isin([primary,'full','center896'])];g.pivot(index='target',columns='method',values=metric).plot(ax=ax,marker='o');ax.set(xlabel='Actual adapter target (pixels)',ylabel=metric+' (px / ratio)')
 fig.suptitle('Frozen Holdout300; actual NEAREST at224/256/392/512/640');save(fig,'actual_resize','실제로변환한마스크의양성픽셀수와원본성분ID생존율이다. 원본ID생존과출력연결성분개수는합쳐짐·분절때문에같지않을수있다. 모델정확도개선으로바꾸어해석하지않는다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5));g=ps[(ps.cohort=='dev_general')&ps.method.isin(main_methods)];axes[0].bar(g.method,g.any_no_candidate_rate);axes[1].bar(g.method,g.mixed_fallback_rate)
 for ax in axes:ax.tick_params(axis='x',rotation=90,labelsize=6);ax.set_xlabel('Method /240 declared products')
 axes[0].set_ylabel('Any view missing candidate (fraction)');axes[1].set_ylabel('Fallback on1..4views (fraction)');fig.suptitle('Five-view consistency: candidate status, NOT product GT accuracy');save(fig,'five_view_failure','5시점중하나라도후보가없는제품과일부시점만Fallback인제품을분리한다. 관측mask만완전보존한비율은미제공시점의정상성보증이아니다.')
 fig,ax=plt.subplots(figsize=(13,5))
 for family in ['border_lab','border_rgb','contour_canny','grabcut90','grabcut80','grabcut_bbox']:
  g=dg[dg.method.isin([f'{family}_m{m}' for m in [0,10,20,30]])].copy();g['margin']=g.method.str.extract(r'_m(\d+)')[0].astype(int);g=g.sort_values('margin');ax.plot(g.margin,g.retention,'o-',label=family)
 ax.set(xlabel='Margin on EACH original box side (%)',ylabel='Conditional pixel weighted retention (ratio)');ax.legend();fig.suptitle('General1,200/positive409; margin increases total span by1+2m');save(fig,'margin_curves','미검출은NA이고이곡선은후보조건부다. 확대한여백은결함을회복할수있지만배경과전체프레임사용도늘릴수있다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5));g=dg[dg.method.isin(['grabcut90_m10',primary,'hybrid_m10_center896','hybrid_m10_full','hybrid_m10_trainprior'])];axes[0].bar(g.method,g.fallback_rate);axes[1].bar(g.method,g.retention)
 for ax in axes:ax.tick_params(axis='x',rotation=35,labelsize=8);ax.set_xlabel('Method')
 axes[0].set_ylabel('Fallback fraction /1,200images');axes[1].set_ylabel('Conditional defect retention (ratio)');fig.suptitle('Fallback paths and retained defect support');save(fig,'fallback','전체복귀로실패를숨기지않도록Fallback비율과보존율을같이제시한다. Train품목·시점prior는정상10/2표본의추정이며검증된안전영역이아니다.')
 fig,ax=plt.subplots(figsize=(10,4));ax.axis('off');ax.text(.5,.65,f'600 PROPOSAL boxes\n{len(gt)} human-approved VERIFIED_GT',ha='center',va='center',fontsize=24);ax.text(.5,.2,'Product IoU / Recall / actual pixel occupancy: UNVERIFIED\nAutomatic foreground boxes are NOT ground truth.',ha='center',fontsize=14);fig.suptitle('Product evaluation status, not a zero-valued accuracy measurement');save(fig,'product_gt_pending','제품BBox를사람이검수할때까지제품지표는NA다. BBox정답을얻어도제품실제픽셀점유율은전경maskGT와다르며박스면적대리값으로표기해야한다.')
 quality=pd.read_csv(M/'aligned_image_quality.csv');qs=quality.groupby(['cohort','method','target']).agg(images=('image_path','size'),edge_recall=('edge_recall','mean'),contrast_retention=('local_contrast_retention','mean'),native_local_difference=('native_defect_minus_ring','mean'),restored_local_difference=('restored_defect_minus_ring','mean')).reset_index();qs.to_csv(M/'aligned_quality_summary.csv',index=False)
 fig,axes=plt.subplots(1,2,figsize=(13,5));q=qs[(qs.cohort=='independent_validation_products')&(qs.target==256)];axes[0].bar(q.method,q.edge_recall);axes[1].bar(q.method,q.contrast_retention)
 for ax in axes:ax.tick_params(axis='x',rotation=25,labelsize=8);ax.set_xlabel('Method, heldout image subset150')
 axes[0].set_ylabel('Exact-pixel Canny recall (ratio)');axes[1].set_ylabel('Local contrast retention (ratio)');fig.suptitle('Aligned with same original crop coordinates / target256');save(fig,'aligned_image_quality','각Crop원본영역과그영역의복원영상을비교했다. 서로다른영역의평균화질을전제품성능으로비교하면안된다. 결함주변12pxring은제품GT없어배경혼입가능성미확인이다.')
 fig,axes=plt.subplots(1,2,figsize=(12,5));holdchart=hh[hh.method.isin(['full','center896',primary])];axes[0].bar(holdchart.method,holdchart.retention);axes[1].bar(holdchart.method,holdchart.linear_gain)
 for ax in axes:ax.tick_params(axis='x',rotation=25,labelsize=8)
 axes[0].set_ylabel('Pixel weighted defect retention (ratio)');axes[1].set_ylabel('Mean geometric linear gain (ratio)');fig.suptitle('Independent Validation products60 / images300 / positive masks103');save(fig,'independent_holdout','이Holdout결과를본뒤정책을다시조정하지않았다. 새Test는소모하지않았고원래Validation선언제품에서미사용그룹을선택했다. 과거전수메타/밝기통계는이미있던데이터임을한계로남긴다.')
 # Internal examples: same30 categories plus the heldout partial-loss case.
 choices=dev[(dev.cohort=='dev_general')&(dev.method==primary)&(dev.original_pixels>0)].copy();choices=choices.sort_values(['retention','original_pixels']).groupby('category').head(1)
 failure_hold=hold[(hold.method==primary)&(hold.original_pixels>0)&(hold.retention<1)].sort_values('retention').head(5);examples=pd.concat([choices,failure_hold],ignore_index=True);examples.to_csv(M/'illustrated_cases.csv',index=False)
 eval_lookup={}
 for stage in ['development','holdout']:
  for r in map(json.loads,(B/f'checkpoints/evaluation_{stage}.jsonl').read_text().splitlines()):eval_lookup[r['image_path']]=r
 for i,r in enumerate(examples.to_dict('records'),1):
  path=r['image_path'];meta=lookup.loc[path];image=cv2.imread(str(Path('dataset')/path));mask=cv2.imread(str(Path('dataset')/meta.mask_path),0)>0;records={v['method']:v for v in eval_lookup[path]['results']}
  from mv_analysis.yolo_crop_geometry import square_crop
  lab_crop=records['border_lab_m10']['crop'] if 'border_lab_m10' in records else square_crop(cp[path]['proposals']['border_lab']['bbox'],.1)
  items=[('Original',[0,0,1024,1024]),('Center896',records['center896']['crop']),('Lab m10 (illustration)',lab_crop),('GrabCut90 m10',records[primary]['crop'])]
  fig,axes=plt.subplots(2,4,figsize=(16,8))
  for col,(name,crop) in enumerate(items):
   if crop is None:axes[0,col].text(.1,.5,'NO CANDIDATE',transform=axes[0,col].transAxes);axes[1,col].text(.1,.5,'NA',transform=axes[1,col].transAxes);continue
   x0,y0,x1,y1=crop;c=image[y0:y1,x0:x1];m=mask[y0:y1,x0:x1];show=cv2.cvtColor(c,cv2.COLOR_BGR2RGB);show[m]=(show[m]*.65+np.array([255,0,0])*.35).astype(np.uint8);ret=m.sum()/mask.sum();axes[0,col].imshow(show);axes[0,col].set_title(f'{name}\nside{x1-x0}px; defect{ret:.3%}',fontsize=9)
   resized=cv2.resize(m.astype(np.uint8),(256,256),interpolation=cv2.INTER_NEAREST);axes[1,col].imshow(resized,cmap='gray',vmin=0,vmax=1,interpolation='nearest');axes[1,col].set_title(f'Actual256 mask, positive{int(resized.sum())}px',fontsize=9)
  for ax in axes.flat:ax.set(xlabel='x native/output pixels',ylabel='y native/output pixels');ax.tick_params(labelsize=6)
  fig.suptitle(f'INTERNAL n=1 /{r["category"]} {r["view"]} {r["cohort"]} /{r["case_id"]}\nRed=defect GT, not product mask. Auto foreground/product proposals remain UNVERIFIED.',fontsize=10)
  save(fig,f'case_{i+1:02}_{r["category"]}',f'단일사례n=1,제공결함양성{int(mask.sum())}px. 품목별작은마스크와검증후손실사례를설명목적으로골랐으며대표표본빈도와다르다. Holdout사례를검수했어도정책파라미터를수정하지않았다.')
 # Report all meanings and gaps instead of pretending candidate coverage is accuracy.
 main=dg[dg.method.isin(main_methods)];holdsummary=hh[['method','images','positive_masks','retention','removed','partial','side_mean','linear_gain','full_frame_rate']]
 report=['# Real-IAD 비학습 Object-aware Crop 비교 연구 보고서',
 '**내부 검토용 제조 원본·파생 사례 포함. 제품 자동 박스는 정답이 아니며 외부 공개용 통계와 분리한다.**',
 '## 1. 연구 목적과 배경',
 '제품/결함보존과입력에서의확대효과를동시에얻는오프라인전처리후보를찾는다. 원본전체는기하보존100%지만확대효과없음,작은Crop은확대되지만결함을자를수있다. 별도딥러닝학습/YOLO추론/다운로드/API/Push없이OpenCV이미지기반추정과기존YOLO캐시를비교했다.',
 '## 2. 기존 YOLO11 실험 요약',
 '기존일반1200장COCO검출770/미검출430,Center896약98.59%,YOLO A30+Fallback약99.06%,YOLO∪Center896+전체Fallback100%를실제CSV와대조했다. 마지막정책은전체프레임82.08%,평균변1013.37px여서확대가제한됐다. 모든수치의분모는일반제공양성409장이고전수51295와혼용하지않는다.',link(B/'baseline_crosscheck.json'),
 '## 3. 데이터 표본 구성과 독립성',table(sample.groupby(['stage','cohort','status']).size().rename('images').reset_index()),
 '실제이미지1950장:기존일반1200·위험150(Development),Train정상300(품목별2제품×5시점),미사용Validation60제품·300장(Holdout). 기존배경표본300/ROI검수336의알려진제품도Holdout선정에서제외했다. Holdout은YOLO/OpenCVCrop정책에미사용인제품그룹이지,과거전수밝기·메타·CenterCrop집계에도전혀사용되지않은역사적순수데이터라는뜻은아니다. 추가Test는사용하지않았다.',
 '기존Test일부가Development에포함되어이미탐색에사용됐음을기록한다. 이번고정후Holdout결과를다시튜닝에쓰면새로운독립검증이필요하다. Train/Validation/Test라벨과제품ID/C1~C5는변경하지않았다.',link(B/'sample_manifest.csv'),
 '## 4. 비교 Crop 알고리즘',
 '전체Resize,Center896/768/640,RGB/Lab/HSV Border,gray BackgroundDifference,Otsu/Adaptive/Canny/Closing contour,GrabCut90/80/이미지전경BBox초기화,AdaptiveCenter고정중심/전경중심,Train품목·시점prior,합의Hybrid와3Fallback을비교했다. Development82방법행에는기존YOLO2개캐시도포함된다. 방법들의중간연산이공유되므로82개의독립알고리즘이라는뜻은아니다. AdaptiveShift는LabBBox사각화의재표현으로중복관계를공개한다.',
 '## 5. 제품 영역 추정 원리',
 '가장자리10px/256frame통계로배경을추정하고RGB·HSV원형Hue/gray거리의median+MAD기반threshold를쓴다. Lab은기존border-lab-v5의경계색/조명plane추정을재사용한다. Otsu/Adaptive는테두리양성비율로극성을결정한다. Canny60/180과7×7closing,외곽contour채움은별도후보다. 연결성분은면적뿐아니라중앙거리·종횡비·테두리접촉으로점수화해하나를선택한다. 가장큰성분이나모든성분Union을제품정답으로간주하지않는다.',
 'GrabCut은256에서2회초기반복후1회추가하고마지막전경변화율을기록한다. 변화2%이상은불안정진단이며수학적미수렴판정은아니다. 사각형밖은배경으로초기화되므로중앙90%밖제품이있으면원천적으로잘릴수있다. [OpenCV GrabCut 설명](https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html),[Thresholding](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html),[Contours](https://docs.opencv.org/4.x/d4/d73/tutorial_py_contours_begin.html). 사용라이브러리는OpenCV5.0이고참고문서는4.x이므로API와실제동작은실행검증결과를우선한다.',
 '## 6. Margin 및 Fallback',
 '각변m×원래BBox폭/높이를추가해전체폭(1+2m)로확장,정사각화후정수경계보호2px추가,1024상한으로프레임내평행이동한다. m=0/10/20/30%. Hybrid는quality기준통과후서로다른border/nonborder계열에서IoU .8이상지지2개이상을얻은한BBox를선택하며무조건Union하지않는다. 이QC는수작업정답으로보정된확률이아니다.',
 'Hybrid Fallback은Center896/전체1024/Train정상품목·시점prior를비교했다. prior는category10장/category-view2장뿐이라검증된안전영역이아니다. 최종GrabCut90+10%+fullfb는후보없음에서만원본복귀하고,불안정/유사색후보를완전히걸러내는검증gate는없다. 이를제품전체안전성보장으로부르면안된다.',
 '## 7. 제품 BBox 평가',f'600장검수용박스를구축했으나현재사람승인VERIFIED_GT는{len(gt)}장이다. 자동600박스는PROPOSAL이며기존OpenCV/YOLO를GT로쓰지않았다. 승인없는제품IoU·제품전체Recall·부분물체율·실제제품픽셀점유율은UNVERIFIED다. 승인BBox가생겨도BBox면적Recall/점유율은실제제품픽셀mask지표와구분한다.',
 f'검수도구: `uv run --offline python scripts/review_product_bboxes.py`, 같은PC http://127.0.0.1:8766 .제품전체를직접수정/확인하고검수자ID와체크를해야VERIFIED_GT append된다. synthetic테스트는실제승인ledger에쓰지않았다.',link(B/'review/product_bbox_proposals.csv'),
 '## 8. 결함 마스크 보존율',table(main[['method','images','candidate_rate','positive_masks','available_positive_masks','retention','removed','partial']]),
 'raw방법의보존율은후보있는마스크에조건부이며실패를임의제외해안전성으로포장하지않도록후보율/미생성수를같이제시한다. 전체출력이있는Fallback/고정정책만동일분모Pareto에사용한다. 미제공NG는NA,제공빈마스크는별도이며NG를OK로재분류하지않는다. mask>0는검증한기존기술통계정책이다.',
 '## 9. 작은 결함 분석',
 '작은mask이미지는원본양성면적1024px²미만,작은source성분은각8연결성분면적1024미만이다. 원본성분ID를NEAREST로추적해한픽셀이라도남는지세고,출력연결성분개수와별도기록한다. 성분합침/분절로둘은같지않을수있다. 외곽결함은원본128pxband와의접촉으로정의한다.',link(M/'summary_by_small_mask.csv'),link(M/'summary_by_outer_mask.csv'),
 '## 10. 확대 효과 분석',
 f'고정후보 `{primary}`의Development평균변{primary_dev.side_mean:.2f}px,기하선형gain{primary_dev.linear_gain:.4f},전체프레임{primary_dev.full_frame_rate:.3%}다. Holdout에서는변{primary_hold.side_mean:.2f}px,gain{primary_hold.linear_gain:.4f},전체{primary_hold.full_frame_rate:.3%}다. 선형gain평균은1024/평균변과같지않다. 실제제품점유율이아닌원본배경제거/확대가능성대리지표이며부분제품을확대했을가능성은GT검수전남아있다.',
 '## 11. Resize 후 정보 보존',table(resize[(resize.cohort=='independent_validation_products')&resize.method.isin([primary,'full','center896'])]),
 'Development는실제256/512,Holdout은고정후보와고정기준에서224/256/392/512/640의NEAREST양성픽셀·source ID생존을계산했다. 이는모델공식입력해상도권고나성능개선주장이아니다. imagequality는Development150/Holdout150의같은원본Crop영역에복원해EdgeRecall/국소대비를계산했다. 다른Crop영역지표를같은전체영상품질로해석하지않는다. 결함12px주변ring의제품내부여부는GT없어UNVERIFIED다.',table(qs),
 '## 12. 품목별 결과',link(M/'summary_by_category.csv'),
 '동일품목의초기/최종결과와후보율·quality·Fallback을동시에본다. 제품과배경이유사한검은부품,종이/반사/구멍/얇은부품,테두리접촉에서전경잘림이나배경성분선택이가능하다. 실제실패는아래사례와목록의관측결함손실로구분하고원인해석은가설임을표시한다.',
 '## 13. 배경별 결과',link(M/'summary_by_background.csv'),
 'BLACK/WHITE/GRAY는기존자동배경분류다. 배경유형별차이는품목·시점·조명혼합에의해달라질수있어배경색의인과효과로단정하지않는다. GrabCut은배경치환증강이아니라영상내전경추정이다.',
 '## 14. 5시점 일관성',table(ps[(ps.cohort.isin(['dev_general','independent_validation_products']))&ps.method.isin([primary,'full','center896'])]),
 '한시점BBox를다른시점에재사용하지않고각시점을추정했다. any_no_candidate/mixed_fallback은제품검출실패정답률이아닌후보/정책상태다. all_observed_defects_preserved는정답제공시점만의보존이며미제공시점의결함부재를증명하지않는다. 제공양성시점이없는제품은그분모에서NA다.',
 '## 15. Pareto 분석과 후보 고정',table(complete[complete.pareto_proxy][['method','retention','linear_gain','side_mean','full_frame_rate']]),
 'Development일반표본만사용해완전출력후보중완전제거0·픽셀보존>=.995·평균기하gain>=1.05조건을우선한뒤최대gain을선택했다. 위험150은진단전용으로선택에쓰지않았다. 보존최대후보와동일하여고정후보는1개다. 이지표만으로실제제품전체보존을보증하지않는다.',link(B/'frozen_policy.json'),
 '## 16. 실패 사례 분석',
 f'고정후보의Holdout제공양성{primary_hold.positive_masks}장에서완전제거{primary_hold.removed},부분잘림{primary_hold.partial},픽셀보존{primary_hold.retention:.6%}다. 사례는결과확인후설명용으로선정했지만방법이나마진은수정하지않았다. 아래빨간mask는결함위치이고제품mask가아니다. 미수렴은마지막반복변화량진단이며수학적convergence증명이아니다.',
 '## 17. 최종 후보 정책 및 Independent Holdout',table(holdsummary),
 f'후속검증후보는 `{primary}`다. 결함proxy에서는기존YOLO일반표본보다보존/확대절충이유망했고Holdout에서도선택당시정책을유지했다. 그러나부분손실이남고제품GT가없으므로최종판정은 **INCONCLUSIVE**다. ADOPT_CANDIDATE나전품목공통전처리확정으로보고하지않는다.',
 '## 18. 분석 한계',
 '600제품BBox는검수대기PROPOSAL이다. 제품정답지표NA,실제foreground점유율NA. 256전경추정은원본경계를양자화하고작은부품을놓칠수있다. category/viewprior의2표본은안전범위를입증하지못한다. 개발표본의Test사용은이미탐색오염으로기록한다. Holdout도메타·밝기전수통계가존재한집합이며완전한역사적미접촉데이터는아니다. 사람이제품BBox를승인하거나Holdout결과에따라새정책을설계하면이전결과와새실험을분리한다.',
 '## 19. 후속 모델 실험 설계',
 '먼저제품전체BBox를독립검수하고정책손실허용기준을정한다. 그다음원본Resize/고정Center/고정GrabCut후보를같은제품분할·모델·예산에서비교한다. PatchCore/Dinomaly/INP의추가CenterCrop,torchvision내부Resize,YOLO/RT-DETR/ViTDet의정규화·범위를개별adapter에서명시한다. Crop좌표와원본크기를보존하고GT박스/마스크도같이변환한다. 원본고해상도를유지한오프라인좌표캐시를쓴다. 실제12모델학습성능·추론속도는이번에측정하지않았다.',
 '## 20. 재현 방법 및 검증',
 '`uv run --offline python scripts/object_aware_crop_experiment.py smoke/train/dev/freeze/holdout`의순서로실행했다(각phase별도명령). 체크포인트에서완료이미지를건너뛰며source/runner해시가바뀌면중단한다. `object_crop_aligned_quality.py`는고정정책의제한표본영상지표만계산한다. 기존151050장해상도전수나YOLO추론은재실행하지않았다. 기존파일·원본은보존했다.',link(B/'config.json'),link(M/'all_method_summary.csv'),link(M/'five_view_product_metrics.csv'),link(B/'review/http_smoke_validation.json'),
 '## 통계 그래프와 내부 사례']
 for f in figures:report.extend([f'### {f["name"]}',f'![{f["name"]}](../{f["path"]})',f['caption']])
 (P/'OBJECT_AWARE_CROP_COMPARISON_REPORT.md').write_text('\n\n'.join(report))
 (P/'CROP_POLICY_DECISION_SUMMARY.md').write_text('# Crop 정책 검토 요약\n\n최종판정: **INCONCLUSIVE** (제품전체GT미검수).\n\n'+table(holdsummary)+'\n\n후속검증후보: '+primary+' .같은300Holdout에서정책변경없이결함보존/확대proxy를검증했으나제품BBox600장사람승인과독립모델성능평가가필요하다. 신규Test는사용하지않았다. 원본Resize는안전기준선으로유지한다.\n')
 failures=d[(d.original_pixels>0)&d.available&(d.retention<1)&d.method.isin([primary,'center896'])];failures.to_csv(M/'frozen_and_center_failure_cases.csv',index=False)
 (P/'CROP_FAILURE_CASES.md').write_text('# Crop 실패·검수 대기 사례\n\n제공mask손실은관측값이고자동BBox의실제제품완전성은미검수다.\n\n'+table(failures[['cohort','category','view','case_id','method','original_pixels','kept_pixels','retention','mask_state']].head(80))+'\n\n[전수표본실패목록](../outputs/object_aware_crop_v1/metrics/frozen_and_center_failure_cases.csv). 그림자·유사색·얇은부품·테두리초기화가실패원인후보이며인과로확정하지않았다. 사람승인전제품GT지표는UNVERIFIED다.\n')
 savej(B/'report_generation.json',dict(success=True,figures=len(figures),internal_image_cases=len(examples),primary=primary,verdict='INCONCLUSIVE',product_gt_verified=len(gt),holdout_candidate=primary_hold.to_dict(),source_development_sha256=sha(M/'per_image_development.csv'),source_holdout_sha256=sha(M/'per_image_holdout.csv')))
 print(json.dumps(j(B/'report_generation.json'),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
