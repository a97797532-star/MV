import json
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import pytest
from mv_analysis.core import parse_image,metadata,audit_masks,binary_mask,components,brightness_metrics,information_loss
from mv_analysis.cli import main


@pytest.fixture
def dataset(tmp_path):
    root=tmp_path/'data';root.mkdir()
    for number in range(1,5):
        for status in ['OK','NG']:
            for view in range(1,6):
                folder=root/'widget'/status
                if status=='NG':folder=folder/'scratch'
                folder=folder/f'S{number:04}';folder.mkdir(parents=True,exist_ok=True)
                name=f'widget_{number:04}_{status}_'+('scratch_' if status=='NG' else '')+f'C{view}_20260101000000'
                image=np.full((48,64,3),100,np.uint8);image[:,::3]=180
                cv2.imwrite(str(folder/(name+'.jpg')),image)
                if status=='NG':
                    mask=np.zeros((48,64),np.uint8);mask[2:6,3:8]=255;mask[30:35,40:46]=255
                    cv2.imwrite(str(folder/(name+'.png')),mask)
    return root


def test_metadata_split_and_pairs(dataset,tmp_path):
    out=tmp_path/'result';out.mkdir();df,r=metadata(dataset,out)
    assert len(df)==40 and r['png_count']==20 and r['ng_without_mask']==0
    assert not r['incomplete_capture_groups'] and not r['product_split_leakage']
    assert df.groupby('product_id').split.nunique().max()==1
    assert len(pd.read_csv(out/'image_mask_pairs.csv'))==20


def test_mask_and_components():
    mask=np.zeros((8,8),np.uint8);mask[1,1]=255;mask[2,2]=255
    policy={'validated':True,'threshold':0}
    assert components(binary_mask(mask,policy))==[(1,1,3,3,2)]
    with pytest.raises(ValueError):binary_mask(mask,{'validated':False})
    mask[0,0]=128
    with pytest.raises(ValueError):binary_mask(mask,policy)


def test_color_and_resolution():
    bgr=np.zeros((32,32,3),np.uint8);bgr[:,:,2]=255
    assert brightness_metrics(bgr)['brightness']==76
    m=information_loss(bgr,16)
    assert m['ssim']==pytest.approx(1) and m['rgb_rmse']==0
    checker=np.indices((64,64)).sum(0)%2*255;image=np.repeat(checker[:,:,None],3,axis=2).astype('uint8')
    assert information_loss(image,16)['ssim']<.1


def test_full_synthetic_and_exports(dataset,tmp_path):
    out=tmp_path/'output'
    assert main(['--data-root',str(dataset),'--output',str(out),'run-all','--limit','40'])==0
    b=pd.read_csv(out/'defect_bboxes.csv');assert len(b)==40
    assert (b.x1>b.x0).all() and (b.y1>b.y0).all()
    coco=json.loads((out/'defect_coco.json').read_text());assert coco['categories'][0]['id']==1
    classes=json.loads((out/'classes.json').read_text());assert classes['yolo']['scratch']==0
    labels=list((out/'yolo_labels'/'widget'/'OK').rglob('*.txt'));assert len(labels)==20
    assert all(p.read_text()=='' for p in labels)
    assert len(pd.read_csv(out/'per_view_information_loss.csv'))==120
    assert (out/'REAL_IAD_FINAL_ANALYSIS.md').exists()
    known=np.load(out/'occupancy_known.npy');positive=np.load(out/'occupancy_positive.npy')
    assert known.shape==positive.shape and known.shape[1:]==(64,64)
    assert np.all(positive<=known)
    with pytest.raises(SystemExit):main(['--data-root',str(dataset),'--output',str(out),'metadata'])


def test_unverified_mask_stops(dataset,tmp_path):
    mask_path=next(dataset.rglob('*.png'));m=cv2.imread(str(mask_path),0);m[0,0]=128;cv2.imwrite(str(mask_path),m)
    out=tmp_path/'bad';out.mkdir();df,_=metadata(dataset,out);p=audit_masks(dataset,df,out)
    assert not p['validated'] and p['threshold'] is None


def test_unannotated_ng_is_included_without_fabrication(dataset,tmp_path):
    mask=next(dataset.rglob('*.png'));mask.unlink() # synthetic fixture only
    out=tmp_path/'without_mask';out.mkdir();df,r=metadata(dataset,out)
    assert len(df)==40 and r['ng_without_mask']==1 and not r['mask_absence_is_error']
    row=df[df.image_path==str(mask.relative_to(dataset).with_suffix('.jpg'))].iloc[0]
    assert row.status=='NG' and not row.has_mask and row.mask_path==''
    assert r['ng_with_mask']==19 and r['existing_mask_pair_success_rate']==1
    assert not mask.exists()


def test_extra_filename_separator(tmp_path):
    root=tmp_path/'data';path=root/'audiojack'/'NG'/'BX'/'S0001'/'audiojack__0001_NG_BX_C1_20231023111538.jpg'
    row=parse_image(path,root)
    assert row['category']=='audiojack' and row['product_id']=='audiojack/0001'
    assert row['filename_category_token']=='audiojack_'


