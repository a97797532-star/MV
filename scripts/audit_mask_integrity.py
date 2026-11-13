# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Audit every provided NG mask independently of threshold approval."""
import argparse
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import pandas as pd
from mv_analysis.core import audit_masks,save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--metadata-run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
parent=json.loads((args.metadata_run/'run.json').read_text());root=Path(parent['config']['root']);df=pd.read_csv(args.metadata_run/'image_metadata_with_split.csv',keep_default_na=False)
args.output.mkdir(parents=True,exist_ok=False);start=time.time();policy=audit_masks(root,df,args.output)
save_json(args.output/'execution.json',dict(time=datetime.now(timezone.utc).isoformat(),argv=sys.argv,root=str(root),metadata_run=str(args.metadata_run),target=policy['expected'],success=policy['inspected']-len(policy['errors']),errors=len(policy['errors']),elapsed_s=time.time()-start))
print(json.dumps({k:v for k,v in policy.items() if k not in ('histogram','values','errors')},indent=2));print('decode_errors',len(policy['errors']));raise SystemExit(bool(policy['errors']))
