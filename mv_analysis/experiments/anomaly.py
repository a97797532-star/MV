"""영상/픽셀 정답을 분리하는 이상탐지 평가. Validation 고정 Threshold만 Test에 적용한다."""
import cv2
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
from .contracts import PROTOCOL, ThresholdPolicy, aligned_records, digest
from .pixels import PixelAccumulator
from pathlib import Path
from .contracts import file_sha256


def binary_counts(labels, scores, threshold):
    y = np.asarray(labels, bool)
    pred = np.asarray(scores) >= threshold
    tp, fp, fn, tn = (int(np.sum(a)) for a in (pred & y, pred & ~y, ~pred & y, ~pred & ~y))
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=tp/(tp+fp) if tp+fp else 0.,
                recall=tp/(tp+fn) if tp+fn else 0., f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)


def binary_metrics(labels, scores, threshold=None):
    y, s = np.asarray(labels, dtype=int), np.asarray(scores, dtype=float)
    if len(y) != len(s) or not np.isfinite(s).all() or not np.isin(y, [0, 1]).all():
        raise ValueError('Invalid binary labels/scores')
    result = dict(n=len(y), positives=int(y.sum()), auroc=None, ap=None, f1=None,
                  precision=None, recall=None, roc=None, pr=None, score_distribution=None)
    if not len(y):
        result['reason'] = 'NO_VALID_GROUND_TRUTH'
        return result
    result['score_distribution'] = {str(k): np.quantile(s[y == k], [0, .05, .5, .95, 1]).tolist()
                                    for k in (0, 1) if np.any(y == k)}
    if len(np.unique(y)) == 2:
        result['auroc'] = float(roc_auc_score(y, s))
        fpr, tpr, _ = roc_curve(y, s)
        result['roc'] = {'fpr': fpr.tolist(), 'tpr': tpr.tolist()}
    else:
        result['auroc_reason'] = 'SINGLE_GT_CLASS'
    if y.sum():
        result['ap'] = float(average_precision_score(y, s))
        precision, recall, _ = precision_recall_curve(y, s)
        result['pr'] = {'recall': recall.tolist(), 'precision': precision.tolist()}
    else:
        result['ap_reason'] = 'NO_POSITIVE_GT'
    if threshold is not None:
        result.update(binary_counts(y, s, threshold), threshold=float(threshold))
    else:
        result['threshold_reason'] = 'NO_VALIDATION_THRESHOLD'
    return result


def best_f1_threshold(labels, scores):
    """같은 F1이면 높은 Threshold를 선택한다. Test 평가에서는 이 함수를 호출하지 않는다."""
    y, s = np.asarray(labels, int), np.asarray(scores, float)
    if not len(y) or len(np.unique(y)) < 2:
        return None
    if not np.isfinite(s).all():
        raise ValueError('Nonfinite validation scores')
    precision, recall, thresholds = precision_recall_curve(y, s)
    f1 = 2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1], 1e-30)
    return float(thresholds[np.flatnonzero(np.isclose(f1, f1.max(), rtol=0, atol=1e-12))[-1]])


def pixel_inputs(g, p):
    """미주석/빈 NG는 제외한다. OK만 정당한 전영역 음성 GT를 가질 수 있다."""
    hw = tuple(g['original_hw'])
    if g['status'] == 'NG' and g['mask_status'] != 'PRESENT_POSITIVE':
        return None, 'NG_'+g['mask_status']
    if g['mask_status'] == 'INVALID':
        return None, 'INVALID_MASK'
    raw=g.get('mask')
    if isinstance(raw,dict) and 'original_mask_path' in raw:
        path=Path(raw['original_mask_path']);stat=path.stat()
        if raw['source_fingerprint']!=f'{stat.st_size}:{stat.st_mtime_ns}':raise ValueError('Original GT mask fingerprint changed')
        decoded=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
        if decoded is None:raise ValueError('Cannot decode original GT mask')
        raw=decoded>0
    mask = np.zeros(hw, bool) if g['status'] == 'OK' and raw is None else np.asarray(raw)
    if mask.shape != hw or not np.isin(mask, [False, True, 0, 1]).all():
        raise ValueError('GT mask must be binary on the original grid')
    mask = mask.astype(bool)
    if (g['status'] == 'OK' and mask.any()) or (g['status'] == 'NG' and not mask.any()):
        raise ValueError('Contradictory mask/image GT')
    score = p.get('score_map')
    if score is None:
        return None, 'NO_SCORE_MAP'
    if isinstance(score,dict) and 'array_path' in score:
        root=Path(p['_array_root']).resolve();path=(root/score['array_path']).resolve()
        if not path.is_relative_to(root) or file_sha256(path)!=score['sha256']:raise ValueError('Score sidecar mismatch')
        score=np.load(path,allow_pickle=False,mmap_mode='r')
    score = np.asarray(score, float)
    scope=g.get('evaluation_mask')
    if isinstance(scope,dict) and 'crop_xyxy' in scope:
        x0,y0,x1,y1=scope['crop_xyxy']
        if any(int(v)!=v for v in (x0,y0,x1,y1)) or not 0<=x0<x1<=hw[1] or not 0<=y0<y1<=hw[0]:raise ValueError('Invalid fixed GT scope')
        scope=np.zeros(hw,bool);scope[y0:y1,x0:x1]=True
    else:scope=np.ones(hw,bool) if scope is None else np.asarray(scope,bool)
    if score.shape != hw or scope.shape != hw or not scope.any():
        raise ValueError('Original score grid/evaluation scope mismatch')
    if not np.isfinite(score[scope]).all():
        return None, 'UNOBSERVED_OR_NONFINITE_IN_GT_SCOPE'
    return (mask, score, scope), None


