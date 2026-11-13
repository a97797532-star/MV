# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Two INTERNAL visual reports using cached YOLO/geometry; no inference or training."""
import os,sys,json,re,hashlib
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyBboxPatch
B=Path('outputs/yolo11_dynamic_crop_v1');H=B/'hybrid_extension';O=B/'visual_reports_v1';P=Path('reports')
from mv_analysis.yolo_crop_geometry import transform_boxes
cv2.setNumThreads(1)
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: d.
def table(d):
 # val: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: x.
 def val(x):return 'NA' if pd.isna(x) else f'{x:.6g}' if isinstance(x,float) else str(x)
 return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(val(v) for v in r)+' |' for r in d.itertuples(index=False,name=None)])
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if O.exists() or (P/'YOLO11_CROP_RESULT_REPORT.md').exists():raise SystemExit('Preserve existing report version')
 O.mkdir();(O/'yolo_cases').mkdir();(O/'hybrid_cases').mkdir();(O/'figures').mkdir()
 sample=pd.read_csv(B/'sample_manifest.csv').set_index('image_path');metrics=pd.read_csv(B/'metrics/per_image_crop_metrics.csv',low_memory=False);sums=pd.read_csv(B/'metrics/method_summary.csv');hybrid=pd.read_csv(H/'per_image_metrics.csv');hs=pd.read_csv(H/'summary.csv')
 evalrows={r['image_path']:r for r in map(json.loads,(B/'evaluation_checkpoint.jsonl').read_text().splitlines())};inference={r['image_path']:r for r in map(json.loads,(B/'inference_checkpoint.jsonl').read_text().splitlines())};hcoords={(r['image_path'],r['method']):r['crop'] for r in map(json.loads,(H/'crop_coordinates.jsonl').read_text().splitlines())}
 original_inference_sha=sha(B/'inference_checkpoint.jsonl')
 # One provided-positive NG per category: prioritize removed/partial cases, then small mask.
 pool=metrics[(metrics.cohort=='general')&(metrics.method=='confidence_m30_fallback')&(metrics.geometric_defect_pixels>0)].copy();pool['priority']=pool.crop_state.map({'removed':0,'partial':1,'preserved':2});selected=pool.sort_values(['priority','geometric_defect_pixels','image_path']).groupby('category',sort=True).head(1).sort_values('category')
 # Extra small/edge failure cases; every illustration selection is explicitly post-hoc.
 extra=pool[pool.crop_state.isin(['removed','partial']) & ~pool.image_path.isin(selected.image_path)].sort_values(['priority','geometric_defect_pixels']).head(6);selected=pd.concat([selected,extra],ignore_index=True)
 selected[['case_id','image_path','category','view','crop_state','geometric_defect_pixels','kept_pixels']].to_csv(O/'illustrated_cases.csv',index=False)
 # rgb: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: im.
 def rgb(im):return cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
 # overlay: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: im, mask.
 def overlay(im,mask):
  out=rgb(im).copy()
  if mask is not None:out[mask]=(out[mask].astype(float)*.65+np.array([255,0,0])*.35).astype(np.uint8)
  return out
 # reconstruct: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: im, crop, target.
 def reconstruct(im,crop,target=256):
  canvas=np.full_like(im,128)
  if crop is not None:
   x0,y0,x1,y1=crop;small=cv2.resize(im[y0:y1,x0:x1],(target,target),interpolation=cv2.INTER_AREA);canvas[y0:y1,x0:x1]=cv2.resize(small,(x1-x0,y1-y0),interpolation=cv2.INTER_LINEAR)
  return canvas
 # cropped_mask: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: mask, crop.
 def cropped_mask(mask,crop):
  if crop is None:return np.zeros_like(mask)
  out=np.zeros_like(mask);x0,y0,x1,y1=crop;out[y0:y1,x0:x1]=mask[y0:y1,x0:x1];return out
 case_records=[]
 for i,row in enumerate(selected.to_dict('records'),1):
  path=row['image_path'];meta=sample.loc[path];im=cv2.imread(str(Path('dataset')/path));mask=cv2.imread(str(Path('dataset')/meta.mask_path),0)>0;original=overlay(im,mask);record=evalrows[path];det=inference[path];lookup={r['method']:r for r in record['metrics']};yc=lookup['confidence_m30']['crop'];cc=[64,64,960,960];hc=hcoords[(path,'hybrid896_fullfallback')]
  # Detail center prioritizes pixels removed by YOLO, otherwise smallest source component.
  lost=mask&~cropped_mask(mask,yc)
  if lost.any():yy,xx=np.where(lost);cx,cy=int(np.median(xx)),int(np.median(yy));reason='YOLO-excluded defect region'
  else:
   n,labels,stats,centroids=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8);component=1+np.argmin(stats[1:,cv2.CC_STAT_AREA]);cx,cy=map(int,centroids[component]);reason='smallest provided component'
  x=max(0,min(864,cx-80));y=max(0,min(864,cy-80));detail=[x,y,x+160,y+160]
  for kind in ['yolo','hybrid']:
   fig,axes=plt.subplots(2,3,figsize=(15,9))
   axes[0,0].imshow(original);axes[0,0].set_title('Original 1024; GT defect red; COCO cyan')
   for bbox in sorted(det['detections'],key=lambda d:-d['confidence'])[:5]:
    x0,y0,x1,y1=bbox['xyxy'];axes[0,0].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='cyan',linewidth=1));axes[0,0].text(x0,y0,f"{bbox['coco_name']} {bbox['confidence']:.2f}",color='cyan',fontsize=7)
   axes[0,0].add_patch(Rectangle((x,y),160,160,fill=False,edgecolor='yellow'))
   candidates=[('Center896',cc),('YOLO A30 (no fallback)',yc)] if kind=='yolo' else [('YOLO A30 (no fallback)',yc),('Center896 union YOLO + full fallback',hc)]
   for ax,(label,crop) in zip(axes[0,1:],candidates):
    if crop is None:ax.set_facecolor('#ddd');ax.text(.1,.5,'NO_DETECTION\nNo crop candidate',transform=ax.transAxes);ax.set_title(label)
    else:
     x0,y0,x1,y1=crop;view=overlay(im[y0:y1,x0:x1],mask[y0:y1,x0:x1]);ax.imshow(view);ret=int(mask[y0:y1,x0:x1].sum())/int(mask.sum());ax.set_title(f'{label}\nNative side={x1-x0}px; defect support={ret:.3%}',fontsize=10)
   axes[1,0].imshow(rgb(im[y:y+160,x:x+160]),interpolation='nearest');axes[1,0].set_title('Original 160x160 detail')
   detail_methods=[('YOLO A30 ->256, restored',yc),('Center896 ->256, restored',cc)] if kind=='yolo' else [('Center896 ->256, restored',cc),('Hybrid ->256, restored',hc)]
   for ax,(label,crop) in zip(axes[1,1:],detail_methods):
    rec=reconstruct(im,crop);ax.imshow(rgb(rec[y:y+160,x:x+160]),interpolation='nearest');ax.set_title(label+'\nGray = area excluded by crop',fontsize=10)
   for ax in axes.flat:ax.set(xlabel='x (panel/native crop pixels)',ylabel='y (panel/native crop pixels)');ax.tick_params(labelsize=7)
   fig.suptitle(f'INTERNAL REVIEW / n=1 / {row["category"]} NG {row["view"]} / {row["case_id"]}\n{reason}; product GT unavailable; red mask is defect annotation, not product mask',fontsize=11)
   fig.tight_layout();dest=O/(kind+'_cases')/f'{i:02}_{row["category"]}_{row["case_id"]}.png';fig.savefig(dest,dpi=125,bbox_inches='tight');plt.close(fig)
   # Separate native mask coordinates from actually resized binary supports.
   fig,axes=plt.subplots(1,4,figsize=(15,4))
   mask_methods=[('Native original mask',None),('Center896 ->256',cc),('YOLO A30 ->256',yc),('Hybrid ->256',hc)]
   for ix,(ax,(label,crop)) in enumerate(zip(axes,mask_methods)):
    if ix==0:show=mask.astype(np.uint8);ax.imshow(show,cmap='gray',vmin=0,vmax=1,interpolation='nearest');ax.set_title(f'{label}\npositive pixels={int(show.sum())}')
    elif crop is None:ax.text(.1,.5,'NO CANDIDATE',transform=ax.transAxes);ax.set_title(label)
    else:
     x0,y0,x1,y1=crop;show=cv2.resize(mask[y0:y1,x0:x1].astype(np.uint8),(256,256),interpolation=cv2.INTER_NEAREST);ax.imshow(show,cmap='gray',vmin=0,vmax=1,interpolation='nearest');ax.set_title(f'{label}\npositive pixels={int(show.sum())}')
    ax.set(xlabel='x (native/output pixels)',ylabel='y (native/output pixels)');ax.tick_params(labelsize=7)
   fig.suptitle(f'INTERNAL / {row["category"]} {row["view"]} n=1 / Actual NEAREST masks, not area proxies');fig.tight_layout();maskdest=O/(kind+'_cases')/f'{i:02}_{row["category"]}_{row["case_id"]}_masks.png';fig.savefig(maskdest,dpi=125,bbox_inches='tight');plt.close(fig)
   case_records.append(dict(kind=kind,category=row['category'],case_id=row['case_id'],image_path=path,view=row['view'],original_pixels=int(mask.sum()),yolo_state=row['crop_state'],image_figure=str(dest),mask_figure=str(maskdest),selection='posthoc: per category worst A30+fallback state, then smallest positive mask; extra6 failures'))
  if i%10==0:print(f'Internal visual cases {i}/{len(selected)} (two reports, no YOLO calls)',flush=True)
 pd.DataFrame(case_records).to_csv(O/'case_figure_manifest.csv',index=False)
 # Combined report statistics are always complete-output methods on identical cohorts.
 figs=[]
 # save: 결과를 지정한 출력 위치에 기록합니다.
 # 입력 인수: fig, name, caption.
 def save(fig,name,caption):
  fig.tight_layout();p=O/'figures'/f'{name}.png';fig.savefig(p,dpi=150,bbox_inches='tight');plt.close(fig);figs.append((str(p),caption,name))
 general=metrics[metrics.cohort=='general'];hgeneral=hybrid[hybrid.cohort=='general'];summary=hs[hs.cohort=='general'];baseline=sums[(sums.cohort=='general')&sums.method.isin(['full','center896','confidence_m30_fallback'])]
 fig,axes=plt.subplots(1,2,figsize=(13,5));base=baseline[['method','conditional_pixel_weighted_retention','removed','partial']].rename(columns={'conditional_pixel_weighted_retention':'retention'});combined=summary[['method','pixel_weighted_retention','removed','partial']].rename(columns={'pixel_weighted_retention':'retention'});all=pd.concat([base,combined],ignore_index=True)
 axes[0].bar(all.method,all.retention);axes[0].set(ylabel='Pixel weighted support retention (ratio)',ylim=(0,1.02));all.set_index('method')[['removed','partial']].plot.bar(ax=axes[1]);axes[1].set(ylabel='Positive-mask images (count)')
 for ax in axes:ax.tick_params(axis='x',rotation=35,labelsize=8);ax.set_xlabel('Complete-output method')
 fig.suptitle('Identical general sample n=1,200; all methods have409 provided positive masks');save(fig,'hybrid_global','同一'.replace('同一','同一').replace('同一','同一')+'')
 # Replace the caption above with an explicit Korean interpretation.
 figs[-1]=(figs[-1][0],'일반 동일1200장, 제공 양성409장을 분모로 비교한다. 결합+전체Fallback은 이표본에서 모두 보존했지만 원본전체사용 증가와 함께 해석해야 한다.',figs[-1][2])
 per=[]
 for (category,method),g in hgeneral.groupby(['category','method']):
  pos=g[g.original_pixels>0];per.append(dict(category=category,method=method,positive_masks=len(pos),retention=pos.kept_pixels.sum()/pos.original_pixels.sum() if len(pos) else np.nan))
 per=pd.DataFrame(per);per.to_csv(O/'hybrid_category_statistics.csv',index=False)
 fig,ax=plt.subplots(figsize=(14,5));pivot=per.pivot(index='category',columns='method',values='retention');pivot.plot(ax=ax,marker='o');ax.set_xticks(range(len(pivot)),pivot.index,rotation=90,fontsize=8);ax.set(xlabel='Category',ylabel='Pixel weighted retention (ratio)',ylim=(0,1.02));fig.suptitle('Hybrid by category / general n=1,200, positive masks n=409');save(fig,'hybrid_category','품목별 양성마스크 개수는 companion CSV에 있다. 여기서100%는 제품전체검출 정확도가 아니라 제공결함픽셀의 기하적 보존이다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5))
 for key,ax in zip(['view','cohort'],axes):
  rows=[]
  for (v,m),g in hybrid.groupby([key,'method']):
   pos=g[g.original_pixels>0];rows.append(dict(group=v,method=m,retention=pos.kept_pixels.sum()/pos.original_pixels.sum()))
  pd.DataFrame(rows).pivot(index='group',columns='method',values='retention').plot.bar(ax=ax);ax.set(ylabel='Pixel support retention (ratio)',xlabel=key,ylim=(0,1.02));ax.tick_params(axis='x',rotation=20)
 fig.suptitle('General1,200 / risk150; positive masks409 /103; views balanced within cohort');save(fig,'hybrid_view_cohort','위험표본은 마스크 위치로 골랐으므로 일반표본과 합산하지 않는다. 후속결합은기존결과를보고고안했으므로독립표본검증이필요하다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 for method,g in hgeneral.groupby('method'):axes[0].hist(g.native_side,bins=25,alpha=.45,label=method)
 axes[0].set(xlabel='Native crop side (pixels)',ylabel='Images (count)');axes[0].legend(fontsize=8);axes[1].bar(summary.method,summary.full_frame_fraction);axes[1].set(ylabel='Full original1024 frame used (fraction)',xlabel='Hybrid policy',ylim=(0,1));axes[1].tick_params(axis='x',rotation=20);fig.suptitle('Preservation vs enlargement tradeoff / same general n=1,200');save(fig,'hybrid_extent','전체Fallback결합에서82.0833%는원본전체,평균변길이1013.37px이다. Crop으로제품이실질적으로확대되는경우가제한된다는뜻이며제품점유율을측정한값은아니다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5))
 for t,ax in zip([256,512],axes):
  rows=[]
  for method in ['full','center896','confidence_m30_fallback']:
   g=general[(general.method==method)&(general.geometric_defect_pixels>0)];rows.append((method,g[f't{t}_positive_pixels'].median(),int((g[f't{t}_positive_pixels']==0).sum())))
  for method,g in hgeneral[hgeneral.original_pixels>0].groupby('method'):rows.append((method,g[f't{t}_positive_pixels'].median(),int((g[f't{t}_positive_pixels']==0).sum())))
  ax.bar([r[0] for r in rows],[r[1] for r in rows]);ax.tick_params(axis='x',rotation=40,labelsize=8);ax.set(ylabel=f'Median actual mask support at{t} (pixels)',xlabel='Complete-output method')
 fig.suptitle('Actual NEAREST output masks / same general provided-positive n=409');save(fig,'hybrid_output_support','기하보존100%라도실제축소후양성픽셀수나연결성분이유지된다는뜻은아니다. 각입력크기의NEAREST결과를직접계산해비교했다.')
 # A diagram makes the inclusion guarantee and offline adapter boundary explicit.
 fig,axes=plt.subplots(1,2,figsize=(13,6));ax=axes[0];ax.set(xlim=(0,1024),ylim=(1024,0),xlabel='Native x (pixels)',ylabel='Native y (pixels)',aspect='equal')
 for (x,y,w,h),color,label in [((64,64,896,896),'blue','Center896 anchor'),((0,250,700,700),'orange','Example YOLO candidate'),((0,0,1024,1024),'green','Containing square')]:ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=color,linewidth=2,label=label))
 ax.legend(fontsize=8);ax.set_title('Illustration only; NOT an actual measured image')
 ax=axes[1];ax.axis('off');labels=['ONCE: YOLO offline inference','Cache: native XYXY + mask validity','Crop: high resolution lossless/native reference','Later: model-specific Resize / Normalize','Evaluate: pure model inference (exclude YOLO)']
 for i,label in enumerate(labels):
  y=.9-i*.18;ax.add_patch(FancyBboxPatch((.02,y-.1),.96,.12,boxstyle='round,pad=.01',facecolor='#e6eff6',edgecolor='navy'));ax.text(.5,y-.04,label,ha='center',va='center',fontsize=9)
  if i<4:ax.annotate('',xy=(.5,y-.17),xytext=(.5,y-.11),arrowprops={'arrowstyle':'->'})
 fig.suptitle('Hybrid inclusion rule and offline dataset pipeline / schematic, no sample count');save(fig,'hybrid_pipeline_diagram','합집합을포함하는정사각형은anchor와YOLO후보를모두포함한다. 둘밖의결함보존은보장하지않고,추론이없는미래입력adapter와최초YOLO데이터구축을분리한다.')
 intro='# 내부 검토용: YOLO11 단독 Crop 결과 보고서\n\n**내부 검토용 원본·Crop·결함 마스크 비교 이미지 포함. 외부 공개·기존 외부 AI 검토 ZIP 재포장 대상이 아니다. 사용자 허용에 따라 내부 PDF에 포함했다.**\n\n'
 source=(P/'YOLO11_DYNAMIC_CROP_EXPERIMENT_REPORT.md').read_text();source=re.sub(r'### 후속 제안:.*?(?=## 19\.)','',source,flags=re.S);source=source[source.index('## 1.'):]
 ytext=[intro,source,'## 21. 실제 영상·결함 마스크 비교 사례',
 f'30품목별제공양성NG1장씩과추가실패최대6장,총{len(selected)}개의도적검수사례를넣었다. 품목별로A30+Fallback의완전제거/부분잘림을우선하고그다음작은마스크를선정했다. 무작위대표표본이아니며사례빈도를성공률로읽지않는다. 위통계는일반1200장/위험150장을분리한전체표본의수치다.',
 '위쪽원본의빨간영역은제공결함mask이고청록박스는COCO검출이다. 제품전체정답BBox가아니다. 아래160×160동일원본좌표확대에서Crop제외영역은회색으로표시했다. 각Crop을256으로줄이고그Crop의원본영역에복원한비교이므로외부좌표를억지로정렬하지않았다.']
 for r in case_records:
  if r['kind']!='yolo':continue
  ytext.extend([f'### {r["category"]} {r["view"]} · {r["case_id"]}',f'![원본·YOLO·Center 비교 {r["category"]}](../{r["image_figure"]})',f'단일NG검수사례 n=1,원본양성{r["original_pixels"]}px,A30+Fallback상태={r["yolo_state"]}. 숫자는제품전체검출정확도가아니라제공결함위치의보존이다.',f'![실제 출력 마스크 {r["category"]}](../{r["mask_figure"]})','n=1,원본마스크와실제NEAREST256마스크. 흰색이양성이며패널별축은원본또는출력픽셀단위다. 결합패널은비교용이며자세한정책은별도결합보고서참조.'])
 ytext.extend(['## 22. 검증·제품 정답 한계와 후속 실험',
 '제품전체BBox IoU·Recall·점유율·PARTIAL_OBJECT는UNVERIFIED다. 검출발생64.1667%를제품검출정확도라고부르면안된다. 26개pytest와원본SHA/좌표/캐시검증을수행했다. PDF최종검증파일에서모든페이지렌더·문자페이지경계와실제검수범위를확인한다.',
 '**평가 재사용 주의:** 파일럿은기존Validation와Test의일부제품을포함한다. 이결과를전처리수정에사용했다면동일표본을미사용독립최종평가로취급하지않는다. 후속채택판정은미사용제품holdout또는nested validation으로다시검증해야한다.',
 '[결합 Crop 결과 보고서](COMBINED_CROP_RESULT_REPORT.md). 동일YOLO추론캐시를재사용하므로추론을반복할필요가없다.'])
 (P/'YOLO11_CROP_RESULT_REPORT.md').write_text('\n\n'.join(ytext))
 combined=['# 내부 검토용: CenterCrop·YOLO 결합 Crop 결과 보고서',
 '**내부 검토용 원본·Crop·결함 마스크 비교 이미지를 포함한다. 외부 공개/기존 외부 AI 검토 ZIP 대상이 아니다.**',
 '## 1. 결합의 목적과 결론',
 'Center896은안전망영역으로유지하고YOLO가찾은외곽영역까지포함해동적Crop의결함누락위험을줄일수있는지평가했다. 같은표본을본뒤제안한후속탐색이므로독립검증된최적정책이아니다. 이번일반409/위험103양성마스크에서결합+미검출전체Fallback은기하픽셀100%를보존했다. 다만일반82.0833%가전체프레임이므로확대효과는제한적이다. 최종채택판정은제품정답부재로INCONCLUSIVE다.',
 '## 2. 표본과 공정 비교',
 '일반1200=30품목×8제품×5시점,OK/NG각600. 위험150은마스크정보를사용해별도선정했다. 일반양성409/위험103의보존율을합산하지않았다. YOLO결과는동일1350이미지의최초1회추론캐시를그대로쓰고추가YOLO호출은0이다. no-detection을제외하지않고출력이있는Fallback정책을전체Resize/CenterCrop과같은분모로비교한다.',
 '## 3. 결합 규칙과 기하적 보장',
 'anchor=[64,64,960,960]인Center896, A30은최고confidence COCO박스에서각변원래너비/높이30%여백을추가한정사각Crop이다. 두사각형의좌표최소/최대합집합을모두포함하는가장작은정사각형을프레임내로옮긴다. 따라서원본좌표에서Center896에남은결함을추가로제거하지않는다. 이보장은Resize이전기하포함관계에한정된다.',
 'hybrid896은YOLO후보가없으면Center896을사용한다. hybrid896_fullfallback은YOLO후보가없으면전체1024를사용한다. 검출은있지만부분제품을찾은경우의검증된제품gate는없다. 제품전체정답없이는둘밖의제품/결함이나제품IoU를보증할수없다.',
 '## 4. 동일 일반 표본의 정량 비교',table(all),
 'Center896은픽셀가중98.5876%,제거0/부분14;YOLO A30+미검출전체Fallback은99.0618%,제거5/부분3이다. 단순히평균이높다는이유로단독YOLO를채택할수없다. hybrid896은98.8456%,제거0/부분8이고,hybrid896_fullfallback은100%,제거0/부분0이다. 원본전체Resize는원래100%기하보존이므로결합이그보다보존성능이높다는뜻은아니다.',
 '## 5. 일반·위험 표본과 Resize 결과',table(hs[['cohort','method','images','positive_masks','pixel_weighted_retention','removed','partial','preserved']]),
 table(summary[['method','mean_native_side','full_frame_fraction','t256_mask_pixels_median','t512_mask_pixels_median']]),
 'NEAREST출력mask의양성픽셀수는실제계산값이며연속면적proxy가아니다. 결함픽셀기하보존100%는256/512에서미세성분이나경계가모두보존된다는뜻이아니다. 결합의원본성분ID생존율전수계산은NOT_ANALYZED이며출력연결성분개수와혼동하지않는다.',
 '## 6. 품목·시점별 보존과 확대 효과',table(per),
 '일반fullfallback결합의평균native변1013.37px,전체프레임비율82.0833%다. 원본1024에서입력256으로단순축소하는것과대체로가까우며,Center896처럼강하게확대하는정책은아니다. 실제제품점유율은제품정답이없어UNVERIFIED,남긴프레임면적/변길이는기하적대리지표다.',
 '## 7. 오프라인 데이터셋 구현',
 '모든좌표는원본absolute XYXY·끝exclusive로보존했다. native hybrid cache는크롭이필요한242이미지만lossless PNG로저장하고1108이미지는원본참조로중복을피했다. 이는일반/위험합계다. Resize/Normalize를적용하지않아후속12모델별adapter가처리한다. 원본GT박스는crop원점차감→clip→0면적제거기록후target별scale,mask는동일기하의NEAREST를기본후보로사용한다. 미제공NG는빈negative로취급하지않는다.',
 '## 8. 모델별 충돌과 검증',
 'PatchCore/Dinomaly/INP의공식CenterCrop을native결합Crop뒤에그대로더하면다시결함을자를수있다. 이미지를줄이는공통전처리와모델내Resize/Normalize가겹치지않도록단계별이력을명시한다. YOLO구축비용은후속모델순수추론시간에포함하지않고저장좌표재사용으로추론을반복하지않는다.',
 '## 9. 한계와 의사결정',
 '제품전체BBox정답이없어제품보존율·IoU·Recall·부분물체율은UNVERIFIED다. 본결합은원래실험결과를확인한후고안했고기존Test일부도탐색에사용했으므로동일표본100%를독립검증성능이라고주장하지않는다. 미사용제품holdout과검증제품BBox로다시평가해야한다. 클래스별모델성능·속도이득은NOT_ANALYZED다.',
 '**회의 결정:** (1)전체Resize대비극히작은확대효과를위해YOLO오프라인비용을지불할가치 (2)제품정답BBox검수범위 (3)추가Crop을허용할품목/시점 (4)어떤결함손실도허용하지않을지 (5)원본참조+좌표캐시를데이터셋표준으로할지. 현재는전품목일괄적용을보류한다.',
 '## 10. 통계 그래프·알고리즘 도식']
 for path,caption,name in figs:combined.extend([f'### {name}',f'![{name}](../{path})',caption])
 combined.extend(['## 11. 실제 원본·YOLO·결합 비교 사례',f'YOLO보고서와동일한{len(selected)}개의도적검수사례다. 성공률을추정하는표본이아니라실패조건과확대손실을설명하는자료다. 원본의청록COCO박스는제품전체정답이아니다. 세부확대는동일원본좌표에서256출력을복원해보였다.'])
 for r in case_records:
  if r['kind']!='hybrid':continue
  combined.extend([f'### {r["category"]} {r["view"]} · {r["case_id"]}',f'![원본·YOLO·결합 비교 {r["category"]}](../{r["image_figure"]})',f'n=1,원본양성{r["original_pixels"]}px,YOLO A30+Fallback기하상태={r["yolo_state"]}. 결합의픽셀보존과제품전체탐지성공은별개다.',f'![결합 출력 마스크 {r["category"]}](../{r["mask_figure"]})','n=1,마스크패널은원본·Center896·YOLO·결합의실제양성support다. 원본과출력좌표단위를분리해읽는다.'])
 combined.extend(['## 12. 근거 파일·재현과 검증',
 f'[결합요약](../{H}/summary.csv),[동일표본비교](../{H}/baseline_comparison.csv),[원본좌표캐시](../{H}/crop_coordinates.jsonl),[고해상도native manifest](../{H}/offline_native_dataset_manifest.csv),[기하검증](../{H}/validation.json),[native검증](../{H}/native_dataset_validation.json). [YOLO 단독 보고서](YOLO11_CROP_RESULT_REPORT.md).',
 '`uv run --offline python scripts/evaluate_yolo_center_hybrid.py`와`materialize_yolo_center_hybrid.py`는기존좌표를사용한다. 이미완료된출력을보호하므로새버전이나체크포인트로재개한다. `build_visual_crop_reports.py`는이미저장된결과로내부시각자료만생성한다. 원본은읽기만했고해상도전수계산·YOLO재추론·학습·Push는하지않았다.'])
 (P/'COMBINED_CROP_RESULT_REPORT.md').write_text('\n\n'.join(combined))
 assert sha(B/'inference_checkpoint.jsonl')==original_inference_sha
 (O/'generation_validation.json').write_text(json.dumps(dict(success=True,additional_yolo_calls=0,cases_per_report=len(selected),originals_and_crops_user_authorized_for_internal_use=True,internal_only=True,case_selection='posthoc, not representative',source_inference_sha256=original_inference_sha,images_case_figures=len(case_records)*2,hybrid_statistical_figures=len(figs)),indent=2))
 print(f'Two Markdown reports written. Each has {len(selected)} image comparisons + {len(selected)} actual mask comparisons.',flush=True)
if __name__=='__main__':main()
