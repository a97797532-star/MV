"""Threshold sensitivity study. Does not silently approve an annotation policy."""
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from .core import read_image,components,save_json

THRESHOLDS=(0,32,64,127,192,254)


def validate_thresholds(root,out,df,per_group=3):
    folder=out/'mask_threshold_validation';folder.mkdir(exist_ok=True)
    selected=[]
    for _,group in df[(df.status=='NG')&(df.mask_path!='')].groupby(['category','defect_type']):
        group=group.sort_values(['view','image_path'])
        indices=np.linspace(0,len(group)-1,min(per_group,len(group)),dtype=int)
        selected.extend(group.iloc[indices].to_dict('records'))
    results=[];hist=np.zeros(256,dtype=np.int64);errors=[];overlay_paths=[]
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for i,row in enumerate(selected):
        try:
            mask=read_image(root/row['mask_path'],True);image=read_image(root/row['image_path']);h,w=mask.shape
            if image.shape[:2]!=mask.shape:raise ValueError('shape mismatch')
            hist+=np.bincount(mask.ravel(),minlength=256)
            ref=mask>127;ref_area=int(ref.sum())
            for threshold in THRESHOLDS:
                binary=(mask>threshold).astype(np.uint8);boxes=components(binary);areas=[a for *_,a in boxes]
                pos=int(binary.sum());intersection=int(((binary>0)&ref).sum());union=int(((binary>0)|ref).sum())
                results.append(dict(image_path=row['image_path'],mask_path=row['mask_path'],category=row['category'],defect_type=row['defect_type'],view=row['view'],threshold=threshold,foreground_pixels=pos,foreground_fraction=pos/(h*w),components=len(boxes),tiny_components_le4=sum(a<=4 for a in areas),bbox_area_sum=sum((x1-x0)*(y1-y0) for x0,y0,x1,y1,a in boxes),mask_area_ratio_to_127=pos/ref_area if ref_area else None,iou_to_127=intersection/union if union else 1.,core255_retention=1. if np.any(mask==255) else None))
            # One multi-threshold crop per category, plus highly sensitive cases.
            sensitive=results[-6]['components']>2*max(results[-3]['components'],1)
            if row['category'] not in overlay_paths or (sensitive and len(list(folder.glob('overlay_*.png')))<45):
                binary=(mask>127).astype('uint8');pts=cv2.findNonZero(binary)
                if pts is not None:
                    x,y,bw,bh=cv2.boundingRect(pts);pad=max(20,int(max(bw,bh)*.15));x0=max(0,x-pad);y0=max(0,y-pad);x1=min(w,x+bw+pad);y1=min(h,y+bh+pad)
                else:x0=y0=0;x1=w;y1=h
                fig,axes=plt.subplots(2,4,figsize=(14,7))
                axes.flat[0].imshow(cv2.cvtColor(image[y0:y1,x0:x1],cv2.COLOR_BGR2RGB));axes.flat[0].set_title('Original JPG crop')
                im=axes.flat[1].imshow(mask[y0:y1,x0:x1],vmin=0,vmax=255,cmap='gray');axes.flat[1].set_title('PNG intensity [0,255]');fig.colorbar(im,ax=axes.flat[1])
                for ax,t in zip(list(axes.flat)[2:],THRESHOLDS):
                    crop=image[y0:y1,x0:x1].copy();m=(mask[y0:y1,x0:x1]>t).astype('uint8');contours,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(crop,contours,-1,(0,0,255),1)
                    ax.imshow(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB));ax.set_title(f'>{t}: {int((mask>t).sum())} px / {results[-6+THRESHOLDS.index(t)]["components"]} components')
                for ax in axes.flat:ax.axis('off')
                fig.suptitle(f"{row['category']}/{row['defect_type']}/{row['view']} at ({x0},{y0})");fig.tight_layout();name=f'overlay_{i:04}_{row["category"]}_{row["defect_type"]}.png';fig.savefig(folder/name,dpi=140);plt.close(fig)
                overlay_paths.append(row['category'])
                save_json(folder/name.replace('.png','.json'),dict(image_path=row['image_path'],mask_path=row['mask_path'],crop=[x0,y0,x1,y1]))
        except Exception as exc:errors.append(dict(image_path=row['image_path'],error=str(exc)))
        if (i+1)%20==0:print(f'mask threshold validation {i+1}/{len(selected)}',flush=True)
    result=pd.DataFrame(results);result.to_csv(folder/'threshold_per_mask.csv',index=False)
    summary=result.groupby('threshold').agg(images=('image_path','count'),foreground_pixels=('foreground_pixels','sum'),components=('components','sum'),tiny_components_le4=('tiny_components_le4','sum'),bbox_area_sum=('bbox_area_sum','sum'),median_area_ratio=('mask_area_ratio_to_127','median'),median_iou_to_127=('iou_to_127','median')).reset_index()
    summary.to_csv(folder/'threshold_summary.csv',index=False)
    result.groupby(['category','defect_type','threshold']).agg(images=('image_path','count'),pixels=('foreground_pixels','sum'),components=('components','sum'),tiny=('tiny_components_le4','sum')).to_csv(folder/'category_defect_threshold_summary.csv')
    np.save(folder/'sample_pixel_histogram.npy',hist)
    save_json(folder/'validation.json',dict(selected=len(selected),success=len(selected)-len(errors),errors=errors,categories=sorted({r['category'] for r in selected}),defect_types=sorted({r['defect_type'] for r in selected}),thresholds=list(THRESHOLDS),unique_values=np.flatnonzero(hist).tolist(),policy_status='pending visual and annotation-semantic review; sensitivity comparison is not ground truth'))
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    for ax,metric in zip(axes,['foreground_pixels','components','tiny_components_le4']):ax.plot(summary.threshold,summary[metric],marker='o');ax.set(xlabel='Threshold: foreground = pixel > threshold',ylabel=metric,title=metric)
    fig.tight_layout();fig.savefig(folder/'threshold_sensitivity.png');plt.close(fig)
    return folder
