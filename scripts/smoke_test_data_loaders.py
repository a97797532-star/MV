# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Real-data CPU loader/adapters smoke test, no models/weights/training or new crops."""
import sys,json,hashlib,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd,torch,cv2
from torch.utils.data import DataLoader
from dataclasses import asdict
from mv_analysis.data.manifest import ManifestIndex,ROOT
from mv_analysis.data.datasets import SingleViewDataset,FiveViewDataset
from mv_analysis.data.adapters import SPECS,get_adapter,source_evidence
from mv_analysis.data.collate import single_view_collate,five_view_collate,detection_collate
O=ROOT/'outputs/data_loader_validation_v1';torch.set_num_threads(1);cv2.setNumThreads(1)

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 dest=O/'sample_shapes.json'
 if dest.exists():raise SystemExit('Smoke completed; preserve previous evidence')
 f=json.loads((O/'manifest_fingerprint.json').read_text());index=ManifestIndex(f['selected_manifest'],require_complete=True);d=index.data;rng=np.random.default_rng(20261117);ids=set()
 # add_product: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: pid.
 def add_product(pid):ids.update(d[d.product_id.eq(pid)].image_id)
 for cat in sorted(d.category.unique()):
  for status in ['OK','NG']:
   pool=sorted(d[(d.category==cat)&(d.status==status)].product_id.unique());add_product(rng.choice(pool))
 for split in ['train','validation','test']:
  covered=d[d.image_id.isin(ids)]
  if not covered.split.eq(split).any():add_product(d[d.split.eq(split)].product_id.iloc[0])
 native=pd.read_csv(ROOT/'outputs/spatial_20261111_v7/image_component_summary.csv');empty=set(native[native.annotation_status.eq('provided_empty')].image_path)
 add_product(d[d.source_relative_path.isin(empty)].product_id.iloc[0]);add_product(d[(d.status=='NG')&~d.has_mask].product_id.iloc[0]);add_product(d[d.selected_policy.eq('HUMAN_CROP')].product_id.iloc[0]);add_product(d[d.selected_policy.eq('C')].product_id.iloc[0])
 reviews=pd.read_csv(O/'manual_review_evaluation_risks.csv')
 if reviews.mask_retention.eq(0).any():add_product(d[d.image_id.eq(reviews[reviews.mask_retention.eq(0)].image_id.iloc[0])].product_id.iloc[0])
 dataset=SingleViewDataset(index,image_ids=ids);records=[];models=[];covered_models=set();examples={}
 for i in range(len(dataset)):
  s=dataset[i];x=s['image'];assert x.dtype==torch.float32 and x.shape[0]==3 and 0<=x.min()<=x.max()<=1;assert s['metadata']['manifest_sha256']==f['manifest_sha256']
  if s['mask'] is not None:assert s['mask'].shape==(1,*x.shape[-2:])
  if len(s['boxes']):assert (s['boxes']>=0).all() and (s['boxes'][:,[0,2]]<=x.shape[-1]).all() and (s['boxes'][:,[1,3]]<=x.shape[-2]).all()
  if s['status']=='NG' and s['mask_status']=='MISSING':assert s['mask'] is None and s['detection_status']=='MISSING_ANNOTATION' and not s['detection_trainable']
  records.append(dict(image_id=s['image_id'],product_id=s['product_id'],category=s['category'],view=s['view'],split=s['split'],status=s['status'],policy=s['metadata']['selected_policy'],image_shape=list(x.shape),dtype=str(x.dtype),pixel_min=float(x.min()),pixel_max=float(x.max()),mask_status=s['mask_status'],mask_shape=list(s['mask'].shape) if s['mask'] is not None else None,boxes=len(s['boxes']),class_ids=sorted(set(s['labels'].tolist())),detection_status=s['detection_status'],detection_trainable=s['detection_trainable'],all_defects_cropped_out=s['metadata']['all_defects_cropped_out']))
  examples.setdefault(s['detection_status'],s)
  if s['category'] not in covered_models:
   for name in SPECS:
    out=get_adapter(name)(s);assert out['image'].dtype==torch.float32;assert out['metadata']['adapter_spec']['model_integration']=='UNVERIFIED'
    if out['mask'] is not None:assert out['mask'].shape[-2:]==out['image'].shape[-2:]
    spec=SPECS[name]
    if spec.normalization=='none':assert 0<=out['image'].min()<=out['image'].max()<=spec.pixel_scale
    if spec.normalized_boxes and len(out['boxes']):assert (out['boxes']>=0).all() and (out['boxes']<=1).all()
    models.append(dict(model=name,category=s['category'],image_id=s['image_id'],shape=list(out['image'].shape),dtype=str(out['image'].dtype),pixel_min=float(out['image'].min()),pixel_max=float(out['image'].max()),boxes_format=out['metadata']['boxes_format'],normalized_boxes=out['metadata']['boxes_normalized'],class_ids=out['labels'].tolist(),internal_resize=spec.internal_resize,internal_normalization=spec.internal_normalization,model_integration='UNVERIFIED'))
   covered_models.add(s['category'])
 # Stored native boxes/masks remain None/ragged in collate; no fabricated negatives.
 single=SingleViewDataset(index,image_ids=ids,adapter=get_adapter('EfficientAD-S'));batch=next(iter(DataLoader(single,batch_size=2,num_workers=0,collate_fn=single_view_collate)));assert batch['images'].shape==(2,3,256,256)
 five=FiveViewDataset(single);batch5=next(iter(DataLoader(five,batch_size=2,num_workers=0,collate_fn=five_view_collate)));assert batch5['images'].shape==(2,5,3,256,256);assert all(v==['C1','C2','C3','C4','C5'] for v in batch5['views'])
 valid=[examples[k] for k in ['OK_NEGATIVE','SUPERVISED_VALID'] if k in examples];di,dt=detection_collate([get_adapter('Faster R-CNN')(s) for s in valid]);assert len(di)==len(valid)
 if 'MISSING_ANNOTATION' in examples:
  try:detection_collate([examples['MISSING_ANNOTATION']]);raise AssertionError('Missing NG accepted as detection negative')
  except ValueError:pass
 summary=pd.DataFrame(records);coverage=dict(images=len(records),products=summary.product_id.nunique(),categories=summary.category.nunique(),views=summary.view.value_counts().to_dict(),splits=summary.split.value_counts().to_dict(),statuses=summary.status.value_counts().to_dict(),mask_states=summary.mask_status.value_counts().to_dict(),policies=summary.policy.value_counts().to_dict(),policy_A='NOT_PRESENT_IN_FINAL_MANIFEST',policy_B='NOT_PRESENT_IN_FINAL_MANIFEST',mask_INVALID='NOT_PRESENT_IN_REAL_DATA_UNLESS_DECODE_AUDIT_FINDS_ONE; covered synthetically',models=12,adapter_cases=len(models),five_view_batch_shape=list(batch5['images'].shape),single_view_batch_shape=list(batch['images'].shape),full_crop_or_resize_images_saved=0,model_execution='NOT_RUN',input_adapter_execution='VERIFIED_STANDALONE_CPU',seed=20261117)
 dest.write_text(json.dumps(dict(coverage=coverage,samples=records,model_adapter_samples=models),ensure_ascii=False,indent=2));summary.to_csv(O/'real_sample_loader_summary.csv',index=False)
 evidence=source_evidence();(O/'adapter_contracts.json').write_text(json.dumps({name:dict(spec=asdict(spec),source=evidence[name],condition_change='Official additional CenterCrop disabled; resize-only manifest-preserving experimental condition' if spec.source_center_crop!='none' else 'Deterministic input stage; no new augmentations') for name,spec in SPECS.items()},ensure_ascii=False,indent=2));print(json.dumps(coverage,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
