# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
from pathlib import Path
import json,hashlib,copy,sys
import numpy as np,pandas as pd,pytest,cv2,torch
from torch.utils.data import DataLoader
from mv_analysis.data.manifest import ManifestIndex,ManifestError,geometry_errors
from mv_analysis.data.datasets import SingleViewDataset,FiveViewDataset
from mv_analysis.data.adapters import get_adapter,SPECS,xyxy_to_cxcywh,cxcywh_to_xyxy,MEAN,STD
from mv_analysis.data.collate import single_view_collate,five_view_collate,detection_collate
from mv_analysis.data.targets import read_mask,crop_targets
torch.set_num_threads(1)

# fixture_data: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: tmp_path.
@pytest.fixture
def fixture_data(tmp_path):
 records=[];annotations=[];boxes=[]
 for kind,status,split in [('ok','OK','train'),('positive','NG','test'),('missing','NG','validation'),('empty','NG','test'),('invalid','NG','validation')]:
  pid='category/'+kind+'/serial'
  for view in ['C1','C2','C3','C4','C5']:
   rel=pid+'/'+view+'.jpg';p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True);im=np.empty((16,20,3),np.uint8);im[:]=[10,20,30];cv2.imwrite(str(p),im);st=p.stat();id=hashlib.sha256(rel.encode()).hexdigest()[:16]
   r=dict(image_id=id,product_id=pid,category='category',view=view,split=split,source_relative_path=rel,original_path=str(p),original_width=20,original_height=16,crop_x0=2,crop_y0=3,crop_x1=18,crop_y1=15,crop_width=16,crop_height=12,full_frame=False,coordinate_format='XYXY_EXCLUSIVE_ORIGINAL_PIXELS',policy_version='synthetic-fixed-v1',policy_sha256='synthetic-policy',source_fingerprint=f'stat-v1:{st.st_size}:{st.st_mtime_ns}',selected_policy='HUMAN_CROP',additional_center_crop_allowed=False,normalization_applied=False,resize_applied=False)
   records.append(r);maskrel=pid+'/'+view+'.png' if kind in ['positive','empty','invalid'] else ''
   annotations.append(dict(image_path=rel,product_id=pid,category='category',view=view,split=split,status=status,has_mask=bool(maskrel),mask_path=maskrel))
   if maskrel:
    if kind=='invalid':(tmp_path/maskrel).write_bytes(b'not a PNG')
    else:
     m=np.zeros((16,20),np.uint8)
     if kind=='positive':
      m[5:8,6:9]=255;m[4,12]=255
      for coords,cls in [([6,5,9,8],0),([12,4,13,5],1)]:boxes.append(dict(image_path=rel,x0=coords[0],y0=coords[1],x1=coords[2],y1=coords[3],class_id=cls))
     cv2.imwrite(str(tmp_path/maskrel),m)
 return dict(frame=pd.DataFrame(records),annotations=pd.DataFrame(annotations),bboxes=pd.DataFrame(boxes),classes={'yolo':{'AK':0,'BX':1},'coco':{'AK':1,'BX':2},'classification':{'OK':0,'NG':1}},root=tmp_path)

# index: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: data.
def index(data):return ManifestIndex(data['frame'],data['annotations'],data['bboxes'],data['classes'],data_root=data['root'],require_complete=True)
# one: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: data, kind, adapter.
def one(data,kind,adapter=None):
 ix=index(data);id=ix.data[ix.data.product_id.eq('category/'+kind+'/serial')].image_id.iloc[0];return SingleViewDataset(ix,image_ids=[id],adapter=adapter)[0]

# test_normal_rgb_shape_range_and_fingerprint: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_normal_rgb_shape_range_and_fingerprint(fixture_data):
 s=one(fixture_data,'ok');assert s['image'].shape==(3,12,16) and s['image'].dtype==torch.float32;assert s['image'].min()>=0 and s['image'].max()<=1;assert s['image'][0].mean()>s['image'][2].mean();assert s['crop_xyxy']==(2,3,18,15);assert s['original_size']==(16,20);assert s['status']=='OK'

