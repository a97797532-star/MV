# 한글 안내: 클래스가 바뀐 샘플을 실제 로딩하고 이전 전수 감사와 구분한 새 계약을 기록합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Revalidate only changed annotation targets and reuse the frozen full decode audit."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd,torch
from mv_analysis.data.manifest import ManifestIndex,ROOT,file_hash
from mv_analysis.data.datasets import SingleViewDataset
from mv_analysis.data.collate import detection_collate

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 torch.set_num_threads(1);out=ROOT/'outputs/filename_class_resolution_v1';dest=out/'annotation_contract.csv'
 if dest.exists():raise SystemExit('Preserve existing validation; use a new version')
 audit=pd.read_csv(out/'class_resolution_audit.csv');prior=ROOT/'outputs/data_loader_validation_v1';ix=ManifestIndex(ROOT/'outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v1.csv');ds=SingleViewDataset(ix,image_ids=ix.data[ix.data.source_relative_path.isin(audit.image_path)].image_id)
 contract=pd.read_csv(prior/'annotation_contract.csv',keep_default_na=False).set_index('image_id').astype(object);rows=[]
 for sample in ds:
  meta=sample['metadata'];positive=sample['mask_status']=='PRESENT_POSITIVE';assert sample['status']=='NG'
  assert sample['detection_status']==('SUPERVISED_VALID' if positive else 'MISSING_ANNOTATION')
  if positive:
   assert sample['labels'].tolist()==[5] and meta['native_bbox_mask_match'];detection_collate([sample])
  else:assert sample['mask'] is None and not sample['detection_trainable']
  updates={k:v for k,v in meta.items() if k in contract.columns};updates.update(detection_status=sample['detection_status'],detection_trainable=sample['detection_trainable'],localization_valid=sample['localization_valid'],final_box_count=len(sample['boxes']),final_class_ids=json.dumps(sample['labels'].tolist()),validation_status='VALID_FILENAME_PRIORITY',annotation_hash_match=False)
  for k,v in updates.items():contract.at[sample['image_id'],k]=v
  rows.append(dict(image_id=sample['image_id'],mask_status=sample['mask_status'],detection_status=sample['detection_status'],class_ids=sample['labels'].tolist()))
 contract=contract.reset_index();contract['class_resolution_policy']='USER_AUTHORIZED_FILENAME_PRIORITY';contract.to_csv(dest,index=False);contract[~contract.detection_trainable.eq(True)].to_csv(out/'detection_ineligible.csv',index=False)
 info=dict(status='VERIFIED_CHANGED_TARGETS_WITH_REUSED_PRIOR_FULL_DECODE',rechecked_images=len(rows),positive_targets_recovered=7,missing_annotations_kept_missing=3,detection_counts=contract.detection_status.value_counts().to_dict(),crop_manifest_sha256=ix.sha256,prior_contract_sha256=file_hash(prior/'annotation_contract.csv'),annotations_sha256=file_hash(out/'image_metadata_with_split.csv'),bboxes_sha256=file_hash(out/'defect_bboxes.csv'),annotation_hash_match_note='Changed rows differ from original annotation hashes intentionally; source full-decode evidence is reused, not rerun.',rows=rows)
 original=json.loads((out/'validation.json').read_text());assert file_hash(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv')==original['source_annotations_sha256'];assert file_hash(ROOT/'outputs/spatial_20261111_v7/defect_bboxes.csv')==original['source_boxes_sha256']
 (out/'target_revalidation.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in info.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
