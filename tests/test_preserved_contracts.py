import json
import cv2
import numpy as np
import pandas as pd
from mv_analysis.splits import apply_preserved_split,reproduce_windows_project_split
from mv_analysis.presence_heatmaps import generate


def test_preserved_split_normalization_and_product_grouping(tmp_path):
    rows=[]
    for i in range(8):
        for v in range(1,6):rows.append(dict(category='widget',image_path=f'widget/NG/HS/S{i:04}/widget_{i:04}_NG_HS_C{v}_20260101000000.jpg',product_id=f'widget/{i:04}',split='train'))
    df=pd.DataFrame(rows);restored=reproduce_windows_project_split(df)
    assert restored.groupby('product_id').split.nunique().max()==1
    assert set(restored.split)=={'train','validation','test'}
    manifest=restored.rename(columns={'image_path':'relative_path','windows_project_split':'project_split','windows_product_key':'product_key'})[['relative_path','project_split','product_key','category']]
    manifest.to_csv(tmp_path/'folds.csv',index=False)
    imported,evidence=apply_preserved_split(df,tmp_path/'folds.csv',tmp_path)
    assert imported.split.tolist()==restored.split.tolist() and evidence['matched']==40


def test_presence_preserves_single_pixel_and_separates_denominators(tmp_path):
    root=tmp_path/'data';root.mkdir();out=tmp_path/'out';out.mkdir()
    one=np.zeros((128,128),np.uint8);one[1,1]=255
    cv2.imwrite(str(root/'one.png'),one);cv2.imwrite(str(root/'empty.png'),np.zeros_like(one))
    rows=[dict(category='widget',defect_type='HS',view='C1',status='NG',split='train',height=128,width=128,image_path=f'{i}.jpg',mask_path=mask) for i,mask in enumerate(['one.png','empty.png',''])]
    rows.append(dict(rows[0],view='C2',image_path='unknown.jpg',mask_path=''))
    generate(root,out,pd.DataFrame(rows),{'validated':True,'threshold':0})
    known=np.load(out/'occupancy_known.npy');positive=np.load(out/'occupancy_positive.npy')
    assert known[0,0,0]==.5 and positive[0,0,0]==1
    assert known[0].sum()==.5 and positive[0].sum()==1
    assert np.isnan(known[1]).all() and np.isnan(positive[1]).all()
    report=pd.read_csv(out/'heatmap_summary.csv');assert report.iloc[0].n_known==2 and report.iloc[0].n_unknown==1
    assert json.loads((out/'heatmap_validation.json').read_text())['errors']==0
