# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Derive augmentation review statistics exclusively from train, reusing measured values."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import pandas as pd
from mv_analysis.stages import brightness
from mv_analysis.core import save_json
cv2.setNumThreads(1)
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--quality-manifest',type=Path);args=p.parse_args();out=args.run;run=json.loads((out/'run.json').read_text());b=pd.read_csv(out/'brightness_per_image.csv',keep_default_na=False);train=b[b.split=='train']
if args.quality_manifest:
 review=pd.read_csv(args.quality_manifest,keep_default_na=False);allowed=set(review.loc[review.recommended_image_training_include,'image_path']);train=train[train.image_path.isin(allowed)]
target=out/('train_brightness_policy_quality_aware' if args.quality_manifest else 'train_brightness_policy');target.mkdir(exist_ok=True)
eligible=set(train.image_path)
checkpoint=target/'brightness_per_image.jsonl'
if not checkpoint.exists():
 with (out/'brightness_per_image.jsonl').open() as source,checkpoint.open('w') as dest:
  for line in source:
   row=json.loads(line)
   if row['image_path'] in eligible:dest.write(line)
# Existing successful train rows are reused; no JPG/PNG is decoded again.
brightness(Path(run['config']['root']),target,train,policy=None)
result=pd.read_csv(target/'brightness_per_image.csv');assert result.split.eq('train').all() and len(result)==len(train)
comparisons=pd.read_csv(target/'brightness_comparison.csv');verified=comparisons[comparisons.defect_type!='UNRESOLVED'].copy();verified['abs_d']=verified.cohens_d.abs();verified.sort_values('abs_d',ascending=False).head(40).to_csv(target/'brightness_review_candidates_verified.csv',index=False)
train[train.status=='OK'].groupby(['category','view']).brightness.quantile([.05,.5,.95]).unstack().to_csv(target/'normal_only_train_augmentation_stats.csv')
save_json(target/'scope.json',dict(source_run=str(out),train_images=len(train),normal_train_images=int((train.status=='OK').sum()),all_splits=result.split.unique().tolist(),new_image_decodes=0,statistics_scope='train only; unresolved defect groups excluded from verified review candidates',anomaly_protocol='For normal-only AD use normal_only_train_augmentation_stats.csv, not NG statistics'))
print(f'Train-only policy statistics completed: {len(train)} measured images reused')
