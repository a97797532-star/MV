# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Make report figures/aggregate links work on GitHub; retain large local-only evidence paths."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--images',type=Path,default=Path('images'));p.add_argument('--reports',type=Path,default=Path('reports'));a=p.parse_args();root=Path.cwd().resolve();out=a.images.resolve();manifest_path=out/'manifest.json';manifest=json.loads(manifest_path.read_text());mapping={};by_hash={}
for item in manifest['artifacts']:
 existing=Path(item['path']).resolve()
 if existing.is_file():by_hash[hashlib.sha256(existing.read_bytes()).hexdigest()]=existing
 for alias in item.get('source_aliases',[]):mapping[Path(alias).resolve()]=existing
 if item.get('source'):
  source=Path(item['source']).resolve();mapping[source]=Path(item['path']).resolve()
# share: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: source.
def share(source):
 source=source.resolve()
 if source in mapping:return mapping[source]
 if not source.is_file() or root/'outputs' not in source.parents:return None
 suffix=source.suffix.lower()
 if suffix=='.png':folder='figures'
 elif suffix in {'.csv','.json'} and source.stat().st_size<=1024*1024:folder='tables'
 else:return None
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 if digest in by_hash:
  target=by_hash[digest];mapping[source]=target
  for item in manifest['artifacts']:
   if Path(item['path']).resolve()==target:item.setdefault('source_aliases',[]).append(str(source.relative_to(root)));break
  return target
 target=out/folder/(source.parent.name+'__'+source.name)
 if target.exists() and target.read_bytes()!=source.read_bytes():target=target.with_name(target.stem+'_'+hashlib.sha256(source.read_bytes()).hexdigest()[:8]+suffix)
 if not target.exists():shutil.copy2(source,target)
 mapping[source]=target;by_hash[digest]=target;manifest['artifacts'].append(dict(path=str(target.relative_to(root)),kind='published_report_evidence',source=str(source.relative_to(root))))
 return target
rewrites=[];local_only=[]
for report in sorted(a.reports.glob('*.md')):
 text=report.read_text()
 # replace: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: match.
 def replace(match):
  image,label,target=match.group(1),match.group(2),match.group(3)
  if not target.startswith('../outputs/'):return match.group(0)
  source=(report.parent/target).resolve();shared=share(source)
  if shared:
   import os
   relative=os.path.relpath(shared,report.parent.resolve());rewrites.append(dict(report=str(report),source=target,shared=relative));return f'{image}[{label}]({relative})'
  local_only.append(dict(report=str(report),source=target));return f'{label} (로컬 근거: `{target.removeprefix("../")}`)'
 updated=re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)',replace,text)
 if updated!=text:report.write_text(updated)
for item in manifest['artifacts']:
 path=Path(item['path'])
 if path.is_file():item['bytes']=path.stat().st_size;item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');(a.reports/'SHARED_ARTIFACT_LINKS.json').write_text(json.dumps(dict(rewritten_links=rewrites,large_or_directory_evidence_kept_local=local_only,raw_dataset_uploaded=False),indent=2,ensure_ascii=False)+'\n');print('Shared references',len(rewrites),'local evidence references',len(local_only))
