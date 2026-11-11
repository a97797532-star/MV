"""Prepare an exact upload plan, then commit/push the verified analysis branch without rewriting main."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,default=ROOT/'outputs/git_publication_plan.json');p.add_argument('--prepare',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args();os.chdir(ROOT)
BRANCH='analysis/real-iad-full-20261111';REPO='whrjsdnr/MV';RESULT=ROOT/'outputs/git_delivery_result.json'
def sanitize(text):
 text=re.sub(r'(https?://)[^/@\s]+:[^/@\s]+@',r'\1<redacted>@',text)
 return re.sub(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})','<redacted>',text)
def run(args,check=True):
 env=os.environ.copy();env['GIT_TERMINAL_PROMPT']='0';env['GH_PROMPT_DISABLED']='1';r=subprocess.run(args,capture_output=True,text=True,env=env)
 if r.returncode and check:raise RuntimeError(sanitize(r.stderr or r.stdout))
 return r

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  while chunk:=stream.read(1024*1024):h.update(chunk)
 return h.hexdigest()

def assert_ready():
 for name in ['outputs/full_20261111_v6/resolution_scientific_validation.json','outputs/background_full_20261111_v1/scientific_validation.json','reports/SOURCE_PRESERVATION_VALIDATION.json','reports/REAL_IAD_DETAILED_ANALYSIS.render_validation.json']:
  if not json.loads(Path(name).read_text()).get('success'):raise RuntimeError('Validation not passed: '+name)
 gallery=json.loads(Path('images/manifest.json').read_text());categories={r['category'] for r in gallery['artifacts'] if r['kind']=='category_profile'}
 if len(categories)!=30 or not gallery['full_resolution_complete'] or not gallery['full_regional_complete']:raise RuntimeError('Final gallery incomplete')
 safety=json.loads(Path('reports/GIT_UPLOAD_SAFETY.json').read_text())
 if safety['issues'] or safety['large_candidates']:raise RuntimeError('Upload safety issues remain')
 if run(['git','remote','get-url','origin']).stdout.strip()!='https://github.com/whrjsdnr/MV.git':raise RuntimeError('Unexpected remote; refuse upload')

if a.prepare:
 run([sys.executable,'scripts/check_git_safety.py']);assert_ready()
 if run(['git','diff','--cached','--name-only']).stdout.strip():raise RuntimeError('Index contains existing staged changes; preserve them')
 candidates=run(['git','ls-files','--cached','--others','--exclude-standard','-z']).stdout.split('\0')
 allowed_dirs={'mv_analysis','scripts','tests','notebooks','docs','reports','legacy','images','.github'};allowed_root={'.gitignore','.gitattributes','.env.example','README.md','pyproject.toml','uv.lock','ENVIRONMENT_SETUP.md','ENVIRONMENT_VALIDATION.md','MODEL_COMPATIBILITY.md'}
 files=sorted(set(f for f in candidates if f and Path(f).is_file() and (Path(f).parts[0] in allowed_dirs or f in allowed_root)))
 plan=dict(prepared_utc=datetime.now(timezone.utc).isoformat(),branch=BRANCH,repository=REPO,base_commit=run(['git','rev-parse','HEAD']).stdout.strip(),files=[dict(path=f,bytes=Path(f).stat().st_size,sha256=sha(f)) for f in files],scope='Analysis source/config/docs, selected derived figures and aggregate tables, final Markdown/PDF; no raw dataset/weights/secrets',draft_pr=True)
 a.plan.parent.mkdir(exist_ok=True,parents=True);a.plan.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n');print(json.dumps(dict(branch=BRANCH,files=len(files),total_bytes=sum(r['bytes'] for r in plan['files']),plan=str(a.plan)),indent=2));sys.exit(0)
if not a.execute:raise SystemExit('Use --prepare first; --execute performs the authorized remote write')
plan=json.loads(a.plan.read_text());assert_ready()
if plan['branch']!=BRANCH or plan['repository']!=REPO:raise RuntimeError('Publication plan target mismatch')
for row in plan['files']:
 if sha(row['path'])!=row['sha256']:raise RuntimeError('File changed after plan review: '+row['path'])
if a.resume:
 result=json.loads(RESULT.read_text())
 if run(['git','branch','--show-current']).stdout.strip()!=BRANCH or run(['git','rev-parse','HEAD']).stdout.strip()!=result['commit']:raise RuntimeError('Resume branch/commit changed')
else:
 if run(['git','rev-parse','HEAD']).stdout.strip()!=plan['base_commit']:raise RuntimeError('HEAD changed after plan review')
 if run(['git','diff','--cached','--name-only']).stdout.strip():raise RuntimeError('Preserve preexisting staged changes')
 run(['git','switch','-c',BRANCH]);run(['git','add','--']+[r['path'] for r in plan['files']])
 staged=run(['git','diff','--cached','--name-only','-z']).stdout.split('\0');allowed={r['path'] for r in plan['files']}
 if any(f and f not in allowed for f in staged):raise RuntimeError('Unexpected staged file')
 result=dict(branch=BRANCH,repository=REPO,push_performed=False,prepared_plan=str(a.plan));run(['git','commit','-m','Add reproducible Real-IAD analysis and detailed illustrated reports']);result['commit']=run(['git','rev-parse','HEAD']).stdout.strip();RESULT.write_text(json.dumps(result,indent=2)+'\n')
# Check that historical copies and published binary figures/PDFs reach Git without byte conversion.
for row in plan['files']:
 path=row['path']
 if path.startswith(('legacy/windows_snapshot/','docs/archive/')) or Path(path).suffix.lower() in {'.pdf','.png'}:
  blob=subprocess.check_output(['git','show',f'{result["commit"]}:{path}'])
  if hashlib.sha256(blob).hexdigest()!=row['sha256']:raise RuntimeError('Git blob byte conversion detected: '+path)
# The existing authenticated gh credential helper supplies credentials through Git's private pipe.
run(['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','push','--set-upstream','origin',f'HEAD:refs/heads/{BRANCH}'])
remote=run(['git','ls-remote','--heads','origin',f'refs/heads/{BRANCH}']).stdout.split()
if not remote or remote[0]!=result['commit']:raise RuntimeError('Remote commit verification failed')
result.update(push_performed=True,remote_commit_verified=remote[0],verified_utc=datetime.now(timezone.utc).isoformat());RESULT.write_text(json.dumps(result,indent=2)+'\n')
body=ROOT/'outputs/final_pull_request_body.md'
if body.exists():
 existing=run(['gh','pr','list','--repo',REPO,'--head',BRANCH,'--json','url','--jq','.[0].url']).stdout.strip()
 url=existing or run(['gh','pr','create','--repo',REPO,'--base','main','--head',BRANCH,'--draft','--title','Add reproducible Real-IAD analysis and detailed illustrated reports','--body-file',str(body)]).stdout.strip();result['draft_pr_url']=url;RESULT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));print('Working tree:',sanitize(run(['git','status','--short']).stdout))
