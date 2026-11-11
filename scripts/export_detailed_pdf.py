"""Create a detailed Korean PDF using installed Matplotlib and local fonts only."""
import argparse,json,os,re,sys,unicodedata,zlib,hashlib
from pathlib import Path
from datetime import datetime,timezone
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.ft2font import FT2Font
from mv_analysis.core import save_json
p=argparse.ArgumentParser();p.add_argument('--gallery',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--image-run',required=True,type=Path);p.add_argument('--background-run',required=True,type=Path);p.add_argument('--sample-run',required=True,type=Path);p.add_argument('--mask-study',type=Path,required=True);p.add_argument('--draft',action='store_true');a=p.parse_args()
if a.output.exists():raise SystemExit('PDF exists: preserve it and select a new output filename')
if not a.draft:
 for folder,name in [(a.image_run,'artifact_validation.json'),(a.background_run,'scientific_validation.json')]:
  evidence=json.loads((folder/name).read_text())
  if evidence.get('failures') or evidence.get('failed') or evidence.get('success') is False:raise SystemExit('Analysis validation failed')
 if not (a.image_run/'per_view_information_loss.csv').exists() or not (a.background_run/'regional_validation.json').exists():raise SystemExit('Full resolution/regional analysis not complete')
 if json.loads((a.background_run/'regional_validation.json').read_text())['processed']!=151050:raise SystemExit('Full regional scope not reached')
 with (a.image_run/'per_view_information_loss.csv').open() as stream:
  if sum(1 for _ in stream)!=151050*3+1:raise SystemExit('Full resolution row count not reached')
 gallery_check=json.loads((a.gallery/'manifest.json').read_text())
 if not gallery_check['full_resolution_complete'] or not gallery_check['full_regional_complete']:raise SystemExit('Gallery has incomplete-stage placeholders; regenerate after full analysis')
fonts=[Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf'),Path('/mnt/c/Windows/Fonts/malgun.ttf')];font=next((f for f in fonts if f.exists()),None)
if font is None:raise SystemExit('Install a Korean font or provide NanumGothic/Malgun through the documented system paths')
fontprops=FontProperties(fname=str(font));charmap=FT2Font(str(font)).get_charmap();assert all(ord(c) in charmap for c in '제품밝기배경결함해상도분석보고서')
plt.rcParams.update({'pdf.fonttype':42,'axes.unicode_minus':False,'pdf.compression':6})
pages=[];included_figure_hashes=set()
def clean(text):
 text=re.sub(r'!\[([^]]*)\]\(([^)]+)\)',r'그림 참조: \1 (\2)',text)
 text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text)
 return text.replace('**','').replace('`','')
def wrap(text,width=98):
 result=[]
 for paragraph in str(text).replace('−','-').split('\n'):
  line='';n=0
  for char in paragraph:
   size=2 if unicodedata.east_asian_width(char) in 'WF' else 1
   if n+size>width:result.append(line);line='';n=0
   line+=char;n+=size
  result.append(line)
 return result

def text_pages(title,body,source=''):
 lines=[]
 for paragraph in body:lines.extend(wrap(clean(paragraph)));lines.append('')
 for start in range(0,max(1,len(lines)),42):pages.append(dict(kind='text',title=title+(' (계속)' if start else ''),lines=lines[start:start+42],source=source))

def table_pages(title,rows,source):
 if len(rows)<2:return
 columns=rows[0];values=rows[1:];n=len(columns)
 # Keep category/view identifiers visible when splitting wide numerical tables.
 groups=[list(range(n))] if n<=8 else [list(range(min(2,n)))+list(range(start,min(n,start+6))) for start in range(2,n,6)]
 for gi,indices in enumerate(groups):
  for start in range(0,len(values),22):pages.append(dict(kind='table',title=title+(f' / 열 {gi+1}/{len(groups)}' if len(groups)>1 else ''),columns=[columns[i] for i in indices],rows=[[row[i] if i<len(row) else '' for i in indices] for row in values[start:start+22]],source=source))

def markdown(path,label):
 if not path.exists():return
 title=label;body=[];table=[]
 def flush():
  nonlocal body,table
  if body:text_pages(title,body,str(path));body=[]
  if table:table_pages(title,table,str(path));table=[]
 source_lines=path.read_text().splitlines()
 for index,line in enumerate(source_lines):
  match=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line.strip())
  if match:
   flush();target=(path.parent/match.group(2)).resolve()
   if target.is_file():
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    if digest not in included_figure_hashes:
     next_text=next((v for v in source_lines[index+1:] if v.strip()),'본문의 해석과 데이터 분모를 함께 확인한다.')
     if next_text.lstrip().startswith(('#','!','|')):next_text='실제 영상/주석 또는 집계 그림이다. 본문의 입력 범위·수치·해석과 함께 확인하고 자동 결과를 정답 정확도로 간주하지 않는다.'
     pages.append(dict(kind='figure',title=label+' · '+match.group(1),path=str(target),caption=clean(next_text),source=str(target)));included_figure_hashes.add(digest)
   continue
  if re.match(r'^#{1,3} ',line):flush();title=label+' · '+line.lstrip('# ').strip()
  elif line.startswith('|'):
   if body:text_pages(title,body,str(path));body=[]
   values=[x.strip() for x in line.strip('|').split('|')]
   if not all(re.fullmatch(r'[: -]+',v or '-') for v in values):table.append(values)
  else:
   if table:table_pages(title,table,str(path));table=[]
   if line.strip() and not line.startswith('```'):body.append(line)
 flush()

