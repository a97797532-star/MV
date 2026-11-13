# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path('scripts').resolve()))
from generate_full_crop_manifest import process_source

# metadata: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def metadata():return dict(image_path='missing.jpg',product_id='declared/product',category='test',view='C1',split='train',width=1024,height=1024)
# policy: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def policy():return dict(production_mode='FULL_FRAME_UNVERIFIED_SCOPES',approved_scopes={},policy_version='synthetic-safe')
# test_source_failure_does_not_become_gate_pass: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path.
def test_source_failure_does_not_become_gate_pass(tmp_path):
 row=process_source((metadata(),policy(),'test-policy',tmp_path,None,{}))
 assert row['selected_policy']=='C' and row['crop_x1']==1024 and row['crop_y1']==1024
 assert row['processing_status']=='ERROR_SOURCE_FALLBACK' and row['quality_status']=='ERROR' and row['image_gate_status']!='PASS'
# test_annotation_fields_rejected_from_production_inputs: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path, forbidden.
@pytest.mark.parametrize('forbidden',['status','defect_type','has_mask','mask_path'])
def test_annotation_fields_rejected_from_production_inputs(tmp_path,forbidden):
 r=metadata();r[forbidden]='forbidden'
 with pytest.raises(AssertionError):process_source((r,policy(),'test-policy',tmp_path,None,{}))
