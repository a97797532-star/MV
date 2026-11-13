# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('gate_review',Path('scripts/review_crop_gate_bboxes.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
P={'case_id':'test','image_path':'not-an-actual-image'}
# test_pending_rejected_do_not_create_gt: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_pending_rejected_do_not_create_gt():
 for state in ['PENDING','REJECTED']:
  r=m.review_event(P,dict(review_state=state,reviewer='test',notes='Needs manual review'))
  assert r['status']==state and not r['human_ack'] and 'bbox' not in r

# test_approval_requires_human_ack_and_valid_coordinates: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_approval_requires_human_ack_and_valid_coordinates():
 with pytest.raises(ValueError):m.review_event(P,dict(review_state='VERIFIED_GT',reviewer='test',bbox=[0,0,1024,1024]))
 with pytest.raises(ValueError):m.review_event(P,dict(review_state='REJECTED',reviewer='test',notes=''))
