"""요청한 네 분석: 클래스 밝기, GAN 위치 히트맵, GT 박스, 입력 해상도.

증강·학습 정답은 포함하지 않습니다. 두 패키지는 backend.components만 다릅니다.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from core import read_rgb, read_mask, gray, nearest, save, KEY, GROUP, NORMAL
from backend import components, NAME

BOX_COLS = KEY + ['image_id', 'image_path', 'anomaly_class', 'project_split',
    'component_id', 'x0', 'y0', 'x1', 'y1', 'width', 'height',
    'bbox_width', 'bbox_height', 'mask_area', 'box_area', 'cx_norm', 'cy_norm',
    'w_norm', 'h_norm', 'label_version']

def mask_to_boxes(mask):
    """검증한 bool/0-1/0-255 이진 마스크 → 8연결 성분, 최소면적 제거 없음."""
    m = np.asarray(mask)
    if m.ndim != 2 or not m.size or not np.isfinite(m).all():
        raise ValueError('finite nonempty 2D binary mask required')
    if not (np.isin(m, [0, 1]).all() or np.isin(m, [0, 255]).all()):
        raise ValueError('explicitly map class/ignore mask values before analysis')
    _, regs = components(m > 0)
    return [dict(component_id=cid, **r) for cid, r in
            sorted(regs, key=lambda x: (x[1]['x0'], x[1]['y0'], x[1]['x1'], x[1]['y1']))]


def coarse_occupancy(mask, grid=64):
    """영상별 격자 점유 여부. 1픽셀 결함도 보존."""  # per-image binary occupancy; preserves 1-pixel defects
    if not isinstance(grid, int) or grid < 1:
        raise ValueError('positive integer grid required')
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    yy, xx = np.nonzero(m)
    out = np.zeros((grid, grid), np.float64)
    # Pool by normalized source coordinates, never resize with interpolation.
    out[np.minimum(yy * grid // h, grid-1), np.minimum(xx * grid // w, grid-1)] = 1
    return out


def class_brightness(root, selected, out):
    """이미지별 통계와 클래스×품목×뷰 평균 정규화 히스토그램."""
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    details, distributions = [], {}
    bins = np.linspace(0, 256, 33)
    for rec in selected.to_dict('records'):
        if rec['status'] != 'ok':
            continue
        rgb = read_rgb(root / rec['image_path']); g = gray(rgb)
        key = (rec['category'], rec['anomaly_class'], rec['view_id'])
        hist = np.histogram(g, bins=bins)[0] / g.size
        distributions.setdefault(key, []).append(hist)
        row = {k: rec[k] for k in KEY + ['anomaly_class', 'project_split']}
        row.update(mean=float(g.mean()), median=float(np.median(g)),
            p05=float(np.percentile(g, 5)), p95=float(np.percentile(g, 95)),
            dark_ratio=float((g <= 5).mean()), saturated_ratio=float((g >= 250).mean()),
            defect_mean=np.nan, nondefect_mean=np.nan, mask_state=rec['mask_state'])
        if rec['mask_state'] in ('positive', 'empty'):
            mask = read_mask(root / rec['mask_path'], rgb.shape[:2])
            if mask.any(): row['defect_mean'] = float(g[mask].mean())
            if (~mask).any(): row['nondefect_mean'] = float(g[~mask].mean())
        details.append(row)
    cols = KEY + ['anomaly_class','project_split','mean','median','p05','p95',
        'dark_ratio','saturated_ratio','defect_mean','nondefect_mean','mask_state']
    detail = pd.DataFrame(details, columns=cols)
    if detail.empty: raise ValueError('no readable development images')
    summary = detail.groupby(['category', 'anomaly_class', 'view_id']).agg(
        n_images=('mean','size'), n_products=('sample_key','nunique'),
        mean_of_image_means=('mean','mean'), median_of_image_medians=('median','median'),
        mean_dark_ratio=('dark_ratio','mean'), mean_saturated_ratio=('saturated_ratio','mean'),
        n_positive_mask_images=('defect_mean','count'), defect_mean=('defect_mean','mean'),
        nondefect_mean=('nondefect_mean','mean')).reset_index()
    histrows = []
    for (cat, cls, view), arrays in sorted(distributions.items()):
        for i, value in enumerate(np.mean(arrays, axis=0)):
            histrows.append(dict(category=cat, anomaly_class=cls, view_id=view,
                bin_left=bins[i], bin_right=bins[i+1], mean_pixel_fraction=float(value),
                n_images=len(arrays)))
    hist = pd.DataFrame(histrows)
    save(detail, out/'brightness_per_image.csv')
    save(summary, out/'brightness_by_class_view.csv')
    save(hist, out/'brightness_histograms.csv')
    for j, ((cat,view), group) in enumerate(detail.groupby(['category','view_id'])):
        classes = sorted(group.anomaly_class.unique())
        fig, axes = plt.subplots(1,2,figsize=(10,3.2))
        axes[0].boxplot([group[group.anomaly_class==x]['mean'].to_numpy() for x in classes],
                        tick_labels=classes)
        axes[0].set(ylabel='Per-image mean gray [0,255]', title=f'{cat} / {view}', ylim=(0,255))
        for cls in classes:
            g = hist[(hist.category==cat)&(hist.view_id==view)&(hist.anomaly_class==cls)]
            axes[1].plot((g.bin_left+g.bin_right)/2, g.mean_pixel_fraction, label=cls)
        axes[1].set(xlabel='Gray value [0,255]',ylabel='Mean pixel fraction'); axes[1].legend()
        fig.tight_layout(); fig.savefig(out/f'brightness_{j:03d}.png',dpi=120); plt.close(fig)
    return detail, summary, hist


def gan_heatmaps(root, selected, out, grid=64):
    """학습 train의 불량 클래스별/품목별/뷰별 위치 분포; val/test 자동 포함 안 함."""
    root, out = Path(root), Path(out); out.mkdir(parents=True,exist_ok=True)
    train = selected[selected.project_split.eq('train')].copy()
    train = train[~train.anomaly_class.str.lower().isin(NORMAL)]
    source_rows, meta = [], []
    for (cat, cls, view), group in train.groupby(['category','anomaly_class','view_id']):
        known = group[group.status.eq('ok') & group.mask_state.isin(['positive','empty'])]
        acc = np.zeros((grid,grid), np.float64); npos = 0
        for rec in known.to_dict('records'):
            rgb = read_rgb(root/rec['image_path'])
            mask = read_mask(root/rec['mask_path'],rgb.shape[:2])
            acc += coarse_occupancy(mask, grid)
            npos += int(mask.any())
            source_rows.append({k:rec[k] for k in KEY+['image_path','mask_path','project_split','anomaly_class']})
        ident = hashlib.sha256(json.dumps([cat,cls,view]).encode()).hexdigest()[:12]
        occupancy_known = acc/len(known) if len(known) else np.full_like(acc,np.nan)
        occupancy_positive = acc/npos if npos else np.full_like(acc,np.nan)
        np.savez_compressed(out/f'{ident}.npz',occupancy_known=occupancy_known,
            occupancy_positive=occupancy_positive, count=acc)
        rec = dict(heatmap_id=ident,category=cat,anomaly_class=cls,view_id=view,
            n_selected_train_images=len(group),n_known=len(known),n_positive=npos,
            n_unknown=len(group)-len(known),grid=grid,split='train',npz=f'{ident}.npz')
        meta.append(rec)
        if len(known):
            fig,axes=plt.subplots(1,2,figsize=(8,3.4))
            for ax,arr,title in zip(axes,[occupancy_known,occupancy_positive],
                    [f'Known masks n={len(known)}',f'Positive masks n={npos}']):
                im=ax.imshow(arr,vmin=0,vmax=1,cmap='magma',extent=(0,1,1,0),interpolation='nearest')
                ax.set(title=title,xlabel='x / W',ylabel='y / H');fig.colorbar(im,ax=ax)
            fig.suptitle(f'TRAIN ONLY / {cat} / {cls} / {view}')
            fig.tight_layout();fig.savefig(out/f'{ident}.png',dpi=120);plt.close(fig)
    meta_cols=['heatmap_id','category','anomaly_class','view_id','n_selected_train_images',
        'n_known','n_positive','n_unknown','grid','split','npz']
    info=pd.DataFrame(meta,columns=meta_cols)
    save(info,out/'heatmap_metadata.csv')
    save(pd.DataFrame(source_rows,columns=KEY+['image_path','mask_path','project_split','anomaly_class']),out/'gan_source_manifest.csv')
    return info


def export_boxes(root, selected, out):
    """이진 마스크 성분을 single-class defect 라벨로 내보냄. 라벨 파일 stem은 image_id."""
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    boxes,images,excluded=[],[],[]
    valid=selected.sort_values(KEY)
    if valid.duplicated(KEY).any():raise ValueError('duplicate image key')
    for image_id,rec in enumerate(valid.to_dict('records'),1):
        if rec['status']!='ok' or rec['mask_state'] not in ('positive','empty'):
            excluded.append({**{k:rec[k] for k in KEY},'reason':rec['status']+'/'+rec['mask_state']})
            continue
        rgb=read_rgb(root/rec['image_path']);h,w=rgb.shape[:2]
        mask=read_mask(root/rec['mask_path'],(h,w));regs=mask_to_boxes(mask)
        image={**{k:rec[k] for k in KEY+['image_path','project_split','anomaly_class']},
               'image_id':image_id,'width':w,'height':h,'n_boxes':len(regs),
               'yolo_stem':f'{image_id:06d}'}
        images.append(image)
        labeldir=out/'yolo_labels'/rec['project_split'];labeldir.mkdir(parents=True,exist_ok=True)
        lines=[]
        for reg in regs:
            x0,y0,x1,y1=(reg[k] for k in ['x0','y0','x1','y1']);bw,bh=x1-x0,y1-y0
            row={**{k:rec[k] for k in KEY+['image_path','project_split','anomaly_class']},
                'image_id':image_id,**{k:reg[k] for k in ['component_id','x0','y0','x1','y1']},
                'width':w,'height':h,'bbox_width':bw,'bbox_height':bh,
                'mask_area':reg['area'],'box_area':bw*bh,'cx_norm':(x0+x1)/(2*w),
                'cy_norm':(y0+y1)/(2*h),'w_norm':bw/w,'h_norm':bh/h,'label_version':'binary-components-v2'}
            boxes.append(row)
            lines.append('0 '+' '.join(f'{row[k]:.10f}' for k in ['cx_norm','cy_norm','w_norm','h_norm']))
        (labeldir/f'{image_id:06d}.txt').write_text('\n'.join(lines)+('\n' if lines else ''),encoding='utf-8')
    b=pd.DataFrame(boxes,columns=BOX_COLS)
    imcols=KEY+['image_path','project_split','anomaly_class','image_id','width','height','n_boxes','yolo_stem']
    ims=pd.DataFrame(images,columns=imcols)
    save(b,out/'bbox_annotations.csv');save(ims,out/'detection_images.csv')
    save(pd.DataFrame(excluded,columns=KEY+['reason']),out/'bbox_excluded.csv')
    for split,g in ims.groupby('project_split'):
        ids=set(g.image_id)
        coco={'info':{'label_version':'binary-components-v2','area_definition':'bbox_width*bbox_height'},
            'images':[{'id':int(r.image_id),'file_name':r.image_path,'width':int(r.width),'height':int(r.height)} for r in g.itertuples()],
            'annotations':[], 'categories':[{'id':1,'name':'defect'}]}
        for i,r in enumerate(b[b.image_id.isin(ids)].itertuples(),1):
            coco['annotations'].append({'id':i,'image_id':int(r.image_id),'category_id':1,
                'bbox':[int(r.x0),int(r.y0),int(r.bbox_width),int(r.bbox_height)],
                'area':int(r.box_area),'mask_area':int(r.mask_area),'iscrowd':0})
        (out/f'coco_{split}.json').write_text(json.dumps(coco,ensure_ascii=False,indent=2))
    (out/'YOLO_README.md').write_text('''# YOLO label export only

이 폴더는 라벨만 제공합니다. 학습용 이미지 복사·연결은 학생 과제입니다.
`detection_images.csv`의 image_path를 읽어 동일 분할 `images/<split>/<yolo_stem>.png`로
RGB 이미지를 저장/링크하고 `yolo_labels/<split>/<yolo_stem>.txt`를 연결하세요.
원본 파일명과 label stem이 다르므로 이 매핑을 생략하면 학습할 수 없습니다.
정상·결함 비가시 뷰의 확인된 빈 마스크는 빈 txt. 미제공/오류는 bbox_excluded에 기록.
COCO는 원본 image_path 상대경로를 쓰므로 data root를 정확히 지정하세요.
GT는 원본 픽셀 xyxy 끝점 제외. 클래스를 추정하지 않고 defect 1클래스로 내보냅니다.
''',encoding='utf-8')
    return b,ims


def compare_resolutions(root, selected, out, sizes=(1024,512,256)):
    """RGB bilinear + label-map pixel-center nearest; 학습·추론 성능 측정 아님."""
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    rows,comp_rows=[],[]
    for rec in selected.to_dict('records'):
        if rec['status']!='ok':continue
        rgb=read_rgb(root/rec['image_path']);h,w=rgb.shape[:2]
        known=rec['mask_state'] in ('positive','empty')
        labels=None; regs=[]
        if known: labels,regs=components(read_mask(root/rec['mask_path'],(h,w)))
        for size in sizes:
            start=time.perf_counter()
            resized=np.array(Image.fromarray(rgb).resize((size,size),Image.Resampling.BILINEAR))
            resize_ms=(time.perf_counter()-start)*1000
            r={**{k:rec[k] for k in KEY+['anomaly_class','project_split']},
                'target_size':size,'source_width':w,'source_height':h,
                'upscaled':bool(size>w or size>h),'aspect_distorted':h!=w,
                'mean_gray':float(gray(resized).mean()),'rgb_uint8_bytes':int(resized.nbytes),
                'one_view_fp32_mib':3*size*size*4/2**20,'five_view_fp32_mib':5*3*size*size*4/2**20,
                'rgb_resize_ms':resize_ms,'n_components':len(regs) if known else np.nan,
                'lost_components':np.nan,'mask_state':rec['mask_state']}
            if known:
                small=nearest(labels,size)
                counts=np.bincount(small.ravel(),minlength=int(labels.max())+1)
                r['lost_components']=sum(int(counts[cid]==0) for cid,_ in regs)
                for cid,reg in regs:
                    ys,xs=np.where(small==cid)
                    comp_rows.append({**{k:rec[k] for k in KEY+['anomaly_class']},
                        'target_size':size,'component_id':cid,'source_area':reg['area'],
                        'remaining_area':int(counts[cid]),'disappeared':int(counts[cid]==0),
                        'box_width_after':int(xs.max()-xs.min()+1) if len(xs) else 0,
                        'box_height_after':int(ys.max()-ys.min()+1) if len(ys) else 0})
            rows.append(r)
    detail=pd.DataFrame(rows)
    cols=KEY+['anomaly_class','target_size','component_id','source_area','remaining_area',
              'disappeared','box_width_after','box_height_after']
    cr=pd.DataFrame(comp_rows,columns=cols)
    summary=detail.groupby(['category','anomaly_class','target_size']).agg(
        n_images=('sample_key','size'),upscaled_images=('upscaled','sum'),
        mean_gray=('mean_gray','mean'),median_resize_ms=('rgb_resize_ms','median'),
        one_view_fp32_mib=('one_view_fp32_mib','first'),five_view_fp32_mib=('five_view_fp32_mib','first')).reset_index()
    if len(cr):
        cs=cr.groupby(['category','anomaly_class','target_size']).agg(
            n_original_components=('component_id','size'),lost_components=('disappeared','sum'),
            median_remaining_area=('remaining_area','median')).reset_index()
        cs['lost_ratio']=cs.lost_components/cs.n_original_components
        summary=summary.merge(cs,how='left')
    else:
        for col in ['n_original_components','lost_components','median_remaining_area','lost_ratio']:summary[col]=np.nan
    save(detail,out/'resolution_image_comparison.csv');save(cr,out/'resolution_component_comparison.csv')
    save(summary,out/'resolution_class_summary.csv')
    return detail,cr,summary


def show_boxes(root, image_row, boxes):
    rgb=read_rgb(Path(root)/image_row['image_path'])
    fig,ax=plt.subplots(figsize=(7,5));ax.imshow(rgb)
    for r in boxes[boxes.image_id.eq(image_row['image_id'])].itertuples():
        ax.add_patch(Rectangle((r.x0,r.y0),r.x1-r.x0,r.y1-r.y0,fill=False,edgecolor='red',linewidth=1.4))
    ax.set_title(f"{image_row['category']} / {image_row['view_id']} / GT boxes")
    ax.axis('off');fig.tight_layout();return fig


def run_focused(root, selected, out):
    """selected는 core.analyze가 감사 후 저장한 개발 표본 목록."""
    out=Path(out)
    if not len(selected):raise ValueError('empty selected manifest')
    if selected.project_split.eq('test').any():
        raise ValueError('focused EDA excludes locked test data')
    if selected.duplicated(KEY).any():raise ValueError('duplicate selected key')
    if (selected.groupby(GROUP).project_split.nunique()>1).any():raise ValueError('product split leak')
    fingerprint=hashlib.sha256(selected.to_csv(index=False).encode()).hexdigest()
    previous=out/'run_info.json'
    if previous.exists() and json.loads(previous.read_text()).get('selected_sha256')!=fingerprint:
        raise ValueError('selected manifest changed: use a fresh OUTPUT directory to avoid stale labels')
    brightness=class_brightness(root,selected,out/'brightness')
    heatmaps=gan_heatmaps(root,selected,out/'gan_heatmaps')
    boxes=export_boxes(root,selected,out/'boxes')
    resolution=compare_resolutions(root,selected,out/'resolutions')
    (out/'run_info.json').write_text(json.dumps(dict(backend=NAME,
        sizes=[1024,512,256],heatmap_source_split='train',heatmap_grid=64,
        label_version='binary-components-v2',n_selected_images=len(selected),
        selected_sha256=hashlib.sha256(selected.to_csv(index=False).encode()).hexdigest(),
        scope='development EDA; augmentation and training remain student tasks'),indent=2))
    return dict(brightness=brightness,heatmaps=heatmaps,boxes=boxes,resolutions=resolution)
