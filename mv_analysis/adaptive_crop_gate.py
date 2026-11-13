# 한글 안내: 이미지에서 추정한 위험 신호로 Crop 후보를 평가합니다. 결함 정답은 선택 입력으로 쓰지 않습니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Image-only rule gate with an explicit unvalidated-research/deployment boundary."""
import numpy as np,cv2,math
from mv_analysis.object_aware_crop import select_component,box_iou,border_distance,centered_cover
from mv_analysis.background_brightness import segment
from mv_analysis.yolo_crop_geometry import square_crop
VERSION='adaptive-gate-v1'
FORBIDDEN={'status','label','is_ng','defect_type','has_mask','mask_path','defect_mask','cohort'}
FULL=[0,0,1024,1024];CENTER=[64,64,960,960]

# contains: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: a, b, guard.
def contains(a,b,guard=0):return b is not None and a[0]+guard<=b[0] and a[1]+guard<=b[1] and a[2]-guard>=b[2] and a[3]-guard>=b[3]
# valid: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: c.
def valid(c):return c is not None and len(c)==4 and np.isfinite(c).all() and 0<=c[0]<c[2]<=1024 and 0<=c[1]<c[3]<=1024
# extract_features: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: image, cached_proposals.
def extract_features(image,cached_proposals=None):
 """Defect annotation/quality labels are absent from this API by design."""
 cv2.setNumThreads(1);small=cv2.resize(image,(256,256),interpolation=cv2.INTER_AREA);gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(float)
 fg=np.zeros((256,256),bool);error=None;change=None
 try:
  cv2.setRNGSeed(42);labels=np.zeros((256,256),np.uint8);bgm=np.zeros((1,65));fgm=np.zeros((1,65));cv2.grabCut(small,labels,(13,13,230,230),bgm,fgm,2,cv2.GC_INIT_WITH_RECT);before=np.isin(labels,[1,3]);cv2.grabCut(small,labels,None,bgm,fgm,1,cv2.GC_EVAL);fg=np.isin(labels,[1,3]);change=float(np.mean(before!=fg));gc=select_component(fg)
 except cv2.error as e:error=str(e).splitlines()[0];gc=dict(bbox=None,status='GRABCUT_ERROR',quality=False)
 if cached_proposals is not None:
  props={k:cached_proposals[k] for k in ['grabcut90','border_rgb','border_lab','contour_canny']};parity=gc['bbox']==props['grabcut90']['bbox']
 else:
  masks,q=segment(image,grabcut=False);r=select_component(cv2.resize(masks['A'].astype(np.uint8),(256,256),interpolation=cv2.INTER_NEAREST));r['quality'] &= q['segmentation_status']=='accepted_heuristic';rgb,_=border_distance(small,'RGB');edge=cv2.morphologyEx(cv2.Canny(gray,60,180),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)));props=dict(grabcut90=gc,border_rgb=select_component(rgb),border_lab=r,contour_canny=select_component(edge,True));parity=None
 box=props['grabcut90']['bbox'];crop=square_crop(box,.1) if box is not None else None
 props['adaptive_center']=dict(bbox=centered_cover(props['border_lab']['bbox'],0))
 n,cc,stats,_=cv2.connectedComponentsWithStats(fg.astype(np.uint8),8);areas=stats[1:,cv2.CC_STAT_AREA];count=int(fg.sum());largest=float(areas.max()/count) if count else 0.
 contrast=float(np.linalg.norm(np.median(lab[fg],axis=0)-np.median(lab[~fg],axis=0))) if fg.any() and (~fg).any() else None
 # outside: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: c.
 def outside(c):
  if c is None or not count:return None
  x0,y0,x1,y1=[int(round(v/4)) for v in c];return float((count-fg[y0:y1,x0:x1].sum())/count)
 boundary=None
 if crop is not None and count:
  x0,y0,x1,y1=[int(round(v/4)) for v in crop];inside=fg[y0:y1,x0:x1];ring=np.ones_like(inside);ring[2:-2,2:-2]=False;boundary=float(np.count_nonzero(inside&ring)/count)
 pairs=[]
 for name,r in props.items():
  if name=='grabcut90' or box is None or r.get('bbox') is None:continue
  q=r['bbox'];area=lambda a:(a[2]-a[0])*(a[3]-a[1]);pairs.append(dict(method=name,iou=box_iou(box,q),center_distance=float(np.linalg.norm((np.array(box[:2])+box[2:]-np.array(q[:2])-q[2:])/2/1024)),area_ratio=min(area(box),area(q))/max(area(box),area(q))))
 f=dict(proposed_crop=crop,proposal_bbox=box,grabcut_error=error,grabcut_change=change,fg_fraction=count/65536,component_count=len(areas),largest_component_fraction=largest,foreground_contrast=contrast,
  boundary_touch_fraction=boundary,fg_outside_crop=outside(crop),fg_outside_center=outside(CENTER),
  frame_margin=min(box[0],box[1],1024-box[2],1024-box[3])/1024 if box else None,
  crop_side=crop[2]-crop[0] if crop else None,box_aspect=(box[2]-box[0])/(box[3]-box[1]) if box else None,
  center_x=(box[0]+box[2])/2048 if box else None,center_y=(box[1]+box[3])/2048 if box else None,
  crop_center_offset=float(np.linalg.norm((np.array(box[:2])+box[2:]-np.array(crop[:2])-crop[2:])/2/1024)) if box and crop else None,
  valid_other_methods=len(pairs),median_method_iou=float(np.median([p['iou'] for p in pairs])) if pairs else None,
  max_method_center_distance=max([p['center_distance'] for p in pairs],default=None),min_method_area_ratio=min([p['area_ratio'] for p in pairs],default=None),
  center_contains_all_proposals=all(contains(CENTER,r.get('bbox'),8) for r in props.values()),pairs=pairs,cached_bbox_parity=parity,
  other_boxes={k:r['bbox'] for k,r in props.items() if k!='grabcut90'})
 return f

