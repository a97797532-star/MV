# 한글 안내: 저장된 Crop 좌표로 단일 시점과 C1~C5 제품 단위 샘플을 읽고 주석 상태를 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Saved-coordinate Single/Five-view datasets with separate anomaly/detection semantics."""
import numpy as np,pandas as pd,torch,cv2
from collections import Counter
from torch.utils.data import Dataset
from mv_analysis.crop_manifest import crop_xyxy,load_crop_rgb
from .manifest import ManifestIndex,VIEWS,ManifestError,read_table
from .targets import read_mask,crop_targets

# SingleViewDataset: 단일 영상과 해당 주석을 반환합니다. 이상탐지 Train 정상 필터와 검출 적격 여부를 구분합니다.
class SingleViewDataset(Dataset):
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: index, split, task, adapter, image_ids, normal_train_only, detection_valid_only, eligibility, verify_fingerprint.
 def __init__(self,index,*,split=None,task='all',adapter=None,image_ids=None,normal_train_only=True,detection_valid_only=False,eligibility=None,verify_fingerprint=True):
  self.index=index if isinstance(index,ManifestIndex) else ManifestIndex(index);d=self.index.data
  if task not in ['all','anomaly','detection']:raise ValueError('Unknown task')
  if split is not None:
   if split not in ['train','validation','test']:raise ValueError('Unknown split')
   d=d[d.split.eq(split)]
  if task=='anomaly' and normal_train_only:d=d[d.split.ne('train')|d.status.eq('OK')]
  if image_ids is not None:
   ids=set(image_ids)
   if not ids<=set(self.index.data.image_id):raise ValueError('Unknown requested image ID')
   d=d[d.image_id.isin(ids)]
  if detection_valid_only:
   if eligibility is None:raise ValueError('Validated eligibility table required; never assume missing NG is negative')
   q=read_table(eligibility)
   if q.image_id.duplicated().any() or not set(d.image_id)<=set(q.image_id):raise ValueError('Eligibility table missing/duplicate IDs')
   q=q.set_index('image_id');d=d[d.image_id.map(q.detection_trainable).eq(True)]
  self.data=d.reset_index(drop=True);self.task=task;self.adapter=adapter;self.verify_fingerprint=verify_fingerprint;self._native_checks={}
 # __len__: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 def __len__(self):return len(self.data)
 # __getitem__: 저장 좌표로 샘플을 읽고 ID·라벨·마스크 상태를 함께 반환합니다. 읽기 실패를 조용히 제외하지 않습니다.
 # 입력 인수: item.
 def __getitem__(self,item):
  r=self.data.iloc[item].to_dict();rgb=load_crop_rgb(r,data_root=self.index.data_root,verify_fingerprint=self.verify_fingerprint);mask_path=self.index.source_path(r,True) if r['has_mask'] else None;mask,state,error=read_mask(mask_path,(r['original_height'],r['original_width']));boxes,labels=self.index.boxes.get(r['source_relative_path'],(np.empty((0,4),np.float32),np.empty(0,np.int64)));t=crop_targets(r,boxes,labels,mask,state,error)
  native_match=None
  if mask is not None:
   stats=mask_path.stat();key=(r['source_relative_path'],stats.st_size,stats.st_mtime_ns)
   if key not in self._native_checks:
    _,_,components,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8);actual=Counter((int(x),int(y),int(x+w),int(y+h)) for x,y,w,h,_ in components[1:]);self._native_checks[key]=actual==Counter(tuple(v) for v in boxes.tolist())
   native_match=self._native_checks[key]
   if not native_match:t['detection_status']='INVALID_TARGET';t['detection_trainable']=False
  meta={k:v for k,v in t.items() if k not in ['boxes','labels','mask','source_class_ids','box_keep']};meta.update(native_bbox_mask_match=native_match,manifest_sha256=self.index.sha256,policy_version=r['policy_version'],policy_sha256=r.get('policy_sha256',''),source_relative_path=r['source_relative_path'],image_contract='RGB_FLOAT01_UNNORMALIZED',adapter_applied=None,normalization_applied='none',boxes_format='xyxy',boxes_normalized=False,labels_offset=0,additional_center_crop_applied=False,manual_annotation_assisted=bool(r.get('manual_annotation_assisted',False)),requires_evaluation_leakage_review=bool(r.get('requires_evaluation_leakage_review',False)),manual_review_basis='ANNOTATION_REFERENCE_RECORDED' if r.get('manual_annotation_assisted',False) else 'NO_REFERENCE_RECORDED_NOT_PROOF_OF_NO_EXTERNAL_GT_USE',selected_policy=r['selected_policy'])
  sample=dict(image=torch.from_numpy(rgb.copy()).permute(2,0,1).float().div_(255),image_id=r['image_id'],product_id=r['product_id'],category=r['category'],view=r['view'],split=r['split'],status=r['status'],classification_label=t['classification_label'],crop_xyxy=crop_xyxy(r),original_size=(r['original_height'],r['original_width']),image_size=rgb.shape[:2],mask=torch.from_numpy(t['mask'].copy())[None] if t['mask'] is not None else None,mask_status=state,boxes=torch.from_numpy(t['boxes']),labels=torch.from_numpy(t['labels']),detection_status=t['detection_status'],detection_trainable=t['detection_trainable'],localization_valid=t['localization_valid'],metadata=meta)
  return self.adapter(sample) if self.adapter else sample

