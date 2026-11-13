# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Inspect upload candidates. Report paths/line numbers, never credential values."""
import json
import re
import subprocess
from pathlib import Path
result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],capture_output=True,check=True)
paths=[Path(p) for p in result.stdout.decode().split('\0') if p];issues=[];large=[];approved_large=[]
secret=re.compile(r'(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
for p in paths:
 if not p.is_file():continue
 if p.parts[0] in {'dataset','datasets','outputs','results','.uv-cache','.venv'} or p.suffix.lower() in {'.pth','.pt','.ckpt','.safetensors','.onnx'} or p.name=='.env':issues.append(dict(path=str(p),reason='forbidden upload candidate'))
 if p.stat().st_size>10*1024**2:
  evidence=p.with_suffix('.render_validation.json')
  if p.suffix.lower()=='.pdf' and p.stat().st_size<=50*1024**2 and evidence.exists() and json.loads(evidence.read_text()).get('success'):
   approved_large.append(str(p))
  else:large.append(str(p))
 if p.suffix.lower() in {'.jpg','.jpeg'}:issues.append(dict(path=str(p),reason='Raw JPEG upload candidate; only derived PNG figures are shared'))
 if p.suffix.lower()=='.png' and p.parts[0]!='images':issues.append(dict(path=str(p),reason='Shared figures must be under images/'))
 if p.suffix=='.ipynb':
  notebook=json.loads(p.read_text())
  if any(c.get('outputs') or c.get('execution_count') is not None for c in notebook.get('cells',[])):issues.append(dict(path=str(p),reason='Notebook outputs/execution counts must be cleared'))
 try:
  for number,line in enumerate(p.read_text().splitlines(),1):
   if secret.search(line):issues.append(dict(path=str(p),line=number,reason='credential-like string; value suppressed'))
 except UnicodeDecodeError:pass
checks=subprocess.run(['git','check-ignore','dataset/example.jpg','outputs/example.csv','.env','.uv-cache/example','example.pth'],capture_output=True,text=True)
expected={'dataset/example.jpg','outputs/example.csv','.env','.uv-cache/example','example.pth'}
if set(checks.stdout.splitlines())!=expected:issues.append(dict(reason='gitignore coverage incomplete'))
report=dict(candidate_count=len(paths),issues=issues,large_candidates=large,approved_validated_large_pdfs=approved_large,ignored_examples=checks.stdout.splitlines(),push_performed_by_this_scanner=False,audit_scope='Candidate scan before publication; delivery state is recorded separately',limitations='Pattern scan only; user must review staged diff before push',candidates=[str(p) for p in paths])
Path('reports/GIT_UPLOAD_SAFETY.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='candidates'},indent=2));raise SystemExit(bool(issues or large))
