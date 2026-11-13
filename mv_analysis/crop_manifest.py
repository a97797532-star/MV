# 한글 안내: 원본 좌표계 XYXY exclusive Crop을 읽고 영상·마스크·BBox에 같은 기하 변환을 적용합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Single-CSV preprocessing contract. No labels, masks, or policy GT are required to crop."""
from pathlib import Path
import json
import cv2
import numpy as np
import pandas as pd
REQUIRED={'image_id','original_path','original_width','original_height','crop_x0','crop_y0','crop_x1','crop_y1','crop_width','crop_height','selected_policy','policy_version','source_fingerprint','coordinate_format','additional_center_crop_allowed'}

# read_metadata: 입력 파일 또는 기록을 읽습니다.
# 입력 인수: path.
def read_metadata(path):
 d=pd.read_csv(path,keep_default_na=False)
 if REQUIRED-set(d.columns):raise ValueError('Missing crop metadata columns: '+str(sorted(REQUIRED-set(d.columns))))
 if d.image_id.duplicated().any():raise ValueError('Duplicate image IDs')
 for r in d.to_dict('records'):crop_xyxy(r)
 return d

# crop_xyxy: 정수 XYXY 끝 좌표 exclusive 규칙과 원본 범위를 검사합니다. 잘못된 좌표를 자동 보정하지 않습니다.
# 입력 인수: record.
def crop_xyxy(record):
 values=[record[k] for k in ['crop_x0','crop_y0','crop_x1','crop_y1']]
 if any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,float,np.number)) or not np.isfinite(v) or int(v)!=v for v in values):raise ValueError('Crop coordinates must be finite integer pixel bounds')
 x0,y0,x1,y1=map(int,values);w,h=int(record['original_width']),int(record['original_height'])
 if not 0<=x0<x1<=w or not 0<=y0<y1<=h:raise ValueError('Crop outside original image or zero area')
 if record['coordinate_format']!='XYXY_EXCLUSIVE_ORIGINAL_PIXELS':raise ValueError('Unknown coordinate convention')
 return x0,y0,x1,y1

# load_crop_rgb: 원본 파일 식별자를 확인하고 저장된 범위만 읽어 BGR을 RGB로 변환합니다.
# 입력 인수: record, data_root, verify_fingerprint.
def load_crop_rgb(record,data_root=None,verify_fingerprint=True):
 p=Path(data_root)/record['source_relative_path'] if data_root is not None else Path(record['original_path'])
 if verify_fingerprint:
  s=p.stat()
  if record['source_fingerprint']!=f'stat-v1:{s.st_size}:{s.st_mtime_ns}':raise ValueError('Source fingerprint changed; revalidate metadata')
 im=cv2.imread(str(p),cv2.IMREAD_COLOR)
 if im is None:raise ValueError('Cannot decode source image')
 if im.shape[:2]!=(int(record['original_height']),int(record['original_width'])):raise ValueError('Original size mismatch')
 x0,y0,x1,y1=crop_xyxy(record)
 return cv2.cvtColor(im[y0:y1,x0:x1],cv2.COLOR_BGR2RGB)

# transform_boxes: Crop 원점을 빼고 경계로 Clip한 뒤 면적이 남는 박스와 동일한 클래스 선택용 keep을 반환합니다.
# 입력 인수: boxes, record, output_hw, padding_xy.
def transform_boxes(boxes,record,output_hw=None,padding_xy=(0,0)):
 b=np.asarray(boxes,dtype=np.float64)
 if b.size==0:return np.empty((0,4),float),np.zeros(0,dtype=bool)
 if b.ndim!=2 or b.shape[1]!=4 or not np.isfinite(b).all() or np.any(b[:,2:]<b[:,:2]):raise ValueError('Invalid original XYXY boxes')
 x0,y0,x1,y1=crop_xyxy(record);a=b.copy();a[:,[0,2]]=np.clip(a[:,[0,2]]-x0,0,x1-x0);a[:,[1,3]]=np.clip(a[:,[1,3]]-y0,0,y1-y0);keep=(a[:,2]>a[:,0])&(a[:,3]>a[:,1])
 if output_hw is not None:
  h,w=map(int,output_hw)
  if min(h,w)<=0:raise ValueError('Invalid adapter output size')
  a[:,[0,2]]*=w/(x1-x0);a[:,[1,3]]*=h/(y1-y0)
 a[:,[0,2]]+=padding_xy[0];a[:,[1,3]]+=padding_xy[1]
 return a[keep],keep

# transform_mask: 이미지와 동일한 영역을 Crop하고 범주형 픽셀에는 NEAREST 좌표 대응을 적용합니다.
# 입력 인수: mask, record, output_hw.
def transform_mask(mask,record,output_hw=None):
 m=np.asarray(mask)
 if m.ndim!=2 or m.shape!=(int(record['original_height']),int(record['original_width'])):raise ValueError('Mask must match original image; missing masks must remain missing')
 x0,y0,x1,y1=crop_xyxy(record);out=m[y0:y1,x0:x1]
 if output_hw is not None:
  h,w=map(int,output_hw)
  if min(h,w)<=0:raise ValueError('Invalid mask output size')
  # Exact floor-coordinate NEAREST semantics, preserving categorical dtype and IDs.
  ys=np.minimum(np.arange(h,dtype=np.int64)*out.shape[0]//h,out.shape[0]-1);xs=np.minimum(np.arange(w,dtype=np.int64)*out.shape[1]//w,out.shape[1]-1);out=out[np.ix_(ys,xs)]
 return out

# require_no_extra_crop: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: record, model, allow_explicit_experiment.
def require_no_extra_crop(record,model,allow_explicit_experiment=False):
 if not allow_explicit_experiment and model in {'PatchCore','Dinomaly','INP-Former'} and record['additional_center_crop_allowed'] not in (True,np.bool_(True)):
  raise ValueError(f'{model}: disable the native additional CenterCrop or declare a separate audited experiment; do not silently apply a second crop')


# iter_metadata: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path, split, chunksize.
def iter_metadata(path,split=None,chunksize=5000):
    """Stream records from the single CSV without loading all rows or images."""
    for chunk in pd.read_csv(path,chunksize=chunksize,keep_default_na=False):
        if REQUIRED-set(chunk.columns):raise ValueError('Missing preprocessing metadata columns')
        if split is not None:chunk=chunk[chunk.split.eq(split)]
        for record in chunk.to_dict('records'):
            crop_xyxy(record)
            yield record
