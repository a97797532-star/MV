# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
import sys,json,importlib.util
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path('scripts').resolve()))
import freeze_adaptive_crop_gate_recovery as recovery
NAMES=['grabcut_change','fg_fraction','component_count','largest_component_fraction','foreground_contrast','boundary_touch_fraction','fg_outside_crop','crop_side','box_aspect','center_x','center_y','crop_center_offset','median_method_iou','max_method_center_distance','min_method_area_ratio']
# sample: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: tmp_path, monkeypatch, final_seen.
def sample(tmp_path,monkeypatch,final_seen=False):
 monkeypatch.setattr(recovery.runner,'B',tmp_path);(tmp_path/'checkpoints').mkdir();(tmp_path/'metrics').mkdir()
 metadata=[];features=[]
 for i in range(450):
  path=f'synthetic/{i}.jpg';cohort='train_reference' if i<300 else 'calibration';metadata.append(dict(image_path=path,gate_cohort=cohort,status='OK',split='train',category=f'cat{i%30}',view=f'C{1+(i//30)%5}'));features.append(dict(image_path=path,cohort=cohort,features={n:float(i) for n in NAMES}))
 if final_seen:features.append(dict(image_path='final/image.jpg',cohort='final_holdout',features={}))
 (tmp_path/'checkpoints/features.jsonl').write_text('\n'.join(json.dumps(r) for r in features));return pd.DataFrame(metadata),dict(minimum_category_view_n=20,runner_sha256='synthetic',module_sha256='synthetic')
# test_feature_export_and_freeze_reentry_guard: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path, monkeypatch.
def test_feature_export_and_freeze_reentry_guard(tmp_path,monkeypatch):
 d,cfg=sample(tmp_path,monkeypatch);recovery.freeze_reference(d,cfg);out=pd.read_csv(tmp_path/'metrics/normal_reference_features.csv');assert len(out)==450 and all(n in out for n in NAMES);assert json.loads((tmp_path/'frozen_policy.json').read_text())['final_holdout_seen'] is False
 with pytest.raises(RuntimeError):recovery.freeze_reference(d,cfg)
# test_final_must_not_be_seen_before_freeze: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: tmp_path, monkeypatch.
def test_final_must_not_be_seen_before_freeze(tmp_path,monkeypatch):
 d,cfg=sample(tmp_path,monkeypatch,True)
 with pytest.raises(AssertionError):recovery.freeze_reference(d,cfg)
 assert not (tmp_path/'frozen_policy.json').exists()
