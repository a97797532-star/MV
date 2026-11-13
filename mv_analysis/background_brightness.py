# 한글 안내: 배경·제품 후보와 결함 주변을 구분해 밝기를 계산합니다. 자동 분할은 검증된 정답이 아닙니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Unsupervised regional brightness: candidate masks, explicit uncertainty, no ground truth claims."""
from __future__ import annotations
import cv2
import numpy as np

VERSION='border-lab-v5'
SEGMENT_SIZE=256


# region_stats: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: gray, mask, prefix.
def region_stats(gray,mask,prefix):
    values=gray[mask]
    if not values.size:return {prefix+k:None for k in ['mean','median','std','variance','p05','p50','p95','contrast','shadow_ratio','highlight_ratio']}
    hist=np.bincount(values,minlength=256);cdf=np.cumsum(hist)
    # q: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: p.
    def q(p):
        position=(len(values)-1)*p;lo=int(position);hi=int(np.ceil(position))
        x=np.searchsorted(cdf,lo,side='right');y=np.searchsorted(cdf,hi,side='right')
        return float(x+(y-x)*(position-lo))
    mean=float(values.mean());std=float(values.std())
    return {prefix+'mean':mean,prefix+'median':q(.5),prefix+'std':std,prefix+'variance':std**2,prefix+'p05':q(.05),prefix+'p50':q(.5),prefix+'p95':q(.95),prefix+'contrast':q(.95)-q(.05),prefix+'shadow_ratio':float((values<=5).mean()),prefix+'highlight_ratio':float((values>=250).mean())}


# agreement: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: a, b.
def agreement(a,b):
    union=np.count_nonzero(a|b)
    return float(np.count_nonzero(a&b)/union) if union else 1.


# boundary_connected: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: candidate, border.
def boundary_connected(candidate,border):
    n,labels,stats,_=cv2.connectedComponentsWithStats(candidate.astype(np.uint8),8)
    ids=np.unique(labels[candidate&border]);ids=ids[ids>0]
    return np.isin(labels,ids)


