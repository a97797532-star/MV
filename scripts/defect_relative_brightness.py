# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Compute region brightness only for NG with a verified location annotation."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['MV_ANALYSIS_WORKERS']='2'
import cv2
import pandas as pd
from mv_analysis.core import binary_mask,read_image,save_json
from mv_analysis.stages import cached_rows
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--image-run',required=True,type=Path);p.add_argument('--spatial-run',required=True,type=Path);args=p.parse_args();deadline=time.monotonic()+10800
while True:
 try:
  run=json.loads((args.image_run/'run.json').read_text());brightness_done=any(c['command']=='brightness' and c['error'] is None for c in run['commands'])
  policy=json.loads((args.spatial_run/'mask_policy.json').read_text())
  if brightness_done and policy.get('validated'):break
 except (FileNotFoundError,json.JSONDecodeError):pass
 if time.monotonic()>deadline:raise SystemExit('Brightness/policy wait timeout; no fabricated result')
 time.sleep(10)
root=Path(run['config']['root']);df=pd.read_csv(args.image_run/'image_metadata_with_split.csv',keep_default_na=False);ng=df[(df.status=='NG') & df.has_mask]
out=args.spatial_run/'region_brightness';out.mkdir(exist_ok=True)
# calculate: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: row.
def calculate(row):
 image=read_image(root/row['image_path']);mask=binary_mask(read_image(root/row['mask_path'],True),policy).astype(bool);gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
 inside=float(gray[mask].mean()) if mask.any() else None;outside=float(gray[~mask].mean()) if (~mask).any() else None
 return dict(defect_brightness=inside,background_brightness=outside,defect_minus_background=inside-outside if inside is not None and outside is not None else None,defect_to_background_ratio=inside/outside if inside is not None and outside is not None and outside>0 else None,foreground_pixels=int(mask.sum()),foreground_fraction=float(mask.mean()))
result=cached_rows(out,'defect_relative_brightness',ng.to_dict('records'),calculate)
result.groupby(['category','defect_type','view','split']).defect_minus_background.agg(['count','mean','std','median']).to_csv(out/'region_brightness_summary.csv')
save_json(out/'scope.json',dict(total_ng=int((df.status=='NG').sum()),annotated_ng=len(ng),processed=len(result),policy=str(args.spatial_run/'mask_policy.json'),unannotated_ng_excluded=True,unannotated_as_normal=False));print(f'Region brightness completed: {len(result)} annotated NG')
