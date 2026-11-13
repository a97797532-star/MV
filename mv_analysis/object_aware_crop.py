# 한글 안내: OpenCV로 제품 전경 후보를 추정합니다. 자동 후보를 사람이 검수한 제품 정답으로 간주하지 않습니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Image-only nonlearned foreground proposals. No defect-mask or class inputs."""
import time,math
import cv2,numpy as np
from mv_analysis.background_brightness import segment
from mv_analysis.yolo_crop_geometry import square_crop
VERSION='opencv-object-v1'

# box_iou: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: a, b.
def box_iou(a,b):
 if a is None or b is None:return 0.
 w=max(0,min(a[2],b[2])-max(a[0],b[0]));h=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=w*h
 return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter) if inter else 0.

# select_component: 정해진 조건으로 후보를 선택합니다.
# 입력 인수: mask, fill_contours.
def select_component(mask,fill_contours=False):
 mask=mask.astype(np.uint8)
 if fill_contours:
  contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);filled=np.zeros_like(mask);cv2.drawContours(filled,contours,-1,1,cv2.FILLED);mask=filled
 mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
 n,labels,stats,centroids=cv2.connectedComponentsWithStats(mask,8);h,w=mask.shape;options=[]
 for k in range(1,n):
  x,y,bw,bh,area=map(int,stats[k]);frac=area/(w*h)
  if frac<.003:continue
  distance=float(np.linalg.norm((centroids[k]-[w/2,h/2])/[w,h]));touch=int(x<=1)+int(y<=1)+int(x+bw>=w-1)+int(y+bh>=h-1);aspect=bw/max(bh,1)
  score=math.sqrt(frac)*math.exp(-5*distance**2)*(.75**touch)*min(1,aspect/.12,12/max(aspect,.001))
  options.append((score,k,dict(bbox=[x*4,y*4,(x+bw)*4,(y+bh)*4],area_fraction=frac,center_distance=distance,border_edges=touch,component_count=n-1,selected_fraction=area/max(1,int(mask.sum())),aspect=aspect)))
 if not options:return dict(bbox=None,status='NO_FOREGROUND',quality=False,reason='no_component_above_0.003')
 score,k,r=max(options,key=lambda v:v[0]);quality=.015<=r['area_fraction']<=.85 and r['center_distance']<.25 and r['border_edges']==0 and r['selected_fraction']>=.65
 r.update(score=score,quality=quality,status='PROPOSAL' if quality else 'UNCERTAIN_PROPOSAL',reason='' if quality else 'area_position_border_or_fragmentation')
 return r

# border_distance: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: image, space.
def border_distance(image,space):
 im=image.astype(np.float32);h,w=im.shape[:2];border=np.zeros((h,w),bool);border[:10]=1;border[-10:]=1;border[:,:10]=1;border[:,-10:]=1
 if space=='RGB':arr=cv2.cvtColor(image,cv2.COLOR_BGR2RGB).astype(np.float32)
 elif space=='HSV':arr=cv2.cvtColor(image,cv2.COLOR_BGR2HSV).astype(np.float32)
 else:arr=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY).astype(np.float32)[:,:,None]
 center=np.median(arr[border],axis=0);delta=np.abs(arr-center)
 if space=='HSV':
  delta[:,:,0]=np.minimum(delta[:,:,0],180-delta[:,:,0])*(np.minimum(arr[:,:,1],center[1])/255)
 distance=np.linalg.norm(delta,axis=2);b=distance[border];med=float(np.median(b));mad=float(np.median(np.abs(b-med)));threshold=float(np.clip(med+4*1.4826*mad+8,10,70))
 candidate=(distance>threshold).astype(np.uint8);return candidate,dict(border_median=center.tolist(),adaptive_threshold=threshold)

