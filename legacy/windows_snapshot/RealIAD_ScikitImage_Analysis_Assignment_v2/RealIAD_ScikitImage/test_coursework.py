import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from core import read_mask
from coursework import (mask_to_boxes, coarse_occupancy, gan_heatmaps,
    export_boxes, compare_resolutions, class_brightness, run_focused)

class FocusContracts(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        self.rows=[]
        for i,(split,cls,val,state) in enumerate([
                ('train','HS',40,'positive'),('train','HS',80,'empty'),
                ('val','HS',120,'positive'),('train','HS',100,'not_provided'),
                ('train','OK',180,'empty')]):
            name=f'im{i}.png';mn=f'm{i}.png'
            Image.fromarray(np.full((8,10,3),val,np.uint8)).save(self.root/name)
            mask=np.zeros((8,10),np.uint8)
            if state=='positive':mask[0,0]=255;mask[5:8,7:10]=255
            if state!='not_provided':Image.fromarray(mask).save(self.root/mn)
            self.rows.append(dict(category='toy',sample_key=f'p{i}',view_id='C1',
                image_path=name,mask_path=mn if state!='not_provided' else '',
                anomaly_class=cls,project_split=split,status='ok',mask_state=state))
        self.df=pd.DataFrame(self.rows)
    def tearDown(self):self.t.cleanup()
    def test_binary_contracts_and_boxes(self):
        self.assertEqual(mask_to_boxes(np.zeros((2,2),bool)),[])
        m=np.zeros((4,5),np.uint8);m[0,0]=m[1,1]=1;m[3,4]=1
        boxes=mask_to_boxes(m)
        self.assertEqual(len(boxes),2)
        self.assertEqual([boxes[0][k] for k in ['x0','y0','x1','y1']],[0,0,2,2])
        self.assertEqual([boxes[1][k] for k in ['x0','y0','x1','y1']],[4,3,5,4])
        for bad in [np.array([[2]]),np.array([[np.nan]]),np.zeros((1,2,3))]:
            with self.assertRaises(ValueError):mask_to_boxes(bad)
        Image.fromarray(np.array([[0,128]],np.uint8)).save(self.root/'bad.png')
        with self.assertRaises(ValueError):read_mask(self.root/'bad.png',(1,2))
    def test_occupancy_preserves_one_pixel(self):
        m=np.zeros((1024,1024),bool);m[1,1]=True
        self.assertEqual(coarse_occupancy(m,64).sum(),1)
        m[2,2]=True
        self.assertEqual(coarse_occupancy(m,64).sum(),1)
    def test_heatmap_split_and_denominator(self):
        info=gan_heatmaps(self.root,self.df,self.root/'heat',grid=4)
        self.assertEqual(len(info),1)
        r=info.iloc[0];self.assertEqual((r.n_known,r.n_positive,r.n_unknown),(2,1,1))
        a=np.load(self.root/'heat'/r.npz)
        self.assertEqual(a['occupancy_known'][0,0],.5)
        self.assertEqual(a['occupancy_positive'][0,0],1.)
        src=pd.read_csv(self.root/'heat/gan_source_manifest.csv')
        self.assertTrue(src.project_split.eq('train').all())
        self.assertFalse(src.sample_key.eq('p2').any())
    def test_export_roundtrip_and_empty(self):
        b,ims=export_boxes(self.root,self.df,self.root/'boxes')
        self.assertEqual(len(ims),4);self.assertEqual(len(b),4)
        normal=ims[ims.anomaly_class=='OK'].iloc[0]
        self.assertEqual((self.root/'boxes/yolo_labels/train'/f'{normal.image_id:06d}.txt').read_text(),'')
        for r in b.itertuples():
            xyxy=np.array([(r.cx_norm-r.w_norm/2)*r.width,(r.cy_norm-r.h_norm/2)*r.height,
                         (r.cx_norm+r.w_norm/2)*r.width,(r.cy_norm+r.h_norm/2)*r.height])
            np.testing.assert_allclose(xyxy,[r.x0,r.y0,r.x1,r.y1],atol=1e-8)
        coco=json.loads((self.root/'boxes/coco_train.json').read_text())
        self.assertEqual(len(coco['images']),3)
        self.assertTrue(all(a['area']==a['bbox'][2]*a['bbox'][3] for a in coco['annotations']))
        ex=pd.read_csv(self.root/'boxes/bbox_excluded.csv');self.assertEqual(len(ex),1)
    def test_resolution_no_mask_and_actual_values(self):
        detail,comps,summary=compare_resolutions(self.root,self.df,self.root/'res',sizes=(8,4,2))
        self.assertEqual(len(detail),15)
        self.assertTrue(detail[detail.sample_key=='p3'].n_components.isna().all())
        self.assertEqual(detail.iloc[0].five_view_fp32_mib,5*3*8*8*4/2**20)
        _,empty,ss=compare_resolutions(self.root,self.df[self.df.anomaly_class=='OK'],self.root/'normal',sizes=(8,))
        self.assertTrue(empty.empty);self.assertTrue(ss.lost_ratio.isna().all())
    def test_brightness_image_weighting_and_class_view(self):
        detail,summary,hist=class_brightness(self.root,self.df,self.root/'bright')
        self.assertEqual(len(detail),5)
        np.testing.assert_allclose(detail['mean'],[40,80,120,100,180])
        np.testing.assert_allclose(hist.groupby(['category','anomaly_class','view_id']).mean_pixel_fraction.sum(),1.)
    def test_no_test_eda(self):
        d=self.df.copy();d.loc[0,'project_split']='test'
        with self.assertRaises(ValueError):run_focused(self.root,d,self.root/'focus')

if __name__=='__main__':unittest.main()
