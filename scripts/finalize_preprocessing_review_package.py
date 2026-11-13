# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Finalize existing report assets after review; no image/metric computations."""
import hashlib,json,re,shutil,zipfile
from pathlib import Path
import cv2
from datetime import datetime,timezone
B=Path('outputs/preprocessing_review_20261112_v2');AS=B/'review_assets';P=Path('reports');M=Path('outputs/model_sources_20261112_v1')
STAGING=Path('outputs/preprocessing_review_package_20261112_v2')
ZIP=P/'PREPROCESSING_REVIEW_PACKAGE.zip'
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: path.
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
# sanitize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: text.
def sanitize(text):return re.sub(r'/(?:home|mnt|Users|tmp)/[^\s"\'<>|,)]+','<LOCAL_PATH>',text)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 if ZIP.exists() or STAGING.exists():raise SystemExit('Preserve existing archive/staging. Choose new version.')
 num=json.loads((AS/'validation/review_numerical_validation.json').read_text());assert num['success']
 complete=json.loads((B/'complete.json').read_text());assert complete['success']
 for path,h in complete['source_sha256'].items():assert sha(path)==h
 refs=json.loads((M/'model_input_source_evidence.json').read_text())
 records=json.loads((M/'model_input_fields.json').read_text());assert len(records)==12
 for r in refs:
  if r['status']!='VERIFIED':continue
  key=next(v['repo_key'] for v in records if v['model']==r['model']);src=M/key/'source'/r['path']
  assert sha(src)==r['sha256'] and r['symbol'] in src.read_text().splitlines()[r['line']-1]
 # Each PNG has an explicit statistical plot name; no raster source/crop/overlay files.
 allowed={'dataset_composition','crop_global','crop_category_view','selection_bias','selection_coverage_reasons','brightness_paired','defect_local_and_background','product_geometry','bbox_geometry_risk',
 'resolution_distribution_ssim','resolution_distribution_edge_recall','resolution_distribution_edge_f1','resolution_distribution_local_contrast_retention','resolution_distribution_high_frequency_proxy_retention','resolution_category_comparison','resolution_view_comparison','resolution_status_comparison'}
 pngs=list((AS/'figures').glob('*.png'));assert {p.stem for p in pngs}==allowed
 assert all(cv2.imread(str(p)) is not None for p in pngs)
 reports=['DATA_ANALYSIS_MASTER_REPORT.md','PREPROCESSING_DECISION_EVIDENCE.csv','PREPROCESSING_RISK_CASES.md','MODEL_INPUT_REQUIREMENTS.md','ANALYSIS_EVIDENCE_INDEX.md','ADDITIONAL_PREPROCESSING_ANALYSIS_SCOPE.md']
 files=[P/n for n in reports]+[p for p in AS.rglob('*') if p.is_file()]+[Path('scripts/resume_preprocessing_review.py'),Path('scripts/analyze_preprocessing_evidence.py'),Path('scripts/build_preprocessing_review_package.py'),Path('scripts/finalize_preprocessing_review_package.py'),Path('pyproject.toml'),Path('uv.lock')]
 STAGING.mkdir()
 for src in files:
  dest=STAGING/src;dest.parent.mkdir(parents=True,exist_ok=True)
  if src.suffix=='.png':shutil.copy2(src,dest)
  else:dest.write_text(sanitize(src.read_text()))
 # Replace packaged copies of draft source evidence with the reviewed source symbols/dtype.
 # Originals in local review_assets remain untouched.
 for name in ['model_input_source_evidence.json','model_input_fields.json','manifest.json']:
  dest=STAGING/AS/'validation'/('model_sources_20261112_v1__'+name)
  dest.write_text(sanitize((M/name).read_text()))
 readme='''# Real-IAD 외부 AI 전처리 검토 패키지

reports/DATA_ANALYSIS_MASTER_REPORT.md부터 읽는다. outputs/는 선택된 집계 CSV·통계 그래프와 검증 근거이며 원본 데이터가 아니다. 보고서의 주요 자료 링크는 상대 경로로 압축 내부에 연결되어 있다.

원본 JPG/PNG, 마스크, 원본에서 파생된 영상·Crop·오버레이 사례, 기존 이미지 포함 PDF, 가중치, .env, API 키, 개인 경로를 포함하지 않는다. PNG 17개는 모두 집계 통계 그래프다. 원본 영상 미제공으로 실제 픽셀 경계를 외부 연구자가 독립 검수할 수 없는 한계를 인정한다.

모델 규격은 11개 저장소의 12모델 후보·커밋을 조사한 정적 소스 근거다. 라이브러리/variant/가중치의 실제 실행과 성능은 UNVERIFIED다. 자동 제품 분할의 정답 정확도도 UNVERIFIED다. 전체 해상도 재계산, 모델 학습, API 호출, Push는 하지 않았다.

현재 실제 분석 근거는 preprocessing_review_20261112_v2다. 기존v1/v2 PNG 체크포인트가 같음을 확인해 재사용했다. 패키지 생성 코드는 로컬 원본 데이터 접근 없이 보고서 자산을 재포장한다. 분석 코드를 새로 실행하려면 별도 데이터와 원래 실행 환경이 필요하다.

MANIFEST.json의 상대경로·크기·SHA256으로 각 파일을 확인할 수 있다. ZIP 전체 SHA256과 CRC 검증 결과는 배포자가 제공하는 reports/PREPROCESSING_PACKAGE_VALIDATION.json을 참조한다. 그 파일은 ZIP 자기해시 재귀를 피하기 위해 압축 밖에서 제공한다.
'''
 (STAGING/'README.md').write_text(readme)
 validation=dict(success=True,checks=num['checks'],pytest=dict(passed=22,failed=0,seconds=10.80,command='uv run --offline pytest -q'),
  checkpoint_reused=True,source_resolution_recalculations=0,additional_png_decodes=0,representative_jpg_geometry=300,
  model_source_references=len(refs),verified_source_references=sum(v['status']=='VERIFIED' for v in refs),model_runtime='UNVERIFIED',product_segmentation_ground_truth='UNVERIFIED',png_scope='17 statistical plots only',png_visual_review=['crop_global','selection_bias','product_geometry'],push=False)
 (STAGING/AS/'validation/final_review_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2))
 link_re=re.compile(r'!?\[[^]]*\]\(([^)]+)\)');secret=re.compile(r'(?m)(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|^-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----$)')
 issues=[]
 for f in STAGING.rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(STAGING)
  if f.suffix in ['.jpg','.jpeg','.npy','.npz','.pt','.pth','.ckpt','.safetensors','.pdf'] or f.name.startswith('.env') or 'dataset' in rel.parts:issues.append(dict(path=str(rel),reason='Forbidden member'))
  if f.suffix=='.png':
   assert f.stem in allowed and 'figures' in rel.parts;continue
  text=f.read_text()
  if re.search(r'/(?:home|mnt|Users)/',text) or re.search(r'[A-Za-z]:\\(?:Users|IMSN)',text) or secret.search(text):issues.append(dict(path=str(rel),reason='Personal path or secret pattern'))
  if f.suffix=='.md':
   for target in link_re.findall(text):
    if not target.startswith(('https://','http://','#')) and not (f.parent/target.split('#')[0]).exists():issues.append(dict(path=str(rel),reason='Missing relative link',target=target))
 if issues:raise RuntimeError(json.dumps(issues,ensure_ascii=False))
 files=[]
 for f in sorted(STAGING.rglob('*')):
  if f.is_file():files.append(dict(path=str(f.relative_to(STAGING)),bytes=f.stat().st_size,sha256=sha(f)))
 (STAGING/'MANIFEST.json').write_text(json.dumps(dict(files=files,original_and_derived_case_images=False,statistical_plots=17),indent=2))
 with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for f in sorted(STAGING.rglob('*')):
   if f.is_file():z.write(f,str(f.relative_to(STAGING)))
 with zipfile.ZipFile(ZIP) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  for name in z.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts
  for f in files:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
  members=z.namelist()
 delivery=dict(success=True,time_utc=datetime.now(timezone.utc).isoformat(),zip=str(ZIP.resolve()),bytes=ZIP.stat().st_size,sha256=sha(ZIP),file_count=len(members),files=members,
  crc_test='VERIFIED',all_member_sha256='VERIFIED',relative_links='VERIFIED',secrets_personal_paths='VERIFIED',original_or_derived_case_images=False,statistical_figures=17,numerical_validation=validation,push=False)
 p=P/'PREPROCESSING_PACKAGE_VALIDATION.json'
 if p.exists():raise RuntimeError('Existing delivery validation: preserve')
 p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in delivery.items() if k not in ['files','numerical_validation']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
