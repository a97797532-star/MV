# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Check scientific invariants and annotation coverage in a completed regional run."""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=json.loads((a.run/'regional_run.json').read_text());source=Path(run['config']['source']);meta=pd.read_csv(source/'image_metadata_with_split.csv',keep_default_na=False);df=pd.read_csv(a.run/'regional_brightness_per_image.csv');accepted=df.segmentation_status=='accepted_heuristic';checks={}
checks['unique_images']=bool(df.image_path.nunique()==len(df));checks['scope']=set(df.image_path).issubset(set(meta.image_path)) if run['config']['sample'] else set(df.image_path)==set(meta.image_path)
checks['all_statuses_preserved']=bool(df.status.eq(df.image_path.map(meta.set_index('image_path').status)).all())
checks['uncertain_product_missing']=bool(df.loc[~accepted,'product_mean'].isna().all());checks['uncertain_background_missing']=bool(df.loc[~accepted,'background_mean'].isna().all());checks['accepted_product_finite']=bool(np.isfinite(df.loc[accepted,'product_mean']).all())
reconstructed=df.loc[accepted,'product_mean']*df.loc[accepted,'product_pixel_ratio']+df.loc[accepted,'background_mean']*df.loc[accepted,'background_pixel_ratio'];max_error=float((reconstructed-df.loc[accepted,'whole_mean']).abs().max()) if accepted.any() else 0.;checks['complement_region_mean_identity']=max_error<1e-9
local=df.defect_status=='estimated_product_local_context';checks['local_context_valid']=bool((df.loc[local,'defect_local_pixels']>=20).all() and (df.loc[local,'defect_product_overlap']>=.9).all() and df.loc[local,'segmentation_status'].eq('accepted_heuristic').all())
unprovided=df.status.eq('NG')&~df.has_mask;checks['unprovided_ng_kept']=bool(df.loc[unprovided,'defect_status'].eq('not_provided').all());checks['whole_reproduced']=json.loads((a.run/'whole_brightness_reproduction.json').read_text())['max_absolute_difference']<1e-10
for col in ['whole_mean','product_mean','background_mean','defect_mean']:
 if col in df:checks[col+'_range']=bool(df[col].dropna().between(0,255).all())
report=dict(images=len(df),success=all(checks.values()),checks=checks,max_complement_mean_error=max_error,failed=[k for k,v in checks.items() if not v],ground_truth_accuracy_measured=False);(a.run/'scientific_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));sys.exit(not report['success'])
