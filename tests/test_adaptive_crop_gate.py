# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import copy
import pytest
from mv_analysis.adaptive_crop_gate import decide,FORBIDDEN

# fixture: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def fixture():
 names=['grabcut_change','boundary_touch_fraction','fg_outside_crop','median_method_iou','max_method_center_distance','min_method_area_ratio','crop_side','crop_center_offset','center_x','center_y','foreground_contrast','fg_fraction','box_aspect','component_count','largest_component_fraction']
 t={'global':{n:{'low':0,'high':10000} for n in names},'category_view':{},'minimum_category_view_n':20}
 f=dict(proposed_crop=[200,200,800,800],proposal_bbox=[300,300,700,700],grabcut_error=None,grabcut_change=0,boundary_touch_fraction=0,fg_outside_crop=0,frame_margin=.2,valid_other_methods=4,median_method_iou=.9,max_method_center_distance=0,min_method_area_ratio=.9,crop_side=600,crop_center_offset=0,center_x=.5,center_y=.5,foreground_contrast=60,fg_fraction=.3,box_aspect=1,component_count=1,largest_component_fraction=1,fg_outside_center=0,center_contains_all_proposals=True)
 return f,t
# test_gt_missing_does_not_enable_unsafe_deployment: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_gt_missing_does_not_enable_unsafe_deployment():
 f,t=fixture();r=decide(f,t,'toy','C1');assert r['image_quality_status']=='PASS' and r['research_selected_policy']=='A';assert r['selected_policy']=='C' and 'PRODUCT_CONTAINMENT_UNVERIFIED' in r['risk_codes']
# test_all_annotation_inputs_are_rejected: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_all_annotation_inputs_are_rejected():
 f,t=fixture()
 for name in FORBIDDEN:
  leaked=copy.deepcopy(f);leaked[name]='do-not-use'
  with pytest.raises(ValueError):decide(leaked,t,'toy','C1')
# test_review_center_is_checked_not_assumed_safe: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_review_center_is_checked_not_assumed_safe():
 f,t=fixture();t['global']['foreground_contrast']['low']=70
 assert decide(f,t,'toy','C1')['research_selected_policy']=='C'
 f,t=fixture();t['global']['crop_side']['low']=700
 assert decide(f,t,'toy','C1')['research_selected_policy']=='B'
 f['fg_outside_center']=.001
 assert decide(f,t,'toy','C1')['research_selected_policy']=='C'
# test_grabcut_fatal_always_full: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_grabcut_fatal_always_full():
 f,t=fixture();f['proposal_bbox']=None;f['proposed_crop']=None;assert decide(f,t,'toy','C1')['image_quality_status']=='FAIL'
