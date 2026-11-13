"""원본 좌표의 결함 검출 평가. COCO mAP와 고정 Threshold의 운영 지표를 분리한다."""
from contextlib import redirect_stdout
import io
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
from .contracts import PROTOCOL, ThresholdPolicy, aligned_records, digest
from .geometry import validate_boxes


def iou_matrix(a, b):
    a, b = np.asarray(a).reshape(-1,4), np.asarray(b).reshape(-1,4)
    low = np.maximum(a[:,None,:2], b[None,:,:2]); high = np.minimum(a[:,None,2:], b[None,:,2:])
    inter = np.prod(np.maximum(high-low,0),axis=2)
    return inter/(np.prod(a[:,2:]-a[:,:2],axis=1)[:,None]+np.prod(b[:,2:]-b[:,:2],axis=1)[None,:]-inter+1e-30)


def prepare(gt, predictions, split, class_names):
    """정답 미제공 NG는 정상 Negative가 아니라 제외 사유가 있는 항목이다."""
    if any(not isinstance(v,int) or isinstance(v,bool) for v in class_names.values()) or set(class_names.values())!=set(range(len(class_names))):
        raise ValueError('Contiguous zero-based canonical class map required')
    if len(set(class_names.values())) != len(class_names):
        raise ValueError('Class mapping IDs must be unique')
    class_ids = set(class_names.values())
    records, excluded = [], []
    pairs = aligned_records(gt, predictions, split)
    for g,p in pairs:
        # GT 미제공 항목도 예측 형식 자체가 잘못됐는지는 검사한다.
        pb,pl=validate_boxes(p['boxes'],p['labels'],g['original_hw'],class_ids)
        raw_scores=np.asarray(p['scores'],float)
        if raw_scores.shape!=(len(pb),) or not np.isfinite(raw_scores).all() or np.any((raw_scores<0)|(raw_scores>1)):
            raise ValueError('Invalid detection confidence')
        status = g.get('detection_status')
        if status not in ('SUPERVISED_VALID','OK_NEGATIVE'):
            excluded.append(dict(image_id=g['image_id'],reason=status or 'MISSING_ANNOTATION_STATUS'))
            continue
        gb, gl = validate_boxes(g['boxes'],g['labels'],g['original_hw'],class_ids)
        pb, pl = validate_boxes(p['boxes'],p['labels'],g['original_hw'],class_ids)
        scores = np.asarray(p['scores'],float)
        if scores.shape != (len(pb),) or not np.isfinite(scores).all() or np.any((scores<0)|(scores>1)):
            raise ValueError('Invalid detection confidence')
        if (g['status']=='OK' and (len(gb) or status!='OK_NEGATIVE')) or (g['status']=='NG' and (not len(gb) or status!='SUPERVISED_VALID')):
            raise ValueError('Contradictory detection GT/status')
        if g['status'] not in ('OK','NG'):
            raise ValueError('Unknown image GT')
        order = np.argsort(-scores,kind='stable')[:PROTOCOL['detection_max_dets'][-1]]
        records.append((g,gb,gl,pb[order],pl[order],scores[order]))
    return records,excluded,len(pairs)


def counts(records, threshold, class_ids):
    per = {int(c):dict(tp=0,fp=0,fn=0) for c in class_ids}
    details=[]
    for g,gb,gl,pb,pl,scores in records:
        selected=np.flatnonzero(scores>=threshold); used=set(); tp=[]; fp=[]
        for k in selected:
            matches=[j for j in range(len(gb)) if j not in used and gl[j]==pl[k]]
            if matches:
                overlaps=iou_matrix(pb[k:k+1],gb[matches])[0]; best=int(np.argmax(overlaps));j=matches[best]
                if overlaps[best]>=PROTOCOL['detection_count_iou']:
                    used.add(j);per[int(pl[k])]['tp']+=1;tp.append(int(k));continue
            per[int(pl[k])]['fp']+=1;fp.append(int(k))
        fn=[j for j in range(len(gb)) if j not in used]
        for j in fn:per[int(gl[j])]['fn']+=1
        details.append(dict(image_id=g['image_id'],category=g.get('category','UNKNOWN'),view=g.get('view','UNKNOWN'),tp_indices=tp,fp_indices=fp,fn_indices=fn,tp=len(tp),fp=len(fp),fn=len(fn)))
    total={key:sum(v[key] for v in per.values()) for key in ('tp','fp','fn')}
    def enrich(d):
        t,f,n=d['tp'],d['fp'],d['fn']
        return dict(d,precision=t/(t+f) if t+f else 0.,recall=t/(t+n) if t+n else 0.,f1=2*t/(2*t+f+n) if 2*t+f+n else 0.)
    return enrich(total),{str(c):enrich(v) for c,v in per.items()},details


def confusion(records, threshold, class_names):
    """클래스 무관 IoU 매칭 후 GT행/예측열을 기록한다. 마지막 행/열은 배경 FP/FN이다."""
    ids=sorted(class_names.values());pos={c:i for i,c in enumerate(ids)};matrix=np.zeros((len(ids)+1,len(ids)+1),int)
    for g,gb,gl,pb,pl,scores in records:
        used=set()
        for k in np.flatnonzero(scores>=threshold):
            candidates=[j for j in range(len(gb)) if j not in used]
            if candidates:
                overlap=iou_matrix(pb[k:k+1],gb[candidates])[0];best=int(np.argmax(overlap));j=candidates[best]
                if overlap[best]>=PROTOCOL['detection_count_iou']:
                    used.add(j);matrix[pos[int(gl[j])],pos[int(pl[k])]]+=1;continue
            matrix[-1,pos[int(pl[k])]]+=1
        for j in set(range(len(gb)))-used:matrix[pos[int(gl[j])],-1]+=1
    inverse={v:k for k,v in class_names.items()}
    return dict(labels=[inverse[c] for c in ids]+['BACKGROUND'],matrix=matrix.tolist(),axes='rows=GT,columns=prediction')


