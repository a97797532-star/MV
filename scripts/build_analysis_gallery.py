# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Publish selected derived figures and aggregate evidence; never copy raw dataset or weights."""
import argparse,json,os,sys,shutil
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mv_analysis.core import read_image,binary_mask,save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--image-run',type=Path,required=True);p.add_argument('--spatial-run',type=Path,required=True);p.add_argument('--preserved-run',type=Path,required=True);p.add_argument('--background-run',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--categories',nargs='+');a=p.parse_args()
if a.output.exists():raise SystemExit('Gallery output exists; choose a fresh directory')
a.output.mkdir(parents=True);meta=pd.read_csv(a.preserved_run/'image_metadata_with_split.csv',keep_default_na=False);root=Path(json.loads((a.image_run/'run.json').read_text())['config']['root']);policy=json.loads((a.spatial_run/'mask_policy.json').read_text());boxes=pd.read_csv(a.spatial_run/'defect_bboxes.csv');box_index={k:g for k,g in boxes.groupby('image_path')};b=pd.read_csv(a.preserved_run/'brightness_per_image.csv');heat=pd.read_csv(a.preserved_run/'heatmap_summary.csv');known=np.load(a.preserved_run/'occupancy_known.npy');presence=np.load(a.preserved_run/'presence_count.npy');keys=json.loads((a.preserved_run/'heatmap_groups.json').read_text());manifest=[]
resolution=pd.read_csv(a.image_run/'per_view_information_loss.csv') if (a.image_run/'per_view_information_loss.csv').exists() else None
regional=pd.read_csv(a.background_run/'regional_brightness_per_image.csv') if a.background_run and (a.background_run/'regional_brightness_per_image.csv').exists() else None
for folder in ['category_cases','category_profiles','heatmaps','figures','tables']:(a.output/folder).mkdir()
for category,group in meta.groupby('category',sort=True):
 if a.categories and category not in a.categories:continue
 fig,axes=plt.subplots(2,5,figsize=(16,7),squeeze=False);selected=[]
 for axesrow,status in zip(axes,['OK','NG']):
  options=group[group.status==status].groupby('product_id').agg(mask_count=('has_mask','sum'),views=('view','nunique'));options=options[options.views==5];product=options.sort_values(['mask_count'],ascending=False,kind='stable').index[0];capture=group[group.product_id==product].sort_values('view')
  for ax,row in zip(axesrow,capture.to_dict('records')):
   im=read_image(root/row['image_path']);display=im.copy();nboxes=0;annotation='normal_OK' if status=='OK' else 'not_provided'
   if status=='NG' and row['mask_path']:
    mask=binary_mask(read_image(root/row['mask_path'],True),policy)>0;annotation='provided_positive' if mask.any() else 'provided_empty'
    if row.get('label_conflict'):annotation='provided_mask_unresolved_class'
    tint=np.zeros_like(im);tint[:]=[0,0,255];display[mask]=cv2.addWeighted(im,.45,tint,.55,0)[mask]
    for box in box_index.get(row['image_path'],pd.DataFrame()).itertuples():cv2.rectangle(display,(int(box.x0),int(box.y0)),(int(box.x1)-1,int(box.y1)-1),(0,255,0),3);nboxes+=1
   label='mask not provided' if annotation=='not_provided' else 'unresolved defect class' if annotation=='provided_mask_unresolved_class' else f'boxes={nboxes}, {annotation}'
   ax.imshow(cv2.cvtColor(display,cv2.COLOR_BGR2RGB));ax.set_title(f'{status}/{row["view"]} '+(f'{row["defect_type"]}\n{label}' if status=='NG' else 'normal'));ax.axis('off');selected.append(dict(image_path=row['image_path'],status=status,view=row['view'],has_mask=row['has_mask'],annotation_status=annotation))
 fig.suptitle(f'{category}: same capture across C1-C5; red=provided mask, green=component bbox');fig.tight_layout();path=a.output/'category_cases'/f'{category}.png';fig.savefig(path,dpi=110);plt.close(fig);manifest.append(dict(path=str(path),kind='category_five_view_case',category=category,source_run=str(a.preserved_run),selected_images=selected,interpretation='One OK and one annotated NG capture; examples are not population frequencies'))
 fig,axes=plt.subplots(1,5,figsize=(16,3.5))
 for ax,view in zip(axes,['C1','C2','C3','C4','C5']):
  idx=[i for i,k in enumerate(keys) if k[0]==category and k[2]==view];n=int(heat.iloc[idx].n_known.sum());array=presence[idx].sum(0)/n if n else np.full((64,64),np.nan)
  im=ax.imshow(np.ma.masked_invalid(array),vmin=0,vmax=max(.01,float(np.nanmax(array))) if n else 1,cmap='magma');ax.set_title(f'{view}: known masks N={n}');ax.set(xlabel='x / width',ylabel='y / height');fig.colorbar(im,ax=ax,label='Cell presence frequency')
 fig.suptitle(f'{category}: Train only, preserved Windows split, >0 mask; per-view scales differ');fig.tight_layout();path=a.output/'heatmaps'/f'{category}.png';fig.savefig(path,dpi=110);plt.close(fig);manifest.append(dict(path=str(path),kind='category_heatmaps',category=category,source_run=str(a.preserved_run),interpretation='View-wise provided-mask cell presence; unobserved groups are NaN, not normal; pooled defect types'))
 fig,axes=plt.subplots(2,3,figsize=(15,9));part=b[b.category==category]
 for status,data in part.groupby('status'):axes[0,0].hist(data.brightness,bins=np.linspace(0,256,33),density=True,alpha=.5,label=status)
 axes[0,0].set(title='Whole-image mean brightness',xlabel='Gray intensity [0,255]',ylabel='Density');axes[0,0].legend()
 means=part.groupby(['view','status']).brightness.mean().unstack();means.plot.bar(ax=axes[0,1]);axes[0,1].set(title='Whole brightness by view',ylabel='Mean intensity',xlabel='View');axes[0,1].tick_params(axis='x',rotation=0)
 catboxes=boxes[boxes.category==category];axes[0,2].hist(np.log10(catboxes.bbox_area.clip(lower=1)),bins=30);axes[0,2].set(title=f'Connected-component bbox area, N={len(catboxes)}',xlabel='log10(area / native px²)',ylabel='Boxes')
 if resolution is not None:
  rr=resolution[(resolution.category==category)&(resolution.target!=1024)]
  for target,data in rr.groupby('target'):
   summary=data.groupby('view')[['ssim','edge_recall']].mean();axes[1,0].plot(summary.index,summary.ssim,marker='o',label=str(target));axes[1,1].plot(summary.index,summary.edge_recall,marker='o',label=str(target))
  axes[1,0].set(title='Reconstructed JPG SSIM',ylabel='Mean SSIM',xlabel='View');axes[1,1].set(title='Exact-pixel edge recall',ylabel='Mean Canny edge recall',xlabel='View');axes[1,0].legend();axes[1,1].legend()
 else:
  for ax in axes[1,:2]:ax.text(.5,.5,'Full resolution analysis incomplete',ha='center',transform=ax.transAxes);ax.set_axis_off()
 if regional is not None:
  subset=regional[(regional.category==category)&(regional.segmentation_status=='accepted_heuristic')]
  for status,data in subset.groupby('status'):axes[1,2].hist(data.product_mean,bins=np.linspace(0,256,33),density=True,alpha=.5,label=status)
  axes[1,2].set(title=f'Product mean: heuristic subset N={len(subset)}',xlabel='Intensity',ylabel='Density');axes[1,2].legend()
 else:axes[1,2].text(.5,.5,'Full regional analysis incomplete',ha='center',transform=axes[1,2].transAxes);axes[1,2].set_axis_off()
 fig.suptitle(f'{category}: measured distributions; examples do not imply model performance');fig.tight_layout();path=a.output/'category_profiles'/f'{category}.png';fig.savefig(path,dpi=115);plt.close(fig);manifest.append(dict(path=str(path),kind='category_profile',category=category,source_run=str(a.image_run),resolution_complete=resolution is not None,regional_complete=regional is not None))
 print('Gallery category:',category,flush=True)