# test_positive_mask_crop_and_box_origin_class_ids: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_positive_mask_crop_and_box_origin_class_ids(fixture_data):
 s=one(fixture_data,'positive');assert s['mask_status']=='PRESENT_POSITIVE' and s['mask'].shape==(1,12,16) and s['mask'].sum()==10;assert s['mask'][0,1,10] # native one-pixel component
 torch.testing.assert_close(s['boxes'],torch.tensor([[4,2,7,5],[10,1,11,2]],dtype=torch.float32));assert s['labels'].tolist()==[0,1];assert s['detection_trainable'] and s['detection_status']=='SUPERVISED_VALID'

# test_missing_empty_invalid_are_distinct_ng: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data, kind, state, contract.
@pytest.mark.parametrize('kind,state,contract',[('missing','MISSING','MISSING_ANNOTATION'),('empty','PRESENT_EMPTY','EMPTY_NG_REVIEW'),('invalid','INVALID','INVALID_TARGET')])
def test_missing_empty_invalid_are_distinct_ng(fixture_data,kind,state,contract):
 s=one(fixture_data,kind);assert s['status']=='NG' and s['classification_label']==1 and s['mask_status']==state and s['detection_status']==contract and not s['detection_trainable'];assert not s['localization_valid'];assert (s['mask'] is None)==(state in ['MISSING','INVALID'])
 with pytest.raises(ValueError):detection_collate([s])

# test_ok_is_legitimate_detection_negative: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_ok_is_legitimate_detection_negative(fixture_data):
 s=one(fixture_data,'ok');assert s['boxes'].shape==(0,4) and s['labels'].shape==(0,) and s['detection_status']=='OK_NEGATIVE';assert s['detection_trainable'] and s['mask'] is None;images,targets=detection_collate([s]);assert len(images)==1 and targets[0]['status']=='OK'

# test_clipped_and_removed_boxes_no_ng_reclassification: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_clipped_and_removed_boxes_no_ng_reclassification(fixture_data):
 d=copy.deepcopy(fixture_data);sel=d['frame'].product_id.eq('category/positive/serial');d['frame'].loc[sel,['crop_x0','crop_x1','crop_width']]=[8,11,3];s=one(d,'positive');assert s['metadata']['crop_clipped_boxes']==1 and s['metadata']['crop_removed_boxes']==1;torch.testing.assert_close(s['boxes'],torch.tensor([[0,2,1,5]],dtype=torch.float32));assert s['labels'].tolist()==[0] and s['status']=='NG'
 d['frame'].loc[sel,['crop_x0','crop_x1','crop_width']]=[0,2,2];s=one(d,'positive');assert s['mask_status']=='PRESENT_POSITIVE' and s['metadata']['all_defects_cropped_out'];assert s['classification_label']==1 and s['detection_status']=='INVALID_TARGET' and not s['detection_trainable']

# test_invalid_crop_never_repaired: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data, change.
@pytest.mark.parametrize('change',[("crop_x1",21),("crop_x0",2.5),("crop_y1",3),("coordinate_format",'inclusive')])
def test_invalid_crop_never_repaired(fixture_data,change):
 d=copy.deepcopy(fixture_data);d['frame'][change[0]]=d['frame'][change[0]].astype(object);d['frame'].loc[0,change[0]]=change[1]
 with pytest.raises(ManifestError):index(d)

# test_duplicates_and_split_leakage: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_duplicates_and_split_leakage(fixture_data):
 d=copy.deepcopy(fixture_data);d['frame']=pd.concat([d['frame'],d['frame'].iloc[:1]],ignore_index=True)
 with pytest.raises(ManifestError):index(d)
 d=copy.deepcopy(fixture_data);d['frame'].loc[0,'split']='validation'
 with pytest.raises(ManifestError):index(d)

# test_annotation_identity_not_path_guessed: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_annotation_identity_not_path_guessed(fixture_data):
 d=copy.deepcopy(fixture_data);d['annotations'].loc[0,'product_id']='wrong'
 with pytest.raises(ManifestError):index(d)

# test_anomaly_train_ok_filter_preserves_evaluation_ng: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_anomaly_train_ok_filter_preserves_evaluation_ng(fixture_data):
 ix=index(fixture_data);ds=SingleViewDataset(ix,task='anomaly');assert ds.data[ds.data.split.eq('train')].status.eq('OK').all();assert ds.data[ds.data.split.eq('test')].status.eq('NG').all()

