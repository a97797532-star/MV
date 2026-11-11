"""OpenCV-only Real-IAD 5-view RGB downscaling information-loss inspection.
Usage: python realiad_5view_information_loss.py --data-dir notebook_results_real --split train --limit-products 10 --preview-products 2
"""
import argparse
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from PIL import Image

SIZES=(1024,512,256)
VIEWS=('C1','C2','C3','C4','C5')

def product_key(path):
    parts=str(path).replace('\\','/').split('/')
    up=[p.upper() for p in parts]
    ix=next((i for i,p in enumerate(up) if p in ('NG','OK')),None)
    if ix is None: return None
    stop=ix+3 if up[ix]=='NG' else ix+2
    if len(parts)<=stop: return None
    return '/'.join(parts[:stop]).lower()

def gray(im): return cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)

def loss_metrics(ref,down):
    h,w=ref.shape[:2]
    up=cv2.resize(down,(w,h),interpolation=cv2.INTER_LINEAR)
    diff=cv2.absdiff(ref,up)
    g0=gray(ref); g1=gray(up)
    lap0=np.abs(cv2.Laplacian(g0,cv2.CV_32F,ksize=3))
    lap1=np.abs(cv2.Laplacian(g1,cv2.CV_32F,ksize=3))
    # Gradient energy loss is a proxy, not a count of physically lost features.
    grad0=np.hypot(cv2.Sobel(g0,cv2.CV_32F,1,0,ksize=3),cv2.Sobel(g0,cv2.CV_32F,0,1,ksize=3))
    grad1=np.hypot(cv2.Sobel(g1,cv2.CV_32F,1,0,ksize=3),cv2.Sobel(g1,cv2.CV_32F,0,1,ksize=3))
    e0=cv2.Canny(g0,100,200)>0
    e1=cv2.Canny(g1,100,200)>0
    # Edge retention with 1-pixel spatial tolerance; no morph applied to labels/images.
    kernel=np.ones((3,3),np.uint8)
    near=cv2.dilate(e1.astype(np.uint8),kernel)>0
    edge_recall=float(np.count_nonzero(e0&near)/np.count_nonzero(e0)) if np.any(e0) else np.nan
    # Local contrast: standard deviation in fixed 9x9 original-pixel neighborhoods.
    def localstd(g):
        f=g.astype(np.float32)
        mu=cv2.blur(f,(9,9)); mu2=cv2.blur(f*f,(9,9))
        return np.sqrt(np.maximum(mu2-mu*mu,0))
    c0=localstd(g0); c1=localstd(g1)
    return dict(
        mae=float(diff.mean()),rgb_rmse=float(np.sqrt(np.mean((ref.astype(np.float32)-up.astype(np.float32))**2))),
        psnr=float(cv2.PSNR(ref,up)),
        laplacian_energy_original=float(lap0.mean()),laplacian_energy_restored=float(lap1.mean()),
        laplacian_energy_retention=float(lap1.mean()/lap0.mean()) if lap0.mean()>0 else np.nan,
        gradient_energy_retention=float(grad1.mean()/grad0.mean()) if grad0.mean()>0 else np.nan,
        edge_recall_tol1=edge_recall,
        local_contrast_retention=float(c1.mean()/c0.mean()) if c0.mean()>0 else np.nan,
        high_error_pixel_fraction=float(np.mean(np.max(diff,axis=2)>=20)),
        one_view_fp32_mib=3*down.shape[0]*down.shape[1]*4/1048576,
        five_view_fp32_mib=15*down.shape[0]*down.shape[1]*4/1048576,
    ),up,diff,lap0,lap1