# Explicit content-quality examples remain recommendations, without editing raw data.
quality=a.preserved_run/'quality_review'/'quarantine_candidates.csv'
if quality.exists():
 candidates=pd.read_csv(quality,keep_default_na=False);fig,axes=plt.subplots(len(candidates),2,figsize=(9,4*len(candidates)),squeeze=False)
 for axesrow,row in zip(axes,candidates.to_dict('records')):
  im=read_image(root/row['image_path']);axesrow[0].imshow(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));axesrow[0].set_title(f'{row["category"]}/{row["status"]}/{row["view"]}, min={im.min()}, max={im.max()}')
  if row['mask_path']:axesrow[1].imshow(read_image(root/row['mask_path'],True),cmap='gray',vmin=0,vmax=255);axesrow[1].set_title('Provided PNG, original values')
  else:axesrow[1].text(.5,.5,'No provided mask (OK)',ha='center',transform=axesrow[1].transAxes)
  for ax in axesrow:ax.axis('off')
 fig.suptitle('Exact all-zero JPG duplicate pair; preserve raw status and review capture semantics');fig.tight_layout();target=a.output/'figures'/'quality_zero_image_review.png';fig.savefig(target,dpi=110);plt.close(fig);manifest.append(dict(path=str(target),kind='published_aggregate_or_figure',source=str(quality)))