# segment: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: image, grabcut.
def segment(image,grabcut=False):
    h,w=image.shape[:2];scale=SEGMENT_SIZE/max(h,w);small=cv2.resize(image,(max(16,round(w*scale)),max(16,round(h*scale))),interpolation=cv2.INTER_AREA)
    hh,ww=small.shape[:2];lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(np.float32);hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);band=max(2,round(min(hh,ww)*.04));border=np.zeros((hh,ww),bool);border[:band]=True;border[-band:]=True;border[:,:band]=True;border[:,-band:]=True
    pixels=lab[border];sample=pixels[::max(1,len(pixels)//3000)];quant=(sample//12).astype(int);_,indices,counts=np.unique(quant,axis=0,return_inverse=True,return_counts=True);modal=sample[indices==counts.argmax()];center=np.median(modal,axis=0)
    distance=np.linalg.norm(lab-center,axis=2);near=distance[border];support=near<24
    if support.any():center=np.median(pixels[support],axis=0);distance=np.linalg.norm(lab-center,axis=2);near=distance[border]
    # Fit smooth illumination from borders only; never initialize from NG defect masks.
    yy,xx=np.mgrid[-1:1:complex(hh),-1:1:complex(ww)];basis=np.stack([np.ones_like(xx),xx,yy,xx*xx,yy*yy,xx*yy],axis=-1)
    design=basis[border][::3];colors=pixels[::3];inliers=np.ones(len(colors),bool)
    for _ in range(3):
        coef=np.linalg.lstsq(design[inliers],colors[inliers],rcond=None)[0];residual=np.linalg.norm(colors-design@coef,axis=1);med=np.median(residual);spread0=np.median(np.abs(residual-med));new_inliers=residual<=max(8,med+3*1.4826*spread0)
        if new_inliers.sum()<max(20,len(colors)*.5):break
        inliers=new_inliers
    plane=np.clip(basis@coef,0,255).astype(np.float32);plane_distance=np.linalg.norm(lab-plane,axis=2)
    use_plane=float(np.median(plane_distance[border]))+2 < float(np.median(near))
    if use_plane:distance=plane_distance;near=distance[border]
    fit=near[near<max(24,float(np.percentile(near,70)))];median=float(np.median(fit)) if len(fit) else 24.;mad=float(np.median(np.abs(fit-median))) if len(fit) else 8.
    threshold=float(np.clip(median+4*1.4826*mad+6,8,40));candidate=distance<=threshold;connected=boundary_connected(candidate,border)
    # Strong color-matched islands are potential interior openings; kept as background, flagged below.
    hole_candidate=candidate&~connected&(distance<=threshold*.65);bg=connected|hole_candidate
    raw=(~bg).astype(np.uint8);raw=cv2.morphologyEx(raw,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));raw[hole_candidate]=0
    n,labels,stats,_=cv2.connectedComponentsWithStats(raw,8);keep=[i for i in range(1,n) if stats[i,cv2.CC_STAT_AREA]>=max(8,hh*ww*.0002)];a=np.isin(labels,keep)
    markers=np.zeros((hh,ww),np.int32);markers[connected&(distance<threshold*.75)]=1;fgseed=cv2.erode((a&(distance>threshold*1.5)).astype(np.uint8),np.ones((3,3),np.uint8))>0;markers[fgseed]=2
    if fgseed.any() and np.any(markers==1):
        watershed=cv2.watershed(small.copy(),markers.copy());c=watershed==2;c[hole_candidate]=False
    else:c=np.zeros_like(a)
    b=None;grabcut_error=''
    if grabcut:
        seed=np.full((hh,ww),cv2.GC_PR_FGD,np.uint8);seed[connected]=cv2.GC_PR_BGD;seed[connected&(distance<threshold*.65)]=cv2.GC_BGD;seed[fgseed]=cv2.GC_FGD;seed[hole_candidate]=cv2.GC_BGD
        if np.any(seed==cv2.GC_FGD) and np.any(seed==cv2.GC_BGD):
            try:
                cv2.setRNGSeed(42)
                cv2.grabCut(small,seed,None,np.zeros((1,65)),np.zeros((1,65)),2,cv2.GC_INIT_WITH_MASK);b=np.isin(seed,[cv2.GC_FGD,cv2.GC_PR_FGD])
            except cv2.error as exc:grabcut_error=str(exc).splitlines()[0]
        else:grabcut_error='insufficient foreground/background seeds'
    fraction=float(a.mean());border_support=float(candidate[border].mean());border_touch=float(a[border].mean());ac=agreement(a,c)
    border_gray=gray[border];v=hsv[:,:,2][border];l=lab[:,:,0][border];values=gray[connected] if connected.any() else border_gray
    sector=np.array([np.median(gray[:band,:ww//2]),np.median(gray[:band,ww//2:]),np.median(gray[-band:,:ww//2]),np.median(gray[-band:,ww//2:]),np.median(gray[:hh//2,:band]),np.median(gray[hh//2:,:band]),np.median(gray[:hh//2,-band:]),np.median(gray[hh//2:,-band:])])
    spread=float(np.percentile(sector,90)-np.percentile(sector,10));bright=float(np.median(values));lab_l=float(np.median(l[candidate[border]])) if candidate[border].any() else float(np.median(l));hsv_v=float(np.median(v[candidate[border]])) if candidate[border].any() else float(np.median(v))
    confidence=float(np.clip(border_support*(1-min(spread/200,.7)),0,1));mixed=spread>70 and border_support<.82
    bg_type='MIXED' if mixed else ('WHITE' if bright>=205 and lab_l>=200 and hsv_v>=205 else 'BLACK' if bright<=50 and lab_l<=65 else 'GRAY')
    if border_support<.45 or confidence<.25:bg_type='UNKNOWN'
    # Agreement alone can share the same shadow error. Flag low-color-separation foreground.
    near_background_fraction=float(np.count_nonzero(a&(distance<max(threshold*3,45)))/a.sum()) if a.any() else 1.
    edges=cv2.Canny(gray,100,200)>0;near_product=cv2.dilate(a.astype(np.uint8),np.ones((7,7),np.uint8))>0
    outside_edge_fraction=float(np.count_nonzero(edges&~near_product)/edges.sum()) if edges.any() else 0.
    reasons=[]
    if near_background_fraction>.12:reasons.append('possible_shadow_highlight_or_similar_color_product')
    if outside_edge_fraction>.35:reasons.append('substantial_edges_outside_product_candidate')
    if fraction<.005:reasons.append('foreground_too_small_or_color_indistinguishable')
    if fraction>.88:reasons.append('foreground_covers_nearly_entire_frame')
    if border_support<.65:reasons.append('weak_border_color_support')
    if border_touch>.03:reasons.append('product_touches_border_or_mixed_background')
    if ac<.95:reasons.append('color_edge_methods_disagree')
    if mixed and not use_plane:reasons.append('mixed_border_luminance')
    if not fgseed.any():reasons.append('no_strong_foreground_seed')
    ab=agreement(a,b) if b is not None else None
    if ab is not None and ab<.95:reasons.append('grabcut_disagrees')
    status='failed' if fraction<.005 or fraction>.95 or not fgseed.any() else 'uncertain' if reasons else 'accepted_heuristic'
    if status=='failed':bg_type='UNKNOWN';confidence=0.
    metrics=dict(segmentation_status=status,segmentation_reason=';'.join(reasons),segmentation_method='A adaptive border color/illumination + C edge agreement',background_color_model='quadratic_lab_border' if use_plane else 'constant_lab_border',background_type=bg_type,background_confidence=confidence,border_gray_median=float(np.median(border_gray)),border_gray_variance=float(border_gray.var()),border_hsv_v_median=hsv_v,border_lab_l_median=lab_l,border_sector_spread=spread,border_color_support=border_support,adaptive_lab_threshold=threshold,foreground_candidate_fraction=fraction,product_touches_border=border_touch>.03,foreground_border_fraction=border_touch,internal_background_candidate_fraction=float(hole_candidate.mean()),component_count=len(keep),near_background_foreground_fraction=near_background_fraction,outside_product_edge_fraction=outside_edge_fraction,method_A_C_agreement=ac,method_A_B_agreement=ab,grabcut_error=grabcut_error,segmentation_width=ww,segmentation_height=hh,edge_density=float((cv2.Canny(gray,100,200)>0).mean()))
    masks={'A':a,'C':c}
    if b is not None:masks['B']=b
    native={key:cv2.resize(value.astype(np.uint8),(w,h),interpolation=cv2.INTER_NEAREST)>0 for key,value in masks.items()}
    return native,metrics


# analyze: 입력 자료의 특성을 계산하고 분석합니다.
# 입력 인수: image, row, defect, grabcut.
def analyze(image,row,defect=None,grabcut=False):
    masks,quality=segment(image,grabcut);gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);all_mask=np.ones(gray.shape,bool);result={**row,**quality,**region_stats(gray,all_mask,'whole_')};accepted=quality['segmentation_status']=='accepted_heuristic';fg=masks['A'];bg=~fg
    result.update(region_stats(gray,fg if accepted else np.zeros_like(fg),'product_'));result.update(region_stats(gray,bg if accepted else np.zeros_like(bg),'background_'));result['product_pixel_ratio']=float(fg.mean()) if accepted else None;result['background_pixel_ratio']=float(bg.mean()) if accepted else None
    result.update(defect_status='not_provided',defect_pixels=None,defect_local_pixels=None,defect_local_difference=None,defect_product_overlap=None)
    if defect is not None:
        d=defect.astype(bool)
        if d.shape!=gray.shape:raise ValueError('defect/image dimensions differ')
        result.update(region_stats(gray,d,'defect_'));result['defect_pixels']=int(d.sum());result['defect_status']='provided_empty' if not d.any() else 'segmentation_uncertain' if not accepted else 'local_context_pending'
        result['defect_product_overlap']=float((d&fg).sum()/d.sum()) if d.any() else None
        if d.any() and accepted:
            # Radius 12 native pixels (for 1024): never sample outside the estimated product core.
            radius=max(3,round(min(gray.shape)*12/1024));dilated=cv2.dilate(d.astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1)))>0
            product_core=cv2.erode(fg.astype(np.uint8),np.ones((3,3),np.uint8))>0;local=dilated&~d&product_core;result['defect_local_pixels']=int(local.sum())
            if local.sum()>=20 and result['defect_product_overlap']>=.90:
                result.update(region_stats(gray,local,'defect_local_'));result['defect_local_difference']=float(gray[d].mean()-gray[local].mean());result['defect_status']='estimated_product_local_context'
            else:result['defect_status']='insufficient_or_uncertain_product_context'
    return result,masks
