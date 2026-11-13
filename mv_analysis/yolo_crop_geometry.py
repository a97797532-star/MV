# 한글 안내: 저장된 검출 BBox와 Crop·Resize 좌표의 기하 관계 및 결함 보존 지표를 계산합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Image-only YOLO candidate selection and immutable native-coordinate Crop geometry."""
import math
import numpy as np

POLICIES=('confidence','nearest_center','largest_central','union')

# select_box: 정해진 조건으로 후보를 선택합니다.
# 입력 인수: detections, policy, width, height.
def select_box(detections,policy,width=1024,height=1024):
    """No defect masks, product labels, GT boxes or category thresholds are inputs."""
    valid=[d for d in detections if len(d['xyxy'])==4 and np.isfinite(d['xyxy']).all()
           and d['xyxy'][2]>d['xyxy'][0] and d['xyxy'][3]>d['xyxy'][1]]
    if not valid:return None,'NO_DETECTION'
    cx,cy=width/2,height/2
    if policy=='confidence':d=max(valid,key=lambda x:x['confidence'])
    elif policy=='nearest_center':d=min(valid,key=lambda x:((x['xyxy'][0]+x['xyxy'][2])/2-cx)**2+((x['xyxy'][1]+x['xyxy'][3])/2-cy)**2)
    elif policy=='largest_central':
        central=[d for d in valid if d['xyxy'][0]<=cx<=d['xyxy'][2] and d['xyxy'][1]<=cy<=d['xyxy'][3]]
        if not central:return None,'NO_CENTRAL_BOX'
        d=max(central,key=lambda x:(x['xyxy'][2]-x['xyxy'][0])*(x['xyxy'][3]-x['xyxy'][1]))
    elif policy=='union':
        a=np.array([d['xyxy'] for d in valid]);return [float(a[:,0].min()),float(a[:,1].min()),float(a[:,2].max()),float(a[:,3].max())],'CANDIDATE_UNVERIFIED'
    else:raise ValueError(policy)
    return list(map(float,d['xyxy'])),'CANDIDATE_UNVERIFIED'

# square_crop: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: box, margin, width, height.
def square_crop(box,margin,width=1024,height=1024):
    """Margin=m on EACH side relative to original box width/height, then square.

    Shift the square inside the frame instead of independently clipping edges.
    A square larger than the shorter frame side is capped at that side.
    Integer exclusive XYXY; floor/ceil preserve detector box coverage on square images.
    """
    if box is None:return None
    if margin<0:raise ValueError('Negative margin')
    x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2
    if x1<=x0 or y1<=y0:raise ValueError('Degenerate box')
    side=min(min(width,height),math.ceil(max(x1-x0,y1-y0)*(1+2*margin))+2)
    # Two extra integer pixels protect against sub-pixel rounding of both edges.
    left=max(0,min(width-side,math.floor(cx-side/2)))
    top=max(0,min(height-side,math.floor(cy-side/2)))
    return [left,top,left+side,top+side]

# transform_boxes: 좌표나 배열을 지정한 출력 형식으로 변환합니다.
# 입력 인수: boxes, crop, target.
def transform_boxes(boxes,crop,target=None):
    """Absolute original XYXY -> clipped crop XYXY -> optional float target XYXY."""
    a=np.asarray(boxes,dtype=float).reshape(-1,4).copy();x0,y0,x1,y1=crop;w=x1-x0;h=y1-y0
    a[:,[0,2]]=np.clip(a[:,[0,2]]-x0,0,w);a[:,[1,3]]=np.clip(a[:,[1,3]]-y0,0,h)
    keep=(a[:,2]>a[:,0])&(a[:,3]>a[:,1])
    if target is not None:a*=np.array([target/w,target/h,target/w,target/h])
    return a,keep
