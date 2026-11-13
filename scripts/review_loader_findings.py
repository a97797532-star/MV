# 한글 안내: 마스크 손실이 발견된 검수 대상만 표시하고 기존 전체 승인 이력에 재검수 결과를 연결합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Re-review only the 43 saved-crop mask losses; preserve full append-only history."""
import argparse,json
from pathlib import Path
from review_crop_ranges import CropReviewStore,make_crop_server,BASE,ROOT

# FindingsStore: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
class FindingsStore:
 # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
 # 입력 인수: store, selection.
 def __init__(self,store,selection):
  self.store=store;self.selection=selection;self.indices=selection['indices'];self.rows=[store.rows[i] for i in self.indices]
 # row: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: index.
 def row(self,index):
  if not 0<=index<len(self.indices):raise ValueError('Review index out of range')
  return self.store.row(self.indices[index])
 # snapshot: 저장 이력에서 현재 상태를 읽어 구성합니다.
 def snapshot(self):return self.store.snapshot()
 # progress: 현재 처리 또는 검수 진행 건수를 집계합니다.
 # 입력 인수: states.
 def progress(self,states):
  counts=dict(PROPOSAL=0,PENDING=0,REJECTED=0,APPROVED_CROP=0)
  for i,r in zip(self.indices,self.rows):
   event=states.get(r['image_path']);changed=self.store.revision(event)!=self.selection['initial_revisions'][str(i)]
   counts[event['status'] if changed and event else 'PROPOSAL']+=1
  return dict(total=len(self.rows),verified=counts['APPROVED_CROP'],remaining=len(self.rows)-counts['APPROVED_CROP'],states=counts)
 # item: 해당 검수 항목의 상태와 표시 정보를 준비합니다.
 # 입력 인수: index.
 def item(self,index):
  self.row(index);r=self.store.item(self.indices[index]);r['total']=len(self.rows);r['progress']=self.progress(self.snapshot());r['review_reasons']='SAVED_CROP_MASK_PIXEL_LOSS: 기존 승인 Crop에서 양성 마스크 픽셀 손실 확인. 범위를 넓혀 재점검하세요.';return r
 # image: 해당 항목의 원본 이미지 응답을 처리합니다.
 # 입력 인수: index, token.
 def image(self,index,token):self.row(index);return self.store.image(self.indices[index],token)
 # mask_overlay: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: index.
 def mask_overlay(self,index):self.row(index);return self.store.mask_overlay(self.indices[index])
 # mapped: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
 # 입력 인수: payload.
 def mapped(self,payload):
  p=dict(payload);self.row(int(p['index']));p['index']=self.indices[int(p['index'])];return p
 # preview: 저장 전에 후보 범위의 검증 결과를 계산합니다.
 # 입력 인수: payload.
 def preview(self,payload):return self.store.preview(self.mapped(payload))
 # approve: 검수 조건을 확인하고 승인 요청을 처리합니다.
 # 입력 인수: payload.
 def approve(self,payload):
  result=self.store.approve(self.mapped(payload));result['progress']=self.progress(self.snapshot());return result
 # export: 확인된 결과를 별도 산출물로 내보냅니다.
 def export(self):return self.store.export()

# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8771);p.add_argument('--check',action='store_true');args=p.parse_args()
 selection=json.loads((ROOT/'outputs/data_loader_validation_v1/correction_review_set.json').read_text());store=FindingsStore(CropReviewStore(BASE/'manual_crop_review.csv',ROOT/'dataset',BASE/'preprocessing_metadata.csv'),selection)
 if args.check:
  states=store.snapshot();print(json.dumps(store.progress(states)));first=store.item(0);print(json.dumps(dict(case_id=first['case_id'],total=first['total'],image_available=True)));return
 server=make_crop_server(store,args.port)
 # next_pending must include previous approvals awaiting correction; ordinary next/prev remain 0..42.
 handler=server.RequestHandlerClass;original=handler.do_GET
 # get: 요청한 항목이나 설정을 조회합니다.
 def get(self):
  if self.path.startswith('/next_pending/'):
   try:
    i=int(self.path.split('/')[-1]);states=store.snapshot();order=list(range(i+1,len(store.rows)))+list(range(i+1));pending=next((j for j in order if store.store.revision(states.get(store.rows[j]['image_path']))==selection['initial_revisions'][str(store.indices[j])] or states.get(store.rows[j]['image_path'],{}).get('status')!='APPROVED_CROP'),None);self.send(200,dict(index=pending))
   except Exception as exc:self.send(400,dict(error=str(exc)))
  else:original(self)
 handler.do_GET=get
 print(f'Crop loss correction (43 images): http://127.0.0.1:{server.server_port}',flush=True)
 try:server.serve_forever()
 finally:server.server_close()
if __name__=='__main__':main()
