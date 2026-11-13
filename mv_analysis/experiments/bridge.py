"""기존 Dataset/Adapter와 공통 평가 사이의 연결만 담당한다. Crop/라벨 정책은 재설계하지 않는다."""
from collections import Counter
import cv2
import numpy as np
from mv_analysis.data.targets import read_mask
from .geometry import restore_boxes,restore_map,validate_boxes


def ground_truth_records(index,image_ids,*,scope='canonical_crop',lazy=True):
    """원본 GT를 별도로 읽는다. Crop된 타깃을 원본 전체 GT라고 부르지 않는다."""
    if scope not in ('canonical_crop','full_original'):raise ValueError('Unknown fixed pixel evaluation scope')
    ids=set(image_ids)
    if not ids<=set(index.data.image_id):raise ValueError('Unknown ground truth IDs')
    result=[]
    for row in index.data[index.data.image_id.isin(ids)].to_dict('records'):
        hw=(int(row['original_height']),int(row['original_width']))
        path=index.source_path(row,True) if row['has_mask'] else None
        mask,state,error=read_mask(path,hw)
        boxes,labels=index.boxes.get(row['source_relative_path'],(np.empty((0,4)),np.empty(0,int)))
        match=None
        if mask is not None:
            _,_,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8)
            match=Counter((int(x),int(y),int(x+w),int(y+h)) for x,y,w,h,_ in stats[1:])==Counter(tuple(v) for v in boxes.tolist())
        if row['status']=='OK':status='OK_NEGATIVE' if not len(boxes) and (mask is None or not mask.any()) and state!='INVALID' else 'INVALID_TARGET'
        elif state=='MISSING':status='MISSING_ANNOTATION'
        elif state=='PRESENT_EMPTY':status='EMPTY_NG_REVIEW'
        elif state=='PRESENT_POSITIVE' and len(boxes) and match:status='SUPERVISED_VALID'
        else:status='INVALID_TARGET'
        coords=[int(row[k]) for k in ('crop_x0','crop_y0','crop_x1','crop_y1')]
        region={'crop_xyxy':coords} if scope=='canonical_crop' else {'crop_xyxy':[0,0,hw[1],hw[0]]}
        if lazy and path is not None and mask is not None:
            stat=path.stat();mask={'original_mask_path':str(path),'source_fingerprint':f'{stat.st_size}:{stat.st_mtime_ns}'}
        result.append(dict(image_id=row['image_id'],product_id=row['product_id'],category=row['category'],view=row['view'],
            split=row['split'],status=row['status'],mask_status=state,mask=mask,mask_error=error,original_hw=hw,
            boxes=boxes.tolist(),labels=labels.tolist(),detection_status=status,evaluation_mask=region,evaluation_scope=scope))
    return result


def restore_detection_prediction(sample,*,boxes,labels,scores,box_format,normalized,class_offset,class_ids):
    """모델 출력 형식은 담당자가 명시한다. GT Adapter 형식을 모델 출력 형식으로 추측하지 않는다."""
    meta=sample['metadata'];input_hw=sample['image'].shape[-2:]
    source=np.asarray(boxes,float).reshape(-1,4);labels=np.asarray(labels);scores=np.asarray(scores,float)
    if len(labels)!=len(source) or len(scores)!=len(source) or not np.isfinite(scores).all():raise ValueError('Invalid prediction fields')
    if not np.equal(labels,np.floor(labels)).all():raise ValueError('Noninteger source class')
    boxes,keep,audit=restore_boxes(source,original_hw=sample['original_size'],crop_xyxy=sample['crop_xyxy'],input_hw=input_hw,
        scale_xy=meta.get('resize_scale_xy',(1,1)),padding_lrtb=meta.get('padding_lrtb',(0,0,0,0)),box_format=box_format,normalized=normalized)
    canonical=labels.astype(int)[keep]-class_offset;validate_boxes(boxes,canonical,sample['original_size'],set(class_ids))
    if np.any((scores<0)|(scores>1)):raise ValueError('Confidence out of range')
    return dict(image_id=sample['image_id'],split=sample['split'],coordinate_space='original',boxes=boxes.tolist(),labels=canonical.tolist(),scores=scores[keep].tolist(),geometry_audit=audit)


def restore_anomaly_prediction(sample,*,score,score_map):
    """원본 공간으로 복원하되 Crop 밖 점수는 NaN/미관측으로 유지한다."""
    if not np.isfinite(score):raise ValueError('Invalid image anomaly score')
    values,observed=restore_map(score_map,original_hw=sample['original_size'],crop_xyxy=sample['crop_xyxy'],
        input_hw=sample['image'].shape[-2:],padding_lrtb=sample['metadata'].get('padding_lrtb',(0,0,0,0)))
    return dict(image_id=sample['image_id'],split=sample['split'],coordinate_space='original',score=float(score),score_map=values,observed=observed)
