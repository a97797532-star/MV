"""CPU 전용 합성 검증 데이터. 실제 Real-IAD 통계/모델 성능을 재현하지 않습니다."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def generate(destination='demo_data', seed=2026, image_size=(512,640)):
    dest=Path(destination)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f'{dest}: use a fresh directory to avoid overwriting data')
    (dest/'images').mkdir(parents=True,exist_ok=True)
    (dest/'jsons').mkdir(exist_ok=True)
    rng=np.random.default_rng(seed)
    for category in ['toothbrush','toy']:
        meta={'train':[],'val':[],'test':[]}
        for defect in ['OK','ZW','HS']:
            for product in range(6):
                split='train' if product<4 else ('val' if product==4 else 'test')
                sample=f'{category}_{product+1:04d}_{defect}'
                for view in range(1,6):
                    h,w=image_size
                    rgb=np.clip(rng.normal(65+view*15,4,(h,w,3)),0,255).astype(np.uint8)
                    y0,y1,x0,x1=h//4,h*4//5,w//4,w*4//5
                    rgb[y0:y1,x0:x1]=np.clip(rng.normal(180,3,(y1-y0,x1-x0,3)),0,255).astype(np.uint8)
                    mask=np.zeros((h,w),dtype=np.uint8)
                    if defect!='OK' and (view==1 or (product%2 and view==3)):
                        x=int(rng.integers(w//3,w*2//3));y=int(rng.integers(h//3,h*2//3))
                        if defect=='ZW':mask[y:y+7,x:x+8]=255
                        else:mask[y:y+1,x:x+18]=255
                        mask[4,4]=255 # 해상도 소실 및 경계에 가까운 작은 성분
                        rgb[mask>0]=[220,30,40]
                    name=f'{sample}_C{view}_001.png'
                    image=f'{category}/{name}';m=f'{category}/{sample}_C{view}_001_mask.png'
                    (dest/'images'/category).mkdir(exist_ok=True)
                    Image.fromarray(rgb).save(dest/'images'/image)
                    # 일부 결함 시점 마스크는 미제공. 정상으로 채우면 안 됩니다.
                    if defect=='HS' and product==0 and view==5:m=''
                    if m:Image.fromarray(mask).save(dest/'images'/m)
                    meta[split].append(dict(category=category,anomaly_class=defect,image_path=image,mask_path=m))
        (dest/'jsons'/f'{category}.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='demo_data');p.add_argument('--seed',type=int,default=2026)
    a=p.parse_args();generate(a.out,a.seed)
    print(f'SYNTHETIC DEMO ONLY: {Path(a.out).resolve()}')