# analyze_proposals: 입력 자료의 특성을 계산하고 분석합니다.
# 입력 인수: image.
def analyze_proposals(image):
 """Returns boxes only; masks used internally are image-derived and not product GT."""
 start=time.perf_counter();small=cv2.resize(image,(256,256),interpolation=cv2.INTER_AREA);gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);result={}
 t=time.perf_counter();masks,quality=segment(image,grabcut=False);a=cv2.resize(masks['A'].astype(np.uint8),(256,256),interpolation=cv2.INTER_NEAREST);r=select_component(a)
 r.update(legacy_segmentation_status=quality['segmentation_status'],legacy_reason=quality['segmentation_reason'],background_type=quality['background_type']);r['quality'] &= quality['segmentation_status']=='accepted_heuristic';r['elapsed_ms']=(time.perf_counter()-t)*1000;result['border_lab']=r
 for name,space in [('border_rgb','RGB'),('border_hsv','HSV'),('background_difference','GRAY')]:
  t=time.perf_counter();mask,extra=border_distance(small,space);r=select_component(mask);r.update(extra);r['elapsed_ms']=(time.perf_counter()-t)*1000;result[name]=r
 _,otsu=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
 border=np.zeros((256,256),bool);border[:10]=1;border[-10:]=1;border[:,:10]=1;border[:,-10:]=1
 if np.mean(otsu[border]>0)>.5:otsu=255-otsu
 adaptive=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,7)
 if np.mean(adaptive[border]>0)>.5:adaptive=255-adaptive
 canny=cv2.Canny(gray,60,180);kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7));canny=cv2.morphologyEx(canny,cv2.MORPH_CLOSE,kernel)
 for name,mask,fill in [('contour_otsu',otsu,False),('contour_adaptive',adaptive,False),('contour_canny',canny,True),('contour_closing',cv2.morphologyEx(otsu,cv2.MORPH_CLOSE,kernel),True)]:
  t=time.perf_counter();r=select_component(mask,fill);r['elapsed_ms']=(time.perf_counter()-t)*1000;result[name]=r
 for name,rect in [('grabcut90',(13,13,230,230)),('grabcut80',(26,26,204,204)),('grabcut_bbox',None)]:
  t=time.perf_counter()
  if rect is None:
   box=result['border_lab']['bbox']
   if box is None:result[name]=dict(bbox=None,status='NO_INITIAL_BOX',quality=False,reason='lab_proposal_missing');continue
   x0,y0,x1,y1=[v/4 for v in box];pad=max(x1-x0,y1-y0)*.1;x0=max(1,int(x0-pad));y0=max(1,int(y0-pad));x1=min(255,math.ceil(x1+pad));y1=min(255,math.ceil(y1+pad));rect=(x0,y0,x1-x0,y1-y0)
  try:
   cv2.setRNGSeed(42);mask=np.zeros((256,256),np.uint8);bg=np.zeros((1,65));fg=np.zeros((1,65));cv2.grabCut(small,mask,rect,bg,fg,2,cv2.GC_INIT_WITH_RECT);before=np.isin(mask,[1,3]);cv2.grabCut(small,mask,None,bg,fg,1,cv2.GC_EVAL);after=np.isin(mask,[1,3]);change=float(np.mean(before!=after));r=select_component(after)
   r.update(last_iteration_change_fraction=change,stability='UNSTABLE_LAST_STEP' if change>.02 else 'STABLE_LAST_STEP_NOT_PROOF_OF_CONVERGENCE',initial_rect=list(rect));r['quality'] &= change<=.02
  except cv2.error as e:r=dict(bbox=None,status='GRABCUT_ERROR',quality=False,reason=str(e).splitlines()[0])
  r['elapsed_ms']=(time.perf_counter()-t)*1000;result[name]=r
 # Image-only consensus: select ONE proposal, never union every candidate.
 candidates=[(name,r) for name,r in result.items() if r.get('bbox') is not None and r.get('quality')]
 scored=[]
 for name,r in candidates:
  supporters=[other for other,q in candidates if other!=name and box_iou(r['bbox'],q['bbox'])>=.8]
  diverse=any((name.startswith('border') and not v.startswith('border')) or (not name.startswith('border') and v.startswith('border')) for v in supporters)
  if len(supporters)>=2 and diverse:scored.append((len(supporters),r.get('score',0),name,r))
 if scored:
  _,_,name,r=max(scored,key=lambda v:(v[0],v[1]));result['hybrid_consensus']=dict(r,selected_method=name,quality=True,reason='>=2 IoU.8 supporters with border/nonborder diversity')
 else:result['hybrid_consensus']=dict(bbox=None,status='NO_CONSENSUS',quality=False,reason='no_cross_family_agreement')
 result['_total_ms']=(time.perf_counter()-start)*1000
 return result

# centered_cover: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: box, margin.
def centered_cover(box,margin):
 if box is None:return None
 side=min(1024,math.ceil(2*max(abs(v-512) for v in box)*(1+2*margin)))
 side=max(2,side+side%2);lo=(1024-side)//2;return [lo,lo,lo+side,lo+side]

# proposal_methods: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: proposals, priors, category, view.
def proposal_methods(proposals,priors,category,view):
 methods=[]
 for size in [1024,896,768,640]:
  lo=(1024-size)//2;methods.append(dict(method='full' if size==1024 else f'center{size}',crop=[lo,lo,lo+size,lo+size],fallback=False,status='BASELINE',quality=True))
 for name,r in proposals.items():
  if name.startswith('_') or name=='hybrid_consensus':continue
  for m in [0,.1,.2,.3]:methods.append(dict(method=f'{name}_m{int(m*100)}',crop=square_crop(r['bbox'],m),proposal_bbox=r['bbox'],fallback=False,status=r['status'],quality=r['quality']))
 box=proposals['border_lab']['bbox']
 for m in [0,.1,.2,.3]:
  methods.append(dict(method=f'adaptive_center_m{int(m*100)}',crop=centered_cover(box,m),fallback=False,status='PROPOSAL' if box else 'NO_FOREGROUND',quality=proposals['border_lab']['quality']))
  methods.append(dict(method=f'adaptive_shift_m{int(m*100)}',crop=square_crop(box,m),fallback=False,status='PROPOSAL' if box else 'NO_FOREGROUND',quality=proposals['border_lab']['quality']))
 for name,key in [('prior_category',category),('prior_category_view',category+'/'+view)]:
  size=priors.get(key,1024);lo=(1024-size)//2;methods.append(dict(method=name,crop=[lo,lo,lo+size,lo+size],fallback=False,status='TRAIN_NORMAL_PRIOR_UNVERIFIED',quality=False))
 selected=proposals['hybrid_consensus']
 for m in [0,.1,.2,.3]:
  crop=square_crop(selected['bbox'],m)
  for fallback,default in [('center896',[64,64,960,960]),('full',[0,0,1024,1024]),('trainprior',next(r['crop'] for r in methods if r['method']=='prior_category_view'))]:
   methods.append(dict(method=f'hybrid_m{int(m*100)}_{fallback}',crop=crop or default,fallback=crop is None,status=selected['status'],quality=selected['quality'],selected_method=selected.get('selected_method')))
 return methods
