# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Independent cached experiment invariants and original/audit hashes; no YOLO calls."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
B=Path('outputs/yolo11_dynamic_crop_v1')
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(2**20),b''):h.update(v)
 return h.hexdigest()
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 cfg=json.loads((B/'config.json').read_text());sample=pd.read_csv(B/'sample_manifest.csv');d=pd.read_csv(B/'metrics/per_image_crop_metrics.csv',low_memory=False)
 infer=[json.loads(x) for x in (B/'inference_checkpoint.jsonl').read_text().splitlines()];ev=[json.loads(x) for x in (B/'evaluation_checkpoint.jsonl').read_text().splitlines()]
 checks={}
 checks['one_inference_per_image']=len(infer)==len({r['image_path'] for r in infer})==1350
 checks['all_images_inference_error_free']=all(r['error'] is None for r in infer)
 checks['cohorts_not_pooled']=sample.groupby('cohort').size().to_dict()=={'general':1200,'mask_informed_risk':150}
 checks['general_balance']=sample[sample.cohort=='general'].groupby(['category','status','view']).size().eq(4).all().item()
 checks['five_view_product_groups']=bool(sample.groupby('product_id').view.nunique().eq(5).all())
 checks['original_split_preserved']=bool(sample.groupby('product_id').split.nunique().eq(1).all()) and not (sample.split=='train').any()
 checks['36_methods_each_image']=len(d)==1350*36 and bool(d.groupby('image_path').method.nunique().eq(36).all())
 checks['full_resize_identity']=bool(d.query('method=="full" and geometric_defect_pixels>0').pixel_retention.eq(1).all())
 checks['mask_retention_range']=bool(d.pixel_retention.dropna().between(0,1).all())
 checks['ng_without_mask_never_relabelled']=bool(d.loc[(d.status=='NG')&~d.has_mask,'mask_state'].eq('not_provided').all())
 checks['fallback_all_available']=bool(d[d.method.str.endswith('_fallback')].available.all())
 # Entire no-candidate set must be source frame for every fallback, not fake empty labels.
 missing=d[~d.available][['image_path','method']]
 lookup={(r['image_path'],r['method']):r for r in d.to_dict('records')}
 fallback_ok=True
 for r in missing.to_dict('records'):
  f=lookup[(r['image_path'],r['method']+'_fallback')];fallback_ok &= f['crop_width']==1024 and f['frame_occupancy']==1
 checks['fallback_missing_is_full_original']=bool(fallback_ok)
 from mv_analysis.yolo_crop_geometry import transform_boxes
 coordinates=True;masks=True;native=True;labels=True
 for record in ev:
  for r in record['metrics']:
   if not r['available']:continue
   x0,y0,x1,y1=r['crop'];coordinates &= 0<=x0<x1<=1024 and 0<=y0<y1<=1024 and x1-x0==y1-y0
   for t in [224,256,392,512,640]:
    transformed,keep=transform_boxes([[x0,y0,x1,y1]],r['crop'],t)
    coordinates &= bool(np.allclose(transformed,[[0,0,t,t]]) and keep.all())
  offline=record['offline']
  if not offline['fallback']:native &= sha(offline['image_file'])==offline['image_sha256']
  if offline.get('mask_file'):
   m=cv2.imread(offline['mask_file'],0);expected=next(r['kept_pixels'] for r in record['metrics'] if r['method']=='confidence_m30_fallback');masks &= m is not None and int(np.count_nonzero(m))==expected
 checks['crop_coordinates_and_all_requested_target_bounds']=bool(coordinates)
 checks['native_png_hashes_match_creation']=bool(native);checks['native_mask_support_matches_evaluation']=bool(masks)
 # Hash source pixels against the pre-existing full content audit (no image metric recalculation).
 audit=pd.read_csv('outputs/content_audit_20261111_v7/content_hashes.csv',usecols=['path','sha256']);audit=dict(zip(audit.path,audit.sha256));original=True
 for record in ev:
  path=record['image_path'];original &= record['offline']['source_sha256']==audit[path] and sha(Path('dataset')/path)==audit[path]
 for path in sample.loc[sample.has_mask,'mask_path']:original &= sha(Path('dataset')/path)==audit[path]
 checks['sample_jpg_png_hashes_match_prior_full_audit']=bool(original)
 baseline=json.loads((B/'baseline_environment_hashes.json').read_text());checks['root_lock_and_dependencies_unchanged']=all(sha(p)==h for p,h in baseline.items())
 checks['weights_sha256_matches_config']=sha(B/'weights/yolo11n.pt')==cfg['weight_sha256']
 checks['sample_manifest_hash_matches_config']=sha(B/'sample_manifest.csv')==cfg['sample_sha256']
 checks['geometry_source_unchanged']=sha('mv_analysis/yolo_crop_geometry.py')==cfg['geometry_source_sha256']
 checks['inference_runner_source_unchanged']=sha('scripts/yolo11_offline_crop_experiment.py')==cfg['runner_source_sha256']
 result=dict(success=all(checks.values()),checks={k:bool(v) for k,v in checks.items()},images=1350,general=1200,risk=150,original_image_metrics_recalculated_for_full_dataset=False,
  product_bbox_ground_truth='UNVERIFIED',product_iou='UNVERIFIED',product_recall='UNVERIFIED',partial_object_rate='UNVERIFIED',product_occupancy='UNVERIFIED',
  inference_single_cached_pass=True,native_crop_candidate='confidence margin30 plus only missing-candidate fallback; not a validated dataset policy',
  pytest_log=str(B/'pytest_results.txt'),push=False)
 p=B/'validation.json'
 if p.exists():raise SystemExit('Preserve existing validation')
 p.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['success']
if __name__=='__main__':main()
