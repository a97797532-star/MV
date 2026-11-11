"""Real-IAD multi-class defect mask -> bounding boxes -> COCO/YOLO.
Run: python realiad_multiclass_bbox.py --data-dir notebook_results_real --threshold 127 --limit 100
Threshold must be visually verified; 127 is only an example.
"""
import argparse
import json
import re
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from PIL import Image

BOX_COLS = ['image_id','image_path','mask_path','category','defect_type','view','project_split','product_key','component_id','class_id','class_name','x0','y0','x1','y1','width','height','area_pixels']
IMAGE_COLS = ['image_id','image_path','mask_path','category','defect_type','view','project_split','product_key','width','height','component_count','mask_status']
ERROR_COLS = ['image_id','image_path','mask_path','error']

def load_rows(data_dir):
    pairs = pd.read_csv(data_dir/'image_mask_pairs.csv', dtype=str).fillna('')
    meta = pd.read_csv(data_dir/'image_metadata_with_split.csv', dtype=str).fillna('')
    mc = 'mask_path' if 'mask_path' in pairs else 'image_path'
    for c in ['original_image_id','original_image_path',mc]:
        if c not in pairs: raise ValueError(f'pairs missing {c}')
    for c in ['image_id','image_path','relative_path','category','view','product_key','project_split']:
        if c not in meta: raise ValueError(f'metadata missing {c}')
    if pairs.original_image_id.duplicated().any() or meta.image_id.duplicated().any():
        raise ValueError('Duplicate image IDs')
    meta['project_split'] = meta.project_split.str.strip().str.lower().replace({'validation':'val'})
    if not meta.project_split.isin(['train','val','test']).all():
        raise ValueError('Missing or invalid project_split')
    if (meta.groupby('product_key').project_split.nunique() > 1).any():
        raise ValueError('Product leakage across train/val/test')
    pair_cols = pairs[['original_image_id','original_image_path',mc]].rename(columns={
        'original_image_id':'image_id','original_image_path':'pair_image_path',mc:'mask_path'})
    rows = meta.merge(pair_cols,on='image_id',how='inner',validate='one_to_one')
    def norm(s): return str(s).replace('\\','/').lower()
    if any(norm(a)!=norm(b) for a,b in zip(rows.image_path,rows.pair_image_path)):
        raise ValueError('Image path mismatch between metadata and pairs')
    def defect(r):
        existing = str(r.get('defect_type','')).strip()
        if existing: return existing.upper()
        parts = re.split(r'[/\\]+', str(r['relative_path']))
        for i, part in enumerate(parts[:-1]):
            if part.upper()=='NG': return parts[i+1].upper()
        return 'UNKNOWN'
    rows['defect_type'] = rows.apply(defect,axis=1)
    if rows.defect_type.isin(['UNKNOWN','OK','']).any():
        raise ValueError('Some paired masks lack a valid defect_type; inspect relative_path')
    return rows