def coco_metrics(records,class_names):
    """COCO API의 IoU.50:.95, recall101개 지점, maxDets100, area=all을 사용한다. 미정의 AP는 null이다."""
    if not records or not any(len(r[1]) for r in records):
        return dict(map50=None,map50_95=None,per_class={},reason='NO_VALID_POSITIVE_GT')
    dataset={'info':{},'images':[],'annotations':[],
             'categories':[{'id':int(c)+1,'name':name} for name,c in class_names.items()]}
    results=[];annotation=1
    for i,(g,gb,gl,pb,pl,scores) in enumerate(records,1):
        h,w=g['original_hw'];dataset['images'].append(dict(id=i,width=w,height=h))
        for box,label in zip(gb,gl):
            x0,y0,x1,y1=box;dataset['annotations'].append(dict(id=annotation,image_id=i,category_id=int(label)+1,bbox=[x0,y0,x1-x0,y1-y0],area=(x1-x0)*(y1-y0),iscrowd=0));annotation+=1
        for box,label,score in zip(pb,pl,scores):
            x0,y0,x1,y1=box;results.append(dict(image_id=i,category_id=int(label)+1,bbox=[x0,y0,x1-x0,y1-y0],score=float(score)))
    with redirect_stdout(io.StringIO()):
        truth=COCO();truth.dataset=dataset;truth.createIndex()
        if results:predicted=truth.loadRes(results)
        else:
            predicted=COCO();predicted.dataset={'images':dataset['images'],'categories':dataset['categories'],'annotations':[]};predicted.createIndex()
        engine=COCOeval(truth,predicted,'bbox');engine.params.iouThrs=np.array(PROTOCOL['detection_iou_thresholds']);engine.params.maxDets=PROTOCOL['detection_max_dets'];engine.evaluate();engine.accumulate();engine.summarize()
    precision=engine.eval['precision'];recall=engine.eval['recall'];per={}
    def average(values):
        v=values[values>=0];return float(v.mean()) if len(v) else None
    for k,c in enumerate(engine.params.catIds):
        name=next(n for n,v in class_names.items() if v+1==c)
        per[name]=dict(class_id=c-1,ap=average(precision[:,:,k,0,-1]),ap50=average(precision[0,:,k,0,-1]),recall=average(recall[:,k,0,-1]))
    return dict(map50=float(engine.stats[1]) if engine.stats[1]>=0 else None,
                map50_95=float(engine.stats[0]) if engine.stats[0]>=0 else None,per_class=per,
                engine='pycocotools.COCOeval',max_dets=100,area='all',iou_thresholds=PROTOCOL['detection_iou_thresholds'])


def calibrate_detection(gt,predictions,class_names,*,data_kind):
    records,_,_=prepare(gt,predictions,'validation',class_names)
    selected=None
    if any(len(r[1]) for r in records):
        candidates=np.linspace(0,1,101)
        values=[counts(records,t,class_names.values())[0]['f1'] for t in candidates]
        selected=float(candidates[np.flatnonzero(np.isclose(values,max(values),rtol=0,atol=1e-12))[-1]])
    pairs=aligned_records(gt,predictions,'validation')
    return ThresholdPolicy(detection=selected,validation_product_hashes=tuple(sorted({digest(g['product_id']) for g,p in pairs})),validation_ids_sha256=digest([g['image_id'] for g,p in pairs]),
                           protocol_sha256=digest(PROTOCOL),data_kind=data_kind)


def evaluate_detection(gt,predictions,class_names,policy,*,split,data_kind):
    if split not in ('validation','test'):raise ValueError('Invalid evaluation split')
    policy.validate(data_kind)
    policy.validate_cohort(aligned_records(gt,predictions,split),split)
    records,excluded,total=prepare(gt,predictions,split,class_names)
    result=dict(task='detection',split=split,data_kind=data_kind,protocol_sha256=digest(PROTOCOL),
                threshold_policy=policy.to_dict(),evaluation_ids_sha256=digest([g['image_id'] for g,p in aligned_records(gt,predictions,split)]),images=total,evaluated_images=len(records),exclusions=excluded,
                evaluation_coverage_sha256=digest([r[0]['image_id'] for r in records]),evaluated_image_ids=[r[0]['image_id'] for r in records],**coco_metrics(records,class_names))
    if policy.detection is None:
        result.update(precision=None,recall=None,f1=None,tp=None,fp=None,fn=None,threshold_reason='NO_VALIDATION_THRESHOLD',confusion=None,per_image=[],by_category={},by_view={})
    else:
        totals,per,details=counts(records,policy.detection,class_names.values());result.update(totals,counts_by_class=per,per_image=details,confusion=confusion(records,policy.detection,class_names))
        for key in ('category','view'):
            result['by_'+key]={}
            for value in sorted({r[0].get(key,'UNKNOWN') for r in records}):
                group=[r for r in records if r[0].get(key,'UNKNOWN')==value]
                result['by_'+key][value]=dict(counts(group,policy.detection,class_names.values())[0],n=len(group))
    return result
