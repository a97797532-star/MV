from __future__ import annotations
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
from .core import (read_image, binary_mask, components, brightness_metrics,
                   information_loss, prepare_image_reference, save_json, plot_bars)


def cached_rows(out, name, rows, calculate):
    """Append-only checkpoints: each successful input is committed independently."""
    cache=out/f'{name}.jsonl'; done={};errors=[]
    if cache.exists():
        # Stream large checkpoints; retain only parsed successful records in memory.
        with cache.open('rb+') as stream:
            while True:
                offset=stream.tell();line=stream.readline()
                if not line:break
                try:
                    obj=json.loads(line);done[obj['image_path']]=obj
                except json.JSONDecodeError:
                    if stream.read(1):raise
                    stream.seek(offset);stream.truncate();break
    def process(row):
        try:return {**row,**calculate(row)},None
        except Exception as exc:return None,dict(image_path=row['image_path'],error=str(exc))
    pending=[row for row in rows if row['image_path'] not in done]
    with cache.open('a') as stream,ThreadPoolExecutor(max_workers=max(1,min(4,int(os.getenv('MV_ANALYSIS_WORKERS','4'))))) as pool:
        for start in range(0,len(pending),40):
            for obj,error in pool.map(process,pending[start:start+40]):
                if error:errors.append(error)
                else:
                    stream.write(json.dumps(obj,allow_nan=False)+'\n');stream.flush();done[obj['image_path']]=obj
            print(f'{name} {len(done)}/{len(rows)} errors={len(errors)}',flush=True)
    pd.DataFrame(errors,columns=['image_path','error']).to_csv(out/f'{name}_errors.csv',index=False)
    result=pd.DataFrame(list(done.values()));result.to_csv(out/f'{name}.csv',index=False)
    save_json(out/f'{name}_execution.json',dict(target=len(rows),success=len(result),errors=len(errors),checkpoint=str(cache.name)))
    if errors:raise RuntimeError(f'{name}: {len(errors)} failed inputs; successes retained')
    return result


def brightness(root,out,df,policy=None):
    def calc(row):
        im=read_image(root/row['image_path']);m=brightness_metrics(im)
        if row['mask_path'] and policy and policy.get('validated'):
            mask=binary_mask(read_image(root/row['mask_path'],True),policy).astype(bool)
            gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
            m['defect_minus_background']=float(gray[mask].mean()-gray[~mask].mean()) if mask.any() and (~mask).any() else None
        return m
    b=cached_rows(out,'brightness_per_image',df.to_dict('records'),calc)
    keys=['category','defect_type','view','status','split']
    b.groupby(keys).brightness.agg(['count','mean','std','min','max']).reset_index().to_csv(out/'brightness_summary.csv',index=False)
    comparisons=[]
    for (category,defect,view),ng in b[b.status=='NG'].groupby(['category','defect_type','view']):
        ok=b[(b.category==category)&(b.view==view)&(b.status=='OK')]
        x=ok.brightness.to_numpy();y=ng.brightness.to_numpy()
        if min(len(x),len(y))<2: continue
        pooled=np.sqrt(((len(x)-1)*x.var(ddof=1)+(len(y)-1)*y.var(ddof=1))/(len(x)+len(y)-2))
        hx,_=np.histogram(x,bins=np.linspace(0,256,33));hy,_=np.histogram(y,bins=np.linspace(0,256,33))
        comparisons.append(dict(category=category,defect_type=defect,view=view,n_ok=len(x),n_ng=len(y),
                                mean_difference=float(y.mean()-x.mean()),cohens_d=float((y.mean()-x.mean())/pooled) if pooled>0 else None,
                                histogram_overlap=float(np.minimum(hx/hx.sum(),hy/hy.sum()).sum())))
    c=pd.DataFrame(comparisons,columns=['category','defect_type','view','n_ok','n_ng','mean_difference','cohens_d','histogram_overlap'])
    c['cohens_d']=pd.to_numeric(c.cohens_d,errors='coerce')
    c.to_csv(out/'brightness_comparison.csv',index=False)
    c.assign(abs_d=c.cohens_d.abs()).sort_values('abs_d',ascending=False).head(40).to_csv(out/'brightness_review_candidates.csv',index=False)
    train=b[b.split=='train']
    train.groupby(['category','view']).brightness.quantile([.05,.5,.95]).unstack().to_csv(out/'brightness_train_augmentation_stats.csv')
    plot_bars(b.groupby(['view','status']).brightness.mean(),out/'brightness_distribution.png','Mean image brightness by view and status','Mean grayscale intensity [0,255]')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots()
    for status,part in b.groupby('status'):ax.hist(part.brightness,bins=np.linspace(0,256,33),density=True,alpha=.5,label=status)
    ax.set(title='Distribution of image mean brightness',xlabel='Mean grayscale intensity [0,255]',ylabel='Density');ax.legend();fig.tight_layout();fig.savefig(out/'brightness_histogram.png');plt.close(fig)
    (out/'brightness_analysis_report.md').write_text(f'# 밝기 분석\n\n처리 {len(b):,}장. OpenCV BGR→GRAY의 0–255 밝기이며 RGB 채널 평균과 다릅니다.\n\n비교 {len(c)}개: NG 불량유형과 같은 품목·시점의 OK를 비교합니다. Histogram overlap은 32 bin 확률질량의 교집합입니다. Cohen d는 pooled 표준편차를 사용합니다.\n\n증강 통계는 train만 사용합니다. 밝기 차이가 결함 자체인지 조명·재질·촬영 배치 차이인지 후보 원본을 검수해야 합니다. 차이를 모델 검출 난이도로 단정하지 않습니다.\n')


