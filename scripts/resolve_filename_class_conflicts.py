# 한글 안내: 사용자가 정한 파일명 우선 클래스 정책을 새 파생 주석에 기록하고 원본은 보존합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Materialize user-authorized filename class policy; never rewrite source annotations."""
from pathlib import Path
import sys,json,hashlib,re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd,numpy as np,cv2
from mv_analysis.data.manifest import file_hash,DEFAULT_ANNOTATIONS,DEFAULT_BOXES,DEFAULT_CLASSES
from mv_analysis.data.targets import read_mask
ROOT=Path(__file__).resolve().parents[1]

# build: 입력 자료로부터 필요한 결과 구조를 구성합니다.
# 입력 인수: output.
def build(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 if any(output.iterdir()):raise FileExistsError("Refusing to overwrite existing resolution outputs")
 # Always derive from preserved original tables, independent of loader defaults.
 ap=ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv';bp=ROOT/'outputs/spatial_20261111_v7/defect_bboxes.csv'
 manifest=pd.read_csv(ROOT/'outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v1.csv',keep_default_na=False).set_index('source_relative_path')
 a=pd.read_csv(ap,keep_default_na=False);b=pd.read_csv(bp,keep_default_na=False);classes=json.loads(DEFAULT_CLASSES.read_text())['yolo'];changes=[];new=[]
 conflict=a.label_conflict.eq(True)
 for i,r in a[conflict].iterrows():
  m=re.search(r'_NG_([A-Z]+)_C[1-5]_',Path(r.image_path).name)
  if not m or m[1] not in classes or m[1]!=r.filename_defect_type:raise ValueError('Invalid or unknown filename class: '+r.image_path)
  code=m[1];a.loc[i,'defect_type']=code
  row=manifest.loc[r.image_path];root=Path(row.original_path).parents[len(Path(r.image_path).parts)-1]
  mask,state,error=read_mask(root/r.mask_path if r.mask_path else None,(int(r.height),int(r.width)))
  if state not in ['PRESENT_POSITIVE','MISSING']:raise ValueError(f'Cannot recover valid targets: {state} {error}')
  existing=b.image_path.eq(r.image_path)
  if existing.any():b.loc[existing,'class_id']=classes[code];b.loc[existing,'defect_type']=code
  elif state=='PRESENT_POSITIVE':
   _,_,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8)
   for component,(x,y,w,h,area) in enumerate(stats[1:],1):
    entry={c:'' for c in b.columns};entry.update(image_path=r.image_path,mask_path=r.mask_path,category=r.category,defect_type=code,view=r.view,split=r.split,product_id=r.product_id,class_id=classes[code],x0=int(x),y0=int(y),x1=int(x+w),y1=int(y+h),width=int(w),height=int(h),area=int(w*h),component_id=component,component_area=int(area),bbox_area=int(w*h),relative_area=float(w*h/(r.width*r.height)))
    new.append(entry)
  changes.append(dict(image_path=r.image_path,directory_defect_type=r.directory_defect_type,filename_defect_type=code,previous_defect_type=r.defect_type,resolved_defect_type=code,class_id=classes[code],split=r.split,policy='USER_AUTHORIZED_FILENAME_PRIORITY',mask_status=state))
 b=pd.concat([b,pd.DataFrame(new)],ignore_index=True)
 a.to_csv(output/'image_metadata_with_split.csv',index=False);b.to_csv(output/'defect_bboxes.csv',index=False);pd.DataFrame(changes).to_csv(output/'class_resolution_audit.csv',index=False)
 info=dict(policy='USER_AUTHORIZED_FILENAME_PRIORITY',source_annotations_sha256=file_hash(ap),source_boxes_sha256=file_hash(bp),resolved_images=len(changes),new_components=len(new),annotation_rows=len(a),bbox_rows=len(b),original_conflict_flag_preserved=True,mask_threshold='>0',connectivity=8,coordinates='XYXY_EXCLUSIVE_ORIGINAL_PIXELS',crop_coordinates_changed=False)
 (output/'validation.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));print(json.dumps(info,indent=2))
if __name__=='__main__':build(ROOT/'outputs/filename_class_resolution_v1')
