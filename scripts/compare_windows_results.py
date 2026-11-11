"""Read-only comparison against preserved real Windows CSVs; execute pure metrics only."""
import argparse,ast,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,pandas as pd
from PIL import Image
from mv_analysis.core import save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--windows',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(exist_ok=False);root=Path(json.loads((a.run/'run.json').read_text())['config']['root']);old=a.windows
meta=pd.read_csv(old/'image_metadata.csv',keep_default_na=False);meta['image_path']=meta.relative_path.str.replace('\\','/',regex=False)
new=pd.read_csv(a.run/'brightness_per_image.csv',keep_default_na=False);oldb=pd.read_csv(old/'brightness_per_image.csv').merge(meta[['image_id','image_path']],on='image_id',validate='one_to_one')
joined=oldb.merge(new[['image_path','brightness']],on='image_path',validate='one_to_one');joined['opencv_minus_legacy']=joined.brightness-joined['mean'];joined[['image_id','image_path','mean','brightness','opencv_minus_legacy']].to_csv(a.output/'brightness_full_comparison.csv',index=False)
masks=pd.read_csv(old/'mask_metadata.csv',keep_default_na=False);current_masks=pd.read_csv(a.run/'mask_metadata.csv',keep_default_na=False)
mask_col='mask_path' if 'mask_path' in current_masks else 'image_path'
evidence=dict(windows_jpg=len(meta),ubuntu_jpg=len(new),jpg_path_set_equal=set(meta.image_path)==set(new.image_path),windows_png=len(masks),ubuntu_png=len(current_masks),mask_path_set_equal=set(masks.relative_path.str.replace('\\','/',regex=False))==set(current_masks[mask_col]),brightness_joined=len(joined),windows_comparison_rows=len(pd.read_csv(old/'brightness_comparison.csv')),brightness_mean_abs_definition_delta=float(joined.opencv_minus_legacy.abs().mean()),brightness_max_abs_definition_delta=float(joined.opencv_minus_legacy.abs().max()))
base=Path('legacy/windows_snapshot/RealIAD_OpenCV_Analysis_Assignment_v2/RealIAD_OpenCV');notebook=next(base.glob('*executed.ipynb'));cells=json.loads(notebook.read_text())['cells'];function=None
for cell in cells:
 if cell.get('cell_type')=='code' and 'def analyze_brightness(' in ''.join(cell['source']):
  for node in ast.parse(''.join(cell['source'])).body:
   if isinstance(node,ast.FunctionDef) and node.name=='analyze_brightness':function=node
if function is None:raise RuntimeError('Original pure brightness helper missing')
ns=dict(Path=Path,Image=Image,np=np,pd=pd);exec(compile(ast.Module(body=[function],type_ignores=[]),str(notebook),'exec'),ns)
new_index=new.set_index('image_path');sample=joined.sort_values('image_path').groupby(['category','view'],sort=True).head(1);replayed=[]
for row in sample.to_dict('records'):
 local=dict(row);local['image_path']=root/row['image_path'];local['mask_path']=root/new_index.loc[row['image_path'],'mask_path'] if new_index.loc[row['image_path'],'mask_path'] else ''
 result=ns['analyze_brightness'](local);replayed.append(dict(image_path=row['image_path'],saved_mean=row['mean'],replayed_mean=result['mean'],absolute_difference=abs(result['mean']-row['mean'])))
