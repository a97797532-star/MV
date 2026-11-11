"""같은 표본의 새 분석 결과 비교. 시간 값은 제외."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

def compare(left,right):
    left,right=Path(left),Path(right)
    a=json.loads((left/'run_info.json').read_text());b=json.loads((right/'run_info.json').read_text())
    for key in ['sizes','heatmap_source_split','heatmap_grid','label_version','selected_sha256']:
        if a[key]!=b[key]:raise AssertionError(f'config mismatch: {key}')
    paths=['brightness/brightness_per_image.csv','brightness/brightness_by_class_view.csv',
        'brightness/brightness_histograms.csv','boxes/bbox_annotations.csv',
        'boxes/detection_images.csv','boxes/bbox_excluded.csv',
        'gan_heatmaps/heatmap_metadata.csv','gan_heatmaps/gan_source_manifest.csv',
        'resolutions/resolution_image_comparison.csv','resolutions/resolution_component_comparison.csv',
        'resolutions/resolution_class_summary.csv']
    for path in paths:
        x=pd.read_csv(left/path);y=pd.read_csv(right/path)
        drop=[c for c in ['rgb_resize_ms','median_resize_ms','component_id'] if c in x]
        # Component ID numbering may differ; row order is normalized by geometry.
        x=x.drop(columns=drop);y=y.drop(columns=drop)
        if 'remaining_area' in x:
            cols=['category','sample_key','view_id','target_size','source_area','remaining_area','box_width_after','box_height_after']
        elif 'x0' in x:cols=['category','sample_key','view_id','x0','y0','x1','y1']
        else:cols=list(x.columns)
        x=x.sort_values(cols).reset_index(drop=True);y=y.sort_values(cols).reset_index(drop=True)
        pd.testing.assert_frame_equal(x,y,check_dtype=False,check_exact=False,rtol=1e-9,atol=1e-8)
    files=sorted((left/'gan_heatmaps').glob('*.npz'))
    for f in files:
        with np.load(f) as x,np.load(right/'gan_heatmaps'/f.name) as y:
            for key in x.files:np.testing.assert_allclose(x[key],y[key],equal_nan=True)
    print(f'PASS: {len(paths)} CSVs and {len(files)} heatmap archives agree; timing excluded.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('left');p.add_argument('right');a=p.parse_args();compare(a.left,a.right)
