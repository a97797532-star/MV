"""Run a stratified threshold study from a previously generated metadata manifest."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import pandas as pd
from mv_analysis.mask_validation import validate_thresholds
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--data-root',required=True,type=Path);p.add_argument('--metadata',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=False);t=time.time();df=pd.read_csv(args.metadata,keep_default_na=False)
folder=validate_thresholds(args.data_root.resolve(),args.output,df)
record=dict(time=datetime.now(timezone.utc).isoformat(),argv=sys.argv,root=str(args.data_root.resolve()),metadata=str(args.metadata),metadata_sha256=hashlib.sha256(args.metadata.read_bytes()).hexdigest(),elapsed_s=time.time()-t,output=str(folder))
(args.output/'execution.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