def area_heatmap(root,out,df,policy):
    positive={};known={};summary=[]
    train=df[(df.status=='NG')&(df.split=='train')&(df.mask_path!='')]
    for i,row in enumerate(train.to_dict('records')):
        mask=binary_mask(read_image(root/row['mask_path'],True),policy)
        key=(row['category'],row['defect_type'],row['view'])
        # Fraction of each normalized grid cell covered by foreground.
        occupancy=cv2.resize(mask.astype(np.float32),(64,64),interpolation=cv2.INTER_AREA)
        positive[key]=positive.get(key,np.zeros((64,64),np.float64))+occupancy
        known[key]=known.get(key,0)+1
        if (i+1)%1000==0:print(f'heatmap {i+1}/{len(train)}',flush=True)
    if not known:raise ValueError('No train NG masks')
    keys=sorted(known)
    pos=np.stack([positive[k] for k in keys]);kn=np.stack([np.full((64,64),known[k]) for k in keys])
    np.save(out/'occupancy_positive.npy',pos);np.save(out/'occupancy_known.npy',kn)
    save_json(out/'heatmap_groups.json',[list(k) for k in keys])
    for k in keys:
        freq=positive[k]/known[k];mass=positive[k].sum()
        summary.append(dict(category=k[0],defect_type=k[1],view=k[2],observations=known[k],
                            max_occupancy=float(freq.max()),mean_occupancy=float(freq.mean()),
                            top10pct_mass_share=float(np.sort(positive[k].ravel())[-410:].sum()/mass) if mass>0 else 0))
    pd.DataFrame(summary).to_csv(out/'heatmap_summary.csv',index=False)
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,5,figsize=(17,4))
    for ax,view in zip(axs,['C1','C2','C3','C4','C5']):
        idx=[i for i,k in enumerate(keys) if k[2]==view]
        if idx:
            freq=pos[idx].sum(0)/kn[idx].sum(0);im=ax.imshow(freq,vmin=0,vmax=max(.01,float(freq.max())));fig.colorbar(im,ax=ax,label='Foreground area fraction')
        ax.set(title=view,xlabel='Normalized x cell',ylabel='Normalized y cell')
    fig.suptitle('Train NG foreground occupancy (all categories, descriptive only)');fig.tight_layout();fig.savefig(out/'heatmap_visualization.png');plt.close(fig)
    # Per-group plots preserve category/type/view distinctions.
    folder=out/'heatmaps';folder.mkdir(exist_ok=True)
    for i,k in enumerate(keys):
        fig,ax=plt.subplots(figsize=(4,4));im=ax.imshow(pos[i]/kn[i],vmin=0,vmax=1);ax.set(title='/'.join(k),xlabel='Normalized x cell',ylabel='Normalized y cell');fig.colorbar(im,ax=ax,label='Foreground area fraction');fig.tight_layout();fig.savefig(folder/('_'.join(k)+'.png'));plt.close(fig)
    (out/'heatmap_analysis_report.md').write_text(f'# 불량 위치\n\nTrain NG {len(train):,}장, {len(keys)}그룹. 64×64 area occupancy는 마스크 면적 분율입니다. positive는 면적 분율의 합, known은 해당 격자의 관측 마스크 수입니다.\n\n마스크는 이미지 전체를 주석한 것으로 가정합니다. 물체 가시성/주석 누락 여부는 별도 검증이 필요하며, 미관측 그룹은 배열에 없고 정상으로 간주하지 않습니다. 관측 마스크에서 결함이 없던 격자 역시 정상 보장의 근거가 아닙니다. 공간적으로 정렬되지 않은 다른 품목의 종합 그림은 기술 통계입니다. GAN 위치 정책에는 품목·불량·시점별 그림과 관측 수를 사용하고 희소 그룹의 범위를 강제하지 않습니다.\n')


