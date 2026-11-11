"""Preserved per-image cell presence and known/positive conditional denominators."""
import json
import hashlib
import os
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from .core import binary_mask,read_image,save_json
from .legacy_bridge import coursework


def generate(root,out,df,policy,max_new_groups=0):
    train=df[(df.status=='NG')&(df.split=='train')]
    keys=[];counts=[];knowns=[];positives=[];areas=[];summaries=[];errors=[]
    coarse=coursework().coarse_occupancy
    groups=list(train.groupby(['category','defect_type','view'],sort=True))
    processed=0;new_groups=0;cache=out/'presence_checkpoint';cache.mkdir(exist_ok=True)
    for key,group in groups:
        fingerprint=hashlib.sha256((json.dumps(policy,sort_keys=True)+group[['image_path','mask_path']].to_csv(index=False)).encode()).hexdigest()
        checkpoint=cache/('_'.join(key)+'.npz')
        if checkpoint.exists():
            with np.load(checkpoint,allow_pickle=False) as saved:
                if str(saved['fingerprint'])!=fingerprint:raise ValueError('Presence checkpoint inputs changed')
                count=saved['count'];area=saved['area'];nk=int(saved['nk']);np_=int(saved['np_'])
            processed+=nk
        else:
            if max_new_groups and new_groups>=max_new_groups:
                print(f'Presence batch checkpointed; {len(keys)}/{len(groups)} groups complete',flush=True)
                return False
            count=np.zeros((64,64),np.float64);area=np.zeros_like(count);nk=0;np_=0;before_errors=len(errors)
            for row in group[group.mask_path!=''].to_dict('records'):
                try:
                    mask=binary_mask(read_image(root/row['mask_path'],True),policy)
                    if mask.shape!=(int(row['height']),int(row['width'])):raise ValueError('mask/image dimensions differ')
                    count+=coarse(mask,64);area+=cv2.resize(mask.astype(np.float32),(64,64),interpolation=cv2.INTER_AREA)
                    nk+=1;np_+=int(mask.any());processed+=1
                except Exception as exc:errors.append(dict(image_path=row['image_path'],mask_path=row['mask_path'],error=str(exc)))
            if len(errors)==before_errors:
                temporary=checkpoint.with_suffix('.tmp.npz');np.savez(temporary,count=count,area=area,nk=nk,np_=np_,fingerprint=fingerprint);os.replace(temporary,checkpoint)
            new_groups+=1
        known=count/nk if nk else np.full((64,64),np.nan)
        positive=count/np_ if np_ else np.full((64,64),np.nan)
        keys.append(list(key));counts.append(count);knowns.append(known);positives.append(positive);areas.append(area)
        mass=count.sum();summaries.append(dict(category=key[0],defect_type=key[1],view=key[2],n_images=len(group),n_known=nk,n_positive=np_,n_empty=nk-np_,n_unknown=len(group)-nk,observations=nk,max_occupancy=float(np.nanmax(known)) if nk else None,mean_occupancy=float(np.nanmean(known)) if nk else None,top10pct_mass_share=float(np.sort(count.ravel())[-410:].sum()/mass) if mass else None))
        print(f'presence heatmap {len(keys)}/{len(groups)}, masks {processed}',flush=True)
    if not keys:raise ValueError('No train NG groups')
    np.save(out/'occupancy_known.npy',np.stack(knowns));np.save(out/'occupancy_positive.npy',np.stack(positives));np.save(out/'presence_count.npy',np.stack(counts))
    np.save(out/'area_fraction_sum.npy',np.stack(areas));np.save(out/'observation_count.npy',np.stack([np.full((64,64),r['n_known']) for r in summaries]))
    save_json(out/'heatmap_groups.json',keys)
    pd.DataFrame(summaries).to_csv(out/'heatmap_summary.csv',index=False)
    pd.DataFrame(errors,columns=['image_path','mask_path','error']).to_csv(out/'heatmap_errors.csv',index=False)
    save_json(out/'heatmap_schema.json',dict(schema='presence-v2',grid=64,occupancy_known='cell presence count / n_known provided masks; confirmed empty masks included',occupancy_positive='cell presence count / n_positive nonempty masks',missing_groups='NaN, not normal',presence_rule='original coursework.coarse_occupancy: any foreground source pixel, no interpolated mask sampling',area_fraction_sum='additional area-weighted diagnostic; not a presence frequency'))
    save_json(out/'heatmap_validation.json',dict(train_ng_images=len(train),provided_masks=int((train.mask_path!='').sum()),success=processed,errors=len(errors),groups=len(keys),groups_no_known=sum(r['n_known']==0 for r in summaries),groups_no_positive=sum(r['n_positive']==0 for r in summaries),split_policy='source metadata split, preserved in run.json'))
    import matplotlib.pyplot as plt
    folder=out/'heatmaps';folder.mkdir(exist_ok=True)
    for key,known,positive,summary in zip(keys,knowns,positives,summaries):
        fig,axes=plt.subplots(1,2,figsize=(8,3.5))
        for ax,array,title in zip(axes,[known,positive],[f'Known masks N={summary["n_known"]}',f'Positive masks N={summary["n_positive"]}']):
            im=ax.imshow(np.ma.masked_invalid(array),vmin=0,vmax=1,cmap='magma',extent=(0,1,1,0));ax.set(title=title,xlabel='x / width',ylabel='y / height');fig.colorbar(im,ax=ax,label='Empirical cell presence frequency')
        fig.suptitle('/'.join(key));fig.tight_layout();fig.savefig(folder/('_'.join(key)+'.png'),dpi=120);plt.close(fig)
    fig,axes=plt.subplots(1,5,figsize=(17,4))
    stack=np.stack(counts)
    for ax,view in zip(axes,['C1','C2','C3','C4','C5']):
        idx=[i for i,key in enumerate(keys) if key[2]==view];n=sum(summaries[i]['n_known'] for i in idx);freq=stack[idx].sum(0)/n if n else np.full((64,64),np.nan)
        im=ax.imshow(np.ma.masked_invalid(freq),vmin=0,vmax=max(.01,float(np.nanmax(freq))) if n else 1,cmap='magma');ax.set(title=view,xlabel='Normalized x cell',ylabel='Normalized y cell');fig.colorbar(im,ax=ax,label='Known-mask cell presence')
    fig.suptitle('Train NG cell presence; all-category overview is descriptive');fig.tight_layout();fig.savefig(out/'heatmap_visualization.png',dpi=130);plt.close(fig)
    (out/'heatmap_analysis_report.md').write_text('# Train NG 위치 빈도\n\n기존 coursework.coarse_occupancy를 재사용합니다. 64×64 칸에 원본 양성 픽셀이 하나라도 있으면 영상별 1로 집계하므로 1픽셀 결함도 보존합니다. known 분모는 제공된 마스크(빈 마스크 포함), positive 분모는 양성 마스크입니다. 미제공/오류는 분모에서 제외하고 n_unknown에 기록합니다. 분모가 0이면 NaN이며 정상 영역으로 해석하지 않습니다. area_fraction_sum은 별도 면적 진단으로 빈도와 다릅니다. 촬영 배치/정렬/물체 영역/주석 의미 검수 없이 GAN 생성 확률로 단정하지 않습니다.\n')
    if errors:raise RuntimeError(f'Heatmap mask errors: {len(errors)}')
    return True
