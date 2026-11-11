from __future__ import annotations
import hashlib
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

VIEWS = {f'C{i}' for i in range(1, 6)}


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str, allow_nan=False))


def read_image(path, mask=False):
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED if mask else cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'Cannot decode: {path}')
    if mask and (image.ndim != 2 or image.dtype != np.uint8):
        raise ValueError(f'Mask must be uint8 single-channel: {path}')
    return image


from .schema import parse_image,scan


def metadata(root, out, limit=None, decode=True, split_manifest=None, split_policy="hash"):
    images, masks, others = scan(root)
    selected = images[:limit] if limit else images
    records, errors, mask_records = [], [], []
    def inspect(path):
        try:
            row=parse_image(path,root)
            if decode:
                im=read_image(path);row.update(width=im.shape[1],height=im.shape[0])
            st=path.stat();row.update(bytes=st.st_size,mtime_ns=st.st_mtime_ns,readable=os.access(path,os.R_OK))
            return row,None
        except Exception as exc:return None,dict(path=str(path.relative_to(root)),error=str(exc))
    checkpoint=out/'metadata_checkpoint.jsonl'
    done={}
    if checkpoint.exists():
        for line in checkpoint.read_text().splitlines():
            value=json.loads(line);done[value['image_path']]=value
    pending=[path for path in selected if str(path.relative_to(root)) not in done]
    records=list(done.values())
    with ThreadPoolExecutor(max_workers=2) as pool,checkpoint.open('a') as stream:
        for start in range(0,len(pending),1000):
            for row,error in pool.map(inspect,pending[start:start+1000]):
                if error:errors.append(error)
                else:
                    records.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
            print(f'metadata {len(records)}/{len(selected)} errors={len(errors)}',flush=True)
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError('No valid images')
    split_import=None
    if split_policy=='windows-project-v1' and not split_manifest:
        from .splits import reproduce_windows_project_split
        complete=pd.DataFrame([dict(image_path=str(path.relative_to(root)),category=path.relative_to(root).parts[0]) for path in images])
        complete=reproduce_windows_project_split(complete).set_index('image_path')
        df['analysis_hash_split']=df.split
        df['conservative_serial_id']=df.product_id
        for col in ['windows_product_key','windows_project_split','split','product_id','split_origin']:
            df[col]=df.image_path.map(complete[col])
        split_import=dict(policy='windows-project-v1',full_scope_images=len(images),matched=len(df),new_images=0)
    if split_manifest:
        from .splits import apply_preserved_split
        df,split_import=apply_preserved_split(df,split_manifest,root)
    selected_paths = set(df.image_path)
    for mask in masks:
        rel = str(mask.relative_to(root)); pair = str(mask.relative_to(root).with_suffix('.jpg'))
        if not limit or pair in selected_paths:
            mask_records.append(dict(mask_path=rel, image_path=pair, image_exists=mask.with_suffix('.jpg').is_file(), bytes=mask.stat().st_size))
    df.drop(columns='split').to_csv(out/'image_metadata.csv', index=False)
    df.to_csv(out/'image_metadata_with_split.csv', index=False)
    pd.DataFrame(mask_records, columns=['mask_path','image_path','image_exists','bytes']).to_csv(out/'mask_metadata.csv',index=False)
    df.loc[df.mask_path!='', ['image_path','mask_path']].to_csv(out/'image_mask_pairs.csv', index=False)
    grouped = df.groupby('capture_id').view.agg(list)
    incomplete = {k:v for k,v in grouped.items() if set(v)!=VIEWS or len(v)!=5}
    issues = df[(df.status=='NG') & ~df.has_mask]
    png_by_stem={}
    for path in masks:png_by_stem.setdefault(path.stem.casefold(),[]).append(str(path.relative_to(root)))
    missing_rows=[]
    for row in issues.to_dict('records'):
        candidates=png_by_stem.get(Path(row['image_path']).stem.casefold(),[])
        missing_rows.append(dict(image_path=row['image_path'],category=row['category'],defect_type=row['defect_type'],view=row['view'],has_mask=False,reason='path_or_filename_case_mismatch' if candidates else 'not_provided_at_expected_path; cause_unconfirmed',candidate_masks=';'.join(candidates)))
    pd.DataFrame(missing_rows,columns=['image_path','category','defect_type','view','has_mask','reason','candidate_masks']).to_csv(out/'ng_without_mask.csv',index=False)
    paired_ng=int(((df.status=='NG') & df.has_mask).sum())
    df[df.label_conflict].to_csv(out/'metadata_label_conflicts.csv',index=False)
    report = dict(preserved_split_import=split_import,label_conflicts=int(df.label_conflict.sum()),jpg_count=len(images), png_count=len(masks), ignored_files=others,
                  selected=len(selected), success=len(df), errors=errors, decode_verified=decode,
                  ng_without_mask=len(issues),ng_with_mask=paired_ng,
                  mask_coverage_of_ng=paired_ng/int((df.status=='NG').sum()) if (df.status=='NG').any() else None,
                  existing_mask_pair_success_rate=sum(r['image_exists'] for r in mask_records)/len(mask_records) if mask_records else None,
                  mask_absence_is_error=False,mask_absence_reason='Unprovided at expected path; actual omission versus intentionally unannotated view cannot be established without source annotation manifest', orphan_masks=sum(not r['image_exists'] for r in mask_records),
                  duplicate_relative_paths=int(df.image_path.duplicated().sum()),
                  duplicate_content='not checked; path duplication is not byte duplication',
                  incomplete_capture_groups=incomplete, product_split_leakage=int((df.groupby('product_id').split.nunique()>1).sum()),
                  status_counts=df.status.value_counts().to_dict(), view_counts=df.view.value_counts().to_dict(),
                  category_counts=df.category.value_counts().to_dict(),
                  windows_reference={'jpg':146060,'png':50115}, jpg_delta=len(images)-146060,png_delta=len(masks)-50115,
                  split_policy='preserved Windows project split' if split_import else 'SHA256(category/serial), 70/15/15 analysis split',
                  physical_product_identity='conservative serial grouping; actual identity needs dataset owner verification')
    df.groupby(['category','status']).size().unstack(fill_value=0).to_csv(out/'category_status_counts.csv')
    df.groupby(['category','defect_type','view']).size().rename('images').to_csv(out/'category_defect_view_counts.csv')
    report['dimension_counts']={str(k):int(v) for k,v in df.groupby(['width','height']).size().items()} if decode else {}
    save_json(out/'metadata_validation_report.json',report)
    plot_bars(df.groupby(['category','status']).size(),out/'dataset_category_distribution.png','Real-IAD images by category and status','Image count')
    return df, report


