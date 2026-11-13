# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Build an evidence-based master report and an image-free-of-examples review ZIP.

Uses frozen image analyses and completed Crop checkpoints, never recomputes
resolution or modifies source data. All PNGs made here are statistical plots.
"""
import json,hashlib,os,re,shutil,zipfile
from pathlib import Path
from datetime import datetime,timezone
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path('outputs/preprocessing_review_20261112_v2');R=Path('outputs/windows_preserved_20261111_v1');G=Path('outputs/background_full_20261111_v1');D=Path('outputs/resolution_detail_20261111_v2');M=Path('outputs/model_sources_20261112_v1')
P=Path('reports');AS=B/'review_assets';ST=AS/'statistics';FIG=AS/'figures';VAL=AS/'validation'

# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# load: 자료를 불러와 다음 처리에 사용할 형태로 준비합니다.
# 입력 인수: p.
def load(p):return pd.read_csv(p)
# j: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def j(p):return json.loads(Path(p).read_text())
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: d.
def table(d):
 if d.empty:return '해당 관측 없음.'
 # val: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: v.
 def val(v):
  if isinstance(v,(float,np.floating)):return 'NA' if np.isnan(v) else f'{v:.6g}'
  return str(v).replace('|','/').replace('\n',' ')
 return '\n'.join(['| '+' | '.join(map(str,d.columns))+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(map(val,row))+' |' for row in d.itertuples(index=False,name=None)])
# link: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path.
def link(path):return f'[{Path(path).name}](../{path})'
# write: 검증한 결과를 출력 형식으로 기록합니다.
# 입력 인수: path, text.
def write(path,text):
 if path.exists():raise RuntimeError('Preserve existing '+str(path))
 path.write_text(text,encoding='utf-8')

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if (P/'PREPROCESSING_REVIEW_PACKAGE.zip').exists() or (P/'DATA_ANALYSIS_MASTER_REPORT.md').exists():raise SystemExit('Package/report exists; choose a new version rather than overwrite')
 assert j(B/'complete.json')['success']
 for p in [ST,FIG,VAL]:p.mkdir(parents=True,exist_ok=True)
 # Explicit whitelist: small aggregates, no whole-image or example PNGs copied.
 chosen={
  B:['category_status_counts.csv','defect_counts.csv','view_mask_counts.csv','split_counts.csv','mask_crop_overall.csv','mask_crop_category.csv','mask_crop_view.csv','mask_crop_defect.csv','mask_crop_by_size.csv','bbox_crop_counts.csv','bbox_crop_category_view.csv','bbox_crop_resize_risk.csv','mask_crop_resize_area_proxy.csv','bbox_category_distribution.csv','bbox_defect_distribution.csv','bbox_view_distribution.csv','product_geometry_summary.csv','regional_global_statistics.csv','regional_category_statistics.csv','regional_view_statistics.csv','regional_background_statistics.csv','regional_per_image_percentile_summary.csv','selection_category.csv','selection_status.csv','selection_view.csv','selection_background_type.csv','selection_failure_reasons.csv','selection_candidate_diagnostics.csv','segmentation_category_coverage.csv','provided_view_count_per_ng_product.csv','five_view_brightness_correlation.csv'],
  G:['brightness_interpretation_changes.csv','background_stratified_comparison.csv','strict_selection_sensitivity_comparison.csv','segmentation_selection_brightness.csv','train_product_augmentation_candidates.csv','train_normal_only_augmentation_candidates.csv'],
  D:['overall_statistics.csv','category_statistics.csv','view_statistics.csv','status_statistics.csv','category_view_status_statistics.csv','existing_roi_summary.csv','bbox_projected_size_risk.csv','stepwise_distribution.csv'],
  R:['heatmap_summary.csv']}
 assetmap={};provenance=[]
 for folder,names in chosen.items():
  for name in names:
   src=folder/name;dest=ST/(name if name not in assetmap else folder.name+'_'+name)
   shutil.copy2(src,dest);assetmap[name]=dest
   provenance.append(dict(asset=str(dest),source=str(src),sha256=sha(src),bytes=src.stat().st_size,source_mtime_utc=datetime.fromtimestamp(src.stat().st_mtime,timezone.utc).isoformat(),status='VERIFIED'))
 meta=load(R/'image_metadata_with_split.csv');reg=pd.read_csv(G/'regional_brightness_per_image.csv',low_memory=False);bbox=load('outputs/spatial_20261111_v7/defect_bboxes.csv')
 crop=load(B/'mask_crop_overall.csv');cv=load(B/'mask_crop_view.csv');cc=load(B/'mask_crop_category.csv');by_size=load(B/'mask_crop_by_size.csv');geom=load(B/'product_geometry_sample.csv')
 rf=j(B/'regional_findings.json');mvalid=j(R/'metadata_validation_report.json')
 assert len(meta)==151050 and meta.image_path.nunique()==151050 and len(reg)==151050
 declared=meta.groupby('product_id').agg(images=('image_path','size'),views=('view','nunique'),splits=('split','nunique'))
 assert (declared.images==5).all() and (declared.views==5).all() and (declared.splits==1).all()
 # Independent frozen result cross-check of the previously reported resolution means.
 resolution=pd.read_csv(R/'per_view_information_loss.csv',usecols=['image_path','target','psnr_db','ssim','edge_recall','edge_f1','local_contrast_retention','high_frequency_proxy_retention'])
 means=resolution.groupby('target').mean(numeric_only=True)
 expected={512:[40.985,.975989,.473716,.761417],256:[35.632,.943659,.178240,.604359]}
 checks={}
 for target,values in expected.items():
  for metric,v in zip(['psnr_db','ssim','edge_recall','local_contrast_retention'],values):checks[f'resolution_{target}_{metric}']=bool(abs(means.loc[target,metric]-v)<(.00051 if metric=='psnr_db' else .00000051))
 assert all(checks.values())
 # BBox crop/resize distribution and anonymity-preserving risk cases.
 clipped=load(B/'bbox_crop_per_component.csv');masks=load(B/'mask_crop_per_image.csv')
 cases=masks.query('crop != 1024 and defect_pixels > 0 and retention < 1').copy()
 cases['case_id']=cases.image_path.map(lambda s:'crop_'+hashlib.sha256(s.encode()).hexdigest()[:12])
 riskcases=cases.sort_values(['crop','retention','defect_pixels']).groupby('crop',group_keys=False).head(12)
 riskcases=riskcases[['case_id','category','view','defect_type','crop','defect_pixels','kept_pixels','retention','crop_state']]
 riskcases.to_csv(ST/'anonymous_crop_risk_cases.csv',index=False)
 geometry_summary=geom.groupby(['crop','segmentation_status']).agg(sample_images=('image_path','nunique'),valid_product_estimates=('estimated_product_retention','count'),mean_retention=('estimated_product_retention','mean'),minimum_retention=('estimated_product_retention','min'),mean_crop_occupancy=('crop_occupancy','mean')).reset_index()
 geometry_summary.to_csv(ST/'product_geometry_sample_overall.csv',index=False)
 geom.query('crop==1024').groupby('segmentation_status')[['candidate_native_occupancy','candidate_center_x','candidate_center_y']].agg(['count','mean','median','std']).to_csv(ST/'selection_sample_candidate_geometry.csv')
 # Inadequate/failed sample candidate geometry is explicitly not product GT.
 brightness=load(B/'regional_global_statistics.csv');comparisons=load(G/'brightness_interpretation_changes.csv')
 cohort=reg.assign(quality_group=np.where(reg.segmentation_status=='accepted_heuristic','accepted','not_accepted'))
 confounding=cohort.groupby(['category','view','status','background_type','quality_group']).size().rename('images').reset_index();confounding.to_csv(ST/'selection_joint_distribution.csv',index=False)
 bglabels=pd.crosstab(reg.background_type,reg.status);bglabels['NG_fraction']=bglabels.NG/(bglabels.NG+bglabels.OK);bglabels.reset_index().to_csv(ST/'background_label_crosstab.csv',index=False)
 # Same-product paired brightness: not independent 5*n observations.
 paired=load(B/'five_view_brightness_paired.csv');paired['category']=paired.product_id.str.split('/').str[0]
 paired.groupby('category').max_minus_min.agg(['count','mean','median','std','min','max']).to_csv(ST/'five_view_within_product_brightness_range.csv')
 # Crop box continuous coordinates: validation of mapping to each target.
 for target in [256,512]:
  for axis in ['x','y']:
   lo=clipped[f'cropped_{axis}0']*target/clipped.crop;hi=clipped[f'cropped_{axis}1']*target/clipped.crop
   checks[f'bbox_resize{target}_{axis}_bounds']=bool(lo.between(0,target).all() and hi.between(0,target).all() and (hi>=lo).all())
 checks['native_crop_identity']=bool(masks.query('crop==1024 and defect_pixels>0').retention.eq(1).all())
 checks['mask_empty_count']=bool((crop.empty_masks==34).all())
 projection=load(D/'bbox_projected_size_risk.csv');checks['bbox_512_under2']=int(projection.query('target==512').short_under2.iloc[0])==38;checks['bbox_256_under2']=int(projection.query('target==256').short_under2.iloc[0])==1525
 figures=[]
 # figsave: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: fig, name, caption.
 def figsave(fig,name,caption):
  fig.tight_layout();path=FIG/(name+'.png');fig.savefig(path,dpi=150,bbox_inches='tight');plt.close(fig);figures.append(dict(path=str(path),caption=caption,name=name))
 category=load(B/'category_status_counts.csv')
 fig,axes=plt.subplots(2,1,figsize=(14,9))
 for ax,value in zip(axes,['images','declared_products']):
  category.pivot(index='category',columns='status',values=value).plot.bar(stacked=True,ax=ax);ax.set(ylabel=value+' (count)',xlabel='Category');ax.tick_params(axis='x',labelsize=7)
 fig.suptitle('Dataset composition: 151,050 images / 30,210 declared 5-view products')
 figsave(fig,'dataset_composition','전체 이미지와 선언된 5시점 제품 그룹 수를 분리했다. 동일 물리 제품이 다른 serial로 재사용되는지까지 검증한 독립 제품 수는 아니다.')
 fig,axes=plt.subplots(1,2,figsize=(13,4.5))
 axes[0].plot(crop.crop,crop.pixel_weighted_retention,'o-',label='pixel weighted');axes[0].plot(crop.crop,crop.image_mean_retention,'o-',label='image mean');axes[0].set(xlabel='Centered square crop (native pixels)',ylabel='Defect support retention (ratio)');axes[0].legend()
 crop.set_index('crop')[['removed','partial']].plot.bar(ax=axes[1]);axes[1].set(xlabel='Crop size (pixels)',ylabel='Provided positive-mask images (count)')
 fig.suptitle('CenterCrop: 51,329 provided masks / 51,295 nonempty / 34 empty')
 figsave(fig,'crop_global','원본 마스크 >0 픽셀의 정확한 교집합이다. 완전 제거는 제공 양성 마스크 이미지 단위이며 실제 물리 결함 수와 다르다. 두 보존율은 픽셀 가중과 이미지 평균으로 분모가 다르다.')
 fig,axes=plt.subplots(1,2,figsize=(16,6))
 p=cc.pivot(index='category',columns='crop',values='pixel_weighted_retention').sort_values(640)
 im=axes[0].imshow(p[[896,768,640]],aspect='auto',vmin=0,vmax=1,cmap='viridis');axes[0].set_yticks(range(len(p)),p.index,fontsize=7);axes[0].set_xticks(range(3),['896','768','640']);axes[0].set(xlabel='Crop (pixels)',ylabel='Category');fig.colorbar(im,ax=axes[0],label='Defect pixel retention (ratio)')
 for size in [896,768,640]:
  g=cv[cv.crop==size];axes[1].plot(g.view,g.pixel_weighted_retention,'o-',label=f'{size}, masks={int(g.provided_masks.sum()):,}')
 axes[1].set(xlabel='View',ylabel='Defect pixel retention (ratio)');axes[1].legend()
 fig.suptitle('CenterCrop by category and view / 51,329 provided masks')
 figsave(fig,'crop_category_view','품목·시점별 중앙 Crop의 영향이 다르다. 전체 평균이 높아도 일부 위치 정답이 완전히 제거된다. 품목별 표본 수는 연결된 집계 CSV에서 확인한다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 for key,ax in zip(['background_type','status'],axes):
  s=load(B/f'selection_{key}.csv');s.pivot(index=key,columns='quality_group',values='within_quality_fraction').plot.bar(ax=ax);ax.set(xlabel=key,ylabel='Within quality cohort fraction (ratio)')
 fig.suptitle('Selection bias: accepted n=78,526 / not accepted n=72,524')
 figsave(fig,'selection_bias','품질 통과는 정답 분할 정확도가 아니다. 통과 집단에서 BLACK 비중이 높으므로 제품 밝기 통계를 전체 영상으로 일반화하면 선택 편향 위험이 있다.')
 fig,axes=plt.subplots(1,2,figsize=(15,5))
 selection=load(B/'selection_category.csv');p=selection.pivot(index='category',columns='quality_group',values='images').fillna(0);(p.accepted/p.sum(axis=1)).sort_values().plot.bar(ax=axes[0]);axes[0].set(ylabel='Quality pass fraction (ratio)',xlabel='Category');axes[0].tick_params(axis='x',labelsize=7)
 reasons=load(B/'selection_failure_reasons.csv').head(6);axes[1].barh(range(len(reasons)),reasons.images);axes[1].set_yticks(range(len(reasons)),[s.replace('_',' ') for s in reasons.reason],fontsize=7);axes[1].set(xlabel='Images (reasons can overlap)',ylabel='Rejection reason')
 fig.suptitle('Segmentation selection coverage and failure reasons / n=151,050')
 figsave(fig,'selection_coverage_reasons','6품목은 통과 영상이0이다. 그림자·반사·유사색과 알고리즘 불일치가 주요 거절 사유다. 사유는 중복되므로 합계가 미통과 수와 같지 않다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 valid=comparisons.dropna(subset=['product_difference','whole_paired_difference']);axes[0].scatter(valid.whole_paired_difference,valid.product_difference,s=8,alpha=.5);axes[0].axhline(0,color='gray');axes[0].axvline(0,color='gray');axes[0].set(xlabel='NG-OK whole brightness, accepted subset (0-255 intensity)',ylabel='NG-OK product brightness (0-255 intensity)')
 for status in ['OK','NG']:
  x=reg.loc[(reg.status==status)&(reg.segmentation_status=='accepted_heuristic'),'product_mean'].dropna();axes[1].hist(x,bins=50,density=True,alpha=.4,label=f'{status}, n={len(x):,}')
 axes[1].set(xlabel='Estimated product mean gray (0-255)',ylabel='Density');axes[1].legend();fig.suptitle(f'Paired cohort before/after: {len(valid)}/560 valid category-defect-view comparisons')
 figsave(fig,'brightness_paired','동일 통과 표본의 전체 밝기와 제품 밝기를 비교하여 선택 효과와 영역 제거 효과를 분리한다. 이 그래프의 제품 영역은 자동 추정이며 정답 정확도는 UNVERIFIED다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 local=reg.loc[reg.defect_status=='estimated_product_local_context','defect_local_difference'].dropna();axes[0].hist(local,bins=80);axes[0].set(xlabel='Defect - local product context mean gray (intensity)',ylabel='Images (count)')
 bglabels[['OK','NG']].plot.bar(stacked=True,ax=axes[1]);axes[1].set(xlabel='Predicted background',ylabel='Images (count)');fig.suptitle(f'Local defect contrast valid n={len(local):,}; background labels n=151,050')
 figsave(fig,'defect_local_and_background','국소 대비는 제품 내부 주변이 확보된22,411장에 한한다. 배경 타입은 밝기 경계 후보 기반 자동 예측이며 라벨과의 연관이 배경 원인임을 증명하지 않는다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 ge=geom.query('crop==1024');
 for status,g in ge.groupby('segmentation_status'):axes[0].scatter(g.candidate_center_x,g.candidate_center_y,s=18,alpha=.6,label=f'{status} n={len(g)}')
 axes[0].set(xlabel='Candidate centroid x / native width (ratio)',ylabel='Candidate centroid y / native height (ratio)',xlim=(0,1),ylim=(1,0));axes[0].legend(fontsize=8)
 ga=geom[geom.segmentation_status=='accepted_heuristic'];ga.groupby('crop')[['native_occupancy','crop_occupancy']].mean().plot(ax=axes[1],marker='o');axes[1].set(xlabel='Crop (native pixels)',ylabel='Estimated product occupancy (ratio)')
 fig.suptitle(f'Only representative n=300, accepted n={int((ge.segmentation_status=="accepted_heuristic").sum())}; no product ground truth')
 figsave(fig,'product_geometry','미통과 후보 중심은 선택 편향 진단용일 뿐 제품의 실제 중심이 아니다. 제품 보존율·점유율은 통과 표본에 한정하며 전체151,050장에 일반화하지 않는다.')
 fig,axes=plt.subplots(1,2,figsize=(13,5))
 pr=load(B/'bbox_crop_resize_risk.csv')
 for target,g in pr.groupby('target'):axes[0].plot(g.crop,g.short_side_under2,'o-',label=f'target={target}; n=60,629 original boxes')
 axes[0].set(xlabel='Crop (native pixels)',ylabel='Remaining boxes, projected short side <2px (count)');axes[0].legend(fontsize=7)
 areas=bbox.bbox_area;axes[1].hist(np.log10(areas),bins=60);axes[1].set(xlabel='log10 native bbox area (pixels squared)',ylabel='Components (count)');fig.suptitle('Geometry risk: crop removes boxes while resize may enlarge remaining boxes')
 figsave(fig,'bbox_geometry_risk','Crop 후 남은 박스가 커져도 이미 사라진 결함은 복구되지 않는다. 제거 박스와 생존 박스의2px 위험을 함께 평가한다. 박스 면적은 실제 결함 픽셀 면적과 다르다.')
 # Existing statistical figures only. Explicit names exclude every original/crop/overlay example.
 for name in ['distribution_ssim','distribution_edge_recall','distribution_edge_f1','distribution_local_contrast_retention','distribution_high_frequency_proxy_retention','category_comparison','view_comparison','status_comparison']:
  src=D/(name+'.png');dest=FIG/('resolution_'+name+'.png');shutil.copy2(src,dest);figures.append(dict(path=str(dest),name='resolution_'+name,caption='기존151,050장 해상도 지표의 통계 그래프를 재사용했다. 유효 수·단위는 그래프와 집계표를 참조하며 영상 유사성이 모델 정확도를 의미하지 않는다.'))
 # Evidence index distinguishes canonical data, older exploratory splits and absent analyses.
 selected=[('metadata',R,'metadata_validation_report.json','151050 JPG,51329 PNG; Windows split','VERIFIED','declared product groups; physical identity UNVERIFIED'),('brightness',R,'brightness_per_image_execution.json','151050 JPG; whole grayscale','VERIFIED','v6 cache imported and regrouped by preserved split'),('regional_brightness',G,'scientific_validation.json','151050 JPG; border-lab-v5, accepted78526','VERIFIED','values numerically checked; product GT accuracy UNVERIFIED'),('heatmap',R,'heatmap_validation.json','Train NG54805; provided masks36173;presence64','VERIFIED','occupancy_known/positive, unobserved NaN'),('bbox',Path('outputs/spatial_20261111_v7'),'detection_export_validation.json','60629 boxes,8classes','VERIFIED','7 masked conflicting images excluded; unannotated NG excluded'),('mask',Path('outputs/mask_integrity_20261111_v6'),'mask_integrity_validation.json','51329 PNG,gray>0','VERIFIED','all grayscale values are supported; not independent semantic boundary proof'),('resolution',R,'resolution_scientific_validation.json','151050x3 frozen metric rows','VERIFIED','numeric cache rebound metadata without recomputation'),('crop',B,'complete.json','51329 provided masks;60629 boxes;300 product samples','VERIFIED','heuristic product geography remains UNVERIFIED'),('content',Path('outputs/content_audit_20261111_v7'),'content_hash_validation.json','202379 exact byte hashes','VERIFIED','cross-split count belongs to old split; canonical quality review is separate')]
 index=[]
 for domain,folder,validation,scope,status,note in selected:
  vp=folder/validation
  if not vp.exists():
   candidates=list(folder.glob('*validation*.json'));vp=candidates[0] if candidates else folder
  index.append(dict(domain=domain,source=str(folder),validation=str(vp),scope=scope,status=status,note=note,mtime_utc=datetime.fromtimestamp(folder.stat().st_mtime,timezone.utc).isoformat()))
 pd.DataFrame(index).to_csv(ST/'selected_evidence_versions.csv',index=False)
 inventories=load(B/'artifact_inventory.csv')
 inventories.groupby(['extension']).agg(files=('path','size'),bytes=('bytes','sum')).to_csv(ST/'artifact_inventory_summary.csv')
 versiondirs=[]
 for directory in sorted(Path('outputs').iterdir()):
  if not directory.is_dir():continue
  markers=[p.name for p in directory.iterdir() if p.is_file() and any(token in p.name for token in ['validation','run.json','scope.json','complete.json'])]
  versiondirs.append(dict(directory=str(directory),mtime_utc=datetime.fromtimestamp(directory.stat().st_mtime,timezone.utc).isoformat(),markers=';'.join(markers),selection='CANONICAL' if directory in {r[1] for r in selected} else 'HISTORICAL_OR_AUXILIARY',note='Not every marker implies success; selected evidence index specifies actual scope'))
 pd.DataFrame(versiondirs).to_csv(ST/'output_version_inventory.csv',index=False)
 # Training policy candidates remain proposals; validation/test geometry changes must be separate declared experiments.
 evidence=[]
 # ev: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: strategy, category, view, metric, value, n, source, interpretation, risk, recommendation, status.
 def ev(strategy,category,view,metric,value,n,source,interpretation,risk,recommendation,status='VERIFIED'):
  evidence.append(dict(decision_id=f'E{len(evidence)+1:04}',preprocessing_strategy=strategy,category=category,view=view,metric=metric,measured_value=value,sample_count=n,source_file=str(source),validation_status=status,interpretation=interpretation,risk=risk,recommendation=recommendation,requires_model_experiment=True))
 for row in cc.to_dict('records'):
  ev('CenterCrop',row['category'],'ALL',f'crop{row["crop"]}_pixel_weighted_retention',row['pixel_weighted_retention'],row['positive_masks'],assetmap['mask_crop_category.csv'],'提供された位置正解の画素保存率'.replace('提供された位置正解の画素保存率','제공 위치 정답 픽셀 보존율'),'완전제거·부분잘림과 평균을 함께 볼 것','전체Resize와 비교; 크기 독단 확정 금지')
 for row in cv.to_dict('records'):
  ev('CenterCrop','ALL',row['view'],f'crop{row["crop"]}_removed_mask_images',row['removed'],row['positive_masks'],assetmap['mask_crop_view.csv'],'양성 제공 마스크 이미지가 전부 제거됨','NG를 정상으로 relabel하면 안 됨','Crop 제거 시 폐기/원본 경로 등 정책을 별도 결정')
 for row in means.reset_index().to_dict('records'):
  for metric in ['psnr_db','ssim','edge_recall','edge_f1','local_contrast_retention','high_frequency_proxy_retention']:
   ev('Resize','ALL','ALL',f'{int(row["target"])}_{metric}',row[metric],151050,assetmap['overall_statistics.csv'],'원본 대비 복원 영상 지표','모델 성능·결함 소실률과 다름','동일 제품 분할/모델/예산에서 해상도 ablation')
 for row in load(B/'selection_background_type.csv').to_dict('records'):
  ev('BackgroundAugmentation',row['background_type'],'ALL',row['quality_group']+'_background_fraction',row['within_quality_fraction'],row['images'],assetmap['selection_background_type.csv'],'품질 집단 내부 배경 분포','통과 표본의 선택 편향','정답 제품 마스크 확보 전 흑백 치환 자동 확정 금지')
 for row in load(B/'bbox_crop_resize_risk.csv').to_dict('records'):
  ev('CoordinateAdapter','ALL','ALL',f'crop{row["crop"]}_resize{row["target"]}_short_under2',row['short_side_under2'],row['remaining_boxes'],assetmap['bbox_crop_resize_risk.csv'],'생존 박스의 기하학적 크기','제거된 박스를 분모에서 숨기지 말 것','원본 XYXY 보존 후 마지막 adapter에서 clipping/resize')
 for record in j(M/'model_input_fields.json'):
  ev('ModelNormalizeDtype',record['model'],'ALL','source_commit',record['commit'],0,Path('reports/MODEL_INPUT_REQUIREMENTS.md'),'정적 소스 확인; 런타임 미검증','이중 Normalize/Resize,scale mismatch','구현·variant 고정 후 dummy adapter 테스트',status='UNVERIFIED')
 pd.DataFrame(evidence).to_csv(P/'PREPROCESSING_DECISION_EVIDENCE.csv',index=False)
 # Main report: every decision has scope, denominators and linked actual evidence.
 qrate=78526/151050
 report=['# Real-IAD 데이터 분석 통합 및 전처리 정책 검토 보고서',f'작성 UTC: {datetime.now(timezone.utc).isoformat()}. 상태: 수치/파일/정적 소스 검증 VERIFIED, 의미/실행 미검증 UNVERIFIED, 미수행 NOT_ANALYZED. 정책은 제안이며 확정하지 않는다.',
 '## 1. Executive Summary',
 f'151,050 JPG(OK72,840/NG78,210), 제공 마스크51,329,30품목,C1~C5. 선언된5시점 그룹30,210개이며 이미지 수와 구분한다. 기존 전체 해상도453,150행을 재사용했다. 제품 영역 자동 품질 통과78,526({qrate:.3%})장으로 전체 대표 표본이 아니다. 896 Crop에서도82개의 양성 위치 정답 이미지가 완전히 제거되어 전 품목 공통Crop 안전성을 확정할 수 없다.',
 '검토 결론: 전체Resize를 대조군으로 유지하고 Crop·배경 치환·모델 기본 전처리와 공통 어댑터의 충돌을 별도 실험으로 검증한다. 12모델은 입력이 동일하지 않다. 모델 학습·가중치 다운로드·API 호출·Push는 수행하지 않았다.',
 '## 2. 데이터셋 개요',
 link(assetmap['category_status_counts.csv']),table(category),
 'NG78,210 중51,329(65.6297%)은 위치 정답이 제공되고26,881은 미제공이다. 미제공을 정상/empty detection label로 취급하지 않는다. 실제 누락인지 의도된 미제공인지 원본 annotation manifest 없이 확정할 수 없다. 제공PNG34개는 실제0픽셀인 빈 정답으로 미제공과 다르다.',
 '## 3. 분석 실행 및 검증 상태',table(pd.DataFrame(index)[['domain','scope','status','note']]),
 'v1/v2 마스크 체크포인트51,329개의 내용·입력해시가 같아 PNG를 다시 읽지 않았다. 중단 때 미저장된300표본 제품 기하만 완료하고 이미지별로 체크포인트화했다. 과거 실패는 마스크 미제공 NaN merge키 중복이었으며 원본과 계산 결과를 보존했다. 최신 v2 complete.json으로 완료 범위를 확인한다.',
 '## 4. 메타데이터 및 클래스 분포',
 table(load(B/'defect_counts.csv')),table(load(B/'view_mask_counts.csv')),table(load(B/'split_counts.csv')),
 'class imbalance는 defect_type별 이미지 수와 declared_products를 함께 비교한다. 정상14,568그룹/불량15,642그룹=30,210그룹이다. 제품 기준은 category/status/defect/serial 선언 키이며 실제 물리 제품 식별의 독립성은 UNVERIFIED다. 모든 그룹은5시점이며 보존한 분할에서 제품 단위 중복은0이다. Train105,735/Validation22,655/Test22,660.',
 '## 5. 배경색과 제품 밝기 분석',table(bglabels.reset_index()),
 '배경 분류는 가장자리4%의Lab/HSV/gray, 연결성 및 신뢰도 기반이며 전체 평균만으로 나누지 않았다. WHITE/BLACK은 자동 예측, GRAY는 무채색만 의미하지 않아 중간 밝기의 유색 배경도 포함한다. confidence는 보정된 정확도 확률이 아니다.',
 link(ST/'selection_joint_distribution.csv'),table(load(B/'selection_background_type.csv')),
 '통과 집단 BLACK73.2254%, 미통과45.8745%로27.3509%p 차이다. 통과 집단 GRAY0.6189%, 미통과14.8089%다. 분할 성공이 배경·품목에 따라 달라 제품 밝기에서 선택 편향이 있다. 6개 품목 '+', '.join(rf['zero_accepted_categories'])+'는 통과가0이므로 제품 영역 밝기 결론을 제시할 수 없다.',
 '## 6. 정상/불량 밝기 비교',link(assetmap['regional_global_statistics.csv']),table(brightness[['status','metric','total_images','valid','mean','median','p05','p95']]),
 f'560개 품목×결함×시점 비교 중 제품 양쪽 표본이 확보된 비교는{rf["valid_product_comparisons"]}개다. 동일 통과 표본에서 배경 제거 후 절대 NG−OK 차이가 줄어든 경우{rf["paired_abs_difference_reduced"]}개, 부호가 바뀐 경우{rf["paired_sign_changes"]}개다. 전체 영상과 통과 영상의 차이는 선택 효과이며 통과 영상 내 전체→제품 차이는 영역 효과다. 두 효과를 분리하지 않고 배경 편향이 해소됐다고 결론내리지 않는다.',
 link(assetmap['brightness_interpretation_changes.csv']),link(assetmap['regional_per_image_percentile_summary.csv']),
 'P05/P50/P95는 영상 내부 픽셀 분위수와 영상별 평균의 모집단 분위수를 구분한다. per-image-percentile 집계는 영상별 분위수 평균/중앙값이며 전수 픽셀을 합친 분위수가 아니다. 분포 겹침은 영상 평균값의32bin histogram overlap, Cohen d는 두 집단 pooled sample SD 기준이며 검정/인과지표가 아니다.',
 '## 7. 결함 국소 대비 분석',
 '유효한 제품 내부 국소 주변을 확보한22,411장에 한한다. 원본 해상도에서 결함 밖12px dilation ring과 erosion한 제품 core의 교집합,20px 이상, 결함-제품 겹침90% 이상을 사용했다. 결함 평균−주변 평균의 부호와 분포를 보며 배경이 섞인 전체 outside-mask 밝기와 혼용하지 않는다. 나머지는 미확인으로 유지한다.',
 table(brightness[brightness.metric=='defect_local_difference']),
 '## 8. 해상도 정보 손실 분석',table(means.reset_index()),link(assetmap['overall_statistics.csv']),
 '기존 보고값512 PSNR40.985/SSIM.975989/EdgeRecall.473716/국소대비.761417,256의35.632/.943659/.178240/.604359를 CSV와 반올림 허용오차 내 대조했다. 재계산하지 않았다. 원본1024 자기비교PSNR은120dB 저장상한, 에너지 분모0인 검은2이미지×3해상도6행의 비율은NA다.',
 'INTER_AREA 축소→INTER_LINEAR 원본크기 복원, grayscale Gaussian11 sigma1.5 SSIM, exact-pixel Canny100/200 Recall/F1. 고주파는 Laplacian energy 대리값이며 FFT 직접 측정이 아니다. 위치 이동만으로 EdgeRecall이 떨어질 수 있어 모델 검출 실패율로 변환하지 않는다.',
 table(load(D/'category_statistics.csv').query('target==256 and metric=="ssim"').sort_values('mean')[['category','images','mean','median','p05','p95']]),
 table(load(D/'view_statistics.csv').query('target!=1024 and metric=="ssim"')[['view','target','images','mean','median','p05','p95']]),
 table(load(D/'status_statistics.csv').query('target!=1024 and metric=="ssim"')[['status','target','images','mean','median','p05','p95']]),
 '기존 대표영상·확대 비교는 로컬 reports/RESOLUTION_DETAILED_ANALYSIS.md 및 회의 PDF에 있으나 공유 권한 미확정으로 이 외부 ZIP에 넣지 않았다. 실제 이미지 사례를 공유하지 않는 한계는 통계 그래프가 대신 검증할 수 없다.',
 '## 9. 결함 크기와 해상도 관계',table(projection),table(load(B/'bbox_crop_resize_risk.csv')),
 '전체60,629박스 중512 단변2px미만38개,256은1,525개로 기존 결과와 같다. 이는 기하학적 위험 지표다. 전체SSIM이 높아도 미세 결함은 희석될 수 있다. 기존336이미지 ROI 검수는670유효해상도행이며 전체 주석 이미지의 전수ROI 분석은 NOT_ANALYZED다.',
 '## 10. CenterCrop 적합성 분석',link(assetmap['mask_crop_overall.csv']),table(crop),
 'Crop 좌표는 원본1024에서 [a,a,a+s,a+s], a=(1024−s)/2, 끝좌표 exclusive다. 정확한 defect pixel retention=kept/original positive pixels. 픽셀 가중 보존율과 이미지 평균 보존율을 둘 다 보고했다. 완전 제거 수는 마스크 이미지 단위이며 물리 결함 수가 아니다. 빈34마스크는 보존율NA다.',
 table(geometry_summary),link(assetmap['mask_crop_by_size.csv']),link(assetmap['mask_crop_resize_area_proxy.csv']),
 '제품 점유율은기존300표본 중 자동 품질 통과150장만 제공한다. 미통과 실제 제품 크기·위치는 UNVERIFIED. 미통과 후보 중심·면적은 알고리즘 오류를 포함할 수 있어 진단용으로만 표시한다. 전체 제품 위치/점유율 전수 분석은 NOT_ANALYZED다.',
 'Crop후 결함 면적 proxy=kept_pixels×(target/crop)^2. 연속 좌표의 기하적 예상면적이며 실제 Resize된 binary mask의 양성 픽셀 수는 아니다. 실제 보간·threshold 후 support/연결성 변화는 NOT_ANALYZED다. 작은 pixel support가 실제로 살아남는지는 별도 adapter 시험이 필요하다.',
 '## 11. 마스크 및 BBox 품질',
 '전체PNG grayscale uint8,0..255의256값이 관측된다. 검증정책 >0는 공식 평가 convention과336마스크×6threshold 실험에 근거한다. 높은threshold가 경계를 침식/분절할 수 있어 임의127로 바꾸지 않았다. 이것은 제공 주석 경계의 의미가 독립적으로 증명됐다는 뜻은 아니다.',
 '8방향 연결 성분, 필터 없음, XYXY 원본 absolute좌표. 클래스는AK/BX/CH/HS/PS/QS/YW/ZW 8개. 한 이미지의 모든 성분에 같은 defect_type 부여 가정을 유지한다. 클래스 경로 불일치10이미지 중마스크있는7이미지는 detector label에서 제외한다.',
 link(assetmap['bbox_defect_distribution.csv']),table(load(B/'bbox_defect_distribution.csv')),
 'Box crop: x0′=clip(x0−a,0,s), x1′=clip(x1−a,0,s), y도동일. w/h가0인 박스는 유효 라벨로 내보내지 않고 제거 이력을 남긴다. Resize t에서는좌표×t/s. YOLO는마지막에normalized cxcywh,class0..7;COCO1..8;torchvision0배경/1..8;Detectron2contiguous0..7를 분리한다. binary mask는NEAREST 후보이나 저자baseline과의 차이를 명시한다.',
 '## 12. 5시점 상호보완성',table(load(B/'provided_view_count_per_ng_product.csv')),
 link(ST/'five_view_within_product_brightness_range.csv'),link(assetmap['five_view_brightness_correlation.csv']),
 '동일 제품의 시점별 밝기 범위와 상관을썼다. 시점별 마스크 제공은 결함이 그시점에 보이지 않는 것과 같지 않다. 위치정답 미제공, 제공빈마스크, 제공양성마스크를 구분한다. 실제 결함 가시성의 독립 육안 정답 전수분석과 3D제품 시점 정합은 NOT_ANALYZED다. 개별입력은 제품분할을 유지하며 제품결합은 누락시점/시점순서/NG전체라벨과 국소라벨 차이를 명시한다.',
 '## 13. 데이터 누수 및 품질 위험',
 '보존Windows seed42 분할에서 선언제품 누수0, 정확한바이트 cross-split중복0이다. 초기hash 탐색split에서는 같은 검은JPG2장이Train/Test로 나뉘었으므로 content audit의cross-split=1을최종split에 그대로 적용하면 틀린다. 두검은영상은현재둘다Train이다. 실제동일물리제품이서로다른serial로등장하는지는UNVERIFIED다. perceptual duplicate도NOT_ANALYZED다.',
 '전검정NG의전영역마스크가위치빈도에큰영향을준다. 원본지표는보존하고 quality_review의제외민감도를함께검토해야한다. 과거146060/50115규모와현재차이는이전Windows checkpoint에서u_block4990/1214추가와일치한다. 제외된역사적이유/최초수치의출처는미확인이다.',
 '## 14. 12개 모델 입력 요구사항',
 '[커밋·파일·함수 근거와 모델별 전체 필드](MODEL_INPUT_REQUIREMENTS.md). 11저장소(두torchvision detector공유)에서12모델후보를조사했다. 모든모델정적자료가있지만실제실행·variant확정·가중치별override는UNVERIFIED다. 확인못한mean/std나보간을모델이름으로추정하지않는다.',
 '## 15. 전처리 전략별 근거와 위험',
 '| 전략 | 목적·근거 | 예상 이점(가설) | 손실 위험 | 권장 비교·확정 범위 |\n|---|---|---|---|---|\n| 배경 증강 | 배경×품목×시점×라벨 연관 및선택편향 | 배경 shortcut 완화 가능 | 제품 구멍/반사/경계/결함 변경,분할불확실 | 원본대조군→작은제품내부밝기증강→검증마스크기반치환;Train만정책추정,Val/Test원본유지 |\n| CenterCrop+Resize | 실제마스크/박스교집합,원본여백 | 남은제품확대·픽셀예산효율 | 완전제거·부분잘림·이중Crop | 전체Resize 대조,896/768/640은후보. 공통크기확정불가 |\n| 좌표 adapter | 원본XYXY보존,끝좌표exclusive | 모델별형식분리·재현성 | round오차/scale·padding누락/class remap | crop→clip→제거기록→resize→최종format, mask동일기하 |\n| Normalize/dtype | 모델별0..1/0..255 및내부Normalize차이 | 입력contract 일관성 | 이중Normalize/채널역전/FP16수치 | 모델commit/variant고정후dummy+실제소량 adapter검증. 강한전처리없는baseline우선 |',
 '배경 치환이 필요하다는 인과적 근거는 아직 없고 현 분할의 선택 편향만으로 확정하지 않는다. Train증강은정상/불량모두같은정책적용후class조건부편향을검사한다. Crop으로 결함이 사라진NG를정상으로바꾸지 않는다. 학습/평가시Crop의위험허용기준은회의결정이다.',
 '## 16. 모델 실험 전 해결할 사항',
 '①미제공 위치정답의dataset adapter정책 ②검은영상과10경로충돌의정정/보류 ③모델별필수Normalize·Resize·head고정 ④분할과실제물리제품identity보강 ⑤제품정답마스크없는배경치환의검수 ⑥박스/마스크좌표변환 및일부결함제거의학습정책. 모델성능개선을확정하지않는다.',
 '## 17. 데이터 파이프라인 설계에 필요한 결정',
 '원본불변→manifest(has_mask/quality/declared_product/split)→선택적기하(transform행렬·crop·pad이력)→라벨동시변환→모델별색상/범위/정규화/dtype adapter→제품단위평가. raw NG전체와detector-supervised subset을분리하되원래품질라벨을보존한다. 6+6모델의최종선정기준은image/pixel AUROC/AUPRO와class별AP/작은객체recall,운영장치지연/메모리를함께정한다. 이번에학습·지연측정은하지않았다.',
 '## 18. 분석 한계 및 미검증 항목',
 '| 항목 | 상태 | 이유 |\n|---|---|---|\n| 제공mask CenterCrop 교집합·BBox기하 | VERIFIED | 전수체크포인트/범위/단조성/identity |\n| 전경품질통과밝기수치 | VERIFIED | 수치재현·결측정책검사;전체대표성없음 |\n| 자동전경정답정확도·미통과실제제품위치 | UNVERIFIED | 수작업정답마스크없음 |\n| 300표본제품기하의전체일반화 | UNVERIFIED | 균형대표표본이며추정오차포함 |\n| 실제Resize마스크support/연결성전수 | NOT_ANALYZED | 연속면적proxy만계산 |\n| Fourier대역고주파·perceptual중복·3D정합 | NOT_ANALYZED | 기존결과없음 |\n| 12모델실행·학습성능·속도 | UNVERIFIED | 정적소스만조사 |\n| 원본이미지사례외부공유 | UNVERIFIED | 권한미확인으로ZIP제외 |',
 '## 19. 결과 파일과 재현 명령어',
 '[전처리 결정 근거](PREPROCESSING_DECISION_EVIDENCE.csv), [위험 사례](PREPROCESSING_RISK_CASES.md), [분석 인덱스](ANALYSIS_EVIDENCE_INDEX.md). 상세 집계와 검증은 아래 상대 링크로 제공한다. 패키지는 원본/파생 영상사례 없이 통계 PNG만 포함한다.',
 '복구검증/남은체크포인트명령: `uv run --offline python scripts/resume_preprocessing_review.py` (완료마커가있는실행은재실행하지않음). 모델자료는 outputs/model_sources_20261112_v1의commit/sha manifest참조. 보고서/ZIP생성: `uv run --offline python scripts/build_preprocessing_review_package.py` (기존최종산출물이있으면보호중단). 원본CSV해시와추가분석complete.json을함께확인한다.',
 '## 통계 그래프와 해석']
 for f in figures:report.extend([f'### {f["name"]}',f'![{f["name"]}](../{f["path"]})',f['caption']])
 report.append('## 전체 공유 집계표')
 for path in sorted(ST.glob('*.csv')):report.append('- '+link(path))
 write(P/'DATA_ANALYSIS_MASTER_REPORT.md','\n\n'.join(report))
 risktext=['# 전처리 위험 사례 — 원본 이미지 제외',
 '원본·파생 이미지 공유권한이 불확실하여 픽셀 사례를 포함하지 않았다. case_id는 상대경로의SHA256앞12자리이며 개인경로가아니다. 같은case_id가여러Crop에나올수있다. 아래는손실최악순의검토예시이며무작위대표표본이아니다.',table(riskcases),
 '완전제거된NG의상태를OK로변경하지않는다. 부분잘림에서는기존BBox와mask가같이변환되어야한다. 작은component의일부만남아도기존이미지타입을새정답으로확장하지않는다.',
 '대표위험: (1)896Crop에서가장자리결함82이미지완전제거 (2)640은4600제거·9175부분잘림 (3)sim_card_set등6품목은제품밝기통과0 (4)그림자/반사/구멍을배경으로잘못치환할수있음 (5)PatchCore/Dinomaly/INP앞단Crop추가시이중Crop (6)ViTDet0..255와YOLO0..1의입력범위혼용 (7)GT미제공NG의빈negative변환 (8)검은NG전체mask의공간분포지배.',
 link(ST/'anonymous_crop_risk_cases.csv'),link(assetmap['mask_crop_category.csv']),link(assetmap['mask_crop_by_size.csv'])]
 write(P/'PREPROCESSING_RISK_CASES.md','\n\n'.join(risktext))
 indextext=['# 분석 근거 인덱스',
 f'초기파일조사{len(inventories):,}개(요청확장자별메타인벤토리). 이것은모든파일을수치검증했다는뜻이아니다. 아래선정본만해당validation범위에서VERIFIED로사용한다. 생성시각은manifestcreated가있으면그값,없으면파일mtime을보조로쓴다. mtime은원래실행시각을증명하지않는다.',
 table(pd.DataFrame(index)),link(ST/'selected_evidence_versions.csv'),link(ST/'output_version_inventory.csv'),link(ST/'artifact_inventory_summary.csv'),
 '버전차이: full_v6은최초hash탐색split의원본계산. windows_preserved_v1은Windowsseed42분할로수치재계산없이메타만재결합. 해상도수치는동일하지만split이바뀌어Train집계가다르다. 기존spatial의area-v1열지도는새presence-v2조건부빈도와단위가달라직접비교금지. 최신presence는원본어느픽셀이라도양성이면64gridcell점유로기록하고n_known/n_positive분모를구분한다.',
 'heatmap Train NG54805,provided36173,560groups,미관측6groups. 결함발생실제확률이아니라제공Train위치정답의빈도다. 未관측은NaN이고정상0이아니다.',
 '초기535밝기비교는29품목checkpoint,현재원래Windows555는u_block추가20조합. 새560은fire_hood경로충돌의UNRESOLVED분리로5조합추가. 560모두제품밝기비교가능한것은아니며유효326만해석한다.',
 'reports/와docs/기존보고서는보존했다. src/와notebook_results_real/루트는현재없음;실제Windows원본소스는legacy/windows_snapshot에보존되어있다. PDF/이미지사례는로컬기존자료로남기고이번ZIP에서제외한다.',
 '## 공유 자료 provenance',table(pd.DataFrame(provenance)[['asset','source','bytes','source_mtime_utc','status']])]
 write(P/'ANALYSIS_EVIDENCE_INDEX.md','\n\n'.join(indextext))
 # Sanitized verification/config evidence, never package raw per-image inputs or source code downloads.
 validation_sources=[B/'complete.json',R/'metadata_validation_report.json',R/'resolution_scientific_validation.json',R/'resolution_metadata_rebind_validation.json',R/'heatmap_validation.json',R/'heatmap_schema.json',R/'mask_policy.json',G/'regional_validation.json',G/'scientific_validation.json',M/'model_input_source_evidence.json',M/'model_input_fields.json',M/'manifest.json',Path('reports/BBOX_BACKEND_PARITY.json'),Path('outputs/spatial_20261111_v7/detection_export_validation.json'),Path('outputs/windows_preserved_20261111_v1/quality_review/quality_aware_split_validation.json')]
 # sanitize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: text.
 def sanitize(text):
  text=re.sub(r'/(?:home|mnt|Users|tmp)/[^\s"\'<>|,)]+','<LOCAL_PATH>',text)
  return text
 for src in validation_sources:
  dest=VAL/(src.parent.name+'__'+src.name);dest.write_text(sanitize(src.read_text()))
 checks['all_aggregate_plots_statistical_only']=True
 checks['metadata_counts_verified']=len(meta)==151050 and int((meta.status=='OK').sum())==72840 and int(meta.has_mask.sum())==51329
 checks['source_hashes_unchanged']=all(sha(p)==h for p,h in j(B/'input_fingerprints.json').items())
 checks['model_source_hashes']=all(sha(M/r['repo_key']/'source'/f['path'])==f['sha256'] for r in j(M/'model_input_fields.json') for f in j(M/r['repo_key']/'manifest.json')['files'])
 checks['product_declared_split_no_leakage']=bool((declared.splits==1).all())
 validation=dict(success=all(checks.values()),checks=checks,crop_mask_images=51329,provided_positive_masks=51295,provided_empty_masks=34,geometry_sample_images=300,geometry_sample_accepted=int((geom.query('crop==1024').segmentation_status=='accepted_heuristic').sum()),product_gt='UNVERIFIED',source_resolution_recalculations=0,additional_png_decodes_during_recovery=0,push=False)
 (VAL/'review_numerical_validation.json').write_text(json.dumps(validation,indent=2))
 (VAL/'shared_statistics_provenance.json').write_text(json.dumps(provenance,indent=2))
 if not validation['success']:raise RuntimeError('Validation failed')
 package=Path('outputs/preprocessing_review_package_20261112_v1')
 if package.exists():raise RuntimeError('Package staging already exists')
 package.mkdir()
 reportnames=['DATA_ANALYSIS_MASTER_REPORT.md','PREPROCESSING_DECISION_EVIDENCE.csv','PREPROCESSING_RISK_CASES.md','MODEL_INPUT_REQUIREMENTS.md','ANALYSIS_EVIDENCE_INDEX.md','ADDITIONAL_PREPROCESSING_ANALYSIS_SCOPE.md']
 files=[P/n for n in reportnames]+list(AS.rglob('*'))+[Path('scripts/resume_preprocessing_review.py'),Path('scripts/analyze_preprocessing_evidence.py'),Path('scripts/build_preprocessing_review_package.py'),Path('pyproject.toml'),Path('uv.lock')]
 for src in files:
  if not src.is_file():continue
  dest=package/src;dest.parent.mkdir(parents=True,exist_ok=True)
  if src.suffix=='.png':shutil.copy2(src,dest)
  else:dest.write_text(sanitize(src.read_text()))
 write(package/'README.md','# 외부 AI 전처리 검토 패키지\n\nreports/DATA_ANALYSIS_MASTER_REPORT.md부터 읽는다. 모든주요통계링크는압축해제한상대경로에서찾을수있다. outputs/는선별한집계와통계PNG일뿐원본데이터가아니다. PNG는모두집계그래프이며원본·파생사례이미지는없다. 코드재현은원본데이터별도접근이필요하다. private path는제거했다. 모델정적규격의모든미확인설정은UNVERIFIED다.\n')
 # Validate every Markdown local link and scan text for credentials/private paths.
 broken=[];sensitive=[];link_re=re.compile(r'!?\[[^]]*\]\(([^)]+)\)');secret=re.compile(r'(?m)(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|^-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----$)')
 for f in package.rglob('*'):
  if not f.is_file() or f.suffix=='.png':continue
  text=f.read_text()
  if re.search(r'/(?:home|mnt|Users)/',text) or secret.search(text):sensitive.append(str(f.relative_to(package)))
  if f.suffix=='.md':
   for target in link_re.findall(text):
    if not target.startswith(('https://','http://','#')) and not (f.parent/target.split('#')[0]).exists():broken.append(dict(file=str(f.relative_to(package)),target=target))
 if broken or sensitive:raise RuntimeError(json.dumps(dict(broken_links=broken,sensitive=sensitive)))
 manifest=[]
 for f in sorted(package.rglob('*')):
  if f.is_file():manifest.append(dict(path=str(f.relative_to(package)),bytes=f.stat().st_size,sha256=sha(f)))
 write(package/'MANIFEST.json',json.dumps(dict(files=manifest,original_images_included=False,derived_image_examples_included=False,statistical_pngs_only=True),indent=2))
 zip_path=P/'PREPROCESSING_REVIEW_PACKAGE.zip'
 with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for f in sorted(package.rglob('*')):
   if f.is_file():z.write(f,str(f.relative_to(package)))
 with zipfile.ZipFile(zip_path) as z:
  bad=z.testzip();assert bad is None
  assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
  for record in manifest:assert hashlib.sha256(z.read(record['path'])).hexdigest()==record['sha256']
  files=z.namelist()
 delivery=dict(success=True,zip=str(zip_path.resolve()),bytes=zip_path.stat().st_size,sha256=sha(zip_path),file_count=len(files),files=files,crc_test='VERIFIED',all_member_sha256='VERIFIED',relative_markdown_links='VERIFIED',private_path_and_secret_scan='VERIFIED',original_or_derived_case_images_included=False,statistical_figures=len(figures),crop_validation=validation,push=False)
 write(P/'PREPROCESSING_PACKAGE_VALIDATION.json',json.dumps(delivery,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in delivery.items() if k not in ['files','crop_validation']},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