def create_mapping(rows, mode):
    if mode=='defect_type':
        names=sorted(rows.defect_type.unique().tolist())
    else:
        names=sorted((rows.category+'__'+rows.defect_type).unique().tolist())
    return {name:i for i,name in enumerate(names)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',type=Path,default=Path('notebook_results_real'))
    p.add_argument('--threshold',type=int,required=True,help='Manually validated mask threshold, 0..254')
    p.add_argument('--limit',type=int,default=100,help='0 means all')
    p.add_argument('--class-mode',choices=['defect_type','category_defect'],default='defect_type')
    args=p.parse_args()
    if not 0<=args.threshold<=254: p.error('threshold must be between 0 and 254')
    rows=load_rows(args.data_dir)
    # Mapping always built from ALL paired records, not the first 100 or a split.
    mapping=create_mapping(rows,args.class_mode)
    work=rows if args.limit==0 else rows.head(args.limit)
    out=args.data_dir/'bbox_results_multiclass'
    out.mkdir(parents=True,exist_ok=True)
    (out/'classes.json').write_text(json.dumps({'mode':args.class_mode,'names':[k for k in mapping], 'name_to_id':mapping,'mask_threshold':args.threshold},ensure_ascii=False,indent=2),encoding='utf-8')
    records=[]; images=[]; errors=[]
    for i,r in enumerate(work.itertuples(index=False),1):
        try:
            with Image.open(r.image_path) as im: W,H=im.size
            with Image.open(r.mask_path) as im: mask=np.asarray(im)
            if mask.ndim!=2 or mask.dtype!=np.uint8:
                raise ValueError(f'Unsupported mask shape/dtype: {mask.shape}/{mask.dtype}')
            if mask.shape!=(H,W): raise ValueError(f'Mask size {mask.shape} != image {(H,W)}')
            binary=np.ascontiguousarray(mask>args.threshold,dtype=np.uint8)
            n,_,stats,_=cv2.connectedComponentsWithStats(binary,connectivity=8)
            name=r.defect_type if args.class_mode=='defect_type' else f'{r.category}__{r.defect_type}'
            images.append(dict(image_id=r.image_id,image_path=r.image_path,mask_path=r.mask_path,category=r.category,defect_type=r.defect_type,view=r.view,project_split=r.project_split,product_key=r.product_key,width=W,height=H,component_count=n-1,mask_status='positive' if n>1 else 'empty'))
            for component_id in range(1,n):
                x,y,w,h,area=map(int,stats[component_id])
                records.append(dict(image_id=r.image_id,image_path=r.image_path,mask_path=r.mask_path,category=r.category,defect_type=r.defect_type,view=r.view,project_split=r.project_split,product_key=r.product_key,component_id=component_id,class_id=mapping[name],class_name=name,x0=x,y0=y,x1=x+w,y1=y+h,width=w,height=h,area_pixels=area))
        except Exception as e:
            errors.append(dict(image_id=r.image_id,image_path=r.image_path,mask_path=r.mask_path,error=str(e)))
        if i%1000==0: print(f'{i}/{len(work)}')
    bdf=pd.DataFrame(records,columns=BOX_COLS)
    idf=pd.DataFrame(images,columns=IMAGE_COLS)
    edf=pd.DataFrame(errors,columns=ERROR_COLS)
    bdf.to_csv(out/'defect_bboxes.csv',index=False,encoding='utf-8-sig')
    idf.to_csv(out/'image_component_summary.csv',index=False,encoding='utf-8-sig')
    edf.to_csv(out/'bbox_errors.csv',index=False,encoding='utf-8-sig')
    coco={'images':[],'annotations':[],'categories':[{'id':i+1,'name':name} for name,i in mapping.items()]}
    image_ids={}
    for i,r in enumerate(idf.itertuples(index=False),1):
        image_ids[r.image_id]=i
        coco['images'].append(dict(id=i,file_name=r.image_path,width=int(r.width),height=int(r.height)))
    for j,r in enumerate(bdf.itertuples(index=False),1):
        coco['annotations'].append(dict(id=j,image_id=image_ids[r.image_id],category_id=int(r.class_id)+1,bbox=[int(r.x0),int(r.y0),int(r.width),int(r.height)],area=int(r.area_pixels),iscrowd=0))
    (out/'defect_coco.json').write_text(json.dumps(coco,ensure_ascii=False,indent=2),encoding='utf-8')
    label_dir=out/'yolo_labels'
    label_dir.mkdir(exist_ok=True)
    # Clean stale labels from prior runs to avoid accidental dataset contamination.
    for old in label_dir.glob('*.txt'): old.unlink()
    groups={key:g for key,g in bdf.groupby('image_id')}
    for r in idf.itertuples(index=False):
        lines=[]
        for b in groups.get(r.image_id,pd.DataFrame(columns=BOX_COLS)).itertuples(index=False):
            cx=(b.x0+b.x1)/(2*r.width)
            cy=(b.y0+b.y1)/(2*r.height)
            lines.append(f'{b.class_id} {cx:.9f} {cy:.9f} {b.width/r.width:.9f} {b.height/r.height:.9f}')
        (label_dir/f'{r.image_id}.txt').write_text('\n'.join(lines),encoding='utf-8')
    (out/'data.yaml').write_text('names:\n'+''.join(f'  {i}: {name}\n' for name,i in mapping.items()),encoding='utf-8')
    assert len(idf)+len(edf)==len(work)
    assert len(coco['annotations'])==len(bdf)
    if len(bdf):
        assert bdf.class_id.between(0,len(mapping)-1).all()
        dims=idf.set_index('image_id')[['width','height']]
        check=bdf.join(dims,on='image_id',rsuffix='_image')
        assert ((check.x0>=0)&(check.y0>=0)&(check.x1<=check.width_image)&(check.y1<=check.height_image)).all()
    print(f'classes={len(mapping)}, processed={len(idf)}, boxes={len(bdf)}, errors={len(edf)}')
    print('Output:',out)
    print('NOTE: data.yaml contains class names only; image/label train/val/test directory assembly is a separate step.')

if __name__=='__main__': main()
