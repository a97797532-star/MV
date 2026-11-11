from pathlib import Path
import argparse
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image


def ssim_cv(a,b):
    a=a.astype(np.float64); b=b.astype(np.float64)
    vals=[]
    for c in range(3):
        x=a[:,:,c]; y=b[:,:,c]
        mx=cv2.GaussianBlur(x,(11,11),1.5); my=cv2.GaussianBlur(y,(11,11),1.5)
        vx=cv2.GaussianBlur(x*x,(11,11),1.5)-mx*mx
        vy=cv2.GaussianBlur(y*y,(11,11),1.5)-my*my
        cov=cv2.GaussianBlur(x*y,(11,11),1.5)-mx*my
        c1=(.01*255)**2; c2=(.03*255)**2
        vals.append(np.mean(((2*mx*my+c1)*(2*cov+c2))/((mx*mx+my*my+c1)*(vx+vy+c2))))
    return float(np.mean(vals))


def resize_ids(labels,size):
    h,w=labels.shape
    ys=np.clip(np.floor((np.arange(size)+.5)*h/size).astype(np.int64),0,h-1)
    xs=np.clip(np.floor((np.arange(size)+.5)*w/size).astype(np.int64),0,w-1)
    return labels[np.ix_(ys,xs)]


def analyze(image,mask,size,image_id):
    h,w=image.shape[:2]
    down=cv2.resize(image,(size,size),interpolation=cv2.INTER_LINEAR)
    back=cv2.resize(down,(w,h),interpolation=cv2.INTER_LINEAR)
    psnr=float(cv2.PSNR(image,back))
    ssim=ssim_cv(image,back)
    n,labels,stats,_=cv2.connectedComponentsWithStats(np.ascontiguousarray(mask,dtype=np.uint8),8)
    small=resize_ids(labels,size)
    counts=np.bincount(small.ravel(),minlength=n)
    details=[]
    for k in range(1,n):
        ys,xs=np.where(small==k)
        details.append(dict(image_id=image_id,size=size,component_id=k,original_area=int(stats[k,cv2.CC_STAT_AREA]),remaining_pixels=int(counts[k]),survived=bool(len(xs)),resized_bbox_width=int(xs.max()-xs.min()+1) if len(xs) else 0,resized_bbox_height=int(ys.max()-ys.min()+1) if len(ys) else 0))
    original=n-1; survived=int(np.count_nonzero(counts[1:])); mib=3*size*size*4/1048576
    result=dict(image_id=image_id,size=size,psnr=psnr,ssim=ssim,original_components=original,survived_components=survived,lost_components=original-survived,survival_rate=survived/original if original else np.nan,one_view_mib=mib,five_view_mib=5*mib)
    return result,details,down,small


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',default='notebook_results_real')
    p.add_argument('--threshold',type=int,required=True,help='검수 완료된 마스크 임계값; 미검증 값 사용 금지')
    p.add_argument('--limit',type=int,default=100,help='0이면 전체')
    p.add_argument('--preview',action='store_true')
    args=p.parse_args()
    root=Path(args.data_dir); out=root/'resolution_analysis';out.mkdir(parents=True,exist_ok=True)
    pairs=pd.read_csv(root/'image_mask_pairs.csv',dtype=str).fillna('')
    if 'mask_path' not in pairs: pairs=pairs.rename(columns={'image_path':'mask_path'})
    needed={'original_image_id','original_image_path','mask_path'}
    if not needed.issubset(pairs):raise ValueError(f'누락 컬럼: {needed-set(pairs.columns)}')
    if args.limit>0:pairs=pairs.head(args.limit)
    summaries=[]; components=[]; errors=[]
    for i,row in enumerate(pairs.itertuples(index=False)):
        try:
            with Image.open(row.original_image_path) as im:image=np.asarray(im.convert('RGB'))
            with Image.open(row.mask_path) as im:mask=np.asarray(im)
            if mask.ndim!=2:raise ValueError(f'마스크 차원 {mask.shape}: 인코딩 확인 필요')
            if mask.shape!=image.shape[:2]:raise ValueError(f'크기 불일치 {mask.shape} != {image.shape[:2]}')
            binary=(mask>args.threshold).astype(np.uint8)
            for size in (1024,512,256):
                result,detail,down,small=analyze(image,binary,size,row.original_image_id)
                result['category']=getattr(row,'category','');result['view']=getattr(row,'view','')
                summaries.append(result);components.extend(detail)
                if args.preview and i==0:
                    fig,ax=plt.subplots(1,2,figsize=(9,4));ax[0].imshow(down);ax[1].imshow(small>0,cmap='gray');ax[0].set_title(f'RGB {size}');ax[1].set_title(f'Mask {size}');[a.axis('off') for a in ax];fig.tight_layout();fig.savefig(out/f'preview_{size}.png',dpi=130);plt.close(fig)
        except Exception as exc:errors.append(dict(image_id=row.original_image_id,error=str(exc)))
        if (i+1)%100==0:print(f'{i+1}/{len(pairs)} processed')
    df=pd.DataFrame(summaries); comp=pd.DataFrame(components); err=pd.DataFrame(errors,columns=['image_id','error'])
    df.to_csv(out/'resolution_summary.csv',index=False,encoding='utf-8-sig');comp.to_csv(out/'component_survival.csv',index=False,encoding='utf-8-sig');err.to_csv(out/'resolution_errors.csv',index=False,encoding='utf-8-sig')
    if not df.empty:
        agg=df.groupby('size').agg(image_count=('image_id','nunique'),mean_psnr=('psnr','mean'),mean_ssim=('ssim','mean'),original_components=('original_components','sum'),survived_components=('survived_components','sum'),lost_components=('lost_components','sum'),one_view_mib=('one_view_mib','first'),five_view_mib=('five_view_mib','first')).reset_index()
        agg['pooled_survival_rate']=agg['survived_components']/agg['original_components'].replace(0,np.nan)
        agg.to_csv(out/'resolution_comparison.csv',index=False,encoding='utf-8-sig');print(agg.to_string(index=False))
    print('오류:',len(err),'결과 폴더:',out)

if __name__=='__main__':main()
