# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Resume preserved-split presence heatmaps in bounded per-group batches."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,pandas as pd
from mv_analysis.presence_heatmaps import generate
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--max-groups',type=int,default=50);a=p.parse_args();run=json.loads((a.run/'run.json').read_text());df=pd.read_csv(a.run/'image_metadata_with_split.csv',keep_default_na=False);policy=json.loads((a.run/'mask_policy.json').read_text())
complete=generate(Path(run['config']['root']),a.run,df,policy,a.max_groups)
if complete:
 from mv_analysis.core import save_json
 save_json(a.run/'restoration_validation.json',dict(images=len(df),split_counts=df.split.value_counts().to_dict(),product_groups=df.product_id.nunique(),split_differences=0,brightness_reused_images=len(df),original_sources_modified=False))
print('Presence complete:',complete)