# FiveViewDataset: 같은 선언 제품의 C1~C5를 순서대로 묶습니다. 기본값은 누락 시점 허용 안 함입니다.
class FiveViewDataset(Dataset):
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: single_view, allow_partial, pad_storage.
 def __init__(self,single_view,*,allow_partial=False,pad_storage=False):
  if not isinstance(single_view,SingleViewDataset):raise TypeError('Pass a configured SingleViewDataset')
  self.single=single_view;self.allow_partial=allow_partial;self.pad_storage=pad_storage;self.groups=[]
  for pid,g in single_view.data.groupby('product_id',sort=False):
   if g.view.duplicated().any() or g.split.nunique()!=1 or g.category.nunique()!=1:raise ManifestError('Five-view group identity or split mismatch')
   if not allow_partial and set(g.view)!=set(VIEWS):raise ManifestError('Incomplete five-view group: '+str(pid))
   self.groups.append((pid,{v:int(i) for i,v in zip(g.index,g.view)}))
 # __len__: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 def __len__(self):return len(self.groups)
 # __getitem__: 저장 좌표로 샘플을 읽고 ID·라벨·마스크 상태를 함께 반환합니다. 읽기 실패를 조용히 제외하지 않습니다.
 # 입력 인수: item.
 def __getitem__(self,item):
  pid,indices=self.groups[item];samples=[];errors=[]
  for view in VIEWS:
   if view not in indices:errors.append(dict(view=view,error='MISSING_VIEW'));continue
   try:samples.append(self.single[indices[view]])
   except Exception as exc:
    if not self.allow_partial:raise RuntimeError(f'Five-view load failed: {pid}/{view}: {exc}') from exc
    errors.append(dict(view=view,error=str(exc)))
  if not samples:raise RuntimeError('No readable views for '+str(pid))
  if not self.allow_partial and (len(samples)!=5 or errors):raise RuntimeError('Incomplete view loading')
  shapes={tuple(s['image'].shape) for s in samples}
  if len(shapes)!=1 and not self.pad_storage:raise ValueError('Five-view tensor requires equal H/W; choose a fixed-size input adapter or explicit storage padding')
  valid_hw=[tuple(q['image'].shape[-2:]) for q in samples];height=max(q[0] for q in valid_hw);width=max(q[1] for q in valid_hw)
  images=[torch.nn.functional.pad(q['image'],(0,width-q['image'].shape[-1],0,height-q['image'].shape[-2])) for q in samples]
  return dict(product_id=pid,category=samples[0]['category'],split=samples[0]['split'],images=torch.stack(images),views=[s['view'] for s in samples],targets=[{k:v for k,v in s.items() if k!='image'} for s in samples],metadata=dict(manifest_sha256=self.single.index.sha256,complete=len(samples)==5 and not errors,missing_or_failed_views=errors,physical_product_identity='UNVERIFIED_DECLARED_GROUP_ONLY',valid_image_sizes=valid_hw,storage_padding=self.pad_storage,storage_padding_requires_unpad_before_native_model=True))