def aupro(inputs, *, fpr_limit=.3, thresholds=256):
    """8연결 결함 영역별 동일 가중 PRO. 명시한 GT 평가 영역에서 FPR 0~0.3을 선형 적분·정규화한다."""
    regions, normals, values = [], [], []
    for mask, score, scope in inputs:
        binary = (mask & scope).astype(np.uint8)
        n, ids = cv2.connectedComponents(binary, connectivity=8)
        regions.extend(score[(ids == k) & scope] for k in range(1, n))
        normals.append(score[scope & ~mask])
        values.append(score[scope])
    negative = np.concatenate(normals) if normals else np.array([])
    if not regions or not len(negative):
        return dict(value=None, reason='NO_REGIONS_OR_NO_NEGATIVE_PIXELS', region_count=len(regions), curve=None)
    if not 0 < fpr_limit <= 1 or thresholds < 2:
        raise ValueError('Invalid AUPRO protocol')
    low = min(float(v.min()) for v in values)
    high = max(float(v.max()) for v in values)
    levels = np.r_[np.inf, np.linspace(high, low, thresholds)]
    curve = []
    for threshold in levels:
        curve.append((float(np.mean(negative >= threshold)),
                      float(np.mean([np.mean(region >= threshold) for region in regions]))))
    # 같은 FPR의 수직 구간도 순서대로 유지한다. 최대값으로 합치면 수평 구간 면적이 과대평가된다.
    x=np.asarray([v[0] for v in curve]);y=np.asarray([v[1] for v in curve])
    xx=np.r_[x[x<fpr_limit],fpr_limit]
    yy=np.r_[y[x<fpr_limit],np.interp(fpr_limit,x,y)]
    return dict(value=float(np.trapezoid(yy, xx)/fpr_limit), region_count=len(regions),
                negative_pixels=len(negative), thresholds=thresholds, fpr_limit=fpr_limit,
                curve={'fpr': xx.tolist(), 'pro': yy.tolist()})


def calibrate_anomaly(gt, predictions, *, data_kind):
    pairs = aligned_records(gt, predictions, 'validation')
    y, score = [], []
    low, high = np.inf, -np.inf
    for g, p in pairs:
        if g['status'] not in ('OK', 'NG') or not np.isfinite(p['score']):
            raise ValueError('Invalid image score/GT')
        y.append(int(g['status']=='NG')); score.append(float(p['score']))
        item, _ = pixel_inputs(g,p)
        if item is not None:
            mask, values, scope = item
            low=min(low,float(values[scope].min())); high=max(high,float(values[scope].max()))
    score_range=None; threshold=None
    if np.isfinite([low,high]).all():
        if high==low: low,high=low-.5,high+.5
        score_range=(low,high); accumulator=PixelAccumulator(score_range)
        for g,p in pairs:
            item,_=pixel_inputs(g,p)
            if item is not None:accumulator.update(*item)
        threshold=accumulator.best_threshold()
    return ThresholdPolicy(image=best_f1_threshold(y,score),pixel=threshold,pixel_score_range=score_range,
        validation_ids_sha256=digest([g['image_id'] for g,p in pairs]),validation_product_hashes=tuple(sorted({digest(g['product_id']) for g,p in pairs})),protocol_sha256=digest(PROTOCOL),data_kind=data_kind)


def evaluate_anomaly(gt, predictions, policy, *, split, data_kind):
    if split not in ('validation','test'):raise ValueError('Only validation/test evaluation is allowed')
    policy.validate(data_kind);pairs=aligned_records(gt,predictions,split);policy.validate_cohort(pairs,split)
    y,scores,excluded=[],[],[];outside=0;valid_images=0;pixel_ids=[]
    accumulator=PixelAccumulator(policy.pixel_score_range,policy.pixel) if policy.pixel_score_range else None
    for g,p in pairs:
        if g['status'] not in ('OK','NG') or not np.isfinite(p['score']):raise ValueError('Invalid image status/score')
        y.append(int(g['status']=='NG'));scores.append(float(p['score']))
        item,reason=pixel_inputs(g,p)
        if item is None or accumulator is None:
            excluded.append(dict(image_id=g['image_id'],reason=reason or 'NO_VALIDATION_PIXEL_RANGE'))
        else:
            accumulator.update(*item);valid_images+=1;pixel_ids.append(g['image_id']);outside+=int((item[0]&~item[2]).sum())
    if accumulator is not None:pixel,pro=accumulator.result(PROTOCOL['aupro_fpr_limit'],PROTOCOL['aupro_thresholds'])
    else:pixel=binary_metrics([],[]);pro=dict(value=None,reason='NO_VALIDATION_PIXEL_RANGE',region_count=0,curve=None)
    result=dict(task='anomaly',split=split,data_kind=data_kind,protocol_sha256=digest(PROTOCOL),
        threshold_policy=policy.to_dict(),evaluated_image_ids=[g['image_id'] for g,p in pairs],
        evaluation_ids_sha256=digest([g['image_id'] for g,p in pairs]),image=binary_metrics(y,scores,policy.image),pixel=pixel,aupro=pro,pixel_images=valid_images,
        pixel_exclusions=excluded,positive_pixels_outside_fixed_scope=outside,
        evaluation_coverage_sha256=digest({'image':[g['image_id'] for g,p in pairs],'pixel':pixel_ids}),pixel_evaluated_image_ids=pixel_ids)
    for key in ('category','view'):
        groups=sorted({g.get(key,'UNKNOWN') for g,p in pairs})
        result['by_'+key]={v:binary_metrics([int(g['status']=='NG') for g,p in pairs if g.get(key,'UNKNOWN')==v],
            [p['score'] for g,p in pairs if g.get(key,'UNKNOWN')==v],policy.image) for v in groups}
    return result