# test_five_order_shape_and_batch_collate: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_five_order_shape_and_batch_collate(fixture_data):
 ds=SingleViewDataset(index(fixture_data),adapter=get_adapter('PatchCore'));five=FiveViewDataset(ds);s=five[0];assert s['images'].shape==(5,3,224,224) and s['views']==['C1','C2','C3','C4','C5'];assert len(s['targets'])==5;batch=next(iter(DataLoader(five,batch_size=2,collate_fn=five_view_collate)));assert batch['images'].shape==(2,5,3,224,224);assert len(batch['targets'][0])==5

# test_partial_views_off_by_default: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_partial_views_off_by_default(fixture_data):
 ix=index(fixture_data);ids=ix.data[ix.data.product_id.eq('category/ok/serial')].image_id.tolist()[:4];ds=SingleViewDataset(ix,image_ids=ids,adapter=get_adapter('EfficientAD-S'))
 with pytest.raises(ManifestError):FiveViewDataset(ds)
 partial=FiveViewDataset(ds,allow_partial=True)[0];assert partial['images'].shape[0]==4
 with pytest.raises(ValueError):five_view_collate([partial])

# test_decode_failure_is_explicit: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_decode_failure_is_explicit(fixture_data):
 d=fixture_data;p=Path(d['frame'].iloc[0].original_path);p.write_bytes(b'bad JPEG');ds=SingleViewDataset(index(d),verify_fingerprint=False)
 with pytest.raises(ValueError,match='decode'):ds[0]
 with pytest.raises(RuntimeError,match='Five-view load failed'):FiveViewDataset(ds)[0]

# test_single_collate_does_not_make_missing_masks: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_single_collate_does_not_make_missing_masks(fixture_data):
 a,b=one(fixture_data,'ok'),one(fixture_data,'positive');batch=single_view_collate([a,b]);assert batch['images'].shape==(2,3,12,16);assert batch['targets'][0]['mask'] is None and batch['targets'][1]['mask'] is not None

# test_all_model_input_contracts: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data, name.
@pytest.mark.parametrize('name',list(SPECS))
def test_all_model_input_contracts(fixture_data,name):
 raw=one(fixture_data,'positive');s=get_adapter(name)(raw);spec=SPECS[name];assert s['image'].dtype==torch.float32 and s['image'].shape[0]==3;assert s['mask'].shape[-2:]==s['image'].shape[-2:];assert s['canonical_labels'].tolist()==[0,1] and s['labels'].tolist()==[spec.label_offset,1+spec.label_offset]
 if spec.resize in ['square','letterbox','long_side_pad']:assert s['image'].shape[-2:]==(spec.size,spec.size)
 elif spec.resize=='delegated':assert s['image'].shape[-2:]==raw['image'].shape[-2:]
 else:assert min(s['image'].shape[-2:])==800 and max(s['image'].shape[-2:])<=1333
 if spec.normalized_boxes:assert (s['boxes']>=0).all() and (s['boxes']<=1).all()
 assert not s['metadata']['additional_center_crop_applied'];assert s['metadata']['adapter_spec']['model_integration']=='UNVERIFIED'
 with pytest.raises(ValueError):get_adapter(name)(s)
 with pytest.raises(ValueError):get_adapter(name,center_crop=True)
 # Raw input sample must not be changed by the adapter.
 assert raw['metadata']['adapter_applied'] is None and raw['labels'].tolist()==[0,1]

# test_no_external_normalize_for_internal_normalizing_detector: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_no_external_normalize_for_internal_normalizing_detector(fixture_data):
 raw=one(fixture_data,'positive');s=get_adapter('Faster R-CNN')(raw);torch.testing.assert_close(s['image'],raw['image']);assert s['metadata']['normalization_applied']=='none'

# test_yolo_letterbox_geometric_alignment: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_yolo_letterbox_geometric_alignment(fixture_data):
 s=one(fixture_data,'positive',get_adapter('YOLO11'));xyxy=cxcywh_to_xyxy(s['boxes'])*s['boxes'].new_tensor([640,640,640,640]);torch.testing.assert_close(xyxy,s['boxes_xyxy']);assert s['metadata']['padding_lrtb']==(0,0,80,80)

