"""원본 픽셀을 스트리밍 집계하는 고정 구간 히스토그램 평가. 원본 영상 전체를 쌓지 않는다."""
import cv2
import numpy as np

BINS = 2048


class PixelAccumulator:
    def __init__(self, score_range, threshold=None):
        low, high = score_range
        if not np.isfinite([low, high]).all() or high <= low:
            raise ValueError('Invalid validation-frozen pixel range')
        self.edges=np.linspace(low,high,BINS+1)
        self.positive=np.zeros(BINS,np.int64);self.negative=np.zeros(BINS,np.int64)
        self.region=np.zeros(BINS,float);self.regions=0;self.threshold=threshold
        self.tp=self.fp=self.fn=self.tn=0;self.clipped_low=self.clipped_high=0

    def update(self, mask, scores, scope):
        y=mask[scope];s=scores[scope]
        self.clipped_low+=int((s<self.edges[0]).sum());self.clipped_high+=int((s>self.edges[-1]).sum())
        ids=np.searchsorted(self.edges,s,side='right')-1;ids=np.clip(ids,0,BINS-1)
        self.positive+=np.bincount(ids[y],minlength=BINS);self.negative+=np.bincount(ids[~y],minlength=BINS)
        # 각 연결 성분은 크기와 무관하게 같은 가중치다. 평가 영역 밖 GT 손실은 호출자가 별도 기록한다.
        n,components=cv2.connectedComponents((mask & scope).astype(np.uint8),connectivity=8)
        for k in range(1,n):
            vals=scores[components==k];index=np.clip(np.searchsorted(self.edges,vals,side='right')-1,0,BINS-1)
            self.region+=np.bincount(index,minlength=BINS)/len(vals);self.regions+=1
        if self.threshold is not None:
            pred=s>=self.threshold;self.tp+=int((pred&y).sum());self.fp+=int((pred&~y).sum())
            self.fn+=int((~pred&y).sum());self.tn+=int((~pred&~y).sum())

    def best_threshold(self):
        if not self.positive.sum() or not self.negative.sum():return None
        tp=np.cumsum(self.positive[::-1]);fp=np.cumsum(self.negative[::-1]);fn=self.positive.sum()-tp
        f1=2*tp/np.maximum(2*tp+fp+fn,1)
        index=int(np.flatnonzero(np.isclose(f1,f1.max(),atol=1e-12,rtol=0))[0])
        return float(self.edges[-2-index])

    def result(self, fpr_limit=.3, pro_thresholds=256):
        pos,neg=int(self.positive.sum()),int(self.negative.sum());n=pos+neg
        result=dict(n=n,positives=pos,auroc=None,ap=None,f1=None,precision=None,recall=None,roc=None,pr=None,
                    method='HISTOGRAM_APPROX_2048_VALIDATION_FROZEN_RANGE',bins=BINS,
                    score_range=[float(self.edges[0]),float(self.edges[-1])],
                    scores_below_validation_range=self.clipped_low,scores_above_validation_range=self.clipped_high)
        if not n:return result,dict(value=None,reason='NO_VALID_PIXEL_GT',region_count=0,curve=None)
        tp=np.r_[0,np.cumsum(self.positive[::-1])];fp=np.r_[0,np.cumsum(self.negative[::-1])]
        tpr=tp/max(pos,1);fpr=fp/max(neg,1);precision=tp/np.maximum(tp+fp,1)
        if pos and neg:
            result['auroc']=float(np.trapezoid(tpr,fpr));result['roc']=dict(fpr=fpr.tolist(),tpr=tpr.tolist())
        if pos:
            result['ap']=float(np.sum(np.diff(tpr)*precision[1:]));result['pr']=dict(recall=tpr.tolist(),precision=precision.tolist())
        if self.threshold is not None:
            t,f,m=self.tp,self.fp,self.fn
            result.update(tp=t,fp=f,fn=m,tn=self.tn,precision=t/(t+f) if t+f else 0.,
                          recall=t/(t+m) if t+m else 0.,f1=2*t/(2*t+f+m) if 2*t+f+m else 0.,threshold=self.threshold)
        else:result['threshold_reason']='NO_VALIDATION_THRESHOLD'
        pro=dict(value=None,reason='NO_REGIONS_OR_NEGATIVE_PIXELS',region_count=self.regions,curve=None)
        if self.regions and neg:
            values=np.r_[0,np.cumsum(self.region[::-1])/self.regions]
            indices=np.unique(np.r_[0,np.linspace(1,BINS,pro_thresholds).round().astype(int)])
            x=fpr[indices];y=values[indices]
            xx=np.r_[x[x<fpr_limit],fpr_limit];yy=np.r_[y[x<fpr_limit],np.interp(fpr_limit,x,y)]
            pro=dict(value=float(np.trapezoid(yy,xx)/fpr_limit),region_count=self.regions,fpr_limit=fpr_limit,
                     thresholds=pro_thresholds,curve=dict(fpr=xx.tolist(),pro=yy.tolist()),method='VALIDATION_RANGE_BINNED_PRO')
        return result,pro
