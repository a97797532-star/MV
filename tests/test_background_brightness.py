# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import numpy as np
import pytest
from mv_analysis.background_brightness import analyze,segment,region_stats


# test_uniform_is_not_certified_as_product: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_uniform_is_not_certified_as_product():
    image=np.full((128,128,3),240,np.uint8);row,masks=analyze(image,{})
    assert row['segmentation_status']=='failed'
    assert row['whole_mean']==240 and row['product_mean'] is None
    assert row['defect_status']=='not_provided'


# test_adaptive_background_not_fixed_white_black_threshold: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_adaptive_background_not_fixed_white_black_threshold():
    for background,product,bgtype in [(240,50,'WHITE'),(15,190,'BLACK')]:
        im=np.full((256,256,3),background,np.uint8);im[70:185,65:190]=product;im[110:140,110:140]=background
        masks,q=segment(im,False)
        assert q['background_type']==bgtype
        assert masks['A'][85,85] and not masks['A'][120,120] and not masks['A'][0,0]
        assert q['method_A_C_agreement']>.8


# test_uncertainty_invalidates_product_local_context: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_uncertainty_invalidates_product_local_context():
    image=np.zeros((64,64,3),np.uint8);defect=np.zeros((64,64),np.uint8);defect[20:25,20:25]=1
    row,_=analyze(image,{},defect)
    assert row['defect_pixels']==25 and row['defect_mean']==0
    assert row['defect_local_difference'] is None and row['product_mean'] is None


# test_histogram_percentile_exact_and_color_order: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_histogram_percentile_exact_and_color_order():
    gray=np.arange(256,dtype=np.uint8).reshape(16,16);r=region_stats(gray,np.ones(gray.shape,bool),'x_')
    assert r['x_p05']==pytest.approx(np.percentile(gray,5))
    image=np.zeros((64,64,3),np.uint8);image[:,:,2]=255;row,_=analyze(image,{})
    assert row['whole_mean']==76


# test_defect_mask_never_controls_product_and_local_annulus_stays_inside: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_defect_mask_never_controls_product_and_local_annulus_stays_inside():
    image=np.full((256,256,3),240,np.uint8);image[50:205,50:205]=40;image[100:110,100:110]=70
    defect=np.zeros((256,256),np.uint8);defect[100:110,100:110]=1
    row,masks=analyze(image,{},defect);without,other=analyze(image,{})
    assert np.array_equal(masks['A'],other['A'])
    assert row['segmentation_status']=='accepted_heuristic'
    assert row['defect_local_difference']==pytest.approx(30)
    assert row['defect_local_mean']==40


# test_regional_checkpoints_resume_and_keep_unprovided_ng: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path.
def test_regional_checkpoints_resume_and_keep_unprovided_ng(tmp_path):
    import json
    import cv2
    import pandas as pd
    from mv_analysis.regional_cli import main
    from mv_analysis.background_brightness import VERSION
    source=tmp_path/'source';source.mkdir();data=tmp_path/'data';data.mkdir();out=tmp_path/'out';rows=[]
    for i in range(6):
        image=np.full((64,64,3),240,np.uint8);image[15:50,15:50]=40
        path=data/f'{i}.jpg';cv2.imwrite(str(path),image);stat=path.stat()
        rows.append(dict(image_path=path.name,mask_path='',category='widget',view='C1',status='OK' if i<3 else 'NG',defect_type='NORMAL' if i<3 else 'HS',split='train',product_id=str(i),bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,has_mask=False))
    pd.DataFrame(rows).to_csv(source/'image_metadata_with_split.csv',index=False)
    pd.DataFrame([dict(image_path=r['image_path'],brightness=cv2.cvtColor(cv2.imread(str(data/r['image_path'])),cv2.COLOR_BGR2GRAY).mean()) for r in rows]).to_csv(source/'brightness_per_image.csv',index=False)
    (source/'run.json').write_text(json.dumps(dict(config=dict(root=str(data)))))
    (source/'mask_policy.json').write_text(json.dumps(dict(validated=True,threshold=0)))
    review=tmp_path/'review.json';review.write_text(json.dumps(dict(visual_review_completed=False,algorithm_version=VERSION)))
    args=['--source-run',str(source),'--output',str(out),'--validation-evidence',str(review),'--batch-size','3']
    with pytest.raises(SystemExit):main(args)
    review.write_text(json.dumps(dict(visual_review_completed=True,algorithm_version=VERSION)))
    assert main(args)==0 and main(args+['--resume','--finalize'])==0
    result=pd.read_csv(out/'regional_brightness_per_image.csv')
    assert len(result)==6 and result.image_path.nunique()==6
    assert (result[result.status=='NG'].defect_status=='not_provided').all()
    assert len((out/'regional_checkpoint.jsonl').read_text().splitlines())==6
    assert not list(data.glob('*.png'))