# decide: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: features, thresholds, category, view, variant, approved_scopes.
def decide(features,thresholds,category,view,variant='review_center',approved_scopes=None):
 if set(features)&FORBIDDEN:raise ValueError('Label/annotation metadata is forbidden in gate input')
 f=features;codes=[];fatal=False;crop=f['proposed_crop'];t=thresholds['global']
 # high: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: name.
 def high(name):return f.get(name) is not None and f[name]>t[name]['high']
 # low: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: name.
 def low(name):return f.get(name) is not None and f[name]<t[name]['low']
 if f['proposal_bbox'] is None or f['grabcut_error']:codes.append('NO_FOREGROUND');fatal=True
 if crop is not None and not valid(crop):codes.append('INVALID_GEOMETRY');fatal=True
 if high('grabcut_change'):codes.append('UNSTABLE_GRABCUT');fatal=True
 if high('boundary_touch_fraction') or high('fg_outside_crop') or (f.get('frame_margin') is not None and f['frame_margin']<=4/1024):codes.append('BOUNDARY_TOUCH')
 if f['valid_other_methods']<3 or low('median_method_iou') or high('max_method_center_distance') or low('min_method_area_ratio'):codes.append('METHOD_DISAGREEMENT')
 if low('crop_side'):codes.append('SMALL_CROP')
 if high('crop_center_offset') or low('center_x') or high('center_x') or low('center_y') or high('center_y'):codes.append('OFF_CENTER')
 if low('foreground_contrast'):codes.append('LOW_FOREGROUND_CONTRAST')
 ref=thresholds.get('category_view',{}).get(category+'/'+view);prior_scope='category_view' if ref and ref['n']>=thresholds['minimum_category_view_n'] else 'global'
 outlier=low('fg_fraction') or high('fg_fraction') or low('box_aspect') or high('box_aspect') or high('component_count') or low('largest_component_fraction')
 if outlier:codes.append('CATEGORY_VIEW_OUTLIER')
 image_status='FAIL' if fatal else 'REVIEW' if codes else 'PASS'
 center_safe=(f.get('fg_outside_center')==0 and f['center_contains_all_proposals'] and not fatal and not low('foreground_contrast'))
 if image_status=='PASS':proposal='A';proposed=crop
 elif variant=='review_center' and image_status=='REVIEW' and center_safe:proposal='B';proposed=CENTER
 else:proposal='C';proposed=FULL
 # No automatic promotion from image consensus to product-preservation assurance.
 scope=(approved_scopes or {}).get(category+'/'+view,{})
 approved=scope.get('status')=='APPROVED_BY_TEAM' and scope.get('verified_gt_count',0)>0 and bool(scope.get('reviewer')) and scope.get('team_product_loss_tolerance') is not None and scope.get('team_false_pass_tolerance') is not None and bool(scope.get('evidence_sha256'))
 if variant=='validated_scope' and proposal!='C' and not approved:proposal='C';proposed=FULL
 selected=proposal if approved else 'C';selected_crop=proposed if approved else FULL
 return dict(image_quality_status=image_status,image_risk_codes=list(dict.fromkeys(codes)),risk_codes=list(dict.fromkeys(codes+([] if approved else ['PRODUCT_CONTAINMENT_UNVERIFIED']))),
  research_selected_policy=proposal,research_selected_crop=proposed,selected_policy=selected,selected_crop=selected_crop,center896_image_check=center_safe,prior_scope=prior_scope,
  category_view_reference_n=ref['n'] if ref else 0,deployment_eligible=bool(approved),fallback_reason='PRODUCT_CONTAINMENT_UNVERIFIED' if not approved else ('IMAGE_RULE_FALLBACK' if selected=='C' else ''),policy_version=VERSION)
