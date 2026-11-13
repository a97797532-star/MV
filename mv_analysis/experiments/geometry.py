"""모델 출력만 원본 좌표로 복원한다. 저장 Crop이나 기존 로더 코드는 변경하지 않는다."""
import cv2
import numpy as np


def validate_boxes(boxes, labels, original_hw, class_ids):
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    labels = np.asarray(labels)
    h, w = original_hw
    if labels.shape != (len(boxes),) or not np.isfinite(boxes).all():
        raise ValueError('Invalid box/label shape or nonfinite box')
    if not all(isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_)) and int(v) in class_ids for v in labels):
        raise ValueError('Unknown/noninteger canonical class ID')
    if len(boxes) and (np.any(boxes < 0) or np.any(boxes[:, 2:] <= boxes[:, :2]) or
                      np.any(boxes[:, [0, 2]] > w) or np.any(boxes[:, [1, 3]] > h)):
        raise ValueError('Boxes must be valid exclusive XYXY original coordinates')
    return boxes, labels.astype(int)


def _geometry(original_hw, crop_xyxy, scale_xy, padding_lrtb):
    if len(original_hw)!=2 or any(isinstance(v,(bool,np.bool_)) or not np.isfinite(v) or int(v)!=v or v<=0 for v in original_hw):
        raise ValueError('Positive integer original dimensions required')
    h, w = map(int, original_hw)
    raw = np.asarray(crop_xyxy)
    if raw.shape != (4,) or not np.isfinite(raw).all() or not np.equal(raw, np.floor(raw)).all():
        raise ValueError('Integer saved crop required')
    x0, y0, x1, y1 = map(int, raw)
    if not 0 <= x0 < x1 <= w or not 0 <= y0 < y1 <= h:
        raise ValueError('Invalid saved crop')
    sx, sy = scale_xy
    if not np.isfinite([sx, sy]).all() or min(sx, sy) <= 0:
        raise ValueError('Invalid resize scale')
    if len(padding_lrtb) != 4 or any(int(v) != v or v < 0 for v in padding_lrtb):
        raise ValueError('Invalid input padding')
    return h, w, x0, y0, x1, y1


def restore_boxes(boxes, *, original_hw, crop_xyxy, input_hw, scale_xy, padding_lrtb=(0, 0, 0, 0),
                  box_format='xyxy', normalized=False):
    """역순: 정규화 해제→CXCYWH 변환→Pad 제거→Scale 역변환→Crop 원점 복원. keep으로 클래스도 선택한다."""
    h, w, x0, y0, x1, y1 = _geometry(original_hw, crop_xyxy, scale_xy, padding_lrtb)
    out = np.asarray(boxes, dtype=float).reshape(-1, 4).copy()
    if not np.isfinite(out).all():
        raise ValueError('Nonfinite prediction boxes')
    ih, iw = input_hw
    left,right,top,bottom=padding_lrtb
    if min(ih,iw)<=0 or abs((x1-x0)*scale_xy[0]+left+right-iw)>1e-4 or abs((y1-y0)*scale_xy[1]+top+bottom-ih)>1e-4:
        raise ValueError('Scale/padding does not match declared model input grid')
    if normalized:
        if np.any(out < 0) or np.any(out > 1):
            raise ValueError('Normalized boxes out of range')
        out *= [iw, ih, iw, ih]
    if box_format == 'cxcywh':
        center, size = out[:, :2].copy(), out[:, 2:].copy()
        if np.any(size < 0):
            raise ValueError('Negative predicted box size')
        out[:, :2], out[:, 2:] = center-size/2, center+size/2
    elif box_format != 'xyxy':
        raise ValueError('Unknown box format')
    if np.any(out[:, 2:] < out[:, :2]):
        raise ValueError('Inverted predicted boxes')
    left, _, top, _ = padding_lrtb
    out -= [left, top, left, top]
    out /= [*scale_xy, *scale_xy]
    before = out.copy()
    out[:, [0, 2]] = np.clip(out[:, [0, 2]], 0, x1-x0)
    out[:, [1, 3]] = np.clip(out[:, [1, 3]], 0, y1-y0)
    keep = np.all(out[:, 2:] > out[:, :2], axis=1)
    out += [x0, y0, x0, y0]
    return out[keep], keep, {'clipped': int(np.any(before != out-[x0, y0, x0, y0], axis=1).sum()),
                            'removed': int((~keep).sum())}


def restore_map(score_map, *, original_hw, crop_xyxy, input_hw, padding_lrtb=(0, 0, 0, 0), categorical=False):
    """Crop 밖은 미관측이다. 점수는NaN, 범주 마스크는False와 별도의 observed 영역으로 반환한다."""
    _geometry(original_hw, crop_xyxy, (1, 1), padding_lrtb)
    data = np.asarray(score_map)
    if data.ndim != 2 or data.shape != tuple(input_hw) or not np.isfinite(data).all():
        raise ValueError('Score map must be finite and aligned to the declared model input grid')
    left, right, top, bottom = map(int, padding_lrtb)
    data = data[top:data.shape[0]-bottom if bottom else None, left:data.shape[1]-right if right else None]
    if min(data.shape) <= 0:
        raise ValueError('Padding removed the full score map')
    x0, y0, x1, y1 = map(int, crop_xyxy)
    resized = cv2.resize(data.astype(np.float32), (x1-x0, y1-y0),
                         interpolation=cv2.INTER_NEAREST if categorical else cv2.INTER_LINEAR)
    result = np.zeros(original_hw, bool) if categorical else np.full(original_hw, np.nan, np.float32)
    observed = np.zeros(original_hw, bool)
    result[y0:y1, x0:x1] = resized > .5 if categorical else resized
    observed[y0:y1, x0:x1] = True
    return result, observed
