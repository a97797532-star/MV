# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Recover freeze export typo without editing hashed runner or recalculating features."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd
import adaptive_crop_gate_experiment as runner

# freeze_reference: 현재 설정과 근거를 고정해 이후 평가와 구분합니다.
# 입력 인수: sample, cfg.
def freeze_reference(sample,cfg):
 B=runner.B;p=B/'frozen_policy.json'
 if p.exists():raise RuntimeError('Policy already frozen; never retune')
 f=runner.cp(B/'checkpoints/features.jsonl');reference=sample[(sample.gate_cohort=='train_reference')|((sample.gate_cohort=='calibration')&sample.status.eq('OK'))]
 assert len(reference)==450 and reference.split.eq('train').all() and reference.status.eq('OK').all()
 assert not any(v.get('cohort')=='final_holdout' for v in f.values()),'Final features must not have been seen before freeze'
 rows=[dict(f[r['image_path']]['features'],category=r['category'],view=r['view'],image_path=r['image_path']) for r in reference.to_dict('records')];d=pd.DataFrame(rows)
 names=['grabcut_change','fg_fraction','component_count','largest_component_fraction','foreground_contrast','boundary_touch_fraction','fg_outside_crop','crop_side','box_aspect','center_x','center_y','crop_center_offset','median_method_iou','max_method_center_distance','min_method_area_ratio']
 bounds={name:dict(low=float(d[name].dropna().quantile(.01)),high=float(d[name].dropna().quantile(.99)),n=int(d[name].notna().sum())) for name in names}
 groups={cat+'/'+view:dict(n=len(g),status='INSUFFICIENT_NOT_USED') for (cat,view),g in d.groupby(['category','view'])}
 thresholds=dict(global_n=len(d),category_view=groups,minimum_category_view_n=cfg['minimum_category_view_n'],quantiles=[.01,.99],note='Image normal-reference tails only; not calibrated product loss/FPR safety thresholds');thresholds['global']=bounds
 d[['image_path','category','view']+names].to_csv(B/'metrics/normal_reference_features.csv',index=False)
 runner.savej(B/'thresholds.json',thresholds)
 recovery=dict(recovery_script_sha256=runner.sha(__file__),reason='Original freeze tried to export feature columns from metadata reference instead of feature dataframe. Quantile calculation and features unchanged.',original_runner_sha256=cfg['runner_sha256'],recomputed_image_features=0)
 runner.savej(B/'freeze_recovery.json',recovery)
 runner.savej(p,dict(policy_version=runner.VERSION,thresholds_sha256=runner.sha(B/'thresholds.json'),module_sha256=cfg['module_sha256'],fit_source_count=450,source='Train normal only, no defect evaluation used',frozen_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),final_holdout_seen=False,team_loss_tolerances=None,scope_approvals={},recovery=recovery))
if __name__=='__main__':
 sample,cfg=runner.prepare();freeze_reference(sample,cfg);print('Recovered export and froze450 Train-normal references; no images recomputed')
