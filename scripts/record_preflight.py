"""Run required checks and record actual real-data smoke evidence for full analysis."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--smoke',required=True,type=Path);args=p.parse_args()
run=json.loads((args.smoke/'run.json').read_text())
if not any(c['command']=='run-all' and c['error'] is None for c in run['commands']):raise SystemExit('Smoke run-all must finish successfully')
if run['config']['limit'] is None:raise SystemExit('Expected a small real data smoke run')
for name in ['brightness_per_image.csv','per_view_information_loss.csv','REAL_IAD_FINAL_ANALYSIS.md']:
 if not (args.smoke/name).is_file():raise SystemExit(f'Missing smoke artifact: {name}')
root=Path(run['config']['root'])
if not root.is_dir():raise SystemExit('Smoke data unavailable')
for name,command in [('environment',[sys.executable,'scripts/validate_environment.py','--dummy']),('pytest',[sys.executable,'-m','pytest','-q'])]:
 r=subprocess.run(command,text=True,capture_output=True)
 Path('reports',f'preflight_{name}.txt').write_text(r.stdout+r.stderr)
 if r.returncode:raise SystemExit(f'{name} failed: reports/preflight_{name}.txt')
source=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()
lock=hashlib.sha256(Path('uv.lock').read_bytes()).hexdigest()
if run['config']['source_sha256']!=source or run['config']['lock_sha256']!=lock:raise SystemExit('Smoke source/lock stale; rerun smoke')
record=dict(time=datetime.now(timezone.utc).isoformat(),smoke=str(args.smoke),root=str(root),source_sha256=source,lock_sha256=lock,pytest_passed=True,environment_passed=True)
Path('reports/preflight_passed.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