text_pages('데이터 분석 보고서 이용 안내',[
 '이 보고서는 Real-IAD 5시점 제조 외관검사 데이터의 관측 통계, 영상 정보 손실, 주석 품질, 배경 영향과 실무 검수 근거를 통합한다. 모델 학습이나 검출 성능 측정 결과가 아니다.',
 '전체 JPG 151,050장(OK 72,840 / NG 78,210), 제공 PNG 51,329개. NG와 PNG 개수는 같을 필요가 없다. 마스크 없는 NG를 정상으로 바꾸거나 빈 정답을 만들지 않았다.',
 '읽는 순서: 주요 발견과 데이터 품질 → 영역별 밝기 재검증 → 마스크 정책/Windows 비교 → 주요 그림 → 30품목 상세 프로파일/동일 제품 5시점/위치 빈도 → 실행 환경과 재현.',
 'accepted_heuristic는 자동 전경 품질 조건 통과를 의미한다. 사람의 정답 분할 정확도가 아니며 불확실 영상은 제품 통계를 결측으로 남긴다. 공간 빈도는 관측 주석의 분포이며 실제 제조 불량 발생 확률과 같다고 보장하지 않는다.',
 'PDF의 각 그림은 출처를 표시한다. 공유 집계표와 그림은 images/manifest.json, 원본 전체 per-image 결과와 체크포인트는 로컬 outputs/에 보존된다. 공유 PNG는 선택된 검수 사례와 집계 그림이며 원본 데이터셋의 대체물이 아니다.',
 '과거 Windows 참고 규모와 실제 최신 저장 결과를 구분한다. 최신 Windows JPG/PNG 경로 집합은 Ubuntu와 같고, 프로젝트 seed42 분할은 151,050장 모두 동일하게 재현했다.',
 '미세 결함에는 전체 영상 SSIM·평균 밝기가 부족할 수 있다. 박스 크기와 결함 위치 JPG 확대를 함께 보며 입력 해상도를 검토한다. 상관관계를 인과관계로 해석하지 않는다.'
])
if not a.draft:
 import pandas as pd
 native=pd.read_csv(a.image_run/'per_view_information_loss.csv',usecols=['target','ssim','edge_recall','rgb_rmse','local_contrast_retention'])
 rm=native[native.target!=1024].groupby('target').mean().reset_index();del native
 bg=json.loads((a.background_run/'regional_validation.json').read_text());accepted=bg['segmentation_status_counts'].get('accepted_heuristic',0)
 text_pages('회의용 핵심 결과와 다음 의사결정',[
  f'전체 151,050 JPG와 제공 51,329 PNG를 구분해 분석했다. NG 78,210장 중 위치 주석 제공은51,329장, 미제공26,881장이며 미제공을 오류/정상으로 처리하지 않았다.',
  f'배경·제품 영역 재검증은151,050장을 처리했고 자동 품질 통과 {accepted:,}장({accepted/151050*100:.2f}%)만 제품 밝기에 사용했다. 나머지 분할 상태는 {bg["segmentation_status_counts"]}이다. 이는 정답 기반 정확도가 아니다.',
  '픽셀 decode 성공과 내용 품질은 다르다. 전검정 중복2장, 제공 빈 마스크34개, 불량 유형 충돌10장을 별도 검수 대상으로 남겼다. 두 전검정 영상은 보존한 실제 Windows 분할에서는 모두Train이다.',
  '검증된 >0 주석 정책으로60,629개 연결 성분 박스를 추출했다. 원본 bbox area<1,024px²는16,297개이며, 256입력에서 짧은 변이2픽셀 미만으로 축소되는 박스는1,525개다. 기하학적 위험과 실제 검출 실패를 구분한다.',
  '현재 데이터와 최신 Windows 결과의 경로 집합은 동일하다. 과거29품목 체크포인트와의 차이는u_block 범위다. 프로젝트 제품 split은151,050장 전부 재현 일치했고 기존 위치 히트맵 공통555그룹 중553그룹의 격자값이 오차0으로 일치했다.',
  '의사결정1: 작은 결함의 실제 JPG 확대 검수를 유지하고1024참조/512/256모델 실험을 같은 제품 분할에서 비교한다. 아래 전역 영상 지표는 모델 성능이 아니다.',
  '의사결정2: 증강 후보는Train 제품 분포에서만 정하고 배경·결함 국소 대비를 확인한다. 제품 분할이 불확실한 품목은 수작업 제품 마스크 표본을 확보한 뒤 정책을 고정한다.',
  '의사결정3: 제공 마스크의 주석 의미, 전검정 영상의 촬영/라벨 의미, HS/QS 충돌, 폴더 serial의 실제 물리 제품 identity를 담당자가 확인한다. 원본 분석 대상과 권고 학습 subset은 별도 manifest로 유지한다.'
 ],'전체 검증 JSON, bbox CSV, preserved Windows split 및 배경 영역별 집계')
 table_pages('회의용 해상도 비교 · 전체 JPG 평균',[list(rm.columns)]+[[str(v) for v in row] for row in rm.itertuples(index=False,name=None)],str(a.image_run/'per_view_information_loss.csv'))
