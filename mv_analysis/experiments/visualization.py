"""실제/합성 출처를 표기하는 예측 시각화. 결함 GT가 없으면 없다고 표시한다."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from .detection import prepare,counts
from .anomaly import pixel_inputs


def _title(meta,model,threshold,kind):
    return f'{kind} | {model}\nID={meta["image_id"]} category={meta.get("category","UNKNOWN")} view={meta.get("view","UNKNOWN")}\nGT={meta["status"]}/{meta.get("mask_status","UNKNOWN")} threshold={threshold}'


def visualize_anomaly(image,gt,prediction,*,model_name,threshold,output,data_kind):
    """GT·점수·Overlay·이진 예측·FP/FN을 같은 원본 격자에서 나란히 표시한다."""
    if data_kind not in ('REAL','SYNTHETIC'):raise ValueError('Explicit visualization data kind required')
    if Path(output).exists():raise FileExistsError('Preserve existing prediction figure; choose a new path')
    image=np.asarray(image)
    if image.shape[:2]!=tuple(gt['original_hw']):raise ValueError('Original image grid mismatch')
    score=np.asarray(prediction['score_map'],float)
    if score.shape!=image.shape[:2]:raise ValueError('Restore heatmap first')
    item,pixel_reason=pixel_inputs(gt,prediction)
    valid_gt=item is not None
    mask=item[0] if item is not None else None
    binary=score>=threshold if threshold is not None else None
    fig,axes=plt.subplots(1,6,figsize=(19,4))
    axes[0].imshow(image);axes[0].set_title('Original')
    if valid_gt and mask is not None:axes[1].imshow(mask,cmap='gray');axes[1].set_title('GT mask')
    else:axes[1].text(.1,.5,'GT NOT PROVIDED / EXCLUDED');axes[1].set_title('GT unavailable')
    axes[2].imshow(score,cmap='inferno');axes[2].set_title(f'Score map / image score={prediction["score"]:.4g}')
    axes[3].imshow(image);axes[3].imshow(score,cmap='inferno',alpha=.45);axes[3].set_title('Heatmap overlay')
    if binary is not None:axes[4].imshow(binary,cmap='gray');axes[4].set_title('Predicted binary mask')
    else:axes[4].text(.1,.5,'THRESHOLD N/A')
    if valid_gt and mask is not None and binary is not None:
        scope=item[2]&np.isfinite(score)
        error=np.zeros((*binary.shape,3));error[binary&~np.asarray(mask,bool)&scope]=[1,0,0];error[~binary&np.asarray(mask,bool)&scope]=[0,0,1];error[~scope]=[.4,.4,.4]
        axes[5].imshow(error);axes[5].set_title('FP=red / FN=blue / unobserved=gray')
    else:axes[5].text(.1,.5,'FP/FN N/A')
    for ax in axes:ax.axis('off')
    fig.suptitle(_title(gt,model_name,threshold,data_kind),fontsize=9);fig.tight_layout();Path(output).parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,dpi=130);plt.close(fig)
    return Path(output)


def visualize_detection(image,gt,prediction,classes,policy,*,model_name,output,data_kind):
    """제공된 위치 GT가 없으면 박스 없음=정상으로 표시하지 않는다."""
    if Path(output).exists():raise FileExistsError('Preserve existing prediction figure; choose a new path')
    if tuple(np.asarray(image).shape[:2])!=tuple(gt['original_hw']):raise ValueError('Original grid mismatch')
    # imshow 기본 픽셀 중심(-0.5 오프셋) 대신 XYXY exclusive와 같은 이미지 경계 0..W/H를 쓴다.
    fig,ax=plt.subplots(figsize=(7,7));ax.imshow(image,extent=(0,gt['original_hw'][1],gt['original_hw'][0],0));inverse={v:k for k,v in classes.items()};threshold=policy.detection
    order=np.argsort(-np.asarray(prediction['scores']),kind='stable')[:100]
    prediction=dict(prediction,boxes=np.asarray(prediction['boxes']).reshape(-1,4)[order].tolist(),labels=np.asarray(prediction['labels'])[order].tolist(),scores=np.asarray(prediction['scores'])[order].tolist())
    records,excluded,_=prepare([gt],[prediction],gt['split'],classes)
    detail=counts(records,threshold,classes.values())[2][0] if records and threshold is not None else None
    if records:
        for i,(box,label) in enumerate(zip(gt['boxes'],gt['labels'])):
            x0,y0,x1,y1=box;ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,color='cyan',linestyle='--'))
            ax.text(x0,y0,f'GT {inverse[label]}'+(' FN' if detail and i in detail['fn_indices'] else ''),color='cyan',fontsize=7)
    else:ax.text(.02,.02,'LOCATION GT UNAVAILABLE / EXCLUDED',transform=ax.transAxes,color='yellow')
    for i,(box,label,score) in enumerate(zip(prediction['boxes'],prediction['labels'],prediction['scores'])):
        if threshold is not None and score<threshold:continue
        x0,y0,x1,y1=box;tag='TP' if detail and i in detail['tp_indices'] else 'FP' if detail else 'UNVERIFIED'
        color='lime' if tag=='TP' else 'red' if tag=='FP' else 'orange'
        ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,color=color));ax.text(x0,y1,f'{inverse[label]} {score:.3f} {tag}',color=color,fontsize=7)
    ax.set_title(_title(gt,model_name,threshold,data_kind),fontsize=9);ax.set_xlabel('original x [px]');ax.set_ylabel('original y [px]');fig.tight_layout();Path(output).parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,dpi=140);plt.close(fig)
    return Path(output)


def select_cases(gt,predictions,metrics,limit=12):
    """작은 결함·외곽·FP/FN과 품목/시점의 대표 검토 후보를 고른다. 최종 사람 해석과 구분한다."""
    details={r['image_id']:r for r in metrics.get('per_image',[])};pred_by_id={p['image_id']:p for p in predictions};candidates=[]
    for g in gt:
        reasons=[];d=details.get(g['image_id'],{})
        if metrics.get('task')=='anomaly' and metrics.get('image',{}).get('threshold') is not None:
            predicted=pred_by_id[g['image_id']]['score']>=metrics['image']['threshold'];positive=g['status']=='NG'
            if predicted and not positive:reasons.append('FP')
            elif not predicted and positive:reasons.append('FN')
            elif predicted and positive:reasons.append('TP')
        for flag in ('fp','fn','tp'):
            if d.get(flag,0):reasons.append(flag.upper())
        if len(g.get('boxes',[])):
            boxes=np.asarray(g['boxes']);areas=np.prod(boxes[:,2:]-boxes[:,:2],axis=1)
            if areas.min()<32**2:reasons.append('SMALL_DEFECT')
            h,w=g['original_hw']
            if np.any(boxes[:,:2]<16) or np.any(boxes[:,2:]>[w-16,h-16]):reasons.append('EDGE_DEFECT')
        candidates.append(dict(image_id=g['image_id'],category=g.get('category'),view=g.get('view'),reasons=reasons))
    return sorted(candidates,key=lambda r:(-(len(r['reasons'])+10*sum(v in ('FP','FN') for v in r['reasons'])),r['image_id']))[:limit]
