# 한글 안내: 공통 Crop 이후 모델별 크기·정규화·좌표 형식을 적용합니다. 실제 모델 학습 코드는 아닙니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Deterministic standalone model input contracts. No model instantiation or augmentation."""
from dataclasses import dataclass,asdict
import copy,math
import torch
import torch.nn.functional as F
MEAN=(.485,.456,.406);STD=(.229,.224,.225)
# AdapterSpec: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
@dataclass(frozen=True)
class AdapterSpec:
 name:str
 task:str
 resize:str
 size:int|None
 normalization:str
 boxes_format:str='xyxy'
 normalized_boxes:bool=False
 label_offset:int=0
 pixel_scale:float=1.
 internal_resize:str='none'
 internal_normalization:str='none'
 source_center_crop:str='none'
 effective_center_crop:bool=False
 condition:str='manifest_preserving_v1'
 model_integration:str='UNVERIFIED'
 color:str='RGB'
 dtype:str='float32'
 mask_interpolation:str='NEAREST'

SPECS={
 'PatchCore':AdapterSpec('PatchCore','anomaly','square',224,'imagenet',source_center_crop='256->224; disabled, modified condition'),
 'EfficientAD-S':AdapterSpec('EfficientAD-S','anomaly','square',256,'imagenet'),
 'UniAD':AdapterSpec('UniAD','anomaly','square',224,'imagenet'),
 'HVQ-Trans':AdapterSpec('HVQ-Trans','anomaly','square',224,'imagenet'),
 'Dinomaly':AdapterSpec('Dinomaly','anomaly','square',392,'imagenet',source_center_crop='448->392; disabled, modified condition'),
 'INP-Former':AdapterSpec('INP-Former','anomaly','square',392,'imagenet',source_center_crop='448->392; disabled, modified condition'),
 'Faster R-CNN':AdapterSpec('Faster R-CNN','detection','delegated',None,'none',label_offset=1,internal_resize='short800/max1333, padding32',internal_normalization='ImageNet in model'),
 'RetinaNet':AdapterSpec('RetinaNet','detection','delegated',None,'none',label_offset=1,internal_resize='short800/max1333, padding32',internal_normalization='ImageNet in model'),
 'YOLO11':AdapterSpec('YOLO11','detection','letterbox',640,'none','cxcywh',True),
 'RT-DETRv2':AdapterSpec('RT-DETRv2','detection','square',640,'none','cxcywh',True,internal_normalization='backbone contract UNVERIFIED'),
 'YOLOS':AdapterSpec('YOLOS','detection','short_side',800,'imagenet','cxcywh',True),
 'ViTDet':AdapterSpec('ViTDet','detection','long_side_pad',1024,'none',pixel_scale=255.,internal_normalization='RGB0..255 ImageNet constants in model')}

# xyxy_to_cxcywh: 좌상단/우하단 XYXY를 중심 x/y와 너비/높이로 바꿉니다. 원본 Tensor는 유지합니다.
# 입력 인수: boxes.
def xyxy_to_cxcywh(boxes):
 b=boxes.clone();b[:,:2]=(boxes[:,:2]+boxes[:,2:])/2;b[:,2:]=boxes[:,2:]-boxes[:,:2];return b

# cxcywh_to_xyxy: 중심/크기 좌표를 XYXY로 복원합니다. 정규화 여부는 호출자가 유지하는 계약을 따릅니다.
# 입력 인수: boxes.
def cxcywh_to_xyxy(boxes):
 b=boxes.clone();b[:,:2]=boxes[:,:2]-boxes[:,2:]/2;b[:,2:]=boxes[:,:2]+boxes[:,2:]/2;return b

