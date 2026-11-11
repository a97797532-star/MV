"""Verify dataset stat snapshot and preserved Windows sources, without rewriting either."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--data-root',required=True,type=Path);p.add_argument('--content-audit',required=True,type=Path);p.add_argument('--windows-inventory',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();issues=[];data_count=0
with (a.content_audit/'content_hashes.csv').open() as stream:
 for row in csv.DictReader(stream):
  try:
   stat=(a.data_root/row['path']).stat()
   if stat.st_size!=int(row['bytes']) or stat.st_mtime_ns!=int(row['mtime_ns']):issues.append(dict(path=row['path'],issue='dataset stat differs from initial full SHA256 snapshot'))
  except OSError as exc:issues.append(dict(path=row['path'],issue=str(exc)))
  data_count+=1
inventory=json.loads(a.windows_inventory.read_text());source_count=0;notebooks=0
for row in inventory['preserved_sources']:
 source=Path(row['source']);target=Path(row['target']);original=source.read_bytes();source_count+=1
 if hashlib.sha256(original).hexdigest()!=row['source_sha256']:issues.append(dict(path=str(source),issue='original Windows source SHA256 changed'))
 if source.suffix=='.ipynb':
  before=json.loads(original);after=json.loads(target.read_text());notebooks+=1
  if [(c['cell_type'],c.get('source')) for c in before['cells']]!=[(c['cell_type'],c.get('source')) for c in after['cells']]:issues.append(dict(path=str(target),issue='Notebook source cells differ'))
  if any(c.get('outputs') or c.get('execution_count') is not None for c in after['cells']):issues.append(dict(path=str(target),issue='Notebook copy contains outputs/count'))
 elif target.read_bytes()!=original:issues.append(dict(path=str(target),issue='preserved source copy is not byte-identical'))
report=dict(time_utc=datetime.now(timezone.utc).isoformat(),dataset_files_checked=data_count,dataset_expected=202379,dataset_scope='Size/mtime snapshot unchanged; initial full SHA256 audit remains the content fingerprint. No second full dataset hashing claimed.',windows_original_sources_sha256_rechecked=source_count,notebook_copies_source_cells_preserved=notebooks,issues=issues,success=not issues and data_count==202379 and source_count==inventory['source_count'],original_files_modified_by_this_script=False);a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False));sys.exit(not report['success'])
