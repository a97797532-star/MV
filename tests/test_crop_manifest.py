# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import numpy as np,pytest,cv2
from mv_analysis.crop_manifest import crop_xyxy,transform_boxes,transform_mask,require_no_extra_crop,load_crop_rgb

# record: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def record():return dict(original_width=10,original_height=10,crop_x0=2,crop_y0=3,crop_x1=8,crop_y1=9,crop_width=6,crop_height=6,coordinate_format='XYXY_EXCLUSIVE_ORIGINAL_PIXELS',additional_center_crop_allowed=False)
# test_box_origin_clip_scale_and_padding: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_box_origin_clip_scale_and_padding():
 b,keep=transform_boxes([[1,2,5,6],[0,0,1,1],[7,8,10,10]],record(),(12,18),(2,4));assert keep.tolist()==[True,False,True];np.testing.assert_allclose(b,[[2,4,11,10],[17,14,20,16]])
# test_mask_nearest_preserves_class_ids_and_alignment: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_mask_nearest_preserves_class_ids_and_alignment():
 r=record();m=np.arange(100,dtype=np.int32).reshape(10,10);out=transform_mask(m,r,(12,18));expected=cv2.resize(m[3:9,2:8],(18,12),interpolation=cv2.INTER_NEAREST);np.testing.assert_array_equal(out,expected);assert out.dtype==m.dtype
# test_double_crop_requires_explicit_experiment: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: model.
@pytest.mark.parametrize('model',['PatchCore','Dinomaly','INP-Former'])
def test_double_crop_requires_explicit_experiment(model):
 with pytest.raises(ValueError):require_no_extra_crop(record(),model)
 require_no_extra_crop(record(),model,True)
# test_bad_geometry_and_missing_mask_rejected: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_bad_geometry_and_missing_mask_rejected():
 r=record();r['crop_x1']=11
 with pytest.raises(ValueError):crop_xyxy(r)
 with pytest.raises(ValueError):transform_mask(None,record())
# test_rgb_loader_and_changed_source_fingerprint: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path.
def test_rgb_loader_and_changed_source_fingerprint(tmp_path):
 p=tmp_path/'synthetic.png';im=np.zeros((10,10,3),np.uint8);im[:]=[1,2,3];cv2.imwrite(str(p),im);s=p.stat();r=record()|dict(original_path=str(p),source_fingerprint=f'stat-v1:{s.st_size}:{s.st_mtime_ns}');out=load_crop_rgb(r);assert out.shape==(6,6,3) and out[0,0].tolist()==[3,2,1]
 r['source_fingerprint']='changed'
 with pytest.raises(ValueError):load_crop_rgb(r)
