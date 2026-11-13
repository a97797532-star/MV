# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import numpy as np
from mv_analysis.object_aware_crop import select_component,box_iou,centered_cover,analyze_proposals
# test_central_component_beats_larger_corner_noise: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_central_component_beats_larger_corner_noise():
 m=np.zeros((256,256),np.uint8);m[:90,:90]=1;m[100:156,100:156]=1
 r=select_component(m);assert r['bbox']==[400,400,624,624]
# test_iou_and_center_cover_are_geometry_only: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_iou_and_center_cover_are_geometry_only():
 assert box_iou([0,0,100,100],[50,0,150,100])==1/3
 assert box_iou(None,[0,0,1,1])==0
 for m in [0,.1,.3]:
  c=centered_cover([200,300,700,800],m);assert c[0]<=200 and c[1]<=300 and c[2]>=700 and c[3]>=800
# test_blank_image_cannot_be_declared_verified_product: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_blank_image_cannot_be_declared_verified_product():
 r=analyze_proposals(np.zeros((1024,1024,3),np.uint8));assert all(v.get('status')!='VERIFIED_GT' for k,v in r.items() if not k.startswith('_'));assert r['hybrid_consensus']['bbox'] is None
