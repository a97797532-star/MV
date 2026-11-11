"""Run annotated-NG spatial stages after real mask integrity evidence is available."""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--metadata-run',required=True,type=Path);p.add_argument('--image-run',required=True,type=Path);p.add_argument('--integrity',required=True,type=Path);p.add_argument('--study',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--inventory',required=True,type=Path);args=p.parse_args()
state=dict(started=datetime.now(timezone.utc).isoformat(),state='waiting_mask_integrity',commands=[])
status_file=args.image_run/'spatial_analysis_driver.json'
def save():state['updated']=datetime.now(timezone.utc).isoformat();status_file.write_text(json.dumps(state,indent=2))
def command(name,argv):
 state['state']=name;save();print(name,flush=True);t=time.time()
 with (args.image_run/f'spatial_{name}_stdout.log').open('a') as stream:result=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT)
 state['commands'].append(dict(name=name,argv=argv,elapsed_s=time.time()-t,returncode=result.returncode));save()
 if result.returncode:raise RuntimeError(f'{name} failed; see retained log')
save();deadline=time.monotonic()+7200
while not (args.integrity/'execution.json').exists():
 if time.monotonic()>deadline:state['state']='integrity_wait_timeout';save();raise SystemExit('Mask integrity wait timeout')
 time.sleep(10)
try:
 integrity=json.loads((args.integrity/'execution.json').read_text())
 if integrity['errors']:raise RuntimeError('Mask integrity failed; keep spatial stages deferred')
 command('metadata_import',[sys.executable,'scripts/continue_image_analysis.py','--metadata-run',str(args.metadata_run),'--output',str(args.output)])
 command('policy',[sys.executable,'scripts/approve_mask_policy.py','--integrity',str(args.integrity),'--study',str(args.study),'--run',str(args.output)])
 run=json.loads((args.output/'run.json').read_text());base=[sys.executable,'-m','mv_analysis.cli','--data-root',run['config']['root'],'--output',str(args.output),'--resume']
 command('heatmap',base+['heatmap']);command('bbox',base+['bbox']);command('artifact_validation',[sys.executable,'scripts/validate_artifacts.py',str(args.output)])
 command('project_reports',[sys.executable,'scripts/update_project_reports.py','--run',str(args.image_run),'--inventory',str(args.inventory),'--mask-study',str(args.study),'--spatial-run',str(args.output),'--mask-integrity',str(args.integrity)])
 state['state']='complete_spatial_stages';save()
except Exception as exc:
 state['state']='failed_results_retained';state['error']=str(exc);save();raise
