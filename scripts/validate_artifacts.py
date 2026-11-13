# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Validate generated formats/counts without claiming missing stages succeeded."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('run',type=Path);args=p.parse_args();root=args.run;records=[];failures=[]
# check: 조건을 검사하고 확인 결과를 반환합니다.
# 입력 인수: path, condition, detail.
def check(path,condition,detail):
 records.append(dict(path=str(path.relative_to(root)),valid=bool(condition),detail=detail))
 if not condition:failures.append(str(path))
for path in root.rglob('*'):
 if not path.is_file():continue
 try:
  if path.suffix=='.json':json.loads(path.read_text());check(path,True,'JSON parse')
  elif path.suffix=='.npy':a=np.load(path,allow_pickle=False);check(path,(np.isfinite(a)|np.isnan(a)).all() if (root/'heatmap_schema.json').exists() and path.name in {'occupancy_known.npy','occupancy_positive.npy'} else np.isfinite(a).all(),f'NPY {a.shape} {a.dtype}')
  elif path.suffix=='.png':im=cv2.imread(str(path));check(path,im is not None,'PNG decode')
  elif path.suffix=='.csv':
   if path.name=='category_view_loss_summary.csv':df=pd.read_csv(path,header=[0,1])
   else:df=pd.read_csv(path)
   check(path,len(df.columns)>0,f'CSV rows={len(df)}, columns={len(df.columns)}')
 except Exception as exc:check(path,False,str(exc))
metadata=root/'image_metadata_with_split.csv'
if metadata.exists():
 df=pd.read_csv(metadata,keep_default_na=False)
 check(metadata,not df.image_path.duplicated().any(),'unique image paths')
 check(metadata,(df.groupby('product_id').split.nunique()<=1).all(),'no product split leakage')
 check(metadata,((df.mask_path!='')==df.has_mask).all(),'has_mask matches paired path')
 for name in ['brightness_per_image.csv']:
  path=root/name
  if path.exists():
   stage=pd.read_csv(path);check(path,set(stage.image_path)==set(df.image_path),'one record per metadata image')
 path=root/'per_view_information_loss.csv'
 if path.exists():
  stage=pd.read_csv(path);check(path,len(stage)==3*len(df) and set(stage.image_path)==set(df.image_path) and set(stage.target)=={1024,512,256},'3 target sizes per image')
known=root/'occupancy_known.npy';positive=root/'occupancy_positive.npy'
if known.exists() and positive.exists():
 k=np.load(known);v=np.load(positive)
 if (root/'heatmap_schema.json').exists() and json.loads((root/'heatmap_schema.json').read_text()).get('schema')=='presence-v2':
  finite=np.isfinite(k)&np.isfinite(v);check(positive,k.shape==v.shape and np.all(k[np.isfinite(k)]>=0) and np.all(v[np.isfinite(v)]<=1+1e-6) and np.all(v[finite]+1e-6>=k[finite]),'presence frequencies in [0,1]; positive conditional >= known; NaN means no observations')
 else:check(positive,k.shape==v.shape and np.all(v>=0) and np.all(v<=k+1e-6),'positive area sum bounded by observation count')
report=dict(run=str(root),checked=len(records),failures=failures,records=records)
# Validation result is stored alongside its target; future runs parse it too.
(root/'artifact_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(checked=len(records),failures=failures),indent=2));raise SystemExit(bool(failures))
