# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Summarize real cached YOLO11 offline preprocessing; no model inference here."""
import os,json,hashlib,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import cv2,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path('outputs/yolo11_dynamic_crop_v1');MET=B/'metrics';F=B/'figures';P=Path('reports')
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
# jt: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def jt(p):return json.loads(Path(p).read_text())
# json_write: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p, v.
def json_write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df.
def table(df):
 # v: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: x.
 def v(x):
  if isinstance(x,(float,np.floating)):return 'NA' if np.isnan(x) else f'{x:.5g}'
  return str(x).replace('|','/')
 return '\n'.join(['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']+['| '+' | '.join(v(x) for x in row)+' |' for row in df.itertuples(index=False,name=None)])
# link: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def link(p):return f'[{Path(p).name}](../{p})'
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if (P/'YOLO11_DYNAMIC_CROP_EXPERIMENT_REPORT.md').exists():raise SystemExit('Report exists; choose new output version')
 complete=jt(B/'evaluation_complete.json');cfg=jt(B/'config.json');inf=pd.read_csv(MET/'inference_per_image.csv');sample=pd.read_csv(B/'sample_manifest.csv');d=pd.read_csv(MET/'per_image_crop_metrics.csv',low_memory=False);im=pd.read_csv(MET/'aligned_adapter_image_metrics.csv');inf['detected']=inf.detection_count>0
 assert len(sample)==1350 and len(inf)==1350 and inf.image_path.nunique()==1350 and len(d)==1350*36
 groups=[]
 for key in ['category','background_type','view','status','cohort']:
  keys=['cohort',key] if key!='cohort' else ['cohort']
  out=inf.groupby(keys).agg(images=('image_path','size'),detected=('detected','sum'),mean_predict_ms=('wall_predict_ms','mean'),median_predict_ms=('wall_predict_ms','median'),p95_predict_ms=('wall_predict_ms',lambda s:s.quantile(.95)),mean_rss_mb=('rss_mb','mean'),max_rss_mb=('rss_mb','max')).reset_index();out['detection_occurrence_rate']=out.detected/out.images;out['no_detection']=out.images-out.detected;out.to_csv(MET/f'detection_by_{key}.csv',index=False)
  if key=='category':categories=out
  elif key=='cohort':cohorts=out
 # summarize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: frame, keys.
 def summarize(frame,keys):
  result=[]
  for key,g in frame.groupby(keys,dropna=False):
   key=key if isinstance(key,tuple) else (key,);positive=g[g.geometric_defect_pixels>0];available=positive[positive.available];n=int(g.available.sum())
   r=dict(zip(keys,key))|dict(images=len(g),available=n,no_candidate=len(g)-n,positive_masks=len(positive),available_positive_masks=len(available),
    removed=int((available.crop_state=='removed').sum()),partial=int((available.crop_state=='partial').sum()),preserved=int((available.crop_state=='preserved').sum()),
    conditional_pixel_weighted_retention=available.kept_pixels.sum()/available.geometric_defect_pixels.sum() if len(available) else np.nan,
    conditional_image_mean_retention=available.pixel_retention.mean(),median_retention=available.pixel_retention.median(),p05_retention=available.pixel_retention.quantile(.05),
    full_retention_per_all_positive_masks=int((available.crop_state=='preserved').sum())/len(positive) if len(positive) else np.nan,
    mean_bbox_area_retention=available.bbox_area_retention.mean(),box_count=int(available.box_count.sum()),removed_boxes=int(available.removed_boxes.sum()))
   for t in cfg['adapter_evaluation_targets']:
    r[f't{t}_output_pixels_median']=available[f't{t}_positive_pixels'].median()
    r[f't{t}_native_component_survival']=available[f't{t}_original_component_ids_survived'].sum()/available.original_components.sum() if available.original_components.sum() else np.nan
    r[f't{t}_small_component_survival']=available[f't{t}_small_component_ids_survived'].sum()/available.small_native_components.sum() if available.small_native_components.sum() else np.nan
   result.append(r)
  return pd.DataFrame(result)
 sums=summarize(d,['cohort','method']);sums.to_csv(MET/'method_summary.csv',index=False)
 for name,key in [('category','category'),('view','view'),('background','background_type'),('small','small_defect_image'),('outer','outer_defect')]:summarize(d,['cohort',key,'method']).to_csv(MET/f'crop_by_{name}.csv',index=False)
 # Fair paired subset: candidate availability is selected by YOLO output, never masks.
 eligible=set(d[(d.method=='confidence_m0')&d.available].image_path)
 paired=summarize(d[d.image_path.isin(eligible)],['cohort','method']);paired.to_csv(MET/'matched_detection_subset_summary.csv',index=False)
 image_summary=im.groupby(['cohort','method','target']).agg(n=('image_path','size'),edge_recall=('edge_recall','mean'),local_contrast=('local_contrast_retention','mean'),rgb_rmse=('rgb_rmse','mean'),resize_ms=('adapter_image_resize_ms','mean')).reset_index();image_summary.to_csv(MET/'aligned_adapter_summary.csv',index=False)
 detections=[json.loads(x) for x in (B/'inference_checkpoint.jsonl').read_text().splitlines()];flat=[]
 for r in detections:
  for box in r['detections']:flat.append({k:r[k] for k in ['case_id','category','cohort','view','background_type']}|box)
 predicted=pd.DataFrame(flat);predicted.to_csv(MET/'all_coco_detections.csv',index=False)
 predicted.groupby(['cohort','coco_class','coco_name']).size().rename('boxes').reset_index().to_csv(MET/'coco_class_distribution.csv',index=False)
 # Downstream crop/adapter cost benchmark, explicitly not a repeated YOLO benchmark.
 cp=[json.loads(x) for x in (B/'evaluation_checkpoint.jsonl').read_text().splitlines()];lookup={r['image_path']:r for r in cp};perf=[]
 for row in sample[sample.cohort=='general'].groupby('category').head(1).to_dict('records'):
  r=lookup[row['image_path']];crop=r['offline']['crop_xyxy'];img=cv2.imread(str(Path('dataset')/row['image_path']));x0,y0,x1,y1=crop
  for repeat in range(4):
   t=time.perf_counter();native=img[y0:y1,x0:x1].copy();crop_ms=(time.perf_counter()-t)*1000
   t=time.perf_counter();ok,encoded=cv2.imencode('.png',native,[cv2.IMWRITE_PNG_COMPRESSION,3]);encode_ms=(time.perf_counter()-t)*1000;assert ok
   t=time.perf_counter();cv2.resize(native,(512,512),interpolation=cv2.INTER_AREA);resize_ms=(time.perf_counter()-t)*1000
   if repeat:perf.append(dict(case_id=row['case_id'],repeat=repeat,category=row['category'],crop_copy_ms=crop_ms,lossless_encode_ms=encode_ms,adapter_resize512_ms=resize_ms,encoded_bytes=len(encoded),disk_write_measured=False))
 perf=pd.DataFrame(perf);perf.to_csv(MET/'offline_crop_cost_benchmark.csv',index=False)
 # Class-aware original and crop labels, without inventing negative labels for unprovided NG.
 boxes=pd.read_csv('outputs/spatial_20261111_v7/defect_bboxes.csv');boxlookup={p:g for p,g in boxes.groupby('image_path')};labels=[]
 from mv_analysis.yolo_crop_geometry import transform_boxes
 for r in cp:
  crop=r['offline']['crop_xyxy'];g=boxlookup.get(r['image_path']);orig=g[['x0','y0','x1','y1']].to_numpy() if g is not None else np.empty((0,4));transformed,keep=transform_boxes(orig,crop)
  record=dict(case_id=r['case_id'],image_path=r['image_path'],classification_status=r['status'],has_mask=r['has_mask'],crop_xyxy=crop,coordinate_format='native crop absolute XYXY exclusive',detection_supervision='unprovided_do_not_use_as_negative' if r['status']=='NG' and not r['has_mask'] else 'provided_mask_or_normal',objects=[])
  if g is not None:
   for ix,row in enumerate(g.to_dict('records')):record['objects'].append(dict(class_id=row['class_id'],defect_type=row['defect_type'],original_xyxy=orig[ix].tolist(),crop_xyxy=transformed[ix].tolist(),valid=bool(keep[ix])))
  labels.append(record)
 with (MET/'offline_native_class_labels.jsonl').open('x') as stream:
  for r in labels:stream.write(json.dumps(r)+'\n')
 figs=[]
 # figsave: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: fig, name, caption.
 def figsave(fig,name,caption):
  fig.tight_layout();path=F/(name+'.png');fig.savefig(path,dpi=150,bbox_inches='tight');plt.close(fig);figs.append(dict(name=name,path=str(path),caption=caption))
 general=sums[sums.cohort=='general'];short=general[general.method.isin(['full','center896','center768','center640','confidence_m0','confidence_m10','confidence_m20','confidence_m30','confidence_m30_fallback'])]
 fig,ax=plt.subplots(figsize=(13,5));g=categories[categories.cohort=='general'].sort_values('detection_occurrence_rate');ax.bar(g.category,g.detection_occurrence_rate);ax.set(ylabel='Images with any COCO detection / images (ratio)',xlabel='Category',ylim=(0,1));ax.tick_params(axis='x',rotation=90,labelsize=8);fig.suptitle('YOLO occurrence by category: 40 images each / general n=1,200; NOT product accuracy');figsave(fig,'category_detection','일반 표본 품목당40장의 검출 발생률이다. COCO 후보가 있다는 뜻이며 제품 전체 BBox 성공률은 아니다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 for key,ax in zip(['background_type','view'],axes):
  g=inf[inf.cohort=='general'].groupby(key).detected.agg(['sum','size']);ax.bar([f'{k}\nn={v:,}' for k,v in g['size'].items()],g['sum']/g['size']);ax.set(xlabel=key,ylabel='Any detection occurrence (ratio)',ylim=(0,1))
 fig.suptitle('General sample n=1,200 / background is heuristic prediction');figsave(fig,'background_view_detection','배경·시점별 검출 발생률. 품목 구성과 배경 예측 오류가 섞여 있어 원인 효과로 해석하지 않는다.')
 fig,ax=plt.subplots(figsize=(12,5));g=predicted[predicted.cohort=='general'].coco_name.value_counts().head(20);g.plot.bar(ax=ax);ax.set(xlabel='COCO predicted class (top20)',ylabel='Detected boxes (count)');fig.suptitle(f'COCO names are not Real-IAD category labels / general detections n={sum(predicted.cohort=="general")}');figsave(fig,'coco_classes','오분류된 COCO 이름이어도 위치 후보로 평가할 수 있지만 Real-IAD 제품 카테고리 정답으로 바꾸지 않는다.')
 fig,ax=plt.subplots(figsize=(11,5));g=general[general.method.str.endswith('_m0')];ax.bar(g.method,g.available/g.images);ax.set(xlabel='Image-only selection policy',ylabel='Candidate availability (ratio)',ylim=(0,1));fig.suptitle('Four candidate policies / general n=1,200; product success UNVERIFIED');figsave(fig,'policy_availability','중앙 포함 후보가 없으면 해당 정책은 NO_CENTRAL_BOX다. 최고 confidence 정책이 최적이라는 가정을 두지 않는다. 제품 정답이 없어 실제 성공률은 미확인이다.')
 fig,ax=plt.subplots(figsize=(12,5))
 for policy in cfg['policies']:
  g=general[general.method.isin([f'{policy}_m{m}' for m in [0,10,20,30]])].copy();g['margin']=g.method.str.extract(r'_m(\d+)')[0].to_numpy().astype(int);g=g.sort_values('margin');ax.plot(g.margin,g.conditional_pixel_weighted_retention,'o-',label=policy)
 ax.set(xlabel='Margin per box side (%)',ylabel='Conditional positive pixel retention (ratio)',ylim=(0,1.03));ax.legend();fig.suptitle('Margin effect within available candidates; general n=1,200');figsave(fig,'margin_retention','미검출은 보존율 계산에서NA이므로 이 그래프는 후보가 있는 위치정답에 조건부다. 전체 표본 안전성을 뜻하지 않으며 별도 availability와 Fallback을 함께 본다.')
 fig,axes=plt.subplots(2,1,figsize=(13,9));axes[0].bar(short.method,short.conditional_pixel_weighted_retention);axes[0].set(ylabel='Pixel weighted retention (ratio)',ylim=(0,1.03));axes[0].tick_params(axis='x',rotation=35)
 short.set_index('method')[['removed','partial','preserved']].plot.bar(stacked=True,ax=axes[1]);axes[1].set(xlabel='Method',ylabel='Available positive-mask images (count)');axes[1].tick_params(axis='x',rotation=35);fig.suptitle('Same general sample: baseline vs candidates vs missing-candidate fallback / n=1,200');figsave(fig,'center_vs_dynamic','直接候補'.replace('直接候補','일반 표본 동일 이미지의 비교다. ')+'raw dynamic은 후보 없는 이미지를 처리하지 못한다. Fallback 행만 전체 표본에 출력이 있다. 아래 막대 분모가 달라질 수 있어 표의 available_positive_masks를 함께 확인한다.')
 fig,ax=plt.subplots(figsize=(13,5));small=pd.read_csv(MET/'crop_by_small.csv');g=small[(small.cohort=='general')&(small.small_defect_image==True)&(small.method.isin(short.method))];ax.bar(g.method,g.conditional_pixel_weighted_retention);ax.set(xlabel='Method',ylabel='Small-mask pixel retention (ratio)',ylim=(0,1.03));ax.tick_params(axis='x',rotation=35);fig.suptitle('Small defect images: original mask area <1,024 pixels; general subset');figsave(fig,'small_defect_retention','원본 마스크 면적1024px² 미만인 이미지 부분집합이다. 실제 소형 연결 성분의 생존율은 별도 표로 제공하며 서로 분모를 혼용하지 않는다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5));
 for t,ax in zip([256,512],axes):
  ax.bar(short.method,short[f't{t}_output_pixels_median']);ax.set(xlabel='Method',ylabel='Median resized positive support (output pixels)');ax.tick_params(axis='x',rotation=60,labelsize=7);ax.set_title(f'NEAREST mask at {t}x{t}')
 fig.suptitle('Actual resized mask support / available provided-positive masks');figsave(fig,'resized_mask_support','단순 면적비 proxy가 아니라 실제 NEAREST 마스크의 양성 픽셀 수다. Crop으로 제거된 결함은 확대해도 복원되지 않는다.')
 fig,axes=plt.subplots(1,2,figsize=(14,5))
 for t,ax in zip([256,512],axes):
  ax.bar(short.method,short[f't{t}_small_component_survival']);ax.set(xlabel='Method',ylabel='Source small-component IDs survived (ratio)',ylim=(0,1.03));ax.tick_params(axis='x',rotation=60,labelsize=7);ax.set_title(f'{t}x{t}, source component area<1024px2')
 fig.suptitle('Small connected-component identities surviving crop and nearest resize');figsave(fig,'small_component_survival','원본8연결 성분 ID를 NEAREST로 추적했다. 출력의 연결 성분 개수와 동일하지 않으며 두 성분이 합쳐져도 각ID가 남을 수 있다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5));
 for metric,ax in zip(['edge_recall','local_contrast'],axes):
  g=image_summary[(image_summary.cohort=='general')&(image_summary.target==256)];ax.bar(g.method,g[metric]);ax.set(xlabel='Method, image subset n=150',ylabel=metric+' (ratio)');ax.tick_params(axis='x',rotation=50,labelsize=7)
 fig.suptitle('Aligned image adapter metrics at256; each crop compared with same native region');figsave(fig,'aligned_image_quality','Crop마다 같은 원본 좌표 영역에 복원해 비교했다. 서로 다른영역의지표차이는공통전체영상품질우열을뜻하지않는다. raw dynamic은미검출로표본수가달라질수있다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5));axes[0].hist(inf[inf.cohort=='general'].wall_predict_ms,bins=60);axes[0].set(xlabel='YOLO wall prediction cost (ms/image)',ylabel='Images (count)');axes[1].scatter(categories[categories.cohort=='general'].mean_predict_ms,categories[categories.cohort=='general'].detection_occurrence_rate);axes[1].set(xlabel='Category mean offline YOLO cost (ms/image)',ylabel='Any detection occurrence (ratio)');fig.suptitle('ONE-TIME dataset construction cost; excluded from downstream model inference');figsave(fig,'offline_cost','가중치로드·합성warmup은분리했다. 이시간은오프라인데이터구축비용이며후속12모델순수추론시간에포함하지않는다. 이미지내용과품목혼합이비용차이에영향을줄수있다.')
 fig,ax=plt.subplots(figsize=(12,5));g=categories[categories.cohort=='general'].sort_values('no_detection',ascending=False);ax.bar(g.category,g.no_detection);ax.set(xlabel='Category,40 images each',ylabel='NO_DETECTION images (count)');ax.tick_params(axis='x',rotation=90,labelsize=8);fig.suptitle('Verified failure: no COCO detection; PARTIAL_OBJECT remains UNVERIFIED');figsave(fig,'category_failures','제품일부탐지(PARTIAL_OBJECT)는검증된제품정답이없어확정하지않았다. 여기서는검출자체가없는실패만집계한다.')
 fig,axes=plt.subplots(1,2,figsize=(12,5));g=short[short.method.isin(['confidence_m30','confidence_m30_fallback'])];axes[0].bar(g.method,g.available/g.images);axes[0].set(ylabel='Output availability (ratio)',xlabel='Candidate / fallback');axes[1].bar(g.method,g.conditional_pixel_weighted_retention);axes[1].set(ylabel='Conditional pixel retention (ratio)',xlabel='Candidate / fallback');fig.suptitle('Fallback only for missing candidate; no product-quality oracle used');figsave(fig,'fallback_effect','검출실패시원본전체Resize로복귀하면출력coverage는회복되지만잘못된BBox를탐지해복귀시키는검증된gate는없다. 출력이있다는사실은제품전체보존성공이아니다.')
 fig,ax=plt.subplots(figsize=(11,4));g=short.set_index('method').frame_occupancy if 'frame_occupancy' in short else d[(d.cohort=='general')&(d.method.isin(short.method))&d.available].groupby('method').frame_occupancy.mean();g.plot.bar(ax=ax);ax.set(ylabel='Mean crop area / full frame area (ratio)',xlabel='Method');fig.suptitle('FRAME crop area proxy; product occupancy NOT VERIFIED without product GT');figsave(fig,'occupancy_unverified','이값은제품점유율이아니라남긴원본프레임면적이다. 제품정답이없어제품점유율개선과제품영역recall을계산하지않았으며관련주장은UNVERIFIED다.')
 # Product GT absence blocks adoption even if a defect-mask proxy happens to improve.
 verdict='INCONCLUSIVE'
 primary=short[short.method=='confidence_m30_fallback'].iloc[0];center=short[short.method=='center896'].iloc[0]
 report=['# YOLO11 오프라인 동적 Crop 전처리 실험',
 '## 1. 연구 배경과 목적',
 'YOLO11n COCO 사전학습 모델을학습없이제품위치후보추정에쓰고,좌표를저장해오프라인데이터셋을구축하는실험이다. 실시간시스템이나최종검사모델의추론성능실험이아니다. 모델학습·Fine-tuning·유료API·OpenAI API·Push는수행하지않았다.',
 '## 2. 기존 CenterCrop의 한계',
 '기존제공양성마스크51,295장전수에서896/768/640Crop은각각82/967/4600이미지의위치정답을완전히제거했다. 그전수값은새표본의모집단통계와직접비교하지않는다. 본실험의동일표본에서전체·CenterCrop을다시계산했다.',
 '## 3. YOLO11 사전학습 모델 소개',
 f'공식공개파일 yolo11n.pt,5,613,764bytes,SHA256 `{cfg["weight_sha256"]}`. [공식모델문서](https://docs.ultralytics.com/models/yolo11),[공식다운로드](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt),[공식라이선스](https://www.ultralytics.com/license). 공개자료는AGPL-3.0/별도Enterprise라이선스체계를표시한다. 이번에는추론용공개가중치만받았고법적적합성보증을하지않는다.',
 '## 4. 실험 환경',
 f'WSL2 Ubuntu,Python3.12,Ultralytics8.4.210,PyTorch2.15.0+cpu,OpenCV5.0,CPU4logical/torch2threads,CUDA false. 기존uv.lock과.venv를수정하지않고outputs내별도venv에Ultralytics만추가하고기존분석패키지를읽기참조했다. 전체선언의존성설치완료를주장하지않고실제import/추론성공을검증했다. conf={cfg["conf"]}, IoU/NMS={cfg["iou"]},imgsz640,batch1,max_det100,class-awareNMS,FP32. 초기sandbox DNS실패후공개파일접근허용으로설치/다운로드했다.',
 link(B/'config.json'),link(B/'runtime.json'),link(B/'weights/manifest.json'),
 '## 5. 데이터 표본 선정',table(sample.groupby(['cohort','status']).size().rename('images').reset_index()),table(sample.groupby(['cohort','background_type']).size().rename('images').reset_index()),
 'seed20261112. 일반1200=30품목×8선언제품×5시점,OK/NG각600,C1~C5각240,Validation/Test각600. 품목별각split에서OK2/NG2제품을난수선택했다. 마스크위치로선택하지않았다. 별도위험150=30제품×5시점,작은마스크/외곽손실기준으로선정했고일반평가와분리했다. 원래split·NG상태·has_mask를유지했다. 제품선언키는실제물리제품동일성보증은아니다.',
 link(B/'sample_manifest.csv'),
 '## 6. 제품 BBox 추정 방식',
 'A최고confidence,B프레임중심과BBox중심이가장가까운것,C프레임중앙을포함하는것중최대면적,D모든검출Union. GT마스크는정책선택에사용하지않았다. 비교용native캐시는사전지정A+30%이며GT에따라선정한최적정책이아니다. COCO이름을제품분류정답으로재라벨하지않는다. 검증된제품전체BBox정답이없어제품IoU/영역Recall/PartialObjectRate와제품점유율은UNVERIFIED다. 기존OpenCV전경은정답으로사용하지않았다.',
 '## 7. Dynamic Crop 알고리즘',
 '검출BBox(x0,y0,x1,y1),너비w/높이h에서각변에mw/mh를추가하므로확장폭은(1+2m)w이다. 그최대변으로정사각을만들고정수경계손실보호2px를더한다. 변길이는1024상한,이미지밖이면정사각을프레임안으로평행이동한다. 원본absolute XYXY,끝좌표exclusive. 두축을각각잘라직사각으로만드는정책과다르다.',
 '원본해상도의lossless PNG및native defect mask는outputs/native_crops에내부보관하고외부PDF에는포함하지않는다. 대안정책은좌표만저장해재사용한다. 후보없는경우원본경로참조로복귀하여중복이미지를만들지않는다. Crop캐시에는Resize/Normalize를적용하지않고후속모델입력adapter에서수행한다.',
 '## 8. Margin 및 Fallback 정책',
 '0/10/20/30%를비교한다. Fallback은NO_DETECTION/NO_CENTRAL_BOX에서만원본전체좌표를쓴다. confidence만으로제품전체성공을판정하지않고성공여부자체를UNVERIFIED로남긴다. 잘못된부분BBox를검출하는quality gate는제품GT부재로검증하지못했다. 따라서본Fallback은제품보존을보증하는정책이아니다.',
 '## 9. 평가 지표 정의',
 '검출발생률=검출1개이상이미지/전체이미지로제품검출정확도가아니다. 결함픽셀보존율=Crop안양성픽셀/원본양성픽셀,전체요약은픽셀가중합계와영상평균을구분한다. 미제공NG는평가NA,제공빈마스크는양성보존분모에서제외한다. raw dynamic의NO_CANDIDATE는NA이며0보존으로조작하지않는다. 후보조건부표와전체출력가능률,같은후보집합의paired표를함께제공한다.',
 'NEAREST실제출력마스크양성픽셀과8연결성분수를계산하고원본성분ID도별도NN추적했다. 원본성분면적1024px²미만이small component,전체mask면적1024미만이small image,원본가장자리128px에양성하나라도있으면outer image다. 서로분모가다르다. 이미지변화지표는150일반표본에서각Crop영역을동일native영역에복원해비교했다. 256/512만실제adapter평가했고224/392/640전체조합은미실행이다.',
 '## 10. 제품 검출 결과',table(cohorts[['cohort','images','detected','detection_occurrence_rate','no_detection']]),table(categories[categories.cohort=='general'].sort_values('detection_occurrence_rate')[['category','images','detected','no_detection','detection_occurrence_rate']]),
 '제품정답없이COCO검출이유효제품BBox인지확정할수없다. COCO에없는품목에서도후보는나오지만제품전체를감쌌는지독립확인이필요하다. 외곽결함을남겼다는사실만으로제품전체를보존했다고가정하지않는다.',
 '## 11. CenterCrop 비교 결과',table(short[['method','images','available','positive_masks','available_positive_masks','conditional_pixel_weighted_retention']]),
 f'원본전체출력이있는사전지정A30+Fallback의보존율은{primary.conditional_pixel_weighted_retention:.6%},Center896은{center.conditional_pixel_weighted_retention:.6%}로동일일반표본기준차이는{(primary.conditional_pixel_weighted_retention-center.conditional_pixel_weighted_retention)*100:.4f}%p다. 후보없는NG를제외한raw dynamic값을전체표본CenterCrop과동일분모처럼해석하지않는다.',
 link(MET/'matched_detection_subset_summary.csv'),
 '## 12. 결함 마스크 보존율',table(short[['method','available_positive_masks','removed','partial','preserved','median_retention','p05_retention']]),
 '별도위험표본결과는method_summary.csv의cohort=mask_informed_risk를본다. 위험표본은결함위치를사용해선정했으므로일반1200과합쳐성공률을보고하지않는다. Crop으로결함이사라져도NG라벨을OK로바꾸지않는다.',
 '## 13. 작은 결함 분석',table(short[['method','t256_output_pixels_median','t512_output_pixels_median','t256_small_component_survival','t512_small_component_survival']]),
 '작은결함의출력확대와Crop위치손실을함께봐야한다. 남은양성pixel수가늘어도사라진component를복구한것은아니다. 모델검출정확도개선은학습실험전에는주장하지않는다.',
 '## 14. 카테고리·시점·배경별 결과',link(MET/'detection_by_background_type.csv'),link(MET/'detection_by_view.csv'),link(MET/'crop_by_category.csv'),link(MET/'crop_by_view.csv'),link(MET/'crop_by_outer.csv'),
 '배경은기존border-lab-v5자동분류다. 배경과품목/시점의혼합을통제하지않은차이는인과관계가아니다. 같은선언제품5시점은독립표본5개가아니다. 일반/위험을분리한기술통계이며최적정책선택용유의성검정을하지않았다.',
 '## 15. 오프라인 구축 비용 및 메모리',table(cohorts[['cohort','images','mean_predict_ms','median_predict_ms','p95_predict_ms','max_rss_mb']]),
 f'일반표본YOLO wall predict 합계{inf[inf.cohort=="general"].wall_predict_ms.sum()/1000:.3f}초,직렬호출기준처리량{1000/inf[inf.cohort=="general"].wall_predict_ms.mean():.3f}images/sec. 이는디코딩/PNG저장/GT평가시간을제외한다. 프로세스RSS는torch/library를포함하고GPU메모리는사용하지않았다. 실제5시점제품단위비용은해당5개wall시간합계로CSV에서계산한다.',
 table(perf[['crop_copy_ms','lossless_encode_ms','adapter_resize512_ms']].describe(percentiles=[.5,.95]).reset_index()),
 'Crop/인코딩비용은품목별1장×30,사전1회후3회반복한표본추정이며디스크write미포함. 이미지별YOLO는처음1회만실행하여캐시했고같은영상YOLO반복벤치마크는하지않았다. 합성black3회warmup은각프로세스시작에만수행해별도기록했다. YOLO비용은데이터셋최초구축비용이며후속12모델의순수추론/학습시간에포함하지않는다.',
 '## 16. 실패 사례 분석',
 '확정실패는NO_DETECTION또는정책C의NO_CENTRAL_BOX다. EXECUTION_ERROR는0이다. PARTIAL_OBJECT는제품GT없어미확정이다. 마스크완전제거는관측된전처리실패이지만어떤원제품부분이빠졌는지자동으로확정하지않는다. Union은관계없는배경COCO오탐까지포함할수있으며여백확장은보존율을올리면서제품확대효과를줄일수있다.',
 '## 17. 모델별 전처리 충돌 위험',
 'native Crop에는공통Resize/Normalize를하지않았다. PatchCore256→224와Dinomaly/INP448→392의공식중앙Crop을그대로더하면이중Crop이다. torchvision내부800Resize/Normalize와YOLO/RT-DETR0..1,ViTDet0..255를각adapter에서분리한다. 참조: reports/MODEL_INPUT_REQUIREMENTS.md. YOLO의COCOclass와후속결함class는완전히별개다.',
 '## 18. 최종 정책 제안과 판정',
 f'**판정: {verdict}.** 제품전체BBox정답부재로제품보존·부분물체율·정확도를확인하지못해ADOPT_CANDIDATE를선언할수없다. 오프라인구축가능성은실제추론/캐시로VERIFIED지만전품목공통전처리채택은보류한다. 먼저소규모제품전체BBox를독립검수하고품목/배경/시점별로NO_DETECTION및부분BBox를검증해야한다. Fine-tuning필요성은후속가설이며이번에수행하지않았다.',
 '질문별답: (1)검출발생률은표와같으나제품전체안정성은미확인. (2)COCO밖품목에서도후보생성은가능하지만유효성미확인. (3)낮은품목은품목표참조. (4)배경별차이는관측되나인과미확정. (5)최고confidence최선아님/정답없이선정불가. (6)여백곡선은후보조건부보존변화를보여준다. (7)CenterCrop대비동일표본의Fallback표로판단. (8)실제제품점유율은미확인이고프레임면적proxy만보고. (9)오프라인최초비용이므로실시간SLA판정불필요. (10)제품학습이필요할수있으나독립GT평가우선. (11)일괄적용보류. (12)이중Crop위험있음.',
 '## 19. 분석 한계',
 '제품GT·제품IoU/recall/점유율·PARTIAL_OBJECT는UNVERIFIED. 30품목균형표본은전체데이터비율의불편추정이아니다. 위험표본은의도적선택이다. confidence .25/640설정의한사전학습모델만평가했고저confidence나타모델을탐색하지않았다. 실제downstream학습성능·최적해상도·12모델순수추론성능은NOT_ANALYZED. 원본/파생사례영상공유권한미확인으로PDF에는통계그래프만포함했다.',
 '## 20. 재현 방법 및 근거 파일',
 '`outputs/yolo11_dynamic_crop_v1/env/bin/python scripts/yolo11_offline_crop_experiment.py smoke` → `infer` → `evaluate`. 완료이미지는체크포인트를재사용한다. 가중치/metadata/sample/geometry해시가일치해야한다. 보고서집계는`uv run --offline python scripts/report_yolo11_dynamic_crop.py`. 실제Native후보출력과분류상태·원본좌표·변환라벨은offline_native_dataset_manifest.csv와offline_native_class_labels.jsonl로추적한다. 후속모델은이좌표/PNG를재사용하고YOLO를다시실행하지않는다.',
 link(MET/'inference_per_image.csv'),link(MET/'per_image_crop_metrics.csv'),link(MET/'offline_native_dataset_manifest.csv'),link(MET/'offline_native_class_labels.jsonl'),
 '## 통계 그래프와 해석']
 for f in figs:report.extend([f'### {f["name"]}',f'![{f["name"]}](../{f["path"]})',f['caption']])
 (P/'YOLO11_DYNAMIC_CROP_EXPERIMENT_REPORT.md').write_text('\n\n'.join(report))
 summary=['# YOLO11 오프라인 Crop 의사결정 요약',f'판정: **{verdict}**. 학습없는실제추론1350장(일반1200/위험150),오류0. 원본해상도PNG/좌표캐시생성완료. 제품전체GT가없어제품전체보존성공을선언하지않는다.',table(short[['method','available','available_positive_masks','conditional_pixel_weighted_retention','removed','partial']]),'우선결정: 검증제품BBox표본확보,COCO미검출/부분객체gate검증,품목별채택여부,남은결함과크롭손실의교환관계. YOLO비용은최초데이터구축에만계상한다. 모델adapter는nativeCrop후개별Resize/Normalize를한다. 최고confidence+30%는사전지정탐색캐시일뿐추천확정정책이아니다.']
 (P/'YOLO11_DYNAMIC_CROP_DECISION_SUMMARY.md').write_text('\n\n'.join(summary))
 # Basic reproducibility evidence; full source/crop coordinate integrity checked separately.
 json_write(B/'report_generation.json',dict(verdict=verdict,figures=len(figs),general_images=1200,risk_images=150,source_checkpoint_sha256=sha(B/'inference_checkpoint.jsonl'),metric_checkpoint_sha256=sha(B/'evaluation_checkpoint.jsonl'),product_gt='UNVERIFIED',primary_fallback_retention=float(primary.conditional_pixel_weighted_retention),center896_retention=float(center.conditional_pixel_weighted_retention)))
 print(json.dumps(jt(B/'report_generation.json'),indent=2),flush=True)
if __name__=='__main__':main()
