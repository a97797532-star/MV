"""OpenCV: 가이드의 Laplacian 및 8이웃 연결 성분 계약."""
import cv2
import numpy as np
cv2.setNumThreads(1)
NAME='opencv'


def laplacian(g):
    return cv2.Laplacian(g.astype(np.float64),cv2.CV_64F,ksize=1,borderType=cv2.BORDER_REFLECT_101)


def components(mask):
    n, labels, stats, centers=cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8)
    regions=[]
    for cid in range(1,n):
        x,y,w,h,area=map(int,stats[cid]);cx,cy=map(float,centers[cid])
        regions.append((cid,dict(area=area,x0=x,y0=y,x1=x+w,y1=y+h,cx=cx,cy=cy)))
    return labels,regions