def audit_masks(root, df, out, limit=None):
    paths = sorted(set(df.loc[(df.status=='NG') & (df.mask_path!=''),'mask_path']))
    if limit: paths=paths[:limit]
    histogram = np.zeros(256, dtype=np.int64); errors=[]
    by_mask={r['mask_path']:r for r in df[df.mask_path!=''].to_dict('records')}
    for i, rel in enumerate(paths):
        try:
            mask=read_image(root/rel,True)
            row=by_mask[rel]
            if 'height' in row and mask.shape != (row['height'],row['width']): raise ValueError('image/mask shape mismatch')
            histogram += np.bincount(mask.ravel(),minlength=256)
        except Exception as exc: errors.append(dict(path=rel,error=str(exc)))
        if (i+1)%1000==0: print(f'mask audit {i+1}/{len(paths)}',flush=True)
    values=np.flatnonzero(histogram).tolist()
    # Only exact binary encoding permits automatic threshold derivation.
    valid=bool(paths) and not errors and values in ([0,255],[0,1])
    report=dict(inspected=len(paths),expected=len(set(df.loc[df.mask_path!='','mask_path'])),
                values=values,histogram=histogram.tolist(),errors=errors,
                validated=valid and limit is None,
                threshold=0 if valid else None,
                policy='nonzero foreground only for globally verified {0,1} or {0,255}; otherwise keep threshold pending; grayscale is not corruption',
                integrity_valid=not errors,encoding='binary' if valid else 'grayscale_uint8',policy_status='auto_verified_binary' if valid else 'threshold_review_required')
    save_json(out/'mask_policy.json',report); return report


def binary_mask(mask, policy):
    if not policy.get('validated') or policy.get('threshold') not in (0,32,64,127,192,254):
        raise ValueError('No verified binary mask policy; run mask-audit on the complete manifest')
    if mask.ndim!=2 or mask.dtype!=np.uint8 or (policy.get('encoding','binary')=='binary' and not set(np.unique(mask)).issubset({0,1,255})):
        raise ValueError('Mask does not match verified binary encoding')
    return (mask>policy['threshold']).astype(np.uint8)


def components(mask):
    from .legacy_bridge import backend
    _,regions=backend().components(mask)
    return [(r['x0'],r['y0'],r['x1'],r['y1'],r['area']) for _,r in regions]