pd.DataFrame(replayed).to_csv(a.output/'brightness_same_method_replay.csv',index=False);evidence['brightness_same_method_images']=len(replayed);evidence['brightness_same_method_max_abs_delta']=max(r['absolute_difference'] for r in replayed)
spec=importlib.util.spec_from_file_location('legacy_resolution_replay',base/'realiad_5view_information_loss.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
prior=pd.read_csv(old/'resolution_information_loss/per_view_information_loss.csv');prior=prior.merge(meta[['image_id','image_path']],on='image_id',validate='many_to_one');replay=[]
for path,rows in prior.groupby('image_path',sort=True):
 with Image.open(root/path) as im:rgb=np.asarray(im.convert('RGB'))
 for row in rows.to_dict('records'):
  down=cv2.resize(rgb,(int(row['size']),int(row['size'])),interpolation=cv2.INTER_LINEAR);metrics,*_=module.loss_metrics(rgb,down)
  for key,value in metrics.items():
   saved=float(row[key]);delta=abs(saved-value) if np.isfinite(saved) and np.isfinite(value) else None
   replay.append(dict(image_path=path,size=row['size'],metric=key,saved_value=saved,replayed_value=value,absolute_difference=delta))
rr=pd.DataFrame(replay);rr.to_csv(a.output/'resolution_same_method_replay.csv',index=False);evidence['resolution_same_method_images']=prior.image_path.nunique();evidence['resolution_same_method_rows']=len(prior);evidence['resolution_max_abs_delta_by_metric']=rr.groupby('metric').absolute_difference.max().to_dict()
save_json(a.output/'comparison_validation.json',evidence)
report=f'''# Windows 실제 결과와 Ubuntu 비교\n\n원본 Windows 결과는 읽기 전용으로 사용했다. [검증 JSON](../{a.output}/comparison_validation.json).\n\n- 실제 저장 Windows JPG {len(meta):,} / PNG {len(masks):,}. Ubuntu와 상대 경로 집합 동일 여부: JPG {evidence['jpg_path_set_equal']}, PNG {evidence['mask_path_set_equal']}. 과거 참고 146,060/50,115와의 차이 원인은 미확정이다. 최신 Windows 결과에도 u_block이 있다.\n- 저장 split은 151,050장 모두 재현 일치했다. [분할 검증](WINDOWS_SPLIT_REPRODUCTION.json).\n- 전체 밝기 {len(joined):,}장 비교: 새 OpenCV 정수 회색조와 기존 float32 RGB 가중 회색조의 영상 평균 절대 차이 평균 {evidence['brightness_mean_abs_definition_delta']:.8f}, 최대 {evidence['brightness_max_abs_definition_delta']:.8f} intensity. [전체 대조](../{a.output}/brightness_full_comparison.csv). 반올림/회색조 정의 차이를 OS 차이로 보지 않는다.\n- 기존 Notebook의 순수 analyze_brightness를 그대로 추출해 30품목×5시점 {len(replayed)}장 재실행: 저장값 대비 최대 절대 차이 {evidence['brightness_same_method_max_abs_delta']:.10g}. [같은 방법 재검증](../{a.output}/brightness_same_method_replay.csv).\n- 기존 해상도는 50장의 3해상도 150행만 저장되어 있다. 모든 저장 입력에 보존된 loss_metrics를 다시 적용했다. [지표별 같은 방법 대조](../{a.output}/resolution_same_method_replay.csv). 이는 전체 해상도 분석 결과가 아니다.\n\n기존 해상도는 LINEAR 축소, 경계 ±1픽셀 일치 허용, Laplacian 절댓값 평균(ksize3), Sobel magnitude 평균, 9×9 box 국소 표준편차다. 새 통합 분석은 AREA 축소, 경계 정확 위치, Laplacian 제곱 평균(ksize1), Sobel 제곱 에너지, Gaussian11 sigma1.5 국소 대비를 사용한다. PSNR 동일 영상 처리도 기존 OpenCV 약361dB와 새 상한120dB가 다르다. 따라서 서로 다른 정의의 값을 직접 OS 오차로 비교하지 않는다.\n\n기존 multiclass Notebook에는 threshold127 예시와 나중의 None 초기화가 함께 있어 실행 순서 의존성이 있다. 새 정책은 전체 마스크 무결성/층화 overlay/공식 nonzero 평가 규칙에 근거해 >0으로 명시했다. 기존 단일 클래스 함수·backend·coarse_occupancy는 보존 및 재사용하고, 새 default defect_type 8클래스와 기존 category+type 클래스 체계를 구분한다.\n\n초기 area-v1 히트맵은 면적 진단으로 보존한다. 기존 coursework 계약을 재사용하는 presence-v2는 영상별 cell 존재 합/n_known 또는 n_positive이며 관측 0은 NaN이다. 기존 Windows seed42 분할로 별도 재생성한다. 원본 위치별 수치와 직접 동등하다고 주장하려면 split/threshold/grid/분모가 모두 같아야 한다.\n'''
Path('reports/WINDOWS_RESULT_COMPARISON.md').write_text(report);print(json.dumps(evidence,indent=2))
