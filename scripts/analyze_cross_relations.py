# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Descriptive associations across completed analyses; no causal/model performance claims."""
import argparse,json,os,sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--image-run',required=True,type=Path);p.add_argument('--spatial-run',required=True,type=Path);p.add_argument('--background-run',required=True,type=Path);p.add_argument('--roi-run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
metrics=['image_path','target','ssim','edge_recall','rgb_rmse','local_contrast_retention'];r=pd.read_csv(a.image_run/'per_view_information_loss.csv',usecols=metrics);b=pd.read_csv(a.background_run/'regional_brightness_per_image.csv',usecols=['image_path','category','view','status','split','segmentation_status','background_type','whole_mean','product_mean','background_mean','product_pixel_ratio']);boxes=pd.read_csv(a.spatial_run/'defect_bboxes.csv');boxes['short_side']=np.minimum(boxes.x1-boxes.x0,boxes.y1-boxes.y0)
risks=[]
for size in [512,256]:
 data=boxes.assign(target=size,scaled_short_side=boxes.short_side*size/1024,scaled_area=boxes.bbox_area*(size/1024)**2);summary=data.groupby(['category','defect_type','target']).agg(boxes=('bbox_area','size'),native_area_median=('bbox_area','median'),scaled_short_side_median=('scaled_short_side','median'),short_side_under2=('scaled_short_side',lambda v:int((v<2).sum())),scaled_area_under16=('scaled_area',lambda v:int((v<16).sum()))).reset_index();risks.append(summary)
risk=pd.concat(risks,ignore_index=True);risk.to_csv(a.output/'small_defect_resolution_risk.csv',index=False)
per=boxes.groupby('image_path').agg(min_bbox_area=('bbox_area','min'),min_bbox_short_side=('short_side','min'),components=('bbox_area','size')).reset_index();joined=r[r.target==256].merge(b,on='image_path',validate='one_to_one').merge(per,on='image_path',how='left',validate='one_to_one');rows=[]
pairs=[('whole_mean','ssim'),('product_mean','ssim'),('background_mean','ssim'),('product_pixel_ratio','ssim'),('whole_mean','edge_recall'),('min_bbox_short_side','ssim'),('min_bbox_area','edge_recall')]
for key,group in joined.groupby(['category','view','status']):
 for left,right in pairs:
  valid=group[[left,right]].dropna();rho=float(valid[left].rank().corr(valid[right].rank())) if len(valid)>=10 and valid[left].nunique()>1 and valid[right].nunique()>1 else None
  rows.append(dict(category=key[0],view=key[1],status=key[2],feature=left,metric=right,available_pairs=len(valid),group_images=len(group),spearman_rho=rho,interpretation='descriptive association; within category/view/status, not causal or model performance'))
