"""Replay saved Windows group comparisons with the original pure Notebook helper."""
import argparse,ast,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--windows',required=True,type=Path);p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
base=Path('legacy/windows_snapshot/RealIAD_OpenCV_Analysis_Assignment_v2/RealIAD_OpenCV');notebook=next(base.glob('*executed.ipynb'));helper=None
for cell in json.loads(notebook.read_text())['cells']:
 s=''.join(cell.get('source',[]))
 if cell.get('cell_type')=='code' and 'def compare_distributions(' in s:
  helper=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='compare_distributions')
if helper is None:raise RuntimeError('Original pure group helper missing')
namespace=dict(np=np);exec(compile(ast.Module(body=[helper],type_ignores=[]),str(notebook),'exec'),namespace)
values=pd.read_csv(a.windows/'brightness_per_image.csv');prior=pd.read_csv(a.windows/'brightness_comparison.csv');replay=[]
for row in prior.to_dict('records'):
 ok=values[(values.category==row['category'])&(values.view==row['view'])&(values.quality=='OK')]['mean'];ng=values[(values.category==row['category'])&(values.view==row['view'])&(values.quality=='NG')&(values.defect_type==row['defect_type'])]['mean'];m=namespace['compare_distributions'](ok,ng)
 replay.append(dict(category=row['category'],view=row['view'],defect_type=row['defect_type'],mean_diff_abs_error=abs(m['mean_diff']-row['mean_diff']),overlap_abs_error=abs(m['overlap']-row['distribution_overlap']),cohens_d_abs_error=abs(m['cohens_d']-row['cohens_d'])))
pd.DataFrame(replay).to_csv(a.output/'windows_group_same_method_replay.csv',index=False)
current=pd.read_csv(a.run/'brightness_comparison.csv');joined=prior.merge(current,on=['category','defect_type','view'],validate='one_to_one');joined['counts_equal']=(joined.ok_images==joined.n_ok)&(joined.ng_images==joined.n_ng);joined['mean_diff_delta']=joined.mean_difference-joined.mean_diff;joined['cohens_d_delta']=joined.cohens_d_y-joined.cohens_d_x;joined['overlap_delta']=joined.histogram_overlap-joined.distribution_overlap;joined.to_csv(a.output/'windows_vs_opencv_group_comparison.csv',index=False)
replaydf=pd.DataFrame(replay);same=joined[joined.counts_equal];summary=dict(saved_windows_groups=len(prior),new_groups=len(current),common_groups=len(joined),same_sample_count_groups=int(joined.counts_equal.sum()),different_sample_count_groups=joined[~joined.counts_equal][['category','defect_type','view','ng_images','n_ng']].to_dict('records'),same_method_replay_max_abs_errors=replaydf[['mean_diff_abs_error','overlap_abs_error','cohens_d_abs_error']].max().to_dict(),same_count_opencv_minus_legacy_max_abs_deltas=same[['mean_diff_delta','cohens_d_delta','overlap_delta']].abs().max().to_dict(),distribution_definition='Both use 32 bins on per-image mean brightness, common 0..256 range, sample-pooled Cohen d; BGR integer vs RGB float gray differs')
save_json(a.output/'validation.json',summary);print(json.dumps(summary,indent=2))
