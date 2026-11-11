"""Continue authorized full image analysis after brightness, retaining logs/checkpoints."""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--inventory',required=True,type=Path);p.add_argument('--mask-study',required=True,type=Path);args=p.parse_args();out=args.run
status=dict(started=datetime.now(timezone.utc).isoformat(),state='waiting_for_full_brightness',commands=[])
def persist():
 status['updated']=datetime.now(timezone.utc).isoformat();(out/'image_analysis_driver.json').write_text(json.dumps(status,indent=2))
def execute(name,argv):
 status['state']=name;persist();print(name,flush=True);start=time.time()
 with (out/f'{name}_stdout.log').open('a') as log:
  result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,text=True)
 status['commands'].append(dict(name=name,argv=argv,returncode=result.returncode,elapsed_s=time.time()-start,finished=datetime.now(timezone.utc).isoformat()));persist()
 return result.returncode
persist();deadline=time.monotonic()+7200
while True:
 try:
  run=json.loads((out/'run.json').read_text());matches=[c for c in run['commands'] if c['command']=='brightness']
  if matches:
   if matches[-1]['error'] is not None:raise RuntimeError(f'Brightness failed: {matches[-1]["error"]}')
   execution=json.loads((out/'brightness_per_image_execution.json').read_text())
   if execution['target']!=151050 or execution['success']!=151050 or execution['errors']:raise RuntimeError('Full brightness counts did not pass')
   break
 except (FileNotFoundError,json.JSONDecodeError):pass
 if time.monotonic()>deadline:
  status['state']='brightness_wait_timeout';persist();raise SystemExit('Full brightness did not finish in two hours; results retained')
 time.sleep(10)
root=run['config']['root'];cmd=[sys.executable,'-m','mv_analysis.cli','--data-root',root,'--output',str(out),'--resume']
code=execute('resolution',cmd+['resolution'])
if code==0:
 execute('enrich',[sys.executable,'scripts/enrich_analysis_results.py',str(out)])
 execute('run_report',cmd+['report'])
 execute('artifact_validation',[sys.executable,'scripts/validate_artifacts.py',str(out)])
execute('project_reports',[sys.executable,'scripts/update_project_reports.py','--run',str(out),'--inventory',str(args.inventory),'--mask-study',str(args.mask_study)])
status['state']='complete_image_stages' if code==0 and all(c['returncode']==0 for c in status['commands']) else 'failed_stage_results_retained';persist();raise SystemExit(int(status['state']!='complete_image_stages'))