def bbox(root,out,df,policy,class_policy='defect_type'):
    ng=df[(df.status=='NG')&(df.mask_path!='')&(~df.label_conflict)];class_key=lambda r:r['defect_type'] if class_policy=='defect_type' else r['category']+'__'+r['defect_type']
    names=sorted({class_key(r) for r in ng.to_dict('records')});mapping={n:i for i,n in enumerate(names)}
    save_json(out/'classes.json',dict(policy=class_policy,yolo=mapping,coco={n:i+1 for n,i in mapping.items()},classification={'OK':0,'NG':1}))
    boxes=[];summaries=[];errors=[];coco_images=[];annotations=[]
    skipped=[]
    for image_id,row in enumerate(df.to_dict('records'),1):
        if row['status']=='NG' and (not row['mask_path'] or row.get('label_conflict',False)):
            skipped.append(dict(image_path=row['image_path'],reason='NG without location annotation or unresolved defect class; no label generated'));continue
        try:
            h,w=int(row['height']),int(row['width']);found=[]
            annotation_status='normal_OK' if row['status']=='OK' else 'provided_positive'
            if row['status']=='NG':
                mask=binary_mask(read_image(root/row['mask_path'],True),policy)
                if mask.shape!=(h,w):raise ValueError('mask shape mismatch')
                found=components(mask)
                if not found:annotation_status='provided_empty'
            labels=[]
            for x0,y0,x1,y1,area in found:
                if not (0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('invalid xyxy coordinates')
                cid=mapping[class_key(row)]
                boxes.append(dict(image_path=row['image_path'],category=row['category'],defect_type=row['defect_type'],view=row['view'],class_id=cid,x0=x0,y0=y0,x1=x1,y1=y1,component_area=area,bbox_area=(x1-x0)*(y1-y0),relative_area=(x1-x0)*(y1-y0)/(w*h)))
                labels.append(f'{cid} {(x0+x1)/(2*w):.9f} {(y0+y1)/(2*h):.9f} {(x1-x0)/w:.9f} {(y1-y0)/h:.9f}')
                annotations.append(dict(id=len(annotations)+1,image_id=image_id,category_id=cid+1,bbox=[x0,y0,x1-x0,y1-y0],area=(x1-x0)*(y1-y0),iscrowd=0))
            label=out/'yolo_labels'/Path(row['image_path']).with_suffix('.txt');label.parent.mkdir(parents=True,exist_ok=True);label.write_text('\n'.join(labels)+ ('\n' if labels else ''))
            coco_images.append(dict(id=image_id,file_name=row['image_path'],height=h,width=w))
            summaries.append(dict(image_path=row['image_path'],status=row['status'],components=len(found),annotation_status=annotation_status))
            if found and len(summaries)<=15:
                im=read_image(root/row['image_path'])
                for x0,y0,x1,y1,_ in found:cv2.rectangle(im,(x0,y0),(x1-1,y1-1),(0,0,255),2)
                cv2.imwrite(str(out/f'bbox_review_{image_id}.png'),im)
        except Exception as exc:errors.append(dict(image_path=row['image_path'],error=str(exc)))
        if image_id%1000==0:print(f'bbox {image_id}/{len(df)} errors={len(errors)}',flush=True)
    pd.DataFrame(skipped,columns=['image_path','reason']).to_csv(out/'bbox_unannotated_ng_skipped.csv',index=False)
    b=pd.DataFrame(boxes,columns=['image_path','category','defect_type','view','class_id','x0','y0','x1','y1','component_area','bbox_area','relative_area']);b.to_csv(out/'defect_bboxes.csv',index=False)
    pd.DataFrame(summaries).to_csv(out/'image_component_summary.csv',index=False)
    pd.DataFrame(errors,columns=['image_path','error']).to_csv(out/'bbox_errors.csv',index=False)
    save_json(out/'defect_coco.json',dict(images=coco_images,annotations=annotations,categories=[dict(id=i+1,name=n) for n,i in mapping.items()]))
    validation=dict(images=len(summaries),expected_images=len(df)-len(skipped),unannotated_ng_skipped=len(skipped),boxes=len(boxes),errors=len(errors),classes=len(names),normal_empty_labels=sum(s['status']=='OK' and s['components']==0 for s in summaries),provided_empty_ng_masks=sum(s['annotation_status']=='provided_empty' for s in summaries),coordinate_format='xyxy, exclusive x1/y1',small_box_definition='bbox area < 32^2 native pixels',small_box_count=int((b.bbox_area<1024).sum()))
    save_json(out/'bbox_validation_report.json',validation)
    if len(b):plot_bars(b.groupby('defect_type').size(),out/'bbox_class_distribution.png','Component bounding boxes by defect type','Box count')
    (out/'bbox_analysis_report.md').write_text('# Bounding Box\n\n'+json.dumps(validation,ensure_ascii=False,indent=2)+'\n\n8방향 연결 성분, 면적 필터 없음. 원본 좌표 xyxy 끝점은 exclusive입니다. YOLO 0-based, COCO 1-based입니다. 한 NG의 모든 성분은 파일명의 같은 불량 유형으로 가정하며 성분별 실제 의미는 미확인입니다. COCO area는 박스 면적(마스크 분할 라벨은 내보내지 않음)입니다. 정상 YOLO 파일은 빈 파일이며 탐지 normal 클래스를 만들지 않습니다. 기존 제공 PNG가 전부 0인 NG는 annotation_status=provided_empty, 박스 0개/빈 라벨로 표현하되 NG 분류는 유지합니다. 마스크가 없는 NG에는 라벨을 만들지 않습니다. small은 원본 픽셀 박스 면적 기준으로 모델 성능을 의미하지 않습니다.\n')
    if errors:raise RuntimeError(f'BBox errors: {len(errors)}')


def resolution(root,out,df):
    def calc(row):
        im=read_image(root/row['image_path'])
        reference=prepare_image_reference(im)
        return {'metrics':[information_loss(im,size,reference) for size in (1024,512,256)],
                'step_512_to_256':information_loss(cv2.resize(im,(512,512),interpolation=cv2.INTER_AREA),256)}
    raw=cached_rows(out,'resolution_checkpoint',df.to_dict('records'),calc)
    rows=[];steps=[]
    for row in raw.to_dict('records'):
        metrics=row.pop('metrics');step=row.pop('step_512_to_256')
        for metric in metrics:rows.append({**row,**metric})
        steps.append(dict(image_path=row['image_path'],**step,ssim_drop_512_to_256=metrics[1]['ssim']-metrics[2]['ssim'],rgb_rmse_increase=metrics[2]['rgb_rmse']-metrics[1]['rgb_rmse']))
    r=pd.DataFrame(rows);r.to_csv(out/'per_view_information_loss.csv',index=False)
    metric_names=['psnr_db','ssim','edge_recall','edge_f1','laplacian_retention','gradient_retention','local_contrast_retention','rgb_rmse']
    r.groupby(['category','view','status','target'])[metric_names].agg(['count','mean','std','median']).to_csv(out/'category_view_loss_summary.csv')
    pd.DataFrame(steps).to_csv(out/'per_image_stepwise_changes.csv',index=False)
    priority=r[r.target==256].sort_values('ssim');priority.head(50).to_csv(out/'review_priority_images.csv',index=False)
    plot_bars(r[r.target!=1024].groupby(['view','target']).ssim.mean(),out/'resolution_loss_summary.png','Mean SSIM after resize and reconstruction','SSIM [0,1]')
    visualize_resolution(root,out,df,priority)
    (out/'resolution_analysis_report.md').write_text(f'# 해상도 정보 손실\n\n{len(raw):,}개 JPG의 1024/512/256 정사각 resize와 원본 크기 복원을 비교했습니다. 비정사각 영상은 정사각으로 직접 변형하며 원본 좌표로 다시 복원합니다. INTER_AREA 축소, INTER_LINEAR 복원. 512→256 단계는 512 영상을 기준으로 직접 계산합니다.\n\nSSIM: local Gaussian 11×11 sigma 1.5, data range 255. PSNR: BGR 전체 MSE, 완전 일치 시 저장 상한 120 dB. BGR/RGB 재배열은 전체 RGB RMSE를 바꾸지 않습니다. Canny 100/200, 동일 픽셀 경계 교집합을 사용하므로 위치 이동에도 민감합니다. 고주파 대리값은 Laplacian energy 비율이며 주파수 스펙트럼 직접 측정은 아닙니다. 국소 대비는 11×11 표준편차 평균 비율입니다.\n\n원본 크기는 metadata에서 확인합니다. 이 지표는 영상 복원 변화이며 결함 의미, 검출 정확도, 추론 속도를 측정하지 않습니다. 작은 박스와 저 SSIM 후보를 함께 검수한 뒤 해상도를 실험해야 합니다.\n')


def visualize_resolution(root,out,df,priority):
    import matplotlib.pyplot as plt
    chosen=None
    for key,group in df.groupby('capture_id'):
        if set(group.view)=={'C1','C2','C3','C4','C5'}:chosen=group.sort_values('view');break
    if chosen is not None:
        fig,axes=plt.subplots(3,5,figsize=(15,9))
        for col,row in enumerate(chosen.to_dict('records')):
            im=read_image(root/row['image_path'])
            for line,size in enumerate((1024,512,256)):
                show=cv2.resize(im,(size,size),interpolation=cv2.INTER_AREA)
                axes[line,col].imshow(cv2.cvtColor(show,cv2.COLOR_BGR2RGB));axes[line,col].set_title(f"{row['view']} {size}x{size}");axes[line,col].axis('off')
        fig.suptitle('Same capture, five views, three resolutions');fig.tight_layout();fig.savefig(out/'five_view_loss.png');plt.close(fig)
    if priority.empty:return
    row=priority.iloc[0];im=read_image(root/row.image_path);h,w=im.shape[:2]
    recon=cv2.resize(cv2.resize(im,(256,256),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
    diff=np.abs(im.astype(float)-recon).mean(2);score=cv2.blur(diff.astype(np.float32),(64,64));y,x=np.unravel_index(np.argmax(score),score.shape)
    x0=min(max(0,x-64),max(0,w-128));y0=min(max(0,y-64),max(0,h-128))
    fig,axes=plt.subplots(1,4,figsize=(14,4))
    for ax,title,show in zip(axes,['Original crop','512 reconstruction','256 reconstruction','Absolute difference [0,255]'],[im,cv2.resize(cv2.resize(im,(512,512),interpolation=cv2.INTER_AREA),(w,h)),recon,diff]):
        crop=show[y0:y0+128,x0:x0+128]
        ax.imshow(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB) if crop.ndim==3 else crop,cmap='magma',**({'vmin':0,'vmax':255} if crop.ndim==2 else {}));ax.set_title(title);ax.axis('off')
    fig.suptitle(f'Max local reconstruction change; crop x={x0}, y={y0}, size=128');fig.tight_layout();fig.savefig(out/'detail_crop_comparison.png');plt.close(fig)
    save_json(out/'detail_crop_source.json',dict(image_path=row.image_path,x0=int(x0),y0=int(y0),size=128))


def heatmap(root,out,df,policy,mode='presence'):
    if mode=='area':return area_heatmap(root,out,df,policy)
    from .presence_heatmaps import generate
    return generate(root,out,df,policy)