for path,label in [(Path('reports/REAL_IAD_FINAL_ANALYSIS.md'),'통합 분석'),(Path('reports/BACKGROUND_AWARE_BRIGHTNESS_ANALYSIS.md'),'배경·제품 밝기'),(Path('reports/ANALYSIS_CROSS_RELATIONS.md'),'분석 간 관계'),(Path('reports/MASK_THRESHOLD_VALIDATION.md'),'마스크 정책'),(Path('reports/WINDOWS_RESULT_COMPARISON.md'),'Windows 재현 검증')]:markdown(path,label)

def figure(path,title,caption,source=None):
 if Path(path).is_file():
  digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
  if digest not in included_figure_hashes:
   pages.append(dict(kind='figure',title=title,path=str(path),caption=caption,source=source or str(path)));included_figure_hashes.add(digest)
manifest=json.loads((a.gallery/'manifest.json').read_text())
for record in manifest['artifacts']:
 if record['kind']=='published_aggregate_or_figure' and record['path'].endswith('.png'):figure(record['path'],'전체 분석 그림 · '+Path(record['source']).name,'분포·예외 사례를 본문 수치와 함께 확인한다. 평균/영상 지표는 모델 성능이 아니다. 그래프 축과 범례의 단위를 따른다.',record['source'])
