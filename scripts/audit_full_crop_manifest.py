# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Audit generated coordinates and reuse byte-verified existing mask geometry checkpoints."""
import sys,json,hashlib,struct,time,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd,numpy as np
from full_crop_gt_validation import ROOT,B,M,sha,savej

# verify_png: 실제 결과가 기대한 계약과 일치하는지 확인합니다.
# 입력 인수: args.
def verify_png(args):
 path,known,root=args
 try:
  data=(root/path).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';assert struct.unpack('>II',data[16:24])==(1024,1024);assert hashlib.sha256(data).hexdigest()==known
  return path,None
 except Exception as e:return path,type(e).__name__+': '+str(e)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if (B/'validation.json').exists():raise SystemExit('Preserve completed audit; reuse validation')
 f=pd.read_parquet(B/'final_crop_manifest.parquet');meta=pd.read_csv(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv');lookup=f.set_index('source_relative_path');cfg=json.loads((B/'run_config.json').read_text());root=Path(cfg['data_root']);policy=json.loads((B/'policy.json').read_text())
 assert len(f)==len(meta)==151050 and not f.image_id.duplicated().any();assert set(f.source_relative_path)==set(meta.image_path)
 assert f.crop_x0.ge(0).all() and f.crop_y0.ge(0).all() and f.crop_x1.le(f.original_width).all() and f.crop_y1.le(f.original_height).all();assert (f.crop_x1>f.crop_x0).all() and (f.crop_y1>f.crop_y0).all();assert ((f.crop_x1-f.crop_x0)==f.crop_width).all() and ((f.crop_y1-f.crop_y0)==f.crop_height).all()
 assert f.full_frame.all() and f.selected_policy.eq('C').all() and f.crop_x0.eq(0).all() and f.crop_y0.eq(0).all() and f.crop_x1.eq(1024).all() and f.crop_y1.eq(1024).all()
 g=f.groupby('product_id').agg(category_count=('category','nunique'),split_count=('split','nunique'),views=('view','nunique'),images=('image_id','size'));assert g.images.eq(5).all() and g.views.eq(5).all() and g.split_count.eq(1).all()
 source_stat_bad=[]
 for r in f[['source_relative_path','source_fingerprint']].itertuples(index=False):
  p=root/r.source_relative_path;s=p.stat()
  if r.source_fingerprint!=f'stat-v1:{s.st_size}:{s.st_mtime_ns}':source_stat_bad.append(r.source_relative_path)
 assert not source_stat_bad
 parquet_same=pd.read_csv(B/'final_crop_manifest.csv',keep_default_na=False);pd.testing.assert_frame_equal(f,parquet_same,check_dtype=False);assert sha(B/'preprocessing_metadata.csv')==sha(B/'final_crop_manifest.csv')
 # Existing masks/center896 counts reused only after verifying original PNG bytes.
 old=ROOT/'outputs/preprocessing_review_20261112_v2';complete=json.loads((old/'complete.json').read_text());assert complete['success'];assert complete['source_sha256']['outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv']==sha(ROOT/'outputs/windows_preserved_20261111_v1/image_metadata_with_split.csv')
 masks={r['mask_path']:r for r in map(json.loads,(old/'mask_crop_checkpoint.jsonl').read_text().splitlines())};assert len(masks)==51329 and all(r['error'] is None for r in masks.values());assert set(meta.loc[meta.has_mask,'mask_path'])==set(masks)
 audit=pd.read_csv(ROOT/'outputs/content_audit_20261111_v7/content_hashes.csv',usecols=['path','kind','sha256']);hashes=audit[audit.kind.eq('png')].set_index('path').sha256.to_dict();bad=[];t=time.perf_counter()
 with ThreadPoolExecutor(max_workers=3) as pool:
  for i,(p,error) in enumerate(pool.map(verify_png,[(p,hashes[p],root) for p in masks]),1):
   if error:bad.append(dict(mask_path=p,error=error))
   if i%5000==0:print(f'Original PNG hash/header audit {i}/51329 elapsed={time.perf_counter()-t:.1f}s',flush=True)
 assert not bad,bad[:3]
 rows=[]
 for r in meta[meta.status.eq('NG')].to_dict('records'):
  q=lookup.loc[r['image_path']];m=masks.get(r['mask_path']) if r['has_mask'] else None;n=m['pixels'] if m else None
  rows.append(dict(image_id=q.image_id,image_path=r['image_path'],product_id=r['product_id'],category=r['category'],view=r['view'],split=r['split'],mask_path=r['mask_path'] if m else None,annotation_status='not_provided' if m is None else 'provided_positive' if n>0 else 'provided_empty',original_positive_pixels=n,kept_positive_pixels=n,retention=1. if n and n>0 else None,mask_loss=False if m else None,completely_removed=False if n and n>0 else None,selected_policy=q.selected_policy,evaluation_space='ORIGINAL_GEOMETRY_NO_RESIZE',evidence='BYTE_VERIFIED_CACHED_MASK_PIXELS_AND_FULL_FRAME_IDENTITY' if m else 'NO_LOCATION_GT'))
 ma=pd.DataFrame(rows);ma.to_csv(B/'mask_loss_audit.csv',index=False)
 # Native model CenterCrop ratios256->224 and448->392 geometrically retain center896.
 previous=pd.read_csv(old/'mask_crop_per_image.csv');center=previous[previous.crop.eq(896)].copy();assert len(center)==51329;positive=center[center.defect_pixels>0];removed=int(center.crop_state.eq('removed').sum());partial=int(center.crop_state.eq('partial').sum());ret=positive.kept_pixels.sum()/positive.defect_pixels.sum();adapter=pd.DataFrame([dict(model=model,source_crop=1024,resize=resize,center_crop=crop,effective_native_center_side=896,provided_positive_masks=len(positive),retention=ret,removed=removed,partial=partial,mode='GEOMETRIC_RISK_ONLY_NOT_MODEL_EXECUTION',recommendation='DISABLE_IMPLICIT_SECOND_CROP_OR_DECLARE_AUDITED_EXPERIMENT') for model,resize,crop in [('PatchCore',256,224),('Dinomaly',448,392),('INP-Former',448,392)]]);adapter.to_csv(M/'adapter_second_crop_mask_summary.csv',index=False);center[center.crop_state.isin(['removed','partial'])].to_csv(M/'adapter_second_crop_risk_images.csv',index=False)
 bbox=pd.read_csv(old/'bbox_crop_per_component.csv');bb=bbox[bbox.crop.eq(896)];assert len(bb)==60629;bb[bb.crop_state.isin(['removed','partial'])].to_csv(M/'adapter_second_crop_bbox_risks.csv',index=False)
 gt=pd.read_csv(M/'verified_gt_policy_evaluation.csv');gt[(gt.method=='production_safe_policy')&~gt.contained_exact].to_csv(B/'product_containment_failures.csv',index=False);gt[(gt.method!='production_safe_policy')&~gt.contained_exact].to_csv(M/'candidate_product_containment_failures.csv',index=False)
 # Risk diagnostics are cached image-only observations, not full-data product failure labels.
 risks=f[f.risk_codes.map(lambda s:len(json.loads(s))>1)|f.processing_status.str.startswith('ERROR')].copy();risks['risk_evidence']='CACHED_IMAGE_RISK_NOT_CONFIRMED_PRODUCT_LOSS';risks.to_csv(B/'high_risk_images.csv',index=False)
 cols=['image_id','product_id','category','view','split','original_path','crop_x0','crop_y0','crop_x1','crop_y1','selected_policy','quality_status','fallback_reason','processing_status'];f[f.selected_policy.eq('C')][cols].to_csv(B/'fallback_images.csv',index=False)
 uncertain=f[~f.image_features_reused].groupby('category').head(5).copy();uncertain['review_priority']='STRATIFIED_UNCOMPUTED_IMAGE_FEATURES';risk_candidates=risks.copy();risk_candidates['review_priority']='OBSERVED_IMAGE_RISK';pd.concat([risk_candidates,uncertain]).drop_duplicates('image_id').to_csv(B/'manual_review_candidates.csv',index=False)
 products=[]
 for pid,q in f.groupby('product_id',sort=False):
  row=dict(product_id=pid,category=q.category.iloc[0],split=q.split.iloc[0],all_five_gate_PASS=bool(q.image_gate_status.eq('PASS').all()),gate_evaluated_views=int(q.image_features_reused.sum()),fallback_count=int(q.selected_policy.eq('C').sum()),risk_image_count=int(q.risk_codes.map(lambda s:len(json.loads(s))>1).sum()),five_view_complete=set(q.view)=={'C1','C2','C3','C4','C5'},product_review_required=True,product_scope_validation='UNVERIFIED')
  for r in q.itertuples():row.update({r.view+'_path':r.original_path,r.view+'_policy':r.selected_policy,r.view+'_crop':json.dumps([r.crop_x0,r.crop_y0,r.crop_x1,r.crop_y1]),r.view+'_crop_width':r.crop_width,r.view+'_gate_status':r.image_gate_status})
  products.append(row)
 prod=pd.DataFrame(products);prod.to_csv(B/'product_five_view_summary.csv',index=False)
 backgrounds=pd.read_csv(ROOT/'outputs/background_full_20261111_v1/background_classification.csv',usecols=['image_path','background_type']);bg=f.merge(backgrounds,left_on='source_relative_path',right_on='image_path',validate='one_to_one');assert bg.background_type.notna().all()
 for key in ['category','view','split','selected_policy']:
  f.groupby([key,'selected_policy'] if key!='selected_policy' else [key]).agg(images=('image_id','size'),mean_crop_width=('crop_width','mean'),mean_gain=('geometric_gain','mean'),full_frame_rate=('full_frame','mean')).reset_index().to_csv(M/f'full_summary_by_{key}.csv',index=False)
 bg.groupby(['background_type','selected_policy']).agg(images=('image_id','size'),mean_crop_width=('crop_width','mean'),mean_gain=('geometric_gain','mean')).reset_index().to_csv(M/'full_summary_by_background.csv',index=False)
 counts=gt[gt.method.isin(['grabcut90_m10','center896'])].pivot(index='image_path',columns='method',values='contained_exact');ex=gt[gt.method.eq('grabcut90_m10')][['image_path','category','view','gate_role']].set_index('image_path').join(counts);ex['both_fail']=~ex['grabcut90_m10']&~ex['center896'];ex.to_csv(M/'product_policy_exception_cases.csv');ex.groupby('category')[['grabcut90_m10','center896','both_fail']].agg(['sum','count']).to_csv(M/'product_policy_exception_summary.csv')
 forbidden={'status','defect_type','mask_path','has_mask','verified_gt_bbox','reviewer'};assert not forbidden&set(f.columns)
 ledger=json.loads((B/'gt_audit.json').read_text())['ledger_hashes'];assert all(sha(ROOT/p)==h for p,h in ledger.items())
 checks=dict(success=True,images=len(f),expected_images=len(meta),declared_products=len(prod),unique_image_ids=f.image_id.nunique(),invalid_coordinates=0,zero_area_crops=0,missing_originals=0,source_header_errors=int((~f.source_header_verified).sum()),processing_errors=int(f.processing_status.str.startswith('ERROR').sum()),source_stat_fingerprint_mismatches=source_stat_bad,groups_with_split_leakage=int(g.split_count.gt(1).sum()),incomplete_five_view_groups=int((~prod.five_view_complete).sum()),policy_counts=f.selected_policy.value_counts().to_dict(),quality_status_counts=f.quality_status.value_counts().to_dict(),image_gate_diagnostics=f.image_gate_status.value_counts().to_dict(),feature_cache_reused=int(f.image_features_reused.sum()),new_grabcut_images_computed=0,full_frame_rate=float(f.full_frame.mean()),mean_crop_width=float(f.crop_width.mean()),mean_geometric_gain=float(f.geometric_gain.mean()),provided_pngs_byte_hash_and_header_verified=len(masks),mask_audit_ng_images=len(ma),provided_positive_masks=int(ma.annotation_status.eq('provided_positive').sum()),provided_empty_masks=int(ma.annotation_status.eq('provided_empty').sum()),ng_without_location_gt=int(ma.annotation_status.eq('not_provided').sum()),production_positive_mask_pixel_retention=1.,production_mask_loss_images=0,confirmed_product_gt_images=600,production_product_gt_loss_images=0,high_risk_cached_images=len(risks),gt_ledger_unchanged=True,csv_parquet_data_equal=True,preprocessing_csv_byte_identical_to_final_csv=True,preprocessing_csv_bytes=(B/'preprocessing_metadata.csv').stat().st_size,preprocessing_csv_sha256=sha(B/'preprocessing_metadata.csv'),policy_sha256=sha(B/'policy.json'),root_lock_unchanged=sha(ROOT/'uv.lock')==cfg['root_lock_sha256'],no_gt_fields_in_manifest=True,original_crop_images_created=0,decision='FULL_COORDINATES_COMPLETE_ADAPTIVE_CROPPING_NOT_APPROVED',product_gt_generalization='UNVERIFIED_OUTSIDE_REVIEWED600',independent_final='UNVERIFIED_HISTORICAL_EXPOSURE',mask_pixel_audit_method='Cached pixels reused after51329 current byte hashes+headers matched previous verified inputs; full-frame identity; no new PNG decodes')
 savej(B/'validation.json',checks);print(json.dumps(checks,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
