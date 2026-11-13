# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Release smoke runs with generated images, without private outputs or source snapshots."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from smoke_test_shared_data import synthetic_index,validate,main

# test_portable_smoke_without_private_data: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path.
def test_portable_smoke_without_private_data(tmp_path):
 index=synthetic_index(tmp_path)
 result=validate(index,2)
 assert result['status']=='PASSED' and result['images']==10
 assert result['five_view_batch_shape']==[2,5,3,256,256]
 assert result['mask_states']=={'MISSING':6,'PRESENT_POSITIVE':3,'PRESENT_EMPTY':1}
 assert result['detection_contracts']['MISSING_ANNOTATION']==1
 assert result['detection_contracts']['EMPTY_NG_REVIEW']==1
 assert len(result['adapters'])==12 and not result['model_forward']

# test_private_inputs_must_be_provided_explicitly: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: monkeypatch.
def test_private_inputs_must_be_provided_explicitly(monkeypatch):
 monkeypatch.delenv('REALIAD_DATA_ROOT',raising=False)
 monkeypatch.setattr(sys,'argv',['smoke_test_shared_data.py'])
 with pytest.raises(SystemExit) as exc:main()
 assert exc.value.code==2