# test_tiny_mask_resize_loss_recorded_without_relabeling: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_tiny_mask_resize_loss_recorded_without_relabeling():
 x=torch.zeros(3,1024,1024);mask=torch.zeros(1,1024,1024,dtype=torch.bool);mask[0,1,1]=True;s=dict(image=x,mask=mask,mask_status='PRESENT_POSITIVE',boxes=torch.tensor([[1.,1.,2.,2.]]),labels=torch.tensor([0]),status='NG',classification_label=1,localization_valid=True,metadata=dict(image_contract='RGB_FLOAT01_UNNORMALIZED',adapter_applied=None,cropped_positive_pixels=1));out=get_adapter('PatchCore')(s);assert out['status']=='NG' and out['classification_label']==1 and out['mask_status']=='PRESENT_POSITIVE';assert out['metadata']['resize_erased_all_positive_mask'] and not out['localization_valid']

# test_xyxy_cxcywh_round_trip: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_xyxy_cxcywh_round_trip():
 b=torch.tensor([[0.,0.,10.,20.],[1.,2.,3.,4.]]);torch.testing.assert_close(cxcywh_to_xyxy(xyxy_to_cxcywh(b)),b)

# test_reproducible_manifest_and_legacy_geometry: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_reproducible_manifest_and_legacy_geometry(fixture_data):
 a=index(fixture_data);b=index(fixture_data);assert a.sha256==b.sha256;s=one(fixture_data,'positive');from mv_analysis.crop_manifest import transform_boxes
 expected,keep=transform_boxes([[6,5,9,8],[12,4,13,5]],fixture_data['frame'].iloc[5].to_dict());np.testing.assert_allclose(s['boxes'].numpy(),expected);assert len(a.sha256)==64

# test_positive_mask_wrong_size_is_invalid: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_positive_mask_wrong_size_is_invalid(fixture_data):
 r=fixture_data['annotations'][fixture_data['annotations'].status.eq('NG')&fixture_data['annotations'].has_mask].iloc[0];p=fixture_data['root']/r.mask_path;cv2.imwrite(str(p),np.ones((5,5),np.uint8));s=one(fixture_data,'positive');assert s['mask_status']=='INVALID' and s['mask'] is None and not s['detection_trainable']

# test_detection_filter_requires_explicit_validated_contract: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_detection_filter_requires_explicit_validated_contract(fixture_data):
 ix=index(fixture_data)
 with pytest.raises(ValueError):SingleViewDataset(ix,task='detection',detection_valid_only=True)
 eligible=pd.DataFrame(dict(image_id=ix.data.image_id,detection_trainable=ix.data.status.eq('OK')));ds=SingleViewDataset(ix,task='detection',detection_valid_only=True,eligibility=eligible);assert ds.data.status.eq('OK').all()

# test_native_mask_bbox_mismatch_blocks_detection: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_native_mask_bbox_mismatch_blocks_detection(fixture_data):
 d=copy.deepcopy(fixture_data);d['bboxes'].loc[0,'x0']=5;s=one(d,'positive');assert s['metadata']['native_bbox_mask_match'] is False and s['detection_status']=='INVALID_TARGET' and not s['detection_trainable']

# test_approval_match_and_unapproved_crop_not_promoted: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_approval_match_and_unapproved_crop_not_promoted(fixture_data):
 sys.path.insert(0,str(Path('scripts').resolve()));from select_final_preprocessing import audit_candidate
 from review_product_bboxes import json_bytes
 r=fixture_data['frame'].iloc[0].to_dict();base=r|dict(crop_x0=0,crop_y0=0,crop_x1=20,crop_y1=16,crop_width=20,crop_height=16,selected_policy='C',full_frame=True,policy_version='base',policy_sha256='basehash')
 event=dict(status='APPROVED_CROP',crop_xyxy=[2,3,18,15],base_manifest_sha256='basefile',image_path=r['source_relative_path'],source_fingerprint=r['source_fingerprint'],reviewer='synthetic-test',reviewed_utc='test-time',preview_evaluation={'annotation_assisted':False})
 candidate=r|dict(crop_review_status='APPROVED_CROP',crop_reviewer='synthetic-test',crop_reviewed_utc='test-time',manual_annotation_assisted=False,policy_version='base+human-override-v1',policy_sha256=hashlib.sha256(('basehash'+hashlib.sha256(json_bytes(event)).hexdigest()).encode()).hexdigest())
 assert not audit_candidate(pd.DataFrame([base]),pd.DataFrame([candidate]),{r['image_id']:event},'basefile')
 changed=candidate|dict(crop_x0=3,crop_width=15)
 assert any('CROP_DOES_NOT_MATCH' in e['error'] for e in audit_candidate(pd.DataFrame([base]),pd.DataFrame([changed]),{r['image_id']:event},'basefile'))
 assert any('UNAPPROVED' in e['error'] for e in audit_candidate(pd.DataFrame([base]),pd.DataFrame([candidate]),{},'basefile'))

