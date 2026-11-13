# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import numpy as np
from mv_analysis.yolo_crop_geometry import select_box,square_crop,transform_boxes
from mv_analysis.yolo_center_hybrid import anchor_union_square

# test_selection_policies_use_different_image_only_evidence: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_selection_policies_use_different_image_only_evidence():
    ds=[dict(xyxy=[0,0,100,100],confidence=.9),dict(xyxy=[400,400,600,600],confidence=.3),dict(xyxy=[200,200,800,800],confidence=.2)]
    assert select_box(ds,'confidence')[0]==[0,0,100,100]
    assert select_box(ds,'largest_central')[0]==[200,200,800,800]
    assert select_box(ds,'union')[0]==[0,0,800,800]
    assert select_box([], 'confidence')==(None,'NO_DETECTION')
    assert select_box(ds[:1],'largest_central')==(None,'NO_CENTRAL_BOX')

# test_margin_boundary_shift_keeps_box_and_is_monotonic: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_margin_boundary_shift_keeps_box_and_is_monotonic():
    b=[950.5,800.2,1023.1,1015.7];prior=0
    for m in [0,.1,.2,.3]:
        c=square_crop(b,m);x0,y0,x1,y1=c
        assert 0<=x0<=b[0]<b[2]<=x1<=1024
        assert 0<=y0<=b[1]<b[3]<=y1<=1024
        assert x1-x0==y1-y0 and x1-x0>=prior
        prior=x1-x0
    assert square_crop([0,0,1024,1024],.3)==[0,0,1024,1024]

# test_xyxy_clip_resize_and_removed_objects: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_xyxy_clip_resize_and_removed_objects():
    raw=np.array([[0,0,20,20],[400,400,600,600],[900,900,1000,1000]])
    out,keep=transform_boxes(raw,[128,128,896,896],256)
    assert keep.tolist()==[False,True,False]
    assert np.allclose(out[1],[272/3,272/3,472/3,472/3])
    assert out.min()>=0 and out.max()<=256
    assert np.array_equal(raw[0],[0,0,20,20])

# test_hybrid_guarantees_anchor_and_candidate_containment: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_hybrid_guarantees_anchor_and_candidate_containment():
    anchor=[64,64,960,960]
    for candidate in [None,[0,200,400,600],[100,100,400,400],[980,980,1024,1024]]:
        crop=anchor_union_square(anchor,candidate)
        assert 0<=crop[0]<crop[2]<=1024 and 0<=crop[1]<crop[3]<=1024
        for other in [anchor]+([candidate] if candidate else []):
            assert crop[0]<=other[0] and crop[1]<=other[1] and crop[2]>=other[2] and crop[3]>=other[3]
