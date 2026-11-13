# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Add readable per-group heatmaps without overwriting original figures."""
import argparse
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();root=a.run;out=root/'heatmaps_scaled';out.mkdir(exist_ok=True)
keys=json.loads((root/'heatmap_groups.json').read_text());pos=np.load(root/'occupancy_positive.npy');known=np.load(root/'occupancy_known.npy')
for i,key in enumerate(keys):
 name='_'.join(key)+'.png';path=out/name
 if path.exists():continue
 freq=np.divide(pos[i],known[i],out=np.full_like(pos[i],np.nan),where=known[i]>0);maximum=float(np.nanmax(freq))
 fig,ax=plt.subplots(figsize=(5,4));im=ax.imshow(np.ma.masked_invalid(freq),vmin=0,vmax=max(maximum,1e-6),cmap='viridis');ax.set(title='/'.join(key)+f'\nN={int(known[i].max())}, peak={maximum:.4f}',xlabel='Normalized x cell [0,63]',ylabel='Normalized y cell [0,63]');fig.colorbar(im,ax=ax,label='Mean foreground area fraction (adaptive scale)');fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)
 if (i+1)%100==0:print(f'Scaled heatmap {i+1}/{len(keys)}',flush=True)
(out/'render_manifest.json').write_text(json.dumps(dict(groups=len(keys),files=len(list(out.glob('*.png'))),scale='per-group max; compare colorbar numeric values, not colors',source_arrays=['occupancy_known.npy','occupancy_positive.npy']),indent=2));print('Scaled heatmaps complete')
