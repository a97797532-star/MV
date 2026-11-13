# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Full-result scientific invariants; distinguish numerical limits from model performance."""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();df=pd.read_csv(a.run/'per_view_information_loss.csv');step=pd.read_csv(a.run/'per_image_stepwise_changes.csv');checks={}
checks['full_scope']=len(df)==151050*3 and df.image_path.nunique()==151050
checks['one_record_per_image_target']=not df.duplicated(['image_path','target']).any() and set(df.target)=={1024,512,256} and df.groupby('image_path').target.nunique().eq(3).all()
base=df[df.target==1024];checks['native_identity']=bool((base.rgb_rmse==0).all() and (base.ssim==1).all() and (base.psnr_db==120).all())
for name in ['psnr_db','ssim','rgb_rmse','edge_recall','edge_f1']:
 checks[name+'_finite']=bool(np.isfinite(df[name]).all())
checks['ssim_range']=bool(df.ssim.between(-1.00001,1.00001).all())
for name in ['edge_recall','edge_f1']:checks[name+'_range']=bool(df[name].between(-1e-10,1+1e-10).all())
for name in ['rgb_rmse','laplacian_energy','gradient_energy','laplacian_retention','gradient_retention','local_contrast_retention']:checks[name+'_nonnegative']=bool((df[name].dropna()>=0).all())
checks['high_frequency_proxy_is_declared_laplacian_ratio']=bool(np.allclose(df.high_frequency_proxy_retention,df.laplacian_retention,rtol=0,atol=0,equal_nan=True))
wide=df.pivot(index='image_path',columns='target',values=['ssim','rgb_rmse']);st=step.set_index('image_path');checks['full_step_scope']=len(step)==151050 and step.image_path.nunique()==151050 and set(step.image_path)==set(df.image_path)
if checks['full_step_scope']:
 st=st.loc[wide.index];checks['ssim_drop_matches_direct_targets']=bool(np.allclose(st.ssim_drop_512_to_256,wide['ssim'][512]-wide['ssim'][256],rtol=1e-10,atol=1e-10));checks['rmse_increase_matches_direct_targets']=bool(np.allclose(st.rgb_rmse_increase,wide['rgb_rmse'][256]-wide['rgb_rmse'][512],rtol=1e-10,atol=1e-10))
report=dict(images=df.image_path.nunique(),metric_rows=len(df),step_rows=len(step),success=all(checks.values()),checks={k:bool(v) for k,v in checks.items()},failed=[k for k,v in checks.items() if not v],nonmonotonic_rmse_images=int((wide['rgb_rmse'][256]<wide['rgb_rmse'][512]-1e-10).sum()),nonmonotonic_ssim_images=int((wide['ssim'][256]>wide['ssim'][512]+1e-10).sum()),undefined_ratio_counts=df[['laplacian_retention','gradient_retention','local_contrast_retention']].isna().sum().to_dict(),notes='Nonmonotonic metrics are recorded, not automatically errors. Exact edge agreement is not model recall; high frequency is a Laplacian proxy, not FFT.');(a.run/'resolution_scientific_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));sys.exit(not report['success'])