def test_conflicting_defect_preserves_image(tmp_path):
    root=tmp_path/'data';path=root/'fire_hood'/'NG'/'HS'/'S0131'/'fire_hood_0131_NG_QS_C1_20230928162107.jpg'
    row=parse_image(path,root)
    assert row['status']=='NG' and row['defect_type']=='UNRESOLVED' and row['label_conflict']
    assert row['directory_defect_type']=='HS' and row['filename_defect_type']=='QS'


def test_bbox_does_not_create_negative_labels_for_unannotated_ng(dataset,tmp_path):
    from mv_analysis.stages import bbox
    mask=next(dataset.rglob('*.png'));mask.unlink() # synthetic fixture only
    out=tmp_path/'bbox_missing';out.mkdir();df,_=metadata(dataset,out)
    policy=audit_masks(dataset,df,out)
    bbox(dataset,out,df,policy)
    absent=out/'yolo_labels'/mask.relative_to(dataset).with_suffix('.txt')
    assert not absent.exists()
    report=json.loads((out/'bbox_validation_report.json').read_text())
    assert report['unannotated_ng_skipped']==1 and report['images']==39 and report['errors']==0


def test_two_defect_classes_and_normalized_yolo(dataset,tmp_path):
    from mv_analysis.stages import bbox
    folder=dataset/'widget'/'NG'/'pit'/'S0005';folder.mkdir(parents=True)
    path=folder/'widget_0005_NG_pit_C1_20260101000000.jpg';cv2.imwrite(str(path),np.full((48,64,3),100,np.uint8))
    mask=np.zeros((48,64),np.uint8);mask[4:10,5:12]=255;cv2.imwrite(str(path.with_suffix('.png')),mask)
    out=tmp_path/'multiclass';out.mkdir();df,_=metadata(dataset,out);policy=audit_masks(dataset,df,out);bbox(dataset,out,df,policy)
    classes=json.loads((out/'classes.json').read_text());assert classes['yolo']=={'pit':0,'scratch':1}
    assert classes['coco']=={'pit':1,'scratch':2}
    for label in (out/'yolo_labels').rglob('*.txt'):
        for line in label.read_text().splitlines():
            fields=list(map(float,line.split()));assert fields[0] in (0,1)
            assert all(0<=v<=1 for v in fields[1:])
    from pycocotools.coco import COCO
    coco=COCO(str(out/'defect_coco.json'));assert len(coco.getCatIds())==2 and len(coco.getImgIds())==41


def test_histogram_percentiles_match_numpy():
    rng=np.random.default_rng(4);image=rng.integers(0,256,(47,63,3),dtype=np.uint8)
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);actual=brightness_metrics(image)
    for key,q in [('p05',5),('p50',50),('p95',95)]:assert actual[key]==pytest.approx(np.percentile(gray,q))


def test_gray_mask_requires_reviewed_policy():
    gray=np.array([[0,32,64],[127,192,255]],np.uint8)
    with pytest.raises(ValueError):binary_mask(gray,{'validated':False,'threshold':127,'encoding':'grayscale_uint8'})
    reviewed={'validated':True,'threshold':127,'encoding':'grayscale_uint8'}
    assert binary_mask(gray,reviewed).sum()==2


def test_provided_empty_ng_mask_keeps_ng_class(dataset,tmp_path):
    from mv_analysis.stages import bbox
    mask=next(dataset.rglob('*.png'));cv2.imwrite(str(mask),np.zeros((48,64),np.uint8))
    out=tmp_path/'provided_empty';out.mkdir();df,_=metadata(dataset,out);policy=audit_masks(dataset,df,out);bbox(dataset,out,df,policy)
    records=pd.read_csv(out/'image_component_summary.csv');row=records[records.image_path==str(mask.relative_to(dataset).with_suffix('.jpg'))].iloc[0]
    assert row.status=='NG' and row.components==0 and row.annotation_status=='provided_empty'
    label=out/'yolo_labels'/mask.relative_to(dataset).with_suffix('.txt');assert label.exists() and label.read_text()==''
    report=json.loads((out/'bbox_validation_report.json').read_text());assert report['errors']==0 and report['provided_empty_ng_masks']==1


def test_resume_allows_fresh_stage_but_rejects_changed_cached_producer(dataset,tmp_path):
    out=tmp_path/'producer_guard';assert main(['--data-root',str(dataset),'--output',str(out),'metadata','--limit','40'])==0
    manifest=out/'run.json';record=json.loads(manifest.read_text());record['config']['source_sha256']='historical_source';manifest.write_text(json.dumps(record))
    assert main(['--data-root',str(dataset),'--output',str(out),'--resume','brightness','--limit','40'])==0
    cache=out/'brightness_per_image.jsonl';before=cache.read_bytes()
    record=json.loads(manifest.read_text());record['stage_sources']['brightness']='different_producer';manifest.write_text(json.dumps(record))
    with pytest.raises(SystemExit):main(['--data-root',str(dataset),'--output',str(out),'--resume','brightness','--limit','40'])
    assert cache.read_bytes()==before
