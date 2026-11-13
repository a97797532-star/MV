# 한글 안내: 저장된 전처리 CSV와 주석을 연결하고 좌표·식별자·제품 그룹·Split 무결성을 검사합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read-only manifest validation and explicit annotation joins. Never choose a crop."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from mv_analysis.crop_manifest import crop_xyxy

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_ANNOTATIONS=ROOT/'outputs/filename_class_resolution_v1/image_metadata_with_split.csv'
DEFAULT_BOXES=ROOT/'outputs/filename_class_resolution_v1/defect_bboxes.csv'
DEFAULT_CLASSES=ROOT/'outputs/spatial_20261111_v7/classes.json'
VIEWS=('C1','C2','C3','C4','C5')

# file_hash: 파일을 메모리에 한꺼번에 올리지 않고 SHA-256을 계산해 배포물과 입력 버전을 식별합니다.
# 입력 인수: path.
def file_hash(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()

# read_table: DataFrame은 복사하고 CSV/Parquet는 명시한 경로에서 읽습니다. CSV의 빈 문자열을 임의의 결측 숫자로 바꾸지 않습니다.
# 입력 인수: value.
def read_table(value):
 if isinstance(value,pd.DataFrame):return value.copy()
 return pd.read_parquet(value) if Path(value).suffix=='.parquet' else pd.read_csv(value,keep_default_na=False)

# ManifestError: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
class ManifestError(ValueError):
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: message, errors.
 def __init__(self,message,errors=None):super().__init__(message);self.errors=errors

# geometry_errors: 중복 ID·경로, 정수 exclusive 좌표, 크기·원본 범위·시점·Split을 전수 검사해 오류 목록을 반환합니다.
# 입력 인수: d.
def geometry_errors(d):
 errors=[];needed=['image_id','product_id','category','view','split','source_relative_path','original_path','original_width','original_height','crop_x0','crop_y0','crop_x1','crop_y1','crop_width','crop_height','coordinate_format','policy_version','source_fingerprint','selected_policy']
 if set(needed)-set(d.columns):return pd.DataFrame([dict(image_id='',error='MISSING_COLUMNS:'+','.join(sorted(set(needed)-set(d.columns))))])
 for key in ['image_id','source_relative_path','original_path']:
  for value in d.loc[d[key].duplicated(keep=False),'image_id']:errors.append(dict(image_id=value,error='DUPLICATE_'+key))
 cols=['original_width','original_height','crop_x0','crop_y0','crop_x1','crop_y1','crop_width','crop_height'];n=d[cols].apply(pd.to_numeric,errors='coerce');finite=np.isfinite(n.to_numpy()).all(axis=1);integer=(n==np.floor(n)).all(axis=1)
 valid=finite&integer&(n.original_width>0)&(n.original_height>0)&(n.crop_x0>=0)&(n.crop_y0>=0)&(n.crop_x1<=n.original_width)&(n.crop_y1<=n.original_height)&(n.crop_x1>n.crop_x0)&(n.crop_y1>n.crop_y0)&((n.crop_x1-n.crop_x0)==n.crop_width)&((n.crop_y1-n.crop_y0)==n.crop_height)&d.coordinate_format.eq('XYXY_EXCLUSIVE_ORIGINAL_PIXELS')
 for value in d.loc[~valid,'image_id']:errors.append(dict(image_id=value,error='INVALID_OR_NONINTEGER_EXCLUSIVE_CROP'))
 for value in d.loc[~d.view.isin(VIEWS),'image_id']:errors.append(dict(image_id=value,error='INVALID_VIEW'))
 for value in d.loc[~d.split.isin(['train','validation','test']),'image_id']:errors.append(dict(image_id=value,error='INVALID_SPLIT'))
 if 'full_frame' in d:
  full=n.crop_x0.eq(0)&n.crop_y0.eq(0)&n.crop_x1.eq(n.original_width)&n.crop_y1.eq(n.original_height)
  for value in d.loc[d.full_frame.ne(full),'image_id']:errors.append(dict(image_id=value,error='FULL_FRAME_FLAG_MISMATCH'))
 for value in d.loc[d.selected_policy.eq('C')&~(n.crop_x0.eq(0)&n.crop_y0.eq(0)&n.crop_x1.eq(n.original_width)&n.crop_y1.eq(n.original_height)),'image_id']:errors.append(dict(image_id=value,error='C_FALLBACK_NOT_FULL_FRAME'))
 return pd.DataFrame(errors,columns=['image_id','error'])

# group_audit: 선언 제품별 시점 중복·Split 누수·품목 불일치를 검사합니다. 실제 물리 제품 동일성의 증명은 아닙니다.
# 입력 인수: d, require_complete.
def group_audit(d,require_complete=False):
 g=d.groupby('product_id').agg(images=('image_id','size'),views=('view','nunique'),splits=('split','nunique'),categories=('category','nunique'))
 duplicated=d.duplicated(['product_id','view']).any()
 if g.splits.gt(1).any() or g.categories.gt(1).any() or duplicated:raise ManifestError('Product split/category leakage or duplicated view')
 if require_complete and not (g.images.eq(5)&g.views.eq(5)).all():raise ManifestError('Incomplete five-view product group')
 return g

# ManifestIndex: CSV 출처·원본 좌표·제품 그룹·주석 연결을 검사하고 이후 로더가 재사용할 인덱스를 구성합니다.
class ManifestIndex:
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: manifest, annotations, bboxes, classes, data_root, require_complete.
 def __init__(self,manifest,annotations=None,bboxes=None,classes=None,data_root=None,require_complete=False):
  self.data=read_table(manifest).reset_index(drop=True);self.path=None if isinstance(manifest,pd.DataFrame) else str(Path(manifest).resolve());self.sha256=file_hash(manifest) if self.path else hashlib.sha256(self.data.to_csv(index=False).encode()).hexdigest()
  errors=geometry_errors(self.data)
  if len(errors):raise ManifestError('Invalid crop manifest; no coordinate repair is performed',errors)
  self.groups=group_audit(self.data,require_complete);self.data_root=Path(data_root).resolve() if data_root is not None else None
  self.annotation_source=annotations
  labels=read_table(DEFAULT_ANNOTATIONS if annotations is None else annotations)
  if labels.image_path.duplicated().any():raise ManifestError('Duplicated annotation image paths')
  required={'image_path','product_id','category','view','split','status','has_mask','mask_path'}
  if required-set(labels.columns):raise ManifestError('Missing canonical annotation columns')
  original=self.data.copy();joined=original.merge(labels[list(required)].rename(columns={'product_id':'annotation_product_id','category':'annotation_category','view':'annotation_view','split':'annotation_split'}),left_on='source_relative_path',right_on='image_path',how='left',validate='one_to_one',indicator=True)
  if not joined['_merge'].eq('both').all():raise ManifestError('Missing image annotation; labels must not be inferred from paths')
  for col in ['product_id','category','view','split']:
   if not joined[col].eq(joined['annotation_'+col]).all():raise ManifestError('Canonical annotation identity mismatch: '+col)
  if not joined.status.isin(['OK','NG']).all():raise ManifestError('Unknown OK/NG annotation label')
  if not joined.has_mask.isin([True,False]).all():raise ManifestError('has_mask must be boolean')
  self.data=joined.drop(columns=['_merge']+['annotation_'+c for c in ['product_id','category','view','split']]);self.boxes={};self.bbox_source=bboxes
  if bboxes is None:bboxes=DEFAULT_BOXES
  boxes=read_table(bboxes)
  if len(boxes):
   needed={'image_path','class_id','x0','y0','x1','y1'}
   if needed-set(boxes.columns):raise ManifestError('Missing defect BBox columns')
   arr=boxes[['x0','y0','x1','y1']].to_numpy(float)
   if not np.isfinite(arr).all() or np.any(arr[:,2:]<=arr[:,:2]) or np.any(arr<0):raise ManifestError('Invalid original defect boxes')
   if not np.equal(boxes.class_id,np.floor(boxes.class_id)).all() or boxes.class_id.lt(0).any():raise ManifestError('Invalid source class IDs')
   for p,g in boxes.groupby('image_path',sort=False):self.boxes[p]=(g[['x0','y0','x1','y1']].to_numpy(np.float32),g.class_id.to_numpy(np.int64))
  self.classes=json.loads(Path(DEFAULT_CLASSES if classes is None else classes).read_text()) if not isinstance(classes,dict) else classes
  allowed=set(self.classes['yolo'].values())
  if any(not set(ids)<=allowed for _,ids in self.boxes.values()):raise ManifestError('BBox source IDs do not match canonical zero-based class map')
 # source_path: 개인 data_root와 상대 경로를 연결하며 마스크 경로가 데이터 루트 밖으로 벗어나지 않게 검사합니다.
 # 입력 인수: row, mask.
 def source_path(self,row,mask=False):
  if mask:
   raw=row['mask_path']
   if not isinstance(raw,str) or not raw:return None
   root=self.data_root or Path(row['original_path']).parents[len(Path(row['source_relative_path']).parts)-1];p=(root/raw).resolve()
   if not p.is_relative_to(root.resolve()):raise ManifestError('Mask path escapes data root')
   return p
  if self.data_root is not None:
   p=(self.data_root/row['source_relative_path']).resolve()
   if not p.is_relative_to(self.data_root):raise ManifestError('Image path escapes data root')
   return p
  return Path(row['original_path'])
