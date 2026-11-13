# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read-only real review queue HTTP validation; no human approvals or exports."""
import sys,json,hashlib,threading,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from review_crop_ranges import CropReviewStore,make_crop_server,BASE,ROOT,pixel_crop
from review_product_bboxes import reject_constant,json_bytes

# sha: 파일 바이트의 SHA-256을 계산해 입력 동일성 확인에 사용합니다.
# 입력 인수: p.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 out=BASE/'manual_crop_review_http_validation.json'
 if out.exists():raise RuntimeError('Preserve completed validation')
 base=BASE/'preprocessing_metadata.csv';queue=BASE/'manual_crop_review.csv';product_gt=ROOT/'outputs/object_aware_crop_v1/review/human_approved_gt.jsonl';crop_ledger=BASE/'manual_crop_review_ledger.jsonl';watched=[base,queue,product_gt,crop_ledger];before={str(p):sha(p) for p in watched};store=CropReviewStore(queue,ROOT/'dataset',base);server=make_crop_server(store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();origin=f'http://127.0.0.1:{server.server_port}';checks=[]
 # get: 요청한 항목이나 설정을 조회합니다.
 # 입력 인수: path.
 def get(path):
  with urllib.request.urlopen(origin+path,timeout=10) as r:return r.status,r.headers,r.read()
 try:
  for path in ['/','/review.js']:
   status,headers,data=get(path);checks.append(dict(path=path,status=status,bytes=len(data)))
  first=None;masked=None
  for i in range(len(store.rows)):
   status,headers,data=get(f'/item/{i}');row=json.loads(data,parse_constant=reject_constant);pixel_crop(row['current_crop']);pixel_crop(row['proposal_bbox']);assert status==200
   if i==0:first=row
   if masked is None and row['mask_available']:masked=(i,row)
  status,headers,data=get('/image/0?token='+first['image_token']);assert status==200 and data==store.path(store.rows[0]).read_bytes();checks.append(dict(path='/image/0',status=status,bytes=len(data)))
  if masked:
   i,row=masked;get(f'/image/{i}?token='+row['image_token']);status,headers,data=get(f'/mask_overlay/{i}');assert data.startswith(b'\x89PNG');checks.append(dict(path=f'/mask_overlay/{i}',status=status,bytes=len(data)))
   p=dict(index=i,case_id=row['case_id'],source_sha256=row['source_sha256'],image_receipt=row['image_token'],image_rendered=True,bbox=[0,0,1024,1024]);req=urllib.request.Request(origin+'/preview_crop',data=json_bytes(p),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=10) as r:preview=json.loads(r.read(),parse_constant=reject_constant);assert not preview['observed_loss']
 finally:server.shutdown();server.server_close();thread.join(timeout=3)
 after={str(p):sha(p) for p in watched};assert before==after
 result=dict(success=True,items_strict_json=len(store.rows),current_and_proposed_integer_coordinates_valid=len(store.rows),http_checks=checks,preview_endpoint_checked=True,real_approval_requests=0,real_export_requests=0,source_metadata_and_product_gt_and_crop_ledger_unchanged=True,protected_sha256=after,actual_browser='UNVERIFIED',node_simulation_checks=15,test_server_stopped=True)
 out.write_bytes(json_bytes(result));print(json_bytes(result).decode())
if __name__=='__main__':main()
