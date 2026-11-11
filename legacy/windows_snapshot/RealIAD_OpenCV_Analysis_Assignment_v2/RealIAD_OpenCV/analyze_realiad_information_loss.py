"""Analyze outputs of realiad_5view_information_loss.py; no image reprocessing.
Usage: python analyze_realiad_information_loss.py --data-dir notebook_results_real
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METRICS = {
    'mae': ('RGB absolute error (lower is better)', 'higher'),
    'rgb_rmse': ('RGB RMSE (lower is better)', 'higher'),
    'high_error_pixel_fraction': ('Fraction of pixels with RGB error >=20', 'higher'),
    'edge_recall_tol1': ('Edge recall ±1 pixel (higher is better)', 'lower'),
    'laplacian_energy_retention': ('Laplacian energy ratio (near 1 = similar)', 'deviation'),
    'gradient_energy_retention': ('Gradient energy ratio (near 1 = similar)', 'deviation'),
    'local_contrast_retention': ('Local contrast ratio (near 1 = similar)', 'deviation'),
    'psnr': ('PSNR (higher is better)', 'lower'),
}

def safe_name(x):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(x))[:90]

def savefig(path):
    plt.tight_layout(); plt.savefig(path,dpi=150,bbox_inches='tight'); plt.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',default='notebook_results_real')
    p.add_argument('--top-n',type=int,default=30)
    p.add_argument('--max-categories',type=int,default=15)
    args=p.parse_args()
    source=Path(args.data_dir)/'resolution_information_loss'
    out=source/'analysis';out.mkdir(parents=True,exist_ok=True)
    f=source/'per_view_information_loss.csv'
    if not f.exists():raise FileNotFoundError(f)
    df=pd.read_csv(f,encoding='utf-8-sig')
    required={'product_key','image_id','category','view','size','original_width','original_height',*METRICS}
    missing=required-set(df.columns)
    if missing:raise ValueError(f'Missing columns: {sorted(missing)}')
    if df.empty:raise ValueError('No metrics rows in CSV')
    df['size']=pd.to_numeric(df['size'],errors='coerce')
    for m in METRICS:df[m]=pd.to_numeric(df[m],errors='coerce')
    df=df[df['size'].isin([1024,512,256])].copy()
    keys=['product_key','image_id','category','view']
    duplicates=df.duplicated(keys+['size'],keep=False)
    if duplicates.any():raise ValueError(f'Duplicate image-size metric rows: {int(duplicates.sum())}')
    completeness=df.groupby(keys,dropna=False)['size'].nunique().rename('size_count').reset_index()
    incomplete=completeness[completeness.size_count!=3]
    incomplete.to_csv(out/'incomplete_images.csv',index=False,encoding='utf-8-sig')
    df=df.merge(completeness,on=keys,validate='many_to_one')
    df=df[df.size_count==3].drop(columns='size_count').copy()
    if df.empty:raise ValueError('No images with all three resolution measurements')
    # Each image contributes one sample at each resolution. Avoid pseudo-independent pixels.
    metrics=list(METRICS)
    summary=(df.groupby(['category','view','size'],dropna=False)
             .agg(image_count=('image_id','nunique'),product_count=('product_key','nunique'),
                  **{m+'_mean':(m,'mean') for m in metrics},
                  **{m+'_median':(m,'median') for m in metrics},
                  **{m+'_p10':(m,lambda s:s.quantile(.1)) for m in metrics},
                  **{m+'_p90':(m,lambda s:s.quantile(.9)) for m in metrics})
             .reset_index())
    summary.to_csv(out/'category_view_detailed.csv',index=False,encoding='utf-8-sig')
    # Same-image stepwise comparisons; no 5-view average as decision criterion.
    wide=df.pivot(index=keys,columns='size',values=metrics)
    step_rows=[]
    for (prod,im,cat,view), r in wide.iterrows():
        for a,b in [(1024,512),(512,256),(1024,256)]:
            record=dict(product_key=prod,image_id=im,category=cat,view=view,from_size=a,to_size=b)
            for m in metrics:
                va,vb=r.get((m,a),np.nan),r.get((m,b),np.nan)
                record[m+'_delta']=vb-va
                record[m+'_from']=va
                record[m+'_to']=vb
            step_rows.append(record)
    steps=pd.DataFrame(step_rows)
    steps.to_csv(out/'per_image_stepwise_changes.csv',index=False,encoding='utf-8-sig')
    step_summary=(steps.groupby(['category','view','from_size','to_size'],dropna=False)
                  .agg(image_count=('image_id','nunique'),product_count=('product_key','nunique'),
                       **{m+'_delta_median':(m+'_delta','median') for m in metrics},
                       **{m+'_delta_p10':(m+'_delta',lambda s:s.quantile(.1)) for m in metrics},
                       **{m+'_delta_p90':(m+'_delta',lambda s:s.quantile(.9)) for m in metrics})
                  .reset_index())
    step_summary.to_csv(out/'stepwise_group_changes.csv',index=False,encoding='utf-8-sig')
    # rank review candidates: large 1024->256 edge recall decrease, then absolute error increase.
    review=steps[(steps.from_size==1024)&(steps.to_size==256)].copy()
    review['edge_recall_drop']=(-review['edge_recall_tol1_delta']).clip(lower=0)
    review['mae_increase']=review['mae_delta'].clip(lower=0)
    review['contrast_deviation_at_256']=(review['local_contrast_retention_to']-1).abs()
    review=review.sort_values(['edge_recall_drop','mae_increase'],ascending=False)
    review[['product_key','image_id','category','view','edge_recall_drop','mae_increase','contrast_deviation_at_256']].head(args.top_n).to_csv(out/'review_priority_images.csv',index=False,encoding='utf-8-sig')
    # Visuals: compare all five views separately.
    for m in ['mae','edge_recall_tol1','gradient_energy_retention','local_contrast_retention','high_error_pixel_fraction']:
        fig,ax=plt.subplots(figsize=(9,5))
        vals=df.groupby(['view','size'])[m].median().unstack('size').reindex(columns=[1024,512,256])
        for view,row in vals.iterrows():ax.plot([1024,512,256],row.values,marker='o',label=view)
        ax.set_xticks([1024,512,256]);ax.invert_xaxis();ax.set_xlabel('Square input size')
        ax.set_ylabel(METRICS[m][0]);ax.set_title(f'Five-view comparison: {m}')
        ax.legend(ncol=5,fontsize=8);ax.grid(alpha=.2)
        savefig(out/f'views_{m}.png')
    cats=df.groupby('category')['image_id'].nunique().nlargest(args.max_categories).index
    for m in ['edge_recall_tol1','mae','local_contrast_retention']:
        subset=df[(df.category.isin(cats))&(df['size']==256)]
        vals=subset.groupby(['category','view'])[m].median().unstack('view').reindex(index=cats)
        fig,ax=plt.subplots(figsize=(10,max(4,len(vals)*.42)))
        data=vals.to_numpy(dtype=float)
        im=ax.imshow(data,aspect='auto',cmap='viridis')
        ax.set_xticks(range(len(vals.columns)),vals.columns)
        ax.set_yticks(range(len(vals.index)),vals.index)
        ax.set_title(f'256 input / median {m} (by category and view)')
        fig.colorbar(im,ax=ax)
        savefig(out/f'category_view_256_{m}.png')
    # audit the actual source resolution (1024 can be upsampling)
    source_resolution=(df[df['size']==1024].groupby(['original_width','original_height'])
                       .agg(image_count=('image_id','nunique')).reset_index().sort_values('image_count',ascending=False))
    source_resolution.to_csv(out/'original_resolution_counts.csv',index=False,encoding='utf-8-sig')
    error_file=source/'errors.csv'
    error_count=len(pd.read_csv(error_file)) if error_file.exists() else None
    with open(out/'README_interpretation.txt','w',encoding='utf-8') as h:
        h.write('Information-loss analysis notes\n')
        h.write(f'Complete images: {df.image_id.nunique()}, products: {df.product_key.nunique()}, error log rows: {error_count}\n')
        h.write('Metrics measure image changes after resize+restore, not semantic or defect-specific loss.\n')
        h.write('Energy/contrast ratios may exceed 1; deviation from 1 is not necessarily feature disappearance.\n')
        h.write('Edge recall uses 1-pixel tolerance and depends on Canny thresholds.\n')
        h.write('The script evaluates each view separately; inspect preview crops and original images.\n')
        h.write('Do not choose resolution from test statistics; prefer train/validation and confirm model performance.\n')
    print('Complete images:',df.image_id.nunique(),'products:',df.product_key.nunique())
    print('Source resolution distribution:\n',source_resolution.head().to_string(index=False))
    print('Saved analysis:',out)

if __name__=='__main__':main()
