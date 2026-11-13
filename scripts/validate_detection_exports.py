# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Validate every actual YOLO label and COCO box against full metadata and xyxy CSV."""
import argparse
import json
import math
from pathlib import Path
import pandas as pd
from pycocotools.coco import COCO
p=argparse.ArgumentParser();p.add_argument('run',type=Path);args=p.parse_args();root=args.run
validation=json.loads((root/'bbox_validation_report.json').read_text())
if validation['errors']:raise SystemExit('BBox errors unresolved; retain error report')
df=pd.read_csv(root/'image_metadata_with_split.csv',keep_default_na=False);summary=pd.read_csv(root/'image_component_summary.csv').set_index('image_path');boxes=pd.read_csv(root/'defect_bboxes.csv');classes=json.loads((root/'classes.json').read_text());coco=COCO(str(root/'defect_coco.json'))
errors=[];yolo_files=0;yolo_boxes=0;normal_empty=0;provided_empty=0;unannotated_excluded=0;conflict_excluded=0
box_groups={k:g for k,g in boxes.groupby('image_path')}
for ordinal,row in enumerate(df.to_dict('records'),1):
 path=root/'yolo_labels'/Path(row['image_path']).with_suffix('.txt')
 if row['status']=='NG' and (not row['has_mask'] or row['label_conflict']):
  if path.exists():errors.append(dict(image=row['image_path'],error='Unexpected label for unprovided/unresolved NG'))
  if not row['has_mask']:unannotated_excluded+=1
  else:conflict_excluded+=1
  continue
 if not path.exists():errors.append(dict(image=row['image_path'],error='Expected label missing'));continue
 yolo_files+=1;lines=path.read_text().splitlines();expected=box_groups.get(row['image_path']);count=0 if expected is None else len(expected)
 if len(lines)!=count or len(lines)!=int(summary.loc[row['image_path'],'components']):errors.append(dict(image=row['image_path'],error='Component/label count disagreement'))
 if row['status']=='OK' and not lines:normal_empty+=1
 if row['status']=='NG' and summary.loc[row['image_path'],'annotation_status']=='provided_empty':
  provided_empty+=1
  if lines:errors.append(dict(image=row['image_path'],error='Provided-empty mask has nonempty label'))
 for n,line in enumerate(lines):
  try:
   parts=line.split();assert len(parts)==5;cid=int(parts[0]);vals=list(map(float,parts[1:]));cx,cy,bw,bh=vals
   assert cid in classes['yolo'].values() and all(math.isfinite(v) for v in vals)
   assert 0<=cx<=1 and 0<=cy<=1 and 0<bw<=1 and 0<bh<=1
   r=expected.iloc[n];w=row['width'];h=row['height']
   recovered=[(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h]
   assert max(abs(a-b) for a,b in zip(recovered,[r.x0,r.y0,r.x1,r.y1]))<1e-5
   assert cid==int(r.class_id);yolo_boxes+=1
  except Exception as exc:errors.append(dict(image=row['image_path'],line=n+1,error=f'YOLO/xyxy validation: {type(exc).__name__}'))
 if ordinal%25000==0:print(f'Detection format validation {ordinal}/{len(df)}',flush=True)
for ann in coco.anns.values():
 im=coco.imgs.get(ann['image_id']);x,y,w,h=ann['bbox']
 if im is None or ann['category_id'] not in coco.cats or not (0<=x<x+w<=im['width'] and 0<=y<y+h<=im['height']):errors.append(dict(annotation=ann['id'],error='COCO category/image/bbox range invalid'))
if len(coco.imgs)!=yolo_files or len(coco.anns)!=len(boxes) or yolo_boxes!=len(boxes):errors.append(dict(error='COCO/YOLO/CSV totals disagree'))
result=dict(metadata_images=len(df),eligible_images=yolo_files,normal_empty_labels=normal_empty,provided_empty_ng_annotations=provided_empty,unannotated_ng_excluded=unannotated_excluded,masked_class_conflicts_excluded=conflict_excluded,boxes=len(boxes),classes=len(coco.cats),validated_coco_images=len(coco.imgs),validated_coco_annotations=len(coco.anns),validated_yolo_boxes=yolo_boxes,errors=errors)
(root/'detection_export_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
