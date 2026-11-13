# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('bbox_review',Path(__file__).parents[1]/'scripts/review_product_bboxes.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
# test_automatic_proposal_cannot_silently_be_gt: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_automatic_proposal_cannot_silently_be_gt():
 p=dict(case_id='synthetic',image_path='synthetic.jpg')
 with pytest.raises(ValueError):m.validated_approval(p,dict(bbox=[0,0,1024,1024],reviewer='tester'))
 with pytest.raises(ValueError):m.validated_approval(p,dict(bbox=[0,0,0,10],reviewer='tester',human_ack=True))
 r=m.validated_approval(p,dict(bbox=[10,20,100,200],reviewer='synthetic-test-only',human_ack=True));assert r['status']=='VERIFIED_GT'
