"""출력 CSV 공통 지표 검증. 성분 ID를 geometry 기준으로 정규화합니다."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

KEY=['category','sample_key','view_id']
TABLES={
 'selected_manifest.csv':KEY,
 'image_metrics.csv':KEY,
 'product_summary.csv':['category','sample_key'],
 'components.csv':KEY+['component_id'],
 'resolution_sensitivity.csv':KEY+['component_id','target_size'],
 'resolution_summary.csv':['category','target_size'],
 'visibility.csv':['category','view_id'],
 'counts.csv':['category','project_split','anomaly_class'],
}


def normalized(directory):
    data={f:pd.read_csv(directory/f) for f in TABLES}
    c=data['components.csv']
    old=c[KEY+['component_id']].copy()
    c=c.sort_values(KEY+['y0','x0','y1','x1','area','cy','cx']).copy()
    c['canonical_id']=c.groupby(KEY).cumcount()+1
    mapping=c[KEY+['component_id','canonical_id']]
    data['components.csv']=c.drop(columns='component_id').rename(columns={'canonical_id':'component_id'})
    r=data['resolution_sensitivity.csv']
    r=r.merge(mapping,on=KEY+['component_id'],how='left',validate='many_to_one')
    if len(r) and r.canonical_id.isna().any():raise ValueError('orphan resolution component')
    data['resolution_sensitivity.csv']=r.drop(columns='component_id').rename(columns={'canonical_id':'component_id'})
    return data


def compare(left,right,out,atol=1e-8,rtol=1e-10):
    left,right,out=Path(left),Path(right),Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    findings=[]
    try:
        li=json.loads((left/'run_info.json').read_text());ri=json.loads((right/'run_info.json').read_text())
        for field in ['manifest_sha256','selected_sha256','sizes','selected_splits','expected_views']:
            if li[field]!=ri[field]:raise ValueError(f'different input/config: {field}')
        a,b=normalized(left),normalized(right)
        for filename,keys in TABLES.items():
            try:
                x=a[filename].sort_values(keys).reset_index(drop=True)
                y=b[filename].sort_values(keys).reset_index(drop=True)
                x=x.reindex(sorted(x.columns),axis=1);y=y.reindex(sorted(y.columns),axis=1)
                pd.testing.assert_frame_equal(x,y,check_dtype=False,check_exact=False,atol=atol,rtol=rtol)
                findings.append((filename,'PASS',str(len(x))+' rows'))
            except (AssertionError,ValueError,KeyError) as exc:
                findings.append((filename,'FAIL',str(exc).replace('\n',' ')[:1000]))
    except Exception as exc:
        findings.append(('inputs','FAIL',str(exc)))
    passed=all(x[1]=='PASS' for x in findings) and bool(findings)
    lines=['# OpenCV / scikit-image parity report','',f'Result: {"PASS" if passed else "FAIL"}',
           f'Float tolerance: atol={atol}, rtol={rtol}. Integer counts/geometry also checked.',
           'Input hashes/configuration must match. Timings are excluded. Component IDs are canonicalized by geometry.',
           '', '| Table | Result | Detail |','|---|---|---|']
    for name,status,detail in findings:lines.append(f'| {name} | {status} | {detail.replace("|","/")} |')
    lines += ['', 'Reproduce:',f'`python compare_results.py --left "{left}" --right "{right}" --out "{out}"`',
              '', 'If FAIL: compare selected manifests, decoder/EXIF policy, mask states, gray scale, border mode, then coordinates.']
    out.write_text('\n'.join(lines),encoding='utf-8')
    return passed


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--left',required=True);p.add_argument('--right',required=True)
    p.add_argument('--out',default='parity_report.md');a=p.parse_args()
    ok=compare(a.left,a.right,a.out);print('PASS' if ok else 'FAIL');raise SystemExit(0 if ok else 1)