# Selected existing plots and aggregate tables, with original result paths in provenance.
selected=[(a.image_run,['brightness_distribution.png','brightness_histogram.png','brightness_review_images_readable.png','dataset_category_distribution.png','five_view_loss.png','detail_crop_comparison.png','brightness_category_boxplot.png','resolution_metric_distributions.png','resolution_category_heatmaps.png','resolution_global_distribution_summary.csv','resolution_global_quantiles.csv','resolution_undefined_metric_counts.csv','resolution_metric_definitions.json','category_view_loss_summary.csv','brightness_comparison.csv','metadata_validation_report.json']), (a.preserved_run,['heatmap_visualization.png','heatmap_summary.csv','heatmap_validation.json','restoration_validation.json','heatmap_schema.json']), (a.spatial_run,['bbox_class_distribution.png','bbox_area_distribution.png','bbox_validation_report.json','detection_export_validation.json','classes.json','mask_policy.json'])]
if a.background_run:selected.append((a.background_run,['regional_brightness_overview.png','augmentation_review.png','background_distribution.csv','brightness_before_after_comparison.csv','background_bias_ranking.csv','brightness_interpretation_changes.csv','category_view_regional_comparison.csv','background_stratified_comparison.csv','scientific_validation.json','regional_validation.json','segmentation_selection_by_category.csv','train_product_augmentation_candidates.csv','augmentation_visual_checks.csv']))
cross=Path('outputs/cross_analysis_20261111_v1')
if cross.exists():selected.append((cross,['cross_analysis_associations.png','bbox_size_and_component_distributions.png','small_defect_resolution_risk.csv','within_group_associations.csv','defect_roi_paired_summary.csv','validation.json']))
extra=[(Path('outputs/windows_comparison_20261111_v2'),['comparison_validation.json','brightness_same_method_replay.csv','resolution_same_method_replay.csv']),(Path('outputs/windows_heatmap_comparison_20261111_v1'),['validation.json','heatmap_same_split_comparison.csv']),(Path('outputs/mask_integrity_20261111_v6'),['execution.json','global_threshold_pixel_counts.csv']),(Path('outputs/mask_study_20261111_v4/mask_threshold_validation'),['validation.json','threshold_summary.csv','threshold_per_mask.csv']),(a.preserved_run/'quality_review',['quality_aware_split_validation.json','quarantine_candidates.csv']),(Path('outputs/content_audit_20261111_v7'),['content_hash_validation.json']),(a.preserved_run/'train_brightness_policy_quality_aware',['scope.json','normal_only_train_augmentation_stats.csv','brightness_review_candidates_verified.csv'])]
extra.extend([(Path('outputs/windows_group_comparison_20261111_v1'),['validation.json','windows_group_same_method_replay.csv','windows_vs_opencv_group_comparison.csv']),(Path('outputs/windows_checkpoint_comparison_20261111_v1'),['comparison.json'])])
extra.append((Path('outputs/defect_resolution_review_20261111_v7'),['defect_detail_crop_comparison.png','category_roi_loss_summary.csv','scope.json','defect_jpg_resolution_review.csv']))
extra.append((Path('outputs/report_assets_20261111_v1'),['pipeline_data_flow.png']))
selected.extend(extra)
for source,names in selected:
 for name in names:
  path=source/name
  if not path.exists():continue
  folder='figures' if path.suffix=='.png' else 'tables';target=a.output/folder/(source.name+'__'+name);shutil.copy2(path,target);manifest.append(dict(path=str(target),kind='published_aggregate_or_figure',source=str(path)))
save_json(a.output/'manifest.json',dict(created_by='scripts/build_analysis_gallery.py',original_dataset_modified=False,full_resolution_complete=resolution is not None,full_regional_complete=regional is not None,artifacts=manifest))
(a.output/'README.md').write_text('# 분석 공유 이미지와 집계표\n\ncategory_cases: 같은 제품의 5시점 OK/NG 사례와 제공 마스크/박스 오버레이. category_profiles: 품목별 분포와 지표. heatmaps: 기존 분할 Train의 관측 마스크 기반 위치 빈도. figures: 주요 전체 그림. tables: 소규모 집계/검증 근거. 원본 데이터셋, 전체 per-image 결과, 가중치를 포함하지 않는다. manifest.json에 각 그림의 출처/범위/검수 한계를 기록한다. 모든 그림은 관측 자료이며 모델 성능이 아니다.\n');print('Gallery artifacts',len(manifest))
