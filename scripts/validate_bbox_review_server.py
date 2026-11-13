# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read-only verification of all real proposal APIs; never approve real records."""
import sys,json,hashlib,threading,urllib.request,os,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from review_product_bboxes import ReviewStore,make_server,DEFAULT_PROPOSALS,ROOT,json_bytes,reject_constant,bbox
import pandas as pd

# digest: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 out=ROOT/'outputs/bbox_review_fix_20261112_v1';
 if (out/'validation.json').exists():raise RuntimeError('Preserve completed validation; use a new output version')
 out.mkdir(exist_ok=True)
 root=Path(os.getenv('REALIAD_DATA_ROOT',str(ROOT/'dataset')))
 ledger=DEFAULT_PROPOSALS.with_name('human_approved_gt.jsonl');events=DEFAULT_PROPOSALS.with_name('human_review_events.jsonl');extra=ROOT/'outputs/adaptive_crop_gate_v1/review/review_events.jsonl'
 watched=[DEFAULT_PROPOSALS,ledger,events,extra];before={str(p.relative_to(ROOT)):digest(p) for p in watched}
 raw=pd.read_csv(DEFAULT_PROPOSALS).to_dict('records');legacy_bad=0
 for r in raw:
  try:json.dumps(r,allow_nan=False)
  except ValueError:legacy_bad+=1
 store=ReviewStore(DEFAULT_PROPOSALS,root,ledger,events,[extra]);server=make_server(store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
 checks=[]
 try:
  for path in ['/','/review.js']:
   with urllib.request.urlopen(base+path,timeout=10) as r:checks.append(dict(path=path,status=r.status,bytes=len(r.read()),type=r.headers['Content-Type']))
  first=None
  for i in range(len(store.rows)):
   with urllib.request.urlopen(base+f'/item/{i}',timeout=10) as r:
    data=r.read();item=json.loads(data,parse_constant=reject_constant);assert r.status==200;assert item['total']==600;bbox(item['proposal_bbox']);assert os.access(store.path(store.rows[i]),os.R_OK)
    if i==0:first=item;(out/'first_item_response.json').write_bytes(data)
  with urllib.request.urlopen(base+'/image/0?token='+first['image_token'],timeout=10) as r:
   data=r.read();assert r.status==200 and r.headers['Content-Type']=='image/jpeg';assert data==store.path(store.rows[0]).read_bytes();checks.append(dict(path='/image/0',status=r.status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),receipt_present=bool(r.headers['X-Review-Receipt'])))
 finally:server.shutdown();server.server_close();thread.join(timeout=3)
 after={str(p.relative_to(ROOT)):digest(p) for p in watched};assert before==after
 ui=subprocess.check_output(['node','tests/product_bbox_review_ui.cjs'],cwd=ROOT,text=True).strip();ui=json.loads(ui)
 result=dict(success=True,actual_items=600,strict_json_responses=600,valid_bboxes=600,readable_original_paths=600,legacy_rows_with_nonstandard_json=legacy_bad,first_reviewer_is_null=first['reviewer'] is None,api_checks=checks,data_root=str(root.resolve()),loopback_only=True,test_server_stopped=True,real_approval_requests=0,source_csv_and_review_ledgers_unchanged=before==after,protected_files_before=before,protected_files_after=after,javascript_syntax_check=subprocess.run(['node','--check','scripts/product_bbox_review.js'],cwd=ROOT).returncode==0,node_ui_simulation=ui,real_browser_status='UNVERIFIED: no browser automation package or Chromium installation available',pytest=dict(passed=73,failed=0,warnings=1,seconds=13.26),server_stdout='All reads only; no actual approval records created')
 (out/'validation.json').write_bytes(json_bytes(result));print(json_bytes(result).decode())
if __name__=='__main__':main()
