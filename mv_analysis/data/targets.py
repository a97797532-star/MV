# 한글 안내: 결함 마스크의 제공 상태와 Crop 이후 BBox·클래스·검출 학습 가능 여부를 구분합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Annotation states and geometric target transforms, independent of model/task filtering."""
from pathlib import Path
import cv2,numpy as np
from mv_analysis.crop_manifest import crop_xyxy,transform_boxes
MASK_STATES=('PRESENT_POSITIVE','PRESENT_EMPTY','MISSING','INVALID')
DETECTION_STATES=('SUPERVISED_VALID','OK_NEGATIVE','MISSING_ANNOTATION','EMPTY_NG_REVIEW','INVALID_TARGET')

# read_mask: 미제공·손상·빈 마스크·양성 마스크를 구분합니다. 마스크 없는 NG에 빈 정상 정답을 만들지 않습니다.
# 입력 인수: path, original_hw.
def read_mask(path,original_hw):
 if path is None:return None,'MISSING',''
 try:
  data=Path(path).read_bytes();mask=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_GRAYSCALE)
  if mask is None:raise ValueError('Cannot decode mask')
  if tuple(mask.shape)!=tuple(original_hw):raise ValueError('Mask size does not match original image')
  binary=mask>0
  return binary,'PRESENT_POSITIVE' if binary.any() else 'PRESENT_EMPTY',''
 except Exception as e:return None,'INVALID',type(e).__name__+': '+str(e)

# crop_targets: BBox와 마스크를 함께 변환하고 잘림·제거 수 및 검출 학습 가능 상태를 기록합니다.
# 입력 인수: row, source_boxes, source_labels, mask, mask_status, mask_error.
def crop_targets(row,source_boxes,source_labels,mask,mask_status,mask_error=''):
 boxes=np.asarray(source_boxes,dtype=np.float32).reshape(-1,4);labels=np.asarray(source_labels,dtype=np.int64).reshape(-1)
 if len(boxes)!=len(labels):raise ValueError('Source box/label length mismatch')
 x0,y0,x1,y1=crop_xyxy(row);out,keep=transform_boxes(boxes,row);out=out.astype(np.float32);kept_labels=labels[keep].copy();translated=boxes-np.array([x0,y0,x0,y0],np.float32);clipped=int(np.any(out!=translated[keep],axis=1).sum()) if len(out) else 0
 cropped=mask[y0:y1,x0:x1].copy() if mask is not None else None;native_pixels=int(mask.sum()) if mask is not None else None;cropped_pixels=int(cropped.sum()) if cropped is not None else None;unsupported=0
 if cropped is not None:
  for a in out:
   bx0,by0=np.floor(a[:2]).astype(int);bx1,by1=np.ceil(a[2:]).astype(int)
   if not cropped[by0:by1,bx0:bx1].any():unsupported+=1
 # 영상의 OK/NG 라벨은 보존하고, 검출 학습에 쓸 위치 주석의 유효성만 별도로 판단합니다.
 if row['status']=='OK':
  detection='OK_NEGATIVE' if not len(boxes) and mask_status!='INVALID' and not native_pixels else 'INVALID_TARGET'
 elif mask_status=='MISSING':detection='MISSING_ANNOTATION'
 elif mask_status=='PRESENT_EMPTY':detection='EMPTY_NG_REVIEW'
 elif mask_status=='INVALID' or not len(boxes) or not len(out) or not cropped_pixels or unsupported:detection='INVALID_TARGET'
 else:detection='SUPERVISED_VALID'
 return dict(boxes=out,labels=kept_labels,mask=cropped,mask_status=mask_status,mask_error=mask_error,classification_label=int(row['status']=='NG'),detection_status=detection,detection_trainable=detection in ['OK_NEGATIVE','SUPERVISED_VALID'],localization_valid=mask_status=='PRESENT_POSITIVE' and bool(cropped_pixels),source_box_count=len(boxes),crop_clipped_boxes=clipped,crop_removed_boxes=int((~keep).sum()),boxes_without_mask_support=unsupported,original_positive_pixels=native_pixels,cropped_positive_pixels=cropped_pixels,crop_mask_loss=bool(native_pixels and cropped_pixels<native_pixels),all_defects_cropped_out=bool(native_pixels and not cropped_pixels),source_class_ids=labels.copy(),box_keep=keep)