def brightness_metrics(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    hist=np.bincount(gray.ravel(),minlength=256);cdf=hist.cumsum();n=gray.size
    def percentile(q):
        rank=(n-1)*q;lo=int(rank);hi=int(np.ceil(rank));v0=np.searchsorted(cdf,lo+1);v1=np.searchsorted(cdf,hi+1)
        return float(v0+(v1-v0)*(rank-lo))
    return dict(brightness=float(gray.mean()),p05=percentile(.05),p50=percentile(.5),p95=percentile(.95))



def prepare_image_reference(image):
    a=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY).astype(np.float32)
    ma=cv2.GaussianBlur(a,(11,11),1.5)
    va=cv2.GaussianBlur(a*a,(11,11),1.5)-ma*ma
    lap=cv2.Laplacian(a,cv2.CV_32F)
    gx=cv2.Sobel(a,cv2.CV_32F,1,0);gy=cv2.Sobel(a,cv2.CV_32F,0,1)
    return dict(a=a,ma=ma,va=va,edge=cv2.Canny(a.astype('uint8'),100,200)>0,
                lap=cv2.norm(lap,cv2.NORM_L2SQR)/a.size,
                gradient=(cv2.norm(gx,cv2.NORM_L2SQR)+cv2.norm(gy,cv2.NORM_L2SQR))/a.size,
                contrast=float(np.sqrt(np.maximum(va,0)).mean()))


def information_loss(image,size,reference=None):
    h,w=image.shape[:2];ref=reference if reference is not None else prepare_image_reference(image)
    ratio=lambda x,y:float(x/y) if y>1e-10 else None
    if (h,w)==(size,size):
        return dict(target=size,psnr_db=120.,ssim=1.,edge_recall=1.,edge_f1=1.,laplacian_energy=ref['lap'],laplacian_retention=ratio(ref['lap'],ref['lap']),gradient_energy=ref['gradient'],gradient_retention=ratio(ref['gradient'],ref['gradient']),local_contrast_retention=ratio(ref['contrast'],ref['contrast']),rgb_rmse=0.,high_frequency_proxy_retention=ratio(ref['lap'],ref['lap']))
    small=cv2.resize(image,(size,size),interpolation=cv2.INTER_AREA)
    restored=cv2.resize(small,(w,h),interpolation=cv2.INTER_LINEAR)
    a,ma,va=ref['a'],ref['ma'],ref['va']
    b=cv2.cvtColor(restored,cv2.COLOR_BGR2GRAY).astype(np.float32)
    mse=cv2.norm(image,restored,cv2.NORM_L2SQR)/(h*w*3)
    blur=lambda v:cv2.GaussianBlur(v,(11,11),1.5)
    mb=blur(b);vb=blur(b*b)-mb*mb;cov=blur(a*b)-ma*mb
    ssim=float(np.mean(((2*ma*mb+6.5025)*(2*cov+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))))
    ea=ref['edge'];eb=cv2.Canny(b.astype('uint8'),100,200)>0
    tp=int((ea&eb).sum());recall=tp/int(ea.sum()) if ea.any() else 1.;precision=tp/int(eb.sum()) if eb.any() else float(not ea.any())
    lap=cv2.Laplacian(b,cv2.CV_32F);energy=cv2.norm(lap,cv2.NORM_L2SQR)/b.size
    gx=cv2.Sobel(b,cv2.CV_32F,1,0);gy=cv2.Sobel(b,cv2.CV_32F,0,1)
    gradient=(cv2.norm(gx,cv2.NORM_L2SQR)+cv2.norm(gy,cv2.NORM_L2SQR))/b.size
    return dict(target=size,psnr_db=10*np.log10(255**2/mse) if mse>0 else 120.,ssim=ssim,edge_recall=recall,edge_f1=2*precision*recall/(precision+recall) if precision+recall else 0.,laplacian_energy=energy,laplacian_retention=ratio(energy,ref['lap']),gradient_energy=gradient,gradient_retention=ratio(gradient,ref['gradient']),local_contrast_retention=ratio(np.sqrt(np.maximum(vb,0)).mean(),ref['contrast']),rgb_rmse=float(np.sqrt(mse)),high_frequency_proxy_retention=ratio(energy,ref['lap']))


def load_df(out):
    return pd.read_csv(out/'image_metadata_with_split.csv',keep_default_na=False)


def plot_bars(series,path,title,ylabel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(12,5));series.plot.bar(ax=ax);ax.set(title=title,ylabel=ylabel)
    fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)
