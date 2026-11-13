# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Verify actual quarantined targets and optional storage padding without changing data."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch,pandas as pd
from functools import partial
from torch.utils.data import DataLoader
from mv_analysis.data import ManifestIndex,SingleViewDataset,FiveViewDataset,get_adapter,detection_collate,five_view_collate,flatten_five_view_batch
from mv_analysis.data.manifest import ROOT
O=ROOT/'outputs/data_loader_validation_v1';torch.set_num_threads(1)

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 dest=O/'target_quarantine_smoke.json'
 if dest.exists():raise SystemExit('Preserve smoke evidence')
 f=json.loads((O/'manifest_fingerprint.json').read_text());ix=ManifestIndex(f['selected_manifest']);bad=pd.read_csv(O/'annotation_errors.csv');ds=SingleViewDataset(ix,image_ids=bad.image_id);rows=[]
 for i in range(len(ds)):
  s=ds[i];assert s['status']=='NG' and s['mask_status']=='PRESENT_POSITIVE' and s['detection_status']=='INVALID_TARGET' and not s['detection_trainable'] and len(s['boxes'])==0
  try:detection_collate([s]);raise AssertionError('Invalid class/bbox target passed as normal')
  except ValueError:pass
  rows.append(dict(image_id=s['image_id'],mask_status=s['mask_status'],detection_status=s['detection_status'],status=s['status'],classification_label=s['classification_label']))
 # No source label repair: document actual HS-directory vs QS-filename ambiguity.
 canonical=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv');diagnostic=canonical[canonical.image_path.isin(bad.image_path)][['image_path','label_conflict','filename_defect_type','directory_defect_type','defect_type','product_id','split']];assert diagnostic.label_conflict.all();diagnostic.to_csv(O/'unresolved_defect_class_conflicts.csv',index=False)
 manual=ix.data[ix.data.selected_policy.eq('HUMAN_CROP')].product_id.iloc[0];second=next(v for v in ix.data.product_id.unique() if v!=manual);ids=ix.data[ix.data.product_id.isin([manual,second])].image_id
 single=SingleViewDataset(ix,image_ids=ids,adapter=get_adapter('Faster R-CNN'));five=FiveViewDataset(single,pad_storage=True);batch=next(iter(DataLoader(five,batch_size=2,collate_fn=partial(five_view_collate,pad_storage=True))));images,targets=flatten_five_view_batch(batch,strict_detection=False);assert len(images)==10 and batch['images'].shape[:3]==(2,5,3)
 for b in range(2):
  group=five[b];pid=group['product_id'];native=[single[i] for i in range(len(single)) if single.data.iloc[i].product_id==pid]
  for v,s in enumerate(native):torch.testing.assert_close(images[b*5+v],s['image']);torch.testing.assert_close(targets[b*5+v]['boxes'],s['boxes'])
 dest.write_text(json.dumps(dict(real_invalid_target_cases=rows,unresolved_class_conflict_images=len(diagnostic),native_five_view_storage_batch=list(batch['images'].shape),flattened_per_model_images=len(images),storage_padding_roundtrip_exact=True,no_boxes_or_crop_coordinates_repaired=True,model_forward_executed=False),ensure_ascii=False,indent=2));print('Real invalid targets quarantined:',len(rows),'native five batch',tuple(batch['images'].shape))
if __name__=='__main__':main()
