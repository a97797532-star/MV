"""Compare actual saved Windows occupancy arrays with preserved-split presence-v2."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--windows',required=True,type=Path);p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
old=pd.read_csv(a.windows/'heatmap_summary.csv');new=pd.read_csv(a.run/'heatmap_summary.csv');known=np.load(a.run/'occupancy_known.npy');positive=np.load(a.run/'occupancy_positive.npy');keys=json.loads((a.run/'heatmap_groups.json').read_text());lookup={tuple(k):i for i,k in enumerate(keys)};rows=[]
for row in old.to_dict('records'):
 key=tuple(row[c] for c in ['category','defect_type','view']);i=lookup.get(key)
 if i is None:continue
 base=a.windows/key[0]/key[1]/key[2];k=np.load(base/'occupancy_known.npy',allow_pickle=False);v=np.load(base/'occupancy_positive.npy',allow_pickle=False)
 delta=lambda x,y:float(np.nanmax(np.abs(x-y))) if np.isfinite(x-y).any() else None
 equal=lambda x,y:bool(np.allclose(x,y,rtol=0,atol=0,equal_nan=True))
 rows.append(dict(category=key[0],defect_type=key[1],view=key[2],old_known=row['n_known'],new_known=int(new.iloc[i].n_known),known_max_abs_difference=delta(k,known[i]),positive_max_abs_difference=delta(v,positive[i]),known_equal=equal(k,known[i]),positive_equal=equal(v,positive[i])))
df=pd.DataFrame(rows);df.to_csv(a.output/'heatmap_same_split_comparison.csv',index=False);save_json(a.output/'validation.json',dict(old_groups=len(old),new_groups=len(new),shared_groups=len(df),known_exact_equal=int(df.known_equal.sum()),positive_exact_equal=int(df.positive_equal.sum()),different_groups=df[~(df.known_equal&df.positive_equal)].to_dict('records'),scope='Saved Windows NPY versus same split/nonzero/64-cell presence; unresolved type conflicts remain separate'))
print('Compared',len(df),'shared groups')
