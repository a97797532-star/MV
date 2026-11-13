# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read public GitHub commit metadata and selected text sources. Never fetch weights."""
import concurrent.futures as cf
import hashlib,json,re,time,urllib.request
from pathlib import Path
BASE=Path('outputs/model_sources_20261112_v1')
REPOS={
 'patchcore':('amazon-science/patchcore-inspection',[r'^src/patchcore/datasets/mvtec.py$',r'^bin/run_patchcore.py$']),
 'efficientad':('nelson1425/EfficientAD',[r'^efficientad.py$',r'^common.py$',r'^README.md$']),
 'uniad':('zhiyuanyou/UniAD',[r'^datasets/.*\.py$',r'^experiments/MVTec-AD/.*ya?ml$',r'^configs/.*ya?ml$',r'^README.md$']),
 'hvqtrans':('RuiyingLu/HVQ-Trans',[r'(^|/)datasets?\.py$',r'^main\.py$',r'^configs?/.*ya?ml$',r'^README.md$']),
 'dinomaly':('guojiajeremy/Dinomaly',[r'^dataset.py$',r'^train.py$',r'^dinomaly.py$',r'^main.py$',r'^README.md$']),
 'inpformer':('luow23/INP-Former',[r'^dataset.py$',r'^INP_Former.*\.py$',r'^main.py$',r'^README.md$']),
 'torchvision':('pytorch/vision',[r'^torchvision/models/detection/(transform|faster_rcnn|retinanet|generalized_rcnn)\.py$',r'^references/detection/(transforms|presets)\.py$']),
 'yolo11':('ultralytics/ultralytics',[r'^ultralytics/cfg/default.yaml$',r'^ultralytics/data/(augment|dataset|base)\.py$',r'^ultralytics/models/yolo/detect/(train|predict)\.py$']),
 'rtdetrv2':('lyuwenyu/RT-DETR',[r'^rtdetrv2_pytorch/configs/.*(dataloader|coco_detection).*ya?ml$',r'^rtdetrv2_pytorch/src/data/transforms/.*\.py$',r'^rtdetrv2_pytorch/src/data/dataset/coco_dataset.py$']),
 'yolos':('hustvl/YOLOS',[r'^datasets/(transforms|coco|__init__)\.py$',r'^main.py$',r'^README.md$']),
 'vitdet':('facebookresearch/detectron2',[r'^configs/common/data/coco.*\.py$',r'^projects/ViTDet/configs/.*coco.*\.py$',r'^detectron2/modeling/meta_arch/rcnn.py$',r'^projects/ViTDet/README.md$'])}
# read: 입력 파일 또는 기록을 읽습니다.
# 입력 인수: url.
def read(url):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MV-preprocessing-evidence'}),timeout=35) as response:return response.read()
  except Exception:
   if attempt==2:raise
   time.sleep(1)
# collect: 분석에 필요한 자료와 출처를 수집합니다.
# 입력 인수: item.
def collect(item):
 name,(repo,patterns)=item;folder=BASE/name;folder.mkdir(parents=True,exist_ok=True)
 marker=folder/'manifest.json'
 if marker.exists():return json.loads(marker.read_text())
 commit=json.loads(read(f'https://api.github.com/repos/{repo}/commits/HEAD'));sha=commit['sha']
 tree=json.loads(read(f'https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1'))
 paths=[v['path'] for v in tree['tree'] if v['type']=='blob' and any(re.search(p,v['path']) for p in patterns)]
 (folder/'tree_paths.json').write_text(json.dumps([v['path'] for v in tree['tree'] if v['type']=='blob'],indent=2))
 files=[]
 for path in paths:
  data=read(f'https://raw.githubusercontent.com/{repo}/{sha}/{path}')
  if len(data)>1500000:raise ValueError('Unexpected large source file')
  data.decode('utf-8');destination=folder/'source'/path;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
  files.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),url=f'https://github.com/{repo}/blob/{sha}/{path}'))
 result=dict(repo=repo,commit=sha,commit_date=commit['commit']['committer']['date'],files=files,source_only=True,weights_downloaded=False)
 marker.write_text(json.dumps(result,indent=2));print(name,sha,len(files),flush=True);return result
if __name__=='__main__':
 BASE.mkdir(parents=True,exist_ok=True)
 with cf.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(collect,REPOS.items()))
 (BASE/'manifest.json').write_text(json.dumps(results,indent=2))