# test_saved_status_does_not_change_pixel_transform: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_saved_status_does_not_change_pixel_transform(fixture_data):
 a=one(fixture_data,'ok');b=one(fixture_data,'positive');torch.testing.assert_close(a['image'],b['image']);assert a['classification_label']!=b['classification_label']

# test_five_variable_native_shape_is_not_silently_resized: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_five_variable_native_shape_is_not_silently_resized(fixture_data):
 d=copy.deepcopy(fixture_data);d['frame'].loc[0,['crop_x1','crop_width']]=[17,15]
 ds=SingleViewDataset(index(d))
 with pytest.raises(ValueError,match='equal H/W'):FiveViewDataset(ds)[0]

# test_explicit_storage_padding_roundtrip_preserves_model_input_and_targets: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_explicit_storage_padding_roundtrip_preserves_model_input_and_targets(fixture_data):
 from functools import partial
 from mv_analysis.data.collate import flatten_five_view_batch
 d=copy.deepcopy(fixture_data);d['frame'].loc[0,['crop_x1','crop_width']]=[17,15];single=SingleViewDataset(index(d),adapter=get_adapter('Faster R-CNN'));five=FiveViewDataset(single,pad_storage=True);batch=next(iter(DataLoader(five,batch_size=2,collate_fn=partial(five_view_collate,pad_storage=True))));assert batch['images'].shape[:3]==(2,5,3)
 images,targets=flatten_five_view_batch(batch);assert len(images)==10
 expected=single[0];torch.testing.assert_close(images[0],expected['image']);torch.testing.assert_close(targets[0]['boxes'],expected['boxes']);assert images[0].shape[-1]==15

# test_interpolation_output_stays_within_declared_pixel_bounds: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_interpolation_output_stays_within_declared_pixel_bounds(fixture_data):
 raw=one(fixture_data,'positive');raw['image'].fill_(1.)
 for name in ['YOLO11','RT-DETRv2','ViTDet']:
  out=get_adapter(name)(raw);assert out['image'].max()<=SPECS[name].pixel_scale and out['image'].min()>=0

# test_flatten_five_cannot_silently_train_missing_ng_as_negative: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data.
def test_flatten_five_cannot_silently_train_missing_ng_as_negative(fixture_data):
 from mv_analysis.data.collate import flatten_five_view_batch
 ix=index(fixture_data);ids=ix.data[ix.data.product_id.eq('category/missing/serial')].image_id;ds=SingleViewDataset(ix,image_ids=ids,adapter=get_adapter('Faster R-CNN'));five=FiveViewDataset(ds,pad_storage=True);batch=five_view_collate([five[0]],pad_storage=True)
 with pytest.raises(ValueError):flatten_five_view_batch(batch)
 images,targets=flatten_five_view_batch(batch,strict_detection=False);assert len(images)==5 and all(not t['detection_trainable'] for t in targets)

# test_saved_a_b_policy_coordinates_loaded_without_recalculation: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: fixture_data, policy, coords.
@pytest.mark.parametrize('policy,coords',[('A',(10,10,1010,1010)),('B',(64,64,960,960))])
def test_saved_a_b_policy_coordinates_loaded_without_recalculation(fixture_data,policy,coords):
 d=copy.deepcopy(fixture_data);r=d['frame'].iloc[0];p=Path(r.original_path);cv2.imwrite(str(p),np.full((1024,1024,3),80,np.uint8));st=p.stat();x0,y0,x1,y1=coords
 fields=dict(original_width=1024,original_height=1024,crop_x0=x0,crop_y0=y0,crop_x1=x1,crop_y1=y1,crop_width=x1-x0,crop_height=y1-y0,selected_policy=policy,source_fingerprint=f'stat-v1:{st.st_size}:{st.st_mtime_ns}')
 for key,value in fields.items():d['frame'].at[0,key]=value
 s=one(d,'ok');assert s['crop_xyxy']==coords and s['image'].shape==(3,y1-y0,x1-x0) and s['metadata']['selected_policy']==policy
