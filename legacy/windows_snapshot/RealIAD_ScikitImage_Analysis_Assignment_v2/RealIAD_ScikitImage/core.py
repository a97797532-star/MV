"""Real-IAD 공통 입력·감사·분석. backend.py만 두 패키지에서 다릅니다."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import time
import warnings

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from backend import components, laplacian, NAME

KEY = ['category', 'sample_key', 'view_id']
GROUP = ['category', 'sample_key']
PATTERN = re.compile(r'([a-zA-Z][a-zA-Z0-9_]*_[0-9]{4}_[A-Z][A-Z_]*[A-Z])_(C[0-9])_')
NORMAL = {'ok', 'good', 'normal'}
COMP_COLS = KEY + ['component_id', 'area', 'x0', 'y0', 'x1', 'y1', 'cx', 'cy', 'cx_norm', 'cy_norm']
RES_COLS = KEY + ['component_id', 'target_size', 'source_area', 'resized_area', 'disappeared']


def save(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def read_rgb(path):
    # 공통 디코더: OpenCV BGR와 skimage float 변환 차이를 제거합니다.
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ('RGB', 'L', 'RGBA'):
            raise ValueError(f'unsupported image mode: {im.mode}; explicitly convert first')
        return np.asarray(im.convert('RGB'), dtype=np.uint8).copy()


def gray(rgb):
    return rgb.astype(np.float64) @ np.array([0.299, 0.587, 0.114])


def read_mask(path, shape):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode == 'P':
            a = np.asarray(im)  # 팔레트 색 대신 라벨 인덱스를 보존
        else:
            a = np.asarray(im)
    if a.ndim == 3:
        # RGB 마스크는 3채널이 같을 때만 단일 라벨 마스크로 수용합니다.
        if a.shape[2] < 3 or not np.array_equal(a[..., 0], a[..., 1]) or not np.array_equal(a[..., 0], a[..., 2]):
            raise ValueError('colored mask: provide a reviewed binary conversion')
        a = a[..., 0]
    if a.ndim != 2 or a.shape != shape:
        raise ValueError(f'mask shape {a.shape} != image shape {shape}')
    if not (np.isin(a, [0, 1]).all() or np.isin(a, [0, 255]).all()):
        raise ValueError("map class/ignore mask values to reviewed binary mask first")
    return a > 0


def nearest(a, size):
    """양쪽 공통 pixel-center 최근접: floor((dst+0.5)*src/dst_size).

    임의 라이브러리 기본 resize를 섞지 않도록 명시한 좌표 계약입니다.
    입력 종횡비와 무관하게 size x size. 왜곡 여부는 실험 선택 사항입니다.
    """
    h, w = a.shape
    ys = np.minimum(((np.arange(size) + .5) * h / size).astype(int), h - 1)
    xs = np.minimum(((np.arange(size) + .5) * w / size).astype(int), w - 1)
    return a[np.ix_(ys, xs)]


def resolve_path(root, category, value):
    if value is None or str(value).strip() in ('', 'None', 'null'):
        return ''
    p = Path(str(value).replace('\\', '/'))
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'path must be relative to data root: {value}')
    # 배포 JSON에 category 접두사가 있는 경우와 없는 경우를 모두 허용.
    choices = [p, Path(category) / p]
    present = [q for q in choices if (root / q).is_file()]
    present = list(dict.fromkeys(present))
    if len(present) > 1:
        raise ValueError(f'ambiguous path: {value}; normalize the JSON/CSV')
    return (present[0] if present else p).as_posix()


def load_records(path):
    """split -> list 구조의 공식 JSON, 한 행 한 이미지 JSONL, list JSON 지원."""
    text = Path(path).read_text(encoding='utf-8-sig')
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = [json.loads(x) for x in text.splitlines() if x.strip()]
    if isinstance(obj, list):
        for row in obj:
            if not isinstance(row, dict):
                raise ValueError('record must be an object')
            yield str(row.get('official_split', row.get('split', 'unknown'))), row
    elif isinstance(obj, dict):
        found = False
        for split in ('train', 'val', 'validation', 'test'):
            if split not in obj:
                continue
            if not isinstance(obj[split], list):
                raise ValueError(f'{split}: expected list, use documented adapter CSV')
            found = True
            for row in obj[split]:
                yield split, row
        if not found:
            raise ValueError('unsupported JSON schema; use adapter CSV (README)')
    else:
        raise ValueError('unsupported metadata schema')


def build_manifest(root, json_dir, out, categories=None):
    root, json_dir, out = Path(root), Path(json_dir), Path(out)
    rows = []
    files = sorted(json_dir.glob('*.json')) + sorted(json_dir.glob('*.jsonl'))
    if categories:
        files = [p for p in files if p.stem in categories]
        missing = set(categories) - {p.stem for p in files}
        if missing:
            raise ValueError(f'category JSON missing: {sorted(missing)}')
    if not files:
        raise ValueError('no metadata files; specify the directory containing category JSONs')
    for path in files:
        for split, rec in load_records(path):
            cat = str(rec.get('category', path.stem))
            if 'image_path' not in rec or 'anomaly_class' not in rec:
                raise ValueError(f'{path}: image_path/anomaly_class required')
            image = resolve_path(root, cat, rec['image_path'])
            match = PATTERN.search(Path(image).name)
            # 예외 릴리스는 명시적 키를 입력해야 합니다. 파일명 임의 분할 금지.
            sample = str(rec.get('sample_key', match.group(1) if match else ''))
            view = str(rec.get('view_id', match.group(2) if match else ''))
            rows.append(dict(category=cat, sample_key=sample, view_id=view,
                             image_path=image, mask_path=resolve_path(root, cat, rec.get('mask_path')),
                             anomaly_class=str(rec['anomaly_class']), official_split=split,
                             project_split=split, split_version='official-v1',
                             parse_status='ok' if sample and view else 'parse_error'))
    df = pd.DataFrame(rows)
    save(df, out / 'manifest.csv')
    return df


def load_manifest(path):
    df = pd.read_csv(path, keep_default_na=False, dtype=str)
    required = KEY + ['image_path', 'mask_path', 'anomaly_class', 'official_split', 'project_split']
    if set(required) - set(df):
        raise ValueError(f'missing manifest columns: {set(required) - set(df)}')
    if 'parse_status' not in df:
        df['parse_status'] = np.where(df[KEY].eq('').any(axis=1), 'parse_error', 'ok')
    if 'split_version' not in df:
        df['split_version'] = 'manual-v1'
    return df


def audit(root, manifest, out, expected=('C1', 'C2', 'C3', 'C4', 'C5')):
    """전체 데이터 감사. 시험세트는 읽기 가능 여부/정합성만 확인, EDA는 별도."""
    root, out = Path(root), Path(out)
    issues, checked = [], []
    def issue(row, kind, detail):
        issues.append({**{k: row[k] for k in KEY}, 'issue': kind, 'detail': str(detail)})
    for rec in manifest.to_dict('records'):
        row = dict(rec, width=np.nan, height=np.nan, mask_state='not_provided',
                   status='ok', sha256='', pixel_sha256='')
        if row['parse_status'] != 'ok':
            issue(row, 'parse_error', row['image_path'])
        try:
            p = root / row['image_path']
            with p.open('rb') as stream:
                row['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            rgb = read_rgb(p)
            row['height'], row['width'] = rgb.shape[:2]
            row['pixel_sha256'] = hashlib.sha256(str(rgb.shape).encode() + rgb.tobytes()).hexdigest()
        except Exception as exc:
            row['status'] = 'image_error'
            row['mask_state'] = 'error' if row['mask_path'] else 'not_provided'
            issue(row, 'image_error', exc)
            checked.append(row)
            continue
        if row['mask_path']:
            try:
                m = read_mask(root / row['mask_path'], rgb.shape[:2])
                row['mask_state'] = 'positive' if m.any() else 'empty'
                if m.any() and row['anomaly_class'].lower() in NORMAL:
                    issue(row, 'normal_label_positive_mask', row['mask_path'])
            except Exception as exc:
                row['mask_state'] = 'error'
                issue(row, 'mask_error', exc)
        checked.append(row)
    df = pd.DataFrame(checked)
    for _, row in df[df.duplicated(KEY, keep=False)].iterrows():
        issue(row, 'duplicate_key', row['image_path'])
    for _, g in df.groupby(GROUP, dropna=False):
        r = g.iloc[0]
        actual = set(g.view_id)
        if actual != set(expected) or len(g) != len(expected):
            issue(r, 'view_set_mismatch', f'expected={expected}, actual={sorted(actual)}, rows={len(g)}')
        if g.anomaly_class.nunique() > 1:
            issue(r, 'product_label_conflict', '|'.join(g.anomaly_class.unique()))
        for split in ['official_split', 'project_split']:
            if g[split].nunique() > 1:
                issue(r, 'product_split_leak', split)
    for hash_col in ['sha256', 'pixel_sha256']:
        for h, g in df[df[hash_col] != ''].groupby(hash_col):
            if len(g) < 2:
                continue
            if g.official_split.nunique() > 1 or g.project_split.nunique() > 1:
                issue(g.iloc[0], 'hash_split_leak', f'{hash_col}:{h}')
            if g.anomaly_class.nunique() > 1:
                issue(g.iloc[0], 'hash_label_conflict', f'{hash_col}:{h}')
    issue_df = pd.DataFrame(issues, columns=KEY + ['issue', 'detail'])
    save(df, out / 'manifest.csv')
    save(df[GROUP + ['official_split', 'project_split', 'split_version']].drop_duplicates(), out / 'split_manifest.csv')
    save(issue_df, out / 'integrity_issues.csv')
    (out / 'audit_summary.json').write_text(json.dumps({
        'images':len(df), 'products':len(df[GROUP].drop_duplicates()),
        'issues':issue_df.issue.value_counts().to_dict(), 'expected_views':list(expected),
        'note':'file-byte and decoded-pixel hashes are checked; near-duplicates are not detected'
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return df, issue_df


def project_split(manifest, seed=42, holdout_defects=()):
    """명시적 지도학습 트랙 재분할. 공식 분할 보존, 제품 단위 고정."""
    df = manifest.copy()
    if df[KEY].eq('').any(axis=None) or df.duplicated(KEY).any():
        raise ValueError('resolve invalid/duplicate product-view keys before splitting')
    if (df.groupby(GROUP).anomaly_class.nunique() > 1).any():
        raise ValueError('resolve product label conflicts first')
    products = df[GROUP + ['anomaly_class']].drop_duplicates()
    assignments = {}
    for _, g in products.groupby(['category', 'anomaly_class'], sort=True):
        g = g.sort_values(GROUP)
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(g))
        if g.iloc[0].anomaly_class in holdout_defects:
            labels = ['test'] * len(g)
        else:
            n = len(g)
            if n < 3:
                # 희소 유형은 독립 평가 가능성을 우선: 학습에는 들어가지 않습니다.
                warnings.warn(f'{g.iloc[0].category}/{g.iloc[0].anomaly_class}: n={n}, test only')
                labels = ['test'] * n
            else:
                nval = max(1, round(n * .2))
                ntest = max(1, round(n * .2))
                labels = ['train'] * (n - nval - ntest) + ['val'] * nval + ['test'] * ntest
        for idx, label in zip(order, labels):
            r = g.iloc[idx]
            assignments[(r.category, r.sample_key)] = label
    df['project_split'] = [assignments[(r.category, r.sample_key)] for r in df.itertuples()]
    df['split_version'] = f'supervised-seed{seed}-v1'
    return df


def image_features(rgb):
    g = gray(rgb)
    return dict(brightness_median=float(np.median(g)),
                contrast_p95_p5=float(np.percentile(g, 95, method='linear') - np.percentile(g, 5, method='linear')),
                saturated_ratio=float(np.mean(np.any(rgb >= 250, axis=2))),
                dark_ratio=float(np.mean(np.all(rgb <= 5, axis=2))),
                laplacian_variance=float(np.var(laplacian(g), ddof=0)))


def analyze(root, manifest, out, splits=('train', 'val', 'validation'), sizes=(1024,512,256),
            expected=('C1','C2','C3','C4','C5'), max_products=0, seed=42):
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # 상태·누수 문제는 조용히 제거하지 않고 사전 감사 결과에서 차단합니다.
    audited, issues = audit(root, manifest, out / 'audit', expected)
    fatal = {'parse_error','duplicate_key','product_label_conflict','product_split_leak',
             'hash_split_leak','hash_label_conflict','normal_label_positive_mask'}
    if set(issues.issue) & fatal:
        raise ValueError('blocking integrity issues: inspect output/audit/integrity_issues.csv')
    selected = audited[audited.project_split.isin(splits)].copy()
    if max_products:
        # strata별 정렬 후 round-robin 표본. 동일 seed/manifest면 같은 제품 순서.
        groups = []
        products = selected[GROUP+['anomaly_class']].drop_duplicates()
        for _, g in products.groupby(['category','anomaly_class'], sort=True):
            groups.append(g.sort_values(GROUP).sample(frac=1, random_state=seed).to_dict('records'))
        chosen = []
        while len(chosen) < max_products and any(groups):
            for bucket in groups:
                if bucket and len(chosen) < max_products:
                    chosen.append(bucket.pop(0))
        keys = {(r['category'],r['sample_key']) for r in chosen}
        selected = selected[[tuple(x) in keys for x in selected[GROUP].to_numpy()]]
    if selected.empty:
        raise ValueError('no selected development images; check --splits and manifest')
    selected = selected.sort_values(KEY).reset_index(drop=True)
    save(selected, out / 'selected_manifest.csv')
    metrics, comps, resolutions = [], [], []
    for idx, rec in enumerate(selected.to_dict('records')):
        keys = {k:rec[k] for k in KEY}
        row = dict(rec, brightness_median=np.nan, contrast_p95_p5=np.nan,
                   saturated_ratio=np.nan, dark_ratio=np.nan, laplacian_variance=np.nan,
                   positive_pixels=np.nan, defect_ratio=np.nan, component_count=np.nan,
                   na_reason='', analysis_status='ok')
        if rec['status'] != 'ok':
            row.update(analysis_status='image_error', na_reason='image_error')
            metrics.append(row)
            continue
        rgb = read_rgb(root / rec['image_path'])
        row.update(image_features(rgb))
        if rec['mask_state'] in ('positive','empty'):
            mask = read_mask(root / rec['mask_path'], rgb.shape[:2])
            labels, regions = components(mask)
            row.update(positive_pixels=int(mask.sum()), defect_ratio=float(mask.mean()), component_count=len(regions))
            for cid, reg in regions:
                reg = dict(reg)
                comp = {**keys, 'component_id':cid, **reg,
                        'cx_norm':reg['cx']/rgb.shape[1], 'cy_norm':reg['cy']/rgb.shape[0]}
                comps.append(comp)
            for size in sizes:
                # 마스크 성분을 하나씩 resize하지 않고 원본 라벨맵을 한번 변환.
                # 겹쳐 합쳐져도 원래 성분별 생존 픽셀 수가 유지됩니다.
                resized = nearest(labels, size)
                counts = np.bincount(resized.ravel(), minlength=int(labels.max())+1)
                for cid, reg in regions:
                    resolutions.append({**keys, 'component_id':cid,'target_size':size,
                                        'source_area':reg['area'],'resized_area':int(counts[cid]),
                                        'disappeared':int(counts[cid] == 0)})
        else:
            row['na_reason'] = 'mask_' + rec['mask_state']
        metrics.append(row)
        if (idx+1) % 100 == 0:
            print(f'{idx+1}/{len(selected)} images', flush=True)
    m = pd.DataFrame(metrics)
    c = pd.DataFrame(comps, columns=COMP_COLS)
    res = pd.DataFrame(resolutions, columns=RES_COLS)
    save(m, out/'image_metrics.csv')
    save(c, out/'components.csv')
    save(res, out/'resolution_sensitivity.csv')
    product = []
    for _, g in m.groupby(GROUP):
        r = g.iloc[0]
        known = g.mask_state.isin(['positive','empty']) & g.analysis_status.eq('ok')
        complete = len(g) == len(expected) and set(g.view_id) == set(expected)
        product.append(dict(category=r.category, sample_key=r.sample_key,
                            anomaly_class=r.anomaly_class, project_split=r.project_split,
                            n_views=len(g), complete_views=int(complete),
                            readable_images=int(g.analysis_status.eq('ok').sum()),
                            n_known_mask_views=int(known.sum()),
                            n_positive_views=int((g.mask_state.eq('positive') & known).sum()),
                            all_masks_known=int(known.sum()==len(expected) and complete)))
    p = pd.DataFrame(product)
    save(p, out/'product_summary.csv')
    img_counts = m.groupby(['category','project_split','anomaly_class']).size().rename('n_images').reset_index()
    prod_counts = p.groupby(['category','project_split','anomaly_class']).agg(
        n_products=('sample_key','size'), complete_views=('complete_views','sum')).reset_index()
    counts = img_counts.merge(prod_counts)
    save(counts, out/'counts.csv')
    # 시점별 denominator: 해당 시점이 존재하고 마스크 판정 가능한 결함 제품.
    abnormal = m[~m.anomaly_class.str.lower().isin(NORMAL)].copy()
    vis = []
    for (cat,view), g in abnormal.groupby(['category','view_id']):
        valid = g.mask_state.isin(['positive','empty']) & g.analysis_status.eq('ok')
        numerator = int((g.mask_state.eq('positive') & valid).sum())
        denominator = int(valid.sum())
        vis.append(dict(category=cat,view_id=view,positive=numerator,denominator=denominator,
                        visibility=numerator/denominator if denominator else np.nan,
                        unknown_masks=int((~valid).sum())))
    v = pd.DataFrame(vis, columns=['category','view_id','positive','denominator','visibility','unknown_masks'])
    save(v,out/'visibility.csv')
    quality = m[m.anomaly_class.str.lower().isin(NORMAL) & m.analysis_status.eq('ok')]
    q = quality.groupby(['category','view_id'])[
        ['brightness_median','contrast_p95_p5','saturated_ratio','dark_ratio','laplacian_variance']
    ].agg(['count','median','min','max'])
    q.columns = ['_'.join(col) for col in q.columns]
    save(q.reset_index(), out/'normal_quality_by_view.csv')
    if len(res):
        sr = res.groupby(['category','target_size']).agg(n_components=('component_id','size'),lost=('disappeared','sum'),
                     median_remaining_area=('resized_area','median')).reset_index()
        sr['lost_ratio'] = sr.lost/sr.n_components
    else:
        sr = pd.DataFrame(columns=['category','target_size','n_components','lost','median_remaining_area','lost_ratio'])
    save(sr,out/'resolution_summary.csv')
    figures(root,m,c,p,v,res,out,expected)
    versions = {}
    for package in ['numpy','pandas','Pillow','matplotlib','opencv-python-headless','scikit-image','scipy']:
        try: versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: pass
    run = dict(backend=NAME,python=platform.python_version(),platform=platform.platform(),versions=versions,
               selected_splits=list(splits), sizes=list(sizes),expected_views=list(expected),seed=seed,
               manifest_sha256=hashlib.sha256(manifest.to_csv(index=False).encode()).hexdigest(),
               selected_sha256=hashlib.sha256(selected.to_csv(index=False).encode()).hexdigest(),
               scope='test included explicitly' if 'test' in splits else 'development only')
    (out/'run_info.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'decisions.md').write_text(decisions(m,p,v,sr),encoding='utf-8')
    return m,p


def figures(root,m,c,p,v,res,out,expected):
    dest = out/'figures'
    dest.mkdir(exist_ok=True)
    def finish(name):
        plt.tight_layout()
        plt.savefig(dest/name,dpi=150,bbox_inches='tight')
        plt.close()
    counts = p.groupby(['category','anomaly_class']).size()
    fig, ax = plt.subplots(figsize=(10,4))
    counts.plot.bar(ax=ax);ax.set_ylabel('Products');finish('01_product_counts.png')
    if len(v):
        pivot = v.pivot(index='category',columns='view_id',values='visibility').reindex(columns=expected)
        fig,ax = plt.subplots(figsize=(7,max(3,len(pivot)*.5)))
        im = ax.imshow(pivot.to_numpy(float),vmin=0,vmax=1,cmap='YlOrRd')
        ax.set_xticks(range(len(pivot.columns)),pivot.columns);ax.set_yticks(range(len(pivot)),pivot.index)
        for i,cat in enumerate(pivot.index):
            for j,view in enumerate(pivot.columns):
                row = v[(v.category==cat)&(v.view_id==view)]
                if len(row):
                    r = row.iloc[0]; ax.text(j,i,f'{r.positive}/{r.denominator}',ha='center',va='center',fontsize=9)
        fig.colorbar(im,ax=ax,label='Annotated visibility');finish('02_visibility.png')
    if len(c):
        plt.figure(figsize=(7,4));plt.hist(c.area,bins=np.geomspace(max(1,c.area.min()),max(c.area.max()+1,2),20))
        plt.xscale('log');plt.xlabel('Component area (pixels)');plt.ylabel('Components');finish('03_component_area.png')
        # 카메라 좌표를 섞지 않고 category/view 별로 분리합니다.
        for n,((cat,view),g) in enumerate(c.groupby(['category','view_id'])):
            plt.figure(figsize=(4,4));plt.scatter(g.cx_norm,g.cy_norm,alpha=.6)
            plt.xlim(0,1);plt.ylim(1,0);plt.xlabel('x / W');plt.ylabel('y / H');plt.title(f'{cat} {view}')
            finish(f'04_locations_{n:03d}.png')
    normal = m[m.anomaly_class.str.lower().isin(NORMAL)&m.analysis_status.eq('ok')]
    if len(normal):
        fig,axes=plt.subplots(1,3,figsize=(13,4))
        labels = sorted(normal.view_id.unique())
        for ax,col in zip(axes,['brightness_median','contrast_p95_p5','laplacian_variance']):
            ax.boxplot([normal.loc[normal.view_id==x,col].dropna().to_numpy() for x in labels],tick_labels=labels)
            ax.set_title(col)
        finish('05_normal_quality.png')
    if len(res):
        fig,ax=plt.subplots(figsize=(7,4))
        for cat,g in res.groupby('category'):
            q=g.groupby('target_size').disappeared.mean();ax.plot(q.index,q.values,'o-',label=cat)
        ax.set_ylim(-.02,1.02);ax.set_ylabel('Disappeared original components');ax.set_xlabel('Square input size');ax.legend()
        finish('06_resolution_loss.png')
    # 대표 제품: 표본 목록 순서의 결함/정상 제품을 각각 최대 3개. 성능 우수 사례 선별 아님.
    chosen=[]
    for is_normal in (False,True):
        s=p[p.anomaly_class.str.lower().isin(NORMAL)==is_normal]
        chosen.extend(s.head(3)[GROUP].to_dict('records'))
    for n,prod in enumerate(chosen):
        g=m[(m.category==prod['category'])&(m.sample_key==prod['sample_key'])]
        fig,axes=plt.subplots(1,len(expected),figsize=(3*len(expected),3),squeeze=False)
        for ax,view in zip(axes[0],expected):
            rows=g[g.view_id==view]
            ax.axis('off');ax.set_title(view)
            if len(rows)!=1 or rows.iloc[0].analysis_status!='ok':
                ax.text(.1,.5,'MISSING / ERROR');continue
            r=rows.iloc[0];rgb=read_rgb(root/r.image_path);ax.imshow(rgb)
            if r.mask_state in ('positive','empty'):
                mask=read_mask(root/r.mask_path,rgb.shape[:2])
                overlay=np.zeros((*mask.shape,4));overlay[mask]=[1,0,0,.5];ax.imshow(overlay)
            else: ax.text(.02,.02,'MASK UNKNOWN',transform=ax.transAxes,color='orange')
        fig.suptitle(f"{prod['category']} / {prod['sample_key']}")
        finish(f'07_overlay_{n:02d}.png')


def decisions(m,p,v,sr):
    return f'''# 분석 리뷰 및 모델팀 인수

분석 backend: {NAME}. 이미지 {len(m)}장, 제품 {len(p)}개.
이 파일의 수치는 선택된 개발 표본에만 해당합니다. 자동 모델 선정 결과가 아닙니다.

## 확인 결과
- 기대 시점 완성 제품: {int(p.complete_views.sum())}/{len(p)}.
- 전체 마스크를 판정할 수 있는 제품: {int(p.all_masks_known.sum())}/{len(p)}.
- 마스크 판정이 완전하며 정확히 1개 시점에 양성인 제품: {int(((p.all_masks_known==1)&(p.n_positive_views==1)).sum())}.
- 마스크 미제공 이미지: {int(m.mask_state.eq('not_provided').sum())}.
- 마스크 오류 이미지: {int(m.mask_state.eq('error').sum())}.

## 직접 작성할 결정 (측정 -> 가설 -> 후속 실험)
1. counts.csv: 희소 결함의 제품 수와 분할별 수를 확인하고 별도 평가 대상을 기록.
2. visibility.csv: positive/denominator와 unknown_masks를 함께 보고 단일 고정 시점 vs 5시점 최대 점수 비교.
3. resolution_summary.csv: 원본 성분 소실률로 256/512/1024 또는 ROI 후보를 정함.
4. normal_quality_by_view.csv: 시점별 밝기·초점 차이로 전역/시점별 보정 실험 후보를 정함.
5. components.csv: category/view별 위치 분포로 GAN 마스크 배치 검수 범위를 제안.

## 팀 리뷰 양식
| 질문 | 근거 CSV/그림 | 가설 | 다음 실험 | 담당자 | 확정 여부 |
|---|---|---|---|---|---|
| 입력 해상도 | resolution_summary.csv | 작성 | 작성 | 작성 | 보류 |
| 융합 방법 | visibility.csv | 작성 | 작성 | 작성 | 보류 |
| 전처리 | normal_quality_by_view.csv | 작성 | 작성 | 작성 | 보류 |
| 합성 범위 | components.csv | 작성 | 작성 | 작성 | 보류 |

미제공 마스크를 정상으로 대체하지 않습니다. n_positive_views는 관측 하한입니다.
all_masks_known=0인 제품에서 '정확히 한 시점에서만 결함이 보인다'고 단정하지 않습니다.
시험 제품은 설정 확정 후 별도 명령으로만 분석합니다. GAN 입력·임계값 선정에도 시험 제품을 쓰지 않습니다.
'''


def benchmark(root, manifest, out, splits=('train','val'), repeats=5, max_products=20):
    """가벼운 이미지 품질+성분 커널 비교. 전체 EDA 시간과 구분합니다."""
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    if repeats < 2: raise ValueError('repeats must be >=2')
    df=manifest[manifest.project_split.isin(splits)].sort_values(KEY)
    keys=df[GROUP].drop_duplicates().head(max_products)
    df=df.merge(keys,on=GROUP)
    timings=[]
    for (cat,sample),g in df.groupby(GROUP,sort=True):
        # 제품당 모든 시점 포함. decode와 array 처리 시간을 각각 측정.
        def decode():
            inputs=[]
            for row in g.itertuples():
                rgb=read_rgb(root/row.image_path)
                mask=read_mask(root/row.mask_path,rgb.shape[:2]) if row.mask_path else None
                inputs.append((rgb,mask))
            return inputs
        def process(inputs):
            for rgb,mask in inputs:
                image_features(rgb)
                if mask is not None: components(mask)
        try:
            inputs=decode();process(inputs)  # warmup
            for rep in range(repeats):
                t=time.perf_counter();fresh=decode();process(fresh);end=time.perf_counter()-t
                t=time.perf_counter();process(inputs);arr=time.perf_counter()-t
                timings.append(dict(category=cat,sample_key=sample,n_views=len(g),repeat=rep,
                                    decode_and_process_ms=end*1000,array_only_ms=arr*1000))
        except Exception as exc:
            raise ValueError(f'benchmark failed on {cat}/{sample}; audit first: {exc}') from exc
    t=pd.DataFrame(timings)
    if t.empty: raise ValueError('no benchmark inputs')
    save(t,out/'benchmark_raw.csv')
    product=t.groupby(GROUP)[['decode_and_process_ms','array_only_ms']].median().reset_index()
    save(product,out/'benchmark_product_medians.csv')
    summary={col:dict(median=float(product[col].median()),p95=float(product[col].quantile(.95)))
             for col in ['decode_and_process_ms','array_only_ms']}
    summary.update(backend=NAME,repeats=repeats,n_products=len(product),opencv_threads=1,
                   scope='quality + components, no plotting/hashing/resizing; per-product repetition medians')
    (out/'benchmark_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description=f'Real-IAD EDA / {NAME}')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('manifest');p.add_argument('--root',required=True);p.add_argument('--json-dir',required=True)
    p.add_argument('--categories',nargs='+');p.add_argument('--out',default='work')
    p=sub.add_parser('split');p.add_argument('--manifest',required=True);p.add_argument('--out',required=True)
    p.add_argument('--seed',type=int,default=42);p.add_argument('--holdout-defects',nargs='*',default=[])
    for name in ['audit','analyze','benchmark']:
        p=sub.add_parser(name);p.add_argument('--root',required=True);p.add_argument('--manifest',required=True)
        p.add_argument('--out',required=True)
        if name in ['audit','analyze']:p.add_argument('--expected-views',nargs='+',default=['C1','C2','C3','C4','C5'])
        if name in ['analyze','benchmark']:
            p.add_argument('--splits',nargs='+',default=['train','val','validation'])
            p.add_argument('--max-products',type=int,default=0 if name=='analyze' else 20)
        if name=='analyze':p.add_argument('--sizes',nargs='+',type=int,default=[1024,512,256]);p.add_argument('--seed',type=int,default=42)
        if name=='benchmark':p.add_argument('--repeats',type=int,default=5)
    args=vars(ap.parse_args());cmd=args.pop('cmd')
    if 'max_products' in args and args['max_products']<0: ap.error('max-products must be nonnegative')
    if 'sizes' in args and any(s<=0 for s in args['sizes']):ap.error('sizes must be positive')
    if cmd=='manifest':build_manifest(**args)
    elif cmd=='split':
        df=project_split(load_manifest(args['manifest']),args['seed'],args['holdout_defects']);save(df,args['out'])
    else:
        args['manifest']=load_manifest(args['manifest'])
        if 'expected_views' in args:args['expected']=args.pop('expected_views')
        {'audit':audit,'analyze':analyze,'benchmark':benchmark}[cmd](**args)


if __name__=='__main__':
    main()
