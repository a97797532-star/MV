"""Import completed metadata into a new run, preserving original artifacts and provenance.

Used when only image metric implementation/parallelism changed after metadata started.
Source metadata is accepted only after complete decode and input size/mtime verification.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--metadata-run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
parent=json.loads((args.metadata_run/'run.json').read_text());validation=json.loads((args.metadata_run/'metadata_validation_report.json').read_text())
if not validation['decode_verified'] or validation['errors'] or validation['selected']!=validation['jpg_count'] or validation['success']!=validation['jpg_count']:raise SystemExit('Parent metadata is incomplete/has decode errors')
if not any(c['command'] in {'validate-data','metadata','run-all'} and c['error'] is None for c in parent['commands']):raise SystemExit('Parent validation has not finished')
root=Path(parent['config']['root']);df=pd.read_csv(args.metadata_run/'image_metadata_with_split.csv',keep_default_na=False)
for i,row in enumerate(df.to_dict('records')):
 path=root/row['image_path'];st=path.stat()
 if st.st_size!=row['bytes'] or st.st_mtime_ns!=row['mtime_ns']:raise SystemExit(f'Input changed: {row["image_path"]}')
 if (i+1)%25000==0:print(f'Input snapshot checked {i+1}/{len(df)}',flush=True)
args.output.mkdir(parents=True,exist_ok=False)
files=['image_metadata.csv','image_metadata_with_split.csv','mask_metadata.csv','image_mask_pairs.csv','metadata_validation_report.json','metadata_label_conflicts.csv','ng_without_mask.csv','category_status_counts.csv','category_defect_view_counts.csv','dataset_category_distribution.png']
for name in files:shutil.copy2(args.metadata_run/name,args.output/name)
lock=hashlib.sha256(Path('uv.lock').read_bytes()).hexdigest();source=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()
config=dict(root=str(root),limit=None,lock_sha256=lock,class_policy='defect_type',inventory_only=False,source_sha256=source)
for key in ['split_policy','split_manifest_sha256']:
 if key in parent['config']:config[key]=parent['config'][key]
now=datetime.now(timezone.utc).isoformat();save_json(args.output/'run.json',dict(created=now,config=config,commands=[dict(command='metadata-import',argv=sys.argv[1:],error=None,finished=now,success=len(df),source_run=str(args.metadata_run),snapshot_verified=True)],provenance=parent))
print(f'Created {args.output} with copied complete metadata; original run preserved')
