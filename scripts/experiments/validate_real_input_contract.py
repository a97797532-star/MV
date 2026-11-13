"""실제 이미지를 읽되 예측 성능을 만들지 않는 원본 GT·입력·역변환 계약 검사."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import torch
from mv_analysis.data import ManifestIndex,SingleViewDataset,get_adapter
from mv_analysis.experiments.bridge import ground_truth_records,restore_detection_prediction,restore_anomaly_prediction
from mv_analysis.experiments.contracts import atomic_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('manifest','annotations','bboxes','classes','data-root','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();torch.set_num_threads(1)
 ix=ManifestIndex(a.manifest,a.annotations,a.bboxes,a.classes,data_root=a.data_root,require_complete=True)
 products=[]
 for status in ('OK','NG'):products.append(ix.data[ix.data.status.eq(status)].product_id.iloc[0])
 ids=ix.data[ix.data.product_id.isin(products)].image_id;ground=ground_truth_records(ix,ids)
 dataset=SingleViewDataset(ix,image_ids=ids,adapter=get_adapter('EfficientAD-S'));rows=[]
 for sample in dataset:
  meta=sample['metadata'];h,w=sample['image'].shape[-2:]
  # 타깃 박스를 사용한 기하 왕복 테스트이며 모델 예측·성능평가가 아니다.
  restored=restore_detection_prediction(sample,boxes=sample['boxes'].numpy(),labels=sample['labels'].numpy(),scores=np.ones(len(sample['boxes'])),box_format=meta['boxes_format'],normalized=meta['boxes_normalized'],class_offset=meta['labels_offset'],class_ids=ix.classes['yolo'].values())
  grid=restore_anomaly_prediction(sample,score=0.,score_map=np.zeros((h,w)))
  x0,y0,x1,y1=sample['crop_xyxy'];assert int(grid['observed'].sum())==(x1-x0)*(y1-y0)
  expected=ix.boxes.get(sample['metadata']['source_relative_path'],(np.empty((0,4)),[]))[0].copy()
  if len(expected):
   expected[:,[0,2]]=np.clip(expected[:,[0,2]],x0,x1);expected[:,[1,3]]=np.clip(expected[:,[1,3]],y0,y1);expected=expected[np.all(expected[:,2:]>expected[:,:2],axis=1)]
  np.testing.assert_allclose(np.asarray(restored['boxes']).reshape(-1,4),expected,atol=1e-3)
  rows.append(dict(image_id=sample['image_id'],view=sample['view'],shape=list(sample['image'].shape),mask_status=sample['mask_status'],restored_boxes=len(restored['boxes'])))
 result=dict(status='REAL_INPUT_CONTRACT_ONLY_PASSED',images=len(rows),products=len(products),manifest_sha256=ix.sha256,
             model_inference_performed=False,performance_metrics_generated=False,ground_truth_records=len(ground),rows=rows)
 atomic_json(a.output,result,exclusive=True);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