def preview(rows,out):
    import matplotlib.pyplot as plt
    out.mkdir(parents=True,exist_ok=True)
    # Rows are the five views of one physical sample.
    fig,axs=plt.subplots(5,5,figsize=(17,17),squeeze=False)
    for i,r in enumerate(rows):
        with Image.open(r.image_path) as im: ref=np.asarray(im.convert('RGB'))
        h,w=ref.shape[:2]
        downs=[cv2.resize(ref,(s,s),interpolation=cv2.INTER_LINEAR) for s in SIZES]
        _,up512,diff512,_,_=loss_metrics(ref,downs[1])
        _,up256,diff256,_,_=loss_metrics(ref,downs[2])
        panels=[ref,up512,up256,cv2.applyColorMap(cv2.cvtColor(diff512,cv2.COLOR_RGB2GRAY),cv2.COLORMAP_INFERNO),cv2.applyColorMap(cv2.cvtColor(diff256,cv2.COLOR_RGB2GRAY),cv2.COLORMAP_INFERNO)]
        titles=['Original','512 restored','256 restored','512 absolute error','256 absolute error']
        for j,(p,t) in enumerate(zip(panels,titles)):
            axs[i,j].imshow(cv2.cvtColor(p,cv2.COLOR_BGR2RGB) if j>=3 else p)
            axs[i,j].set_title(f'{r.view}: {t}',fontsize=9);axs[i,j].axis('off')
    fig.suptitle('Five views: visual changes after RGB downscaling (restored to original display size)')
    fig.tight_layout()
    fig.savefig(out/'five_view_loss.png',dpi=125)
    plt.close(fig)
    # A crop from a high-error region, held fixed across all resolutions.
    with Image.open(rows[0].image_path) as im: ref=np.asarray(im.convert('RGB'))
    h,w=ref.shape[:2]
    down=cv2.resize(ref,(256,256),interpolation=cv2.INTER_LINEAR)
    up=cv2.resize(down,(w,h),interpolation=cv2.INTER_LINEAR)
    err=cv2.cvtColor(cv2.absdiff(ref,up),cv2.COLOR_RGB2GRAY).astype(np.float32)
    patch=max(32,min(h,w)//6)
    scores=cv2.boxFilter(err,-1,(patch,patch),normalize=True)
    cy,cx=np.unravel_index(np.argmax(scores),scores.shape)
    x0=int(np.clip(cx-patch//2,0,max(0,w-patch)));y0=int(np.clip(cy-patch//2,0,max(0,h-patch)))
    fig,axs=plt.subplots(1,3,figsize=(12,4))
    for ax,s in zip(axs,SIZES):
        im=cv2.resize(ref,(s,s),interpolation=cv2.INTER_LINEAR)
        back=cv2.resize(im,(w,h),interpolation=cv2.INTER_LINEAR)
        ax.imshow(back[y0:y0+patch,x0:x0+patch]);ax.set_title(f'{s} crop');ax.axis('off')
    fig.tight_layout();fig.savefig(out/'detail_crop_comparison.png',dpi=150);plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-dir',default='notebook_results_real')
    ap.add_argument('--split',default='train',choices=['train','val','test','all'])
    ap.add_argument('--limit-products',type=int,default=10,help='0 = all complete 5-view products')
    ap.add_argument('--preview-products',type=int,default=2)
    args=ap.parse_args()
    root=Path(args.data_dir);out=root/'resolution_information_loss';out.mkdir(parents=True,exist_ok=True)
    source=root/'image_metadata_with_split.csv'
    if not source.exists():source=root/'image_metadata.csv'
    df=pd.read_csv(source,dtype=str).fillna('')
    required={'image_path','relative_path','category','view'}
    if not required.issubset(df.columns):raise ValueError(f'Missing columns: {required-set(df.columns)}')
    df=df[df.image_path.map(lambda s:Path(s).suffix.lower() in ('.jpg','.jpeg'))].copy()
    if args.split!='all':
        if 'project_split' not in df:raise ValueError('project_split is required for train/val/test filtering')
        df=df[df.project_split.str.lower()==args.split].copy()
    df['product_key']=df.relative_path.map(product_key)
    df=df.dropna(subset=['product_key']);df['view']=df.view.str.upper()
    counts=df.groupby(['product_key','view']).size().unstack(fill_value=0).reindex(columns=VIEWS,fill_value=0)
    keys=sorted(counts.index[counts.eq(1).all(axis=1)])
    if args.limit_products>0:keys=keys[:args.limit_products]
    df=df[df.product_key.isin(keys)].sort_values(['product_key','view'])
    print(f'Complete five-view products selected: {len(keys)}, JPG images: {len(df)}')
    rows=[];errors=[];previewed=0
    for key,group in df.groupby('product_key',sort=True):
        for r in group.itertuples(index=False):
            try:
                with Image.open(r.image_path) as im: rgb=np.asarray(im.convert('RGB'))
                h,w=rgb.shape[:2]
                for s in SIZES:
                    down=cv2.resize(rgb,(s,s),interpolation=cv2.INTER_LINEAR)
                    metrics,*_=loss_metrics(rgb,down)
                    rows.append(dict(product_key=key,image_id=getattr(r,'image_id',''),category=r.category,view=r.view,quality=getattr(r,'label',''),size=s,original_width=w,original_height=h,**metrics))
            except Exception as exc:errors.append(dict(product_key=key,view=r.view,image_path=r.image_path,error=str(exc)))
        if previewed<args.preview_products:
            try:preview(group.itertuples(index=False),out/'previews'/f'product_{previewed+1:03d}');previewed+=1
            except Exception as exc:errors.append(dict(product_key=key,view='PREVIEW',image_path='',error=str(exc)))
    metrics=pd.DataFrame(rows)
    metrics.to_csv(out/'per_view_information_loss.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(errors,columns=['product_key','view','image_path','error']).to_csv(out/'errors.csv',index=False,encoding='utf-8-sig')
    if not metrics.empty:
        metrics.groupby(['category','view','size'],as_index=False).agg(images=('image_id','count'),mean_mae=('mae','mean'),mean_edge_recall=('edge_recall_tol1','mean'),mean_gradient_retention=('gradient_energy_retention','mean'),mean_local_contrast_retention=('local_contrast_retention','mean')).to_csv(out/'category_view_loss_summary.csv',index=False,encoding='utf-8-sig')
    print(f'Rows: {len(metrics)}, errors: {len(errors)}, output: {out}')

if __name__=='__main__':main()
