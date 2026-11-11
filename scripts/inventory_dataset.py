"""File structure inspection requiring only Python's standard library."""
import argparse
import collections
import csv
import json
import os
import struct
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mv_analysis.schema import parse_image,scan
p=argparse.ArgumentParser();p.add_argument('--data-root',default=os.getenv('REALIAD_DATA_ROOT'));args=p.parse_args()
if not args.data_root:raise SystemExit('Specify --data-root or REALIAD_DATA_ROOT')
root=Path(args.data_root).resolve();out=Path('outputs')/('inventory_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True)
images,masks,ignored=scan(root);mask_set={str(p.relative_to(root)) for p in masks};mask_by_stem=collections.defaultdict(list)
for path in masks:mask_by_stem[path.stem.casefold()].append(str(path.relative_to(root)))
counts=collections.Counter();views=collections.Counter();errors=[];without=[];captures=collections.defaultdict(list);rows=[]
for path in images:
 try:
  row=parse_image(path,root);counts[(row['category'],row['status'],row['has_mask'])]+=1;views[row['view']]+=1;captures[row['capture_id']].append(row['view']);rows.append(row)
  if row['status']=='NG' and not row['has_mask']:
   candidates=mask_by_stem.get(path.stem.casefold(),[])
   without.append({**row,'reason':'possible_path_or_case_mismatch' if candidates else 'not_provided_at_expected_path; cause_unconfirmed','candidate_masks':';'.join(candidates)})
 except Exception as exc:errors.append({'path':str(path.relative_to(root)),'error':str(exc)})
for name,data,fields in [('file_metadata.csv',rows,list(rows[0]) if rows else ['image_path']),('ng_without_mask.csv',without,list(without[0]) if without else ['image_path'])]:
 with (out/name).open('w',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(data)
image_set={str(p.relative_to(root)) for p in images};orphan=[str(p.relative_to(root)) for p in masks if str(p.relative_to(root).with_suffix('.jpg')) not in image_set]
paired_ng=sum(n for (c,s,m),n in counts.items() if s=='NG' and m);all_ng=sum(n for (c,s,m),n in counts.items() if s=='NG')
report=dict(time=datetime.now(timezone.utc).isoformat(),root=str(root),jpg=len(images),png=len(masks),ok=sum(n for (c,s,m),n in counts.items() if s=='OK'),ng=all_ng,ng_with_mask=paired_ng,ng_without_mask=len(without),ng_mask_coverage=paired_ng/all_ng if all_ng else None,existing_png_pair_success_rate=(len(masks)-len(orphan))/len(masks) if masks else None,orphan_masks=orphan,ignored_files=ignored,views=dict(views),categories=len({c for c,s,m in counts}),category_status_mask_counts=[dict(category=c,status=s,has_mask=m,images=n) for (c,s,m),n in sorted(counts.items())],parse_errors=errors,incomplete_capture_groups=sum(set(v)!={'C1','C2','C3','C4','C5'} or len(v)!=5 for v in captures.values()),mask_absence_is_error=False,mask_absence_cause='Not inferable from absence alone. No matching alternate stem means structure supports unannotated view, but source annotation manifest is needed to rule out omission.',pixel_decode_verified=False,windows_jpg_delta=len(images)-146060,windows_png_delta=len(masks)-50115)
(out/'inventory.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps({k:v for k,v in report.items() if k not in ('category_status_mask_counts','parse_errors')},indent=2));print('Parse errors:',len(errors));print(f'Output: {out}')
