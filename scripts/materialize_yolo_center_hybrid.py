# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Create lossless native hybrid crops from cached coordinates, no YOLO invocation."""
import json,hashlib
from pathlib import Path
import cv2,numpy as np,pandas as pd
B=Path('outputs/yolo11_dynamic_crop_v1');H=B/'hybrid_extension';cv2.setNumThreads(1)
# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 out=B/'native_crops/hybrid896_fullfallback';out.mkdir(parents=True,exist_ok=True)
 manifest=H/'native_dataset_checkpoint.jsonl';done={}
 if manifest.exists():
  for line in manifest.read_text().splitlines():
   row=json.loads(line);done[row['image_path']]=row
 sample=pd.read_csv(B/'sample_manifest.csv').set_index('image_path');before=sha(B/'inference_checkpoint.jsonl')
 coords=[json.loads(v) for v in (H/'crop_coordinates.jsonl').read_text().splitlines()];coords=[r for r in coords if r['method']=='hybrid896_fullfallback']
 with manifest.open('a') as stream:
  for r in coords:
   if r['image_path'] in done:continue
   row=sample.loc[r['image_path']];source=Path('dataset')/r['image_path'];crop=r['crop'];record=dict(image_path=r['image_path'],case_id=r['case_id'],cohort=row.cohort,classification_status=row.status,has_mask=bool(row.has_mask),crop_xyxy=crop,resize_applied=False,normalize_applied=False,product_containment='UNVERIFIED',posthoc=True)
   if crop==[0,0,1024,1024]:
    record.update(storage='original_reference',image_file=str(source))
    if row.has_mask:record.update(mask_file=str(Path('dataset')/row.mask_path),mask_encoding='original grayscale; foreground >0')
   else:
    x0,y0,x1,y1=crop;image=cv2.imread(str(source));cropimage=image[y0:y1,x0:x1];dest=out/(r['case_id']+'.png')
    if not dest.exists():assert cv2.imwrite(str(dest),cropimage,[cv2.IMWRITE_PNG_COMPRESSION,3])
    assert np.array_equal(cv2.imread(str(dest)),cropimage)
    record.update(storage='lossless_native_crop_png',image_file=str(dest),image_sha256=sha(dest))
    if row.has_mask:
     mask=cv2.imread(str(Path('dataset')/row.mask_path),0);mask=((mask[y0:y1,x0:x1]>0)*255).astype(np.uint8);dest=out/(r['case_id']+'_mask.png')
     if not dest.exists():assert cv2.imwrite(str(dest),mask)
     assert np.array_equal(cv2.imread(str(dest),0),mask);record.update(mask_file=str(dest),mask_encoding='binary uint8 >0 foreground')
   stream.write(json.dumps(record)+'\n');stream.flush();done[r['image_path']]=record
 pd.DataFrame(done.values()).to_csv(H/'offline_native_dataset_manifest.csv',index=False)
 evidence=dict(success=len(done)==1350 and sha(B/'inference_checkpoint.jsonl')==before,images=len(done),native_crops=sum(r['storage']=='lossless_native_crop_png' for r in done.values()),original_references=sum(r['storage']=='original_reference' for r in done.values()),additional_yolo_calls=0,resize_applied=False,normalize_applied=False)
 p=H/'native_dataset_validation.json'
 if p.exists():raise SystemExit('Preserve validation')
 p.write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))
if __name__=='__main__':main()