# ModelInputAdapter: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
class ModelInputAdapter:
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: name, center_crop.
 def __init__(self,name,*,center_crop=False):
  if name not in SPECS:raise KeyError('Unknown model input adapter: '+str(name))
  if center_crop:raise ValueError('Additional CenterCrop is prohibited in this manifest-preserving condition; use a separately audited experiment')
  self.spec=SPECS[name]
 # __call__: 이미 적용된 Adapter/Normalize를 거부하고 이미지·박스·마스크에 같은 Resize/Pad를 적용합니다.
 # 입력 인수: sample.
 def __call__(self,sample):
  out=dict(sample);meta=copy.deepcopy(sample['metadata']);x=sample['image']
  if meta.get('adapter_applied') or meta.get('image_contract')!='RGB_FLOAT01_UNNORMALIZED':raise ValueError('Adapter/Normalize already applied or unsupported image contract')
  if x.dtype!=torch.float32 or x.ndim!=3 or x.shape[0]!=3 or not torch.isfinite(x).all() or x.min()<0 or x.max()>1:raise ValueError('Expected RGB CHW float32 pixels in0..1 before adapter')
  boxes=sample['boxes'].clone();labels=sample['labels'].clone();mask=sample['mask'];mask=mask.clone() if mask is not None else None;h,w=x.shape[-2:];s=self.spec;pad=(0,0,0,0);newh,neww=h,w
  if s.resize=='square':newh=neww=s.size
  elif s.resize=='letterbox':
   scale=min(s.size/h,s.size/w);newh,neww=max(1,round(h*scale)),max(1,round(w*scale));dy,dx=s.size-newh,s.size-neww;pad=(round(dx/2-.1),round(dx/2+.1),round(dy/2-.1),round(dy/2+.1))
  elif s.resize=='long_side_pad':
   scale=s.size/max(h,w);newh,neww=max(1,round(h*scale)),max(1,round(w*scale));pad=(0,s.size-neww,0,s.size-newh)
  elif s.resize=='short_side':
   scale=min(s.size/min(h,w),1333/max(h,w));newh,neww=max(1,round(h*scale)),max(1,round(w*scale))
  elif s.resize!='delegated':raise ValueError('Unknown resize rule')
  if (newh,neww)!=(h,w):
   x=F.interpolate(x[None],size=(newh,neww),mode='bilinear',align_corners=False,antialias=s.resize not in ['letterbox'])[0];boxes*=boxes.new_tensor([neww/w,newh/h,neww/w,newh/h])
   if mask is not None:mask=F.interpolate(mask[None].float(),size=(newh,neww),mode='nearest')[0].bool()
  if any(pad):
   left,right,top,bottom=pad;x=F.pad(x,(left,right,top,bottom),value=114/255 if s.resize=='letterbox' else 0.);boxes+=boxes.new_tensor([left,top,left,top])
   if mask is not None:mask=F.pad(mask,(left,right,top,bottom),value=False)
  # Stabilize only floating-point interpolation/scale roundoff at mathematical bounds.
  x=x.clamp(0.,1.);height,width=x.shape[-2:]
  boxes[:,[0,2]]=boxes[:,[0,2]].clamp(0.,float(width));boxes[:,[1,3]]=boxes[:,[1,3]].clamp(0.,float(height))
  out['boxes_xyxy']=boxes.clone();out['canonical_labels']=labels.clone()
  if s.boxes_format=='cxcywh':boxes=xyxy_to_cxcywh(boxes)
  if s.normalized_boxes:boxes/=boxes.new_tensor([width,height,width,height])
  if len(boxes) and (not torch.isfinite(boxes).all() or (s.normalized_boxes and ((boxes<0).any() or (boxes>1).any()))):raise ValueError('Invalid adapter target coordinates')
  if s.normalization=='imagenet':x=(x-x.new_tensor(MEAN)[:,None,None])/x.new_tensor(STD)[:,None,None]
  else:x=x*s.pixel_scale
  labels=labels+s.label_offset
  meta.update(adapter_applied=s.name,adapter_spec=asdict(s),image_contract='MODEL_ADAPTED_'+s.name,normalization_applied=s.normalization,boxes_format=s.boxes_format,boxes_normalized=s.normalized_boxes,labels_offset=s.label_offset,input_size=(height,width),resize_scale_xy=(neww/w,newh/h),padding_lrtb=pad,additional_center_crop_applied=False,numerical_bound_stabilization='after interpolation/scale only; original saved crop coordinates untouched',interpolation='Tensor BILINEAR align_corners=False; antialias='+str(s.resize!='letterbox')+'; runtime bitwise parity to author pipeline UNVERIFIED')
  if mask is not None:meta['positive_pixels_after_resize']=int(mask.sum());meta['resize_erased_all_positive_mask']=bool(sample['metadata'].get('cropped_positive_pixels') and not mask.any())
  out.update(image=x.contiguous(),boxes=boxes,labels=labels,mask=mask,metadata=meta,image_size=(height,width))
  if mask is not None and not mask.any() and sample['mask_status']=='PRESENT_POSITIVE':out['localization_valid']=False
  return out

# get_adapter: 지정 모델의 독립 입력 변환 객체만 반환합니다. 모델 생성·가중치 다운로드·학습은 하지 않습니다.
# 입력 인수: name.
def get_adapter(name,**kwargs):return ModelInputAdapter(name,**kwargs)

SOURCE_KEYS={'PatchCore':'patchcore','EfficientAD-S':'efficientad','UniAD':'uniad','HVQ-Trans':'hvqtrans','Dinomaly':'dinomaly','INP-Former':'inpformer','Faster R-CNN':'torchvision','RetinaNet':'torchvision','YOLO11':'yolo11','RT-DETRv2':'rtdetrv2','YOLOS':'yolos','ViTDet':'vitdet'}
# source_evidence: 있으면 고정 소스 스냅샷의 저장소·커밋·파일 근거를 읽습니다. 캐시 부재를 모델 통합 성공으로 표시하지 않습니다.
# 입력 인수: root.
def source_evidence(root=None):
 """Pinned local source snapshots; absent snapshots do not imply runtime integration."""
 import json
 from pathlib import Path
 base=Path(root) if root is not None else Path(__file__).resolve().parents[2]/'outputs/model_sources_20261112_v1'
 result={}
 for name,key in SOURCE_KEYS.items():
  path=base/key/'manifest.json'
  if path.exists():
   m=json.loads(path.read_text());result[name]=dict(repository=m['repo'],commit=m['commit'],files=[v['path'] for v in m['files']],source_status='CACHED_STATIC_SOURCE',model_integration='UNVERIFIED')
  else:result[name]=dict(source_status='UNVERIFIED_SNAPSHOT_NOT_AVAILABLE',model_integration='UNVERIFIED')
 return result
