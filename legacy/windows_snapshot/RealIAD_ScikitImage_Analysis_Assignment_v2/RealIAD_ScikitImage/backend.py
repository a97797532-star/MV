"""scikit-image + SciPy: OpenCV와 동일한 8이웃·4이웃 Laplacian."""
import numpy as np
from skimage import measure
from scipy import ndimage
NAME='skimage'


def laplacian(g):
    return ndimage.laplace(g.astype(np.float64),mode='mirror')


def components(mask):
    labels=measure.label(mask,background=0,connectivity=2)
    props=measure.regionprops_table(labels,properties=('label','area','bbox','centroid'))
    regions=[]
    for i,cid in enumerate(props['label']):
        regions.append((int(cid),dict(area=int(props['area'][i]),
            x0=int(props['bbox-1'][i]),y0=int(props['bbox-0'][i]),
            x1=int(props['bbox-3'][i]),y1=int(props['bbox-2'][i]),
            cx=float(props['centroid-1'][i]),cy=float(props['centroid-0'][i]))))
    return labels,regions