figure(a.sample_run/'augmentation_review.png','Train 전용 증강 후보 시각 검수','정상/불량, 흰/검은 배경의 실제 Train 이미지. 배경 픽셀을 유지한 제한적인 제품 gain 후보이며 Validation/Test는 바꾸지 않았다. 국소 대비 보존 수치와 미정의 여부를 augmentation_visual_checks.csv에서 함께 확인한다.')
for i in range(1,7):figure(a.sample_run/f'foreground_segmentation_examples_{i:02}.png',f'제품 분할 세 방법 비교 · 대표 품목 {i}/6','왼쪽은 실제 원본, A는 경계 색상/조명 모델, B는 GrabCut, C는 색상 seed watershed. 녹색은 추정 전경, 빨간색은 경계. accepted_heuristic도 정답 검증 완료가 아니다. 그림자·반사·문자·구멍·유사 배경과 잘림을 검수한다.')
folder=a.mask_study/'mask_threshold_validation';figure(folder/'threshold_sensitivity.png','마스크 임계값 민감도','336장 층화 표본의 0/32/64/127/192/254 비교. 높은 임계값의 성분 증가가 결함 분절일 수 있어 작은 성분을 곧바로 노이즈로 단정하지 않는다.')
for path in sorted(folder.glob('overlay_*.png'))[:10]:figure(path,'마스크 경계 검수 · '+path.stem.replace('overlay_',''),'원본 JPG와 제공 PNG의 위치를 대조한다. 회색조 경계 픽셀을 오류로 간주하지 않으며 실제 경계 의미의 한계를 남긴다. 본 위치 분석 정책은 검증된 >0이다.')
roi=Path('outputs/defect_resolution_review_20261111_v7');figure(roi/'defect_detail_crop_comparison.png','실제 결함 위치의 JPG 해상도 확대 비교','336장 대표 ROI 연구 중 검수 사례. 마스크는 결함 위치 선택에만 사용하며 화질 손실은 JPG에서 계산한다. 512/256 복원 차이가 실제 검출 실패를 증명하지는 않는다.')
for category in sorted({r['category'] for r in manifest['artifacts'] if 'category' in r}):
 for kind,title,caption in [('category_profile',f'{category} · 분포와 지표','전체 밝기 분포, C1~C5 평균, 연결 성분 박스 면적, 해상도 SSIM/경계 보존, 제품 밝기의 품질 통과 부분집합을 함께 비교한다. 그림의 product subset과 전체 이미지 분모는 다르다.'),('category_five_view_case',f'{category} · 같은 제품의 5시점 사례','위: 동일 OK 제품의 C1~C5. 아래: 동일 NG 제품의 C1~C5. 각 행은 독립적으로 선택한 서로 다른 제품이다. 빨간 주석은 제공된 결함 마스크, 초록 사각형은 8연결 성분 박스. 모든 성분에 영상의 불량 유형을 적용하는 가정이다. 대표 1개 capture씩이며 발생 빈도가 아니다.'),('category_heatmaps',f'{category} · Train 시점별 결함 위치','보존된 Windows 프로젝트 분할의 Train NG만 집계한다. 각 칸에 양성 픽셀이 하나라도 있으면 영상별 1회 점유로 센다. 제공 빈 마스크는 known 분모에 포함, 미제공은 제외한다. 칸 빈도와 colorbar를 비교하고 관측되지 않은 영역을 정상으로 고정하지 않는다.')]:
  for record in manifest['artifacts']:
   if record.get('category')==category and record['kind']==kind:figure(record['path'],title,caption,record.get('source_run',record['path']))
for path,label in [(Path('reports/ENVIRONMENT_MIGRATION_REPORT.md'),'실행 환경'),(Path('docs/ANALYSIS_PIPELINE.md'),'계산 정의와 재현')]:markdown(path,label)
# Insert a section index after the cover; page numbers account for index pages.
index=[];last=None
for i,page in enumerate(pages):
 group=page['title'].split(' · ')[0]
 if group!=last:index.append((i,group));last=group
