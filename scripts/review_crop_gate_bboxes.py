# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Append-only human review states for existing product proposals; never auto-approve."""
import sys,json,argparse,hashlib,threading
from pathlib import Path
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parent))
from review_product_bboxes import validated_approval,HTML
import pandas as pd
BASE=Path('outputs/adaptive_crop_gate_v1/review')
PROPOSALS=Path('outputs/object_aware_crop_v1/review/product_bbox_proposals.csv')
OLD=PROPOSALS.with_name('human_approved_gt.jsonl')

# review_event: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: proposal, payload.
def review_event(proposal,payload):
 state=payload.get('review_state')
 if state=='VERIFIED_GT':return validated_approval(proposal,payload)
 if state not in ['PENDING','REJECTED']:raise ValueError('Expected PENDING, REJECTED or VERIFIED_GT')
 if len(str(payload.get('reviewer','')).strip())<2:raise ValueError('Reviewer required')
 if not str(payload.get('notes','')).strip():raise ValueError('Reason required for pending/rejected state')
 return dict(case_id=proposal['case_id'],image_path=proposal['image_path'],status=state,reviewer=payload['reviewer'],notes=payload['notes'],reviewed_utc=datetime.now(timezone.utc).isoformat(),human_ack=False)

# effective_states: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: rows.
def effective_states(rows):
 from review_product_bboxes import ReviewStore,ROOT
 store=ReviewStore(ROOT/PROPOSALS,ROOT/'dataset',ROOT/OLD,ROOT/BASE/'review_events.jsonl',extra_ledgers=[ROOT/OLD.with_name('human_review_events.jsonl')])
 events=store.snapshot()
 return {r['image_path']:dict(r,review_state=events[r['image_path']]['status'],review_event=events[r['image_path']]) if r['image_path'] in events else dict(r,review_state='PROPOSAL') for r in rows}

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 from review_product_bboxes import ReviewStore,make_server,json_bytes,ROOT
 import logging,os
 a=argparse.ArgumentParser();a.add_argument('--check',action='store_true');a.add_argument('--port',type=int,default=8767);a.add_argument('--data-root',type=Path,default=Path(os.getenv('REALIAD_DATA_ROOT',str(ROOT/'dataset'))));args=a.parse_args()
 logging.basicConfig(level=logging.INFO)
 store=ReviewStore(ROOT/PROPOSALS,args.data_root,ROOT/OLD,ROOT/BASE/'review_events.jsonl',extra_ledgers=[ROOT/OLD.with_name('human_review_events.jsonl')])
 if args.check:
  print(json_bytes(store.progress(store.snapshot())|dict(proposals=len(store.rows),unreviewed_are_not_gt=True)).decode());return
 server=make_server(store,args.port)
 print(f'Internal human review only: http://127.0.0.1:{server.server_port}',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
