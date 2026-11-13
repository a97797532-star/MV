# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Apply the documented nonzero policy only after real integrity/sensitivity evidence.

This is a project analysis policy supported by the official reference evaluator,
not a claim that every annotation is semantically perfect.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--integrity',required=True,type=Path);p.add_argument('--study',required=True,type=Path);p.add_argument('--run',required=True,type=Path);args=p.parse_args()
policy=json.loads((args.integrity/'mask_policy.json').read_text());evidence=json.loads((args.study/'mask_threshold_validation'/'validation.json').read_text());meta=json.loads((args.run/'metadata_validation_report.json').read_text())
if not policy['integrity_valid'] or policy['errors'] or policy['inspected']!=meta['ng_with_mask']:raise SystemExit('All provided NG masks must pass integrity inspection')
if evidence['success']!=evidence['selected'] or evidence['errors'] or len(evidence['categories'])!=30:raise SystemExit('Threshold study must cover all categories without errors')
if not set(evidence['thresholds'])=={0,32,64,127,192,254}:raise SystemExit('Incomplete threshold comparison')
output=args.run/'mask_policy.json'
if output.exists():raise SystemExit('Policy already exists; preserve it and use a new run')
policy.update(validated=True,threshold=0,encoding='grayscale_uint8',policy_status='reviewed_nonzero_reference_policy',
              policy='Foreground = grayscale pixel > 0, no component area filter',
              reviewed=datetime.now(timezone.utc).isoformat(),
              reference='https://github.com/Tencent/AnomalyDetection_Real-IAD/blob/main/utils/eval_helper.py#L249',
              rationale='Reference EvalPerPixelAUC uses >0; 336-mask 6-threshold study and original-image overlays show high thresholds erode/split annotations. Preserve fractional boundary support.',
              integrity_evidence=str(args.integrity),threshold_evidence=str(args.study),
              threshold_summary_sha256=hashlib.sha256((args.study/'mask_threshold_validation'/'threshold_summary.csv').read_bytes()).hexdigest(),
              limitations='Reference convention for descriptive analysis, not independent ground-truth boundary proof; no tiny-component filtering; unannotated NG excluded; class-conflict boxes excluded')
save_json(output,policy);print(f'Validated nonzero analysis policy written: {output}')