assoc=pd.DataFrame(rows);assoc.to_csv(a.output/'within_group_associations.csv',index=False)
roi=pd.read_csv(a.roi_run/'defect_jpg_resolution_review.csv');paired=roi.merge(r,on=['image_path','target'],validate='one_to_one');assert len(paired)==len(roi) and len(r)==151050*3 and len(b)==151050; paired['roi_minus_whole_rgb_rmse']=paired.roi_rgb_rmse-paired.rgb_rmse;paired.to_csv(a.output/'defect_roi_vs_whole_image_loss.csv',index=False);paired.groupby('target')[['roi_rgb_rmse','rgb_rmse','roi_minus_whole_rgb_rmse','roi_edge_recall','edge_recall']].agg(['count','mean','std','median']).to_csv(a.output/'defect_roi_paired_summary.csv')
fig,axes=plt.subplots(1,3,figsize=(17,4.5))
for bg,group in joined[joined.segmentation_status=='accepted_heuristic'].groupby('background_type'):
 group=group.sort_values('image_path').iloc[::max(1,len(group)//3000)];axes[0].scatter(group.whole_mean,group.ssim,s=4,alpha=.25,label=bg)
axes[0].set(title='256: whole brightness vs SSIM (accepted subset)',xlabel='Whole-image mean brightness [0,255]',ylabel='SSIM');axes[0].legend()
for size,group in risk.groupby('target'):
 agg=group.groupby('category').agg(under2=('short_side_under2','sum'),total=('boxes','sum'));axes[1].plot(range(len(agg)),agg.under2/agg.total,marker='.',label=str(size))
axes[1].set(title='Bboxes with projected short side <2px',xlabel='Category (alphabetical)',ylabel='Fraction of boxes');axes[1].legend()
for size,group in paired.groupby('target'):axes[2].scatter(group.rgb_rmse,group.roi_rgb_rmse,s=10,alpha=.35,label=str(size))
limit=max(paired.rgb_rmse.max(),paired.roi_rgb_rmse.max());axes[2].plot([0,limit],[0,limit],color='gray',linestyle='--');axes[2].set(title='336-mask ROI study: image vs defect ROI',xlabel='Whole JPG RGB RMSE',ylabel='Defect ROI RGB RMSE');axes[2].legend();fig.tight_layout();fig.savefig(a.output/'cross_analysis_associations.png',dpi=130);plt.close(fig)
# table: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df.
def table(df):
 cols=list(df.columns);lines=['| '+' | '.join(cols)+' |','| '+' | '.join('---' for _ in cols)+' |']
 for row in df.itertuples(index=False,name=None):lines.append('| '+' | '.join(f'{v:.5f}' if isinstance(v,float) else str(v) for v in row)+' |')
 return '\n'.join(lines)
summary=risk.groupby('target').agg(boxes=('boxes','sum'),short_side_under2=('short_side_under2','sum'),scaled_area_under16=('scaled_area_under16','sum')).reset_index();strong=assoc.dropna(subset=['spearman_rho']);strong=strong[strong.available_pairs>=30].assign(abs_rho=lambda x:x.spearman_rho.abs()).sort_values('abs_rho',ascending=False)
report=['# 분석 간 관계와 결함 해상도 위험','모든 결과는 관측 자료의 기술 분석이다. 전체 영상 SSIM과 밝기/박스 크기의 관계는 결함 검출 성능이나 인과 효과가 아니다.', '## 작은 결함과 해상도',table(summary),'원본1024 박스 좌표를512/256으로 선형 스케일한 기하학적 위험이다. 2픽셀 미만의 짧은 변은 미세 결함 검수 우선순위이며 실제 결함 소실 비율이 아니다. 연결 성분 bbox는 독립 물리 결함의 개수와 다를 수 있다.', '## 품목·시점·상태를 고정한 상관',table(strong[['category','view','status','feature','metric','available_pairs','group_images','spearman_rho']].head(20)),'단순 전체 상관은 배경/품목 구성에 좌우되므로 품목×시점×OK/NG 내부에서 Spearman rank 상관을 계산했다. 최소10개 유효 쌍, 표에는30개 이상만 보인다. 분산0/관측부족은 결측이다. 다중 비교의 탐색 결과이며 유의성 검정/원인 판정으로 사용하지 않는다. product/background 관련 쌍은 자동 품질 통과 subset이라 선택 편향이 남는다. min bbox 관련 쌍은 제공 마스크의 유효 탐지 라벨이 있는 NG 부분집합이다.', '## 실제 결함 ROI와 전역 영상 변화',table(paired.groupby('target')[['roi_rgb_rmse','rgb_rmse','roi_minus_whole_rgb_rmse','roi_edge_recall','edge_recall']].mean().reset_index()),'동일336장·동일 해상도에서 전역 JPG 복원 오차와 마스크 위치 JPG 복원 오차를 짝지어 비교했다. ROI가 빈 마스크면 ROI 통계는 결측이며 전체 계산을 대체하지 않는다. 그림의 대각선 위는 ROI 복원 오차가 전체 평균보다 크다는 뜻이다. Canny ROI recall과 전역 recall은 영상 경계 일치도이며 모델 recall이 아니다.',f'![분석 간 관계](../{a.output}/cross_analysis_associations.png)','그림 왼쪽은 배경별 기술 산점도로 가독성을 위해 최대 약3,000장/배경으로 간격 표본화했다. 숫자 상관은 전체 유효 행에서 계산했다. 가운데는 품목별 짧은 변 위험, 오른쪽은 동일 ROI/전역 오차다.',f'## 계산 근거\n\n[기하학적 위험](../{a.output}/small_defect_resolution_risk.csv), [전체 그룹 상관](../{a.output}/within_group_associations.csv), [ROI 짝 비교](../{a.output}/defect_roi_vs_whole_image_loss.csv). 재현: scripts/analyze_cross_relations.py.']
components=pd.read_csv(a.spatial_run/'image_component_summary.csv');fig,axes=plt.subplots(1,3,figsize=(16,4.5))
axes[0].hist(np.log10(boxes.bbox_area.clip(lower=1)),bins=45);axes[0].set(title='Native bbox area',xlabel='log10(area / px²)',ylabel='Component boxes')
ng=components[components.status=='NG'];axes[1].hist(ng.components,bins=np.arange(0,min(40,int(ng.components.max()))+2)-.5);axes[1].set(title='Provided-mask NG components (tail >40 omitted)',xlabel='Components/image',ylabel='Images')
for cls,data in boxes.groupby('defect_type'):
 values=np.sort(data.short_side);axes[2].plot(values,np.arange(1,len(values)+1)/len(values),label=cls)
axes[2].set(xscale='log',title='BBox short-side CDF by class',xlabel='Native short side / px',ylabel='Fraction <= x');axes[2].axvline(8,color='gray',linestyle='--');axes[2].legend(ncol=2,fontsize=8);fig.tight_layout();fig.savefig(a.output/'bbox_size_and_component_distributions.png',dpi=130);plt.close(fig)
Path('reports/ANALYSIS_CROSS_RELATIONS.md').write_text('\n\n'.join(report));save_json(a.output/'validation.json',dict(full_resolution_rows=len(r),image_rows_256=len(joined),bbox_rows=len(boxes),roi_rows=len(roi),roi_paired_rows=len(paired),association_rows=len(assoc),no_model_performance_measured=True,no_causal_claims=True));print('Cross-analysis report complete')