index_count=max(1,(len(index)+37)//38)
index_pages=[]
for start in range(0,len(index),38):index_pages.append(dict(kind='text',title='목차 · 분석과 품목별 검수',lines=[f'{name}  ···  {i+index_count+2}' for i,name in index[start:start+38]],source='페이지 번호는 표지와 목차를 포함한다.'))
cover=dict(kind='cover',title='Real-IAD 5시점\n상세 데이터 분석 보고서',lines=['배경·제품·결함 밝기 · 공간 주석 · 다중 클래스 박스','1024 / 512 / 256 해상도 정보 손실','Ubuntu 재현 검증 및 후속 모델 실험 준비', 'DRAFT — 전체 계산 미완료' if a.draft else '전체 분석 및 무결성 검증에 기반한 최종본'])
pages=[cover]+index_pages+pages;a.output.parent.mkdir(parents=True,exist_ok=True);previews=Path('outputs/pdf_previews')/a.output.stem;previews.mkdir(parents=True,exist_ok=False)
with PdfPages(a.output,metadata={'Title':'Real-IAD 5시점 상세 데이터 분석 보고서','Author':'MV project','Subject':'Observed data analysis; no model training','Keywords':'Real-IAD background brightness resolution annotation'}) as pdf:
 for number,page in enumerate(pages,1):
  landscape=page['kind']=='table'
  if page['kind']=='figure':
   shape=cv2.imread(page['path']).shape;landscape=shape[1]/shape[0]>1.5
  fig=plt.figure(figsize=(11.69,8.27) if landscape else (8.27,11.69));fig.patch.set_facecolor('white')
  if page['kind']=='cover':
   fig.text(.10,.75,page['title'],fontproperties=fontprops,fontsize=28,color='#173b62',linespacing=1.8)
   for i,line in enumerate(page['lines']):fig.text(.1,.47-i*.055,line,fontproperties=fontprops,fontsize=13)
   fig.text(.1,.16,datetime.now(timezone.utc).strftime('작성 UTC %Y-%m-%d %H:%M'),fontproperties=fontprops,fontsize=11)
  else:
   title='\n'.join(wrap(page['title'],100 if landscape else 72));fig.text(.065,.94,title,fontproperties=fontprops,fontsize=16,color='#173b62',va='top')
   if page['kind']=='text':
    for i,line in enumerate(page['lines']):fig.text(.07,.865-i*.0176,line,fontproperties=fontprops,fontsize=10.3,va='top')
   elif page['kind']=='table':
    ax=fig.add_axes([.045,.13,.91,.68]);ax.axis('off');cells=[['\n'.join(wrap(str(v),24)) for v in row] for row in page['rows']];headers=['\n'.join(wrap(c,24)) for c in page['columns']];t=ax.table(cellText=cells,colLabels=headers,cellLoc='left',loc='upper center');t.auto_set_font_size(False);t.set_fontsize(8)
    for (row,col),cell in t.get_celld().items():
     cell.get_text().set_fontproperties(fontprops);cell.get_text().set_fontsize(8);cell.set_height(.040 if row else .085);cell.set_edgecolor('#d6dde5')
     if row==0:cell.set_facecolor('#dbe8f4')
     elif row%2==0:cell.set_facecolor('#f3f6f9')
   elif page['kind']=='figure':
    image=cv2.imread(page['path']);image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB);h,w=image.shape[:2]
    if max(h,w)>1800:image=cv2.resize(image,(round(w*1800/max(h,w)),round(h*1800/max(h,w))),interpolation=cv2.INTER_AREA)
    ax=fig.add_axes([.055,.24,.89,.62]);ax.imshow(image);ax.axis('off')
    caption=wrap(page['caption'],100)
    for i,line in enumerate(caption[:7]):fig.text(.07,.20-i*.016,line,fontproperties=fontprops,fontsize=9.3,va='top')
   source=wrap('근거: '+page.get('source',''),145 if landscape else 106)
   for i,line in enumerate(source[:3]):fig.text(.065,.073-i*.012,line,fontproperties=fontprops,fontsize=7.5,color='#475569')
  fig.text(.065,.025,'MV · Real-IAD 데이터 분석'+(' · DRAFT' if a.draft else ''),fontproperties=fontprops,fontsize=8,color='#64748b');fig.text(.94,.025,f'{number} / {len(pages)}',fontproperties=fontprops,fontsize=8,ha='right',color='#64748b')
  pdf.savefig(fig)
  if number in {1,2,4} or page['kind']=='table' and not (previews/'table.png').exists() or page['kind']=='figure' and not (previews/'figure.png').exists():
   name='table' if page['kind']=='table' else 'figure' if page['kind']=='figure' else f'page_{number:03}';fig.savefig(previews/(name+'.png'),dpi=110)
  plt.close(fig)
  if number%20==0:print(f'PDF {number}/{len(pages)} pages',flush=True)
raw=a.output.read_bytes();page_count=len(re.findall(rb'/Type\s*/Page\b',raw));check=dict(pdf_header=raw.startswith(b'%PDF-'),eof_present=raw.rstrip().endswith(b'%%EOF'),page_objects=page_count,expected_pages=len(pages),page_count_matches=page_count==len(pages),korean_glyphs_available=True,type42_font_requested=True,bytes=len(raw),font=str(font),draft=a.draft,validation_scope='PDF structure/header/EOF/page counts and source figure previews; no independent third-party PDF renderer installed')
save_json(a.output.with_suffix('.validation.json'),check);save_json(a.output.with_suffix('.pages.json'),dict(pages=[dict(page=i+1,kind=r['kind'],title=r['title'],source=r.get('source')) for i,r in enumerate(pages)]));print(json.dumps(check,ensure_ascii=False,indent=2));assert check['pdf_header'] and check['eof_present'] and check['page_count_matches']
