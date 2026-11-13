# 한글 안내: 합성·임시 자료로 해당 기능의 계약과 오류 처리를 검사하는 테스트입니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Strict serialization and real loopback HTTP; approvals only in pytest tmp_path."""
import importlib.util,json,threading,urllib.request,urllib.error,logging
from pathlib import Path
import numpy as np,pandas as pd,pytest
from PIL import Image
s=importlib.util.spec_from_file_location('review_http',Path(__file__).parents[1]/'scripts/review_product_bboxes.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

# strict: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: data.
def strict(data):return json.loads(data,parse_constant=m.reject_constant)

# test_missing_nonfinite_scalars_are_json_null: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: value.
@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),np.float32('nan'),np.float64('inf'),pd.NA,pd.NaT,np.datetime64('NaT')])
def test_missing_nonfinite_scalars_are_json_null(value):assert strict(m.json_bytes({'v':value}))=={'v':None}

# test_numpy_scalars_nested_and_existing_types: 정상·오류 상황을 검증하는 회귀 테스트입니다.
def test_numpy_scalars_nested_and_existing_types():
 value={'i':np.int64(7),'f':np.float32(1.5),'b':np.bool_(True),'s':'[1, 2, 3, 4]','a':np.array([1,np.nan]),'nested':(pd.NA,{'x':np.longdouble(2)})}
 assert strict(m.json_bytes(value))=={'i':7,'f':1.5,'b':True,'s':'[1, 2, 3, 4]','a':[1,None],'nested':[None,{'x':2.0}]}

# test_invalid_approval_coordinates: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: box.
@pytest.mark.parametrize('box',[[0,0,float('nan'),20],[0,0,float('inf'),20],[False,0,10,20],[0,0,0,20],[-1,0,20,20],[0,0,1025,20],['1',0,10,20]])
def test_invalid_approval_coordinates(box):
 with pytest.raises(ValueError):m.validated_approval(dict(case_id='tmp',image_path='tmp.jpg'),dict(human_ack=True,reviewer='tester',bbox=box))

# store: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: tmp_path.
@pytest.fixture
def store(tmp_path):
 Image.new('RGB',(1024,1024),(210,220,230)).save(tmp_path/'image.jpg')
 csv=tmp_path/'proposals.csv';pd.DataFrame([dict(case_id='tmp-only',image_path='image.jpg',product_id='synthetic/product',category='synthetic',view='C1',status='NG',proposal_bbox='[132, 244, 896, 732]',bbox_status='PROPOSAL',reviewer=np.nan)]).to_csv(csv,index=False)
 return m.ReviewStore(csv,tmp_path,tmp_path/'temporary_approvals.jsonl')

# http: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: store.
@pytest.fixture
def http(store):
 server=m.make_server(store);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 yield store,f'http://127.0.0.1:{server.server_port}'
 server.shutdown();server.server_close();thread.join(timeout=2)

# request: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: base, path, payload.
def request(base,path,payload=None):
 data=None if payload is None else json.dumps(payload,allow_nan=False).encode()
 r=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'} if data else {})
 try:response=urllib.request.urlopen(r,timeout=5)
 except urllib.error.HTTPError as e:response=e
 with response:return response.status,response.headers,response.read()

# loaded: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: store.
def loaded(store):
 item=store.item(0);store.image(0,item['image_token'])
 return dict(index=0,case_id=item['case_id'],source_sha256=item['source_sha256'],expected_revision=item['review_revision'],image_receipt=item['image_token'],image_rendered=True,human_ack=True,reviewer='synthetic-tester',bbox=[132,244,896,732])

# test_routes_strict_json_and_actual_image: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: http.
def test_routes_strict_json_and_actual_image(http):
 store,base=http
 status,_,body=request(base,'/');assert status==200 and b'<canvas' in body and b'/review.js' in body
 status,_,body=request(base,'/review.js');assert status==200 and b'image.onerror' in body
 status,_,body=request(base,'/item/0');r=strict(body);assert status==200 and r['reviewer'] is None and isinstance(r['proposal_bbox'],str) and r['progress']['verified']==0
 status,headers,data=request(base,'/image/0');assert status==200 and headers['Content-Type']=='image/jpeg' and data==store.path(store.rows[0]).read_bytes()
 assert not store.ledger.exists()

# test_invalid_routes_do_not_wrap_to_last_image: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: http, path.
@pytest.mark.parametrize('path',['/item/-1','/item/1','/image/-1','/unknown/0'])
def test_invalid_routes_do_not_wrap_to_last_image(http,path):
 _,base=http;status,_,body=request(base,path);assert status==404 and strict(body)['error']

# test_http_reject_unseen_and_nonstandard_json_without_ledger: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: http.
def test_http_reject_unseen_and_nonstandard_json_without_ledger(http):
 store,base=http;payload=loaded(store);payload.pop('image_receipt');status,_,body=request(base,'/approve',payload);assert status==400 and strict(body)['error'] and not store.ledger.exists()
 req=urllib.request.Request(base+'/approve',data=b'{"index": NaN}',headers={'Content-Type':'application/json'})
 with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
 assert e.value.code==400 and strict(e.value.read())['error'] and not store.ledger.exists()

# test_approval_idempotence_re_review_and_history_in_temporary_ledger: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: http.
def test_approval_idempotence_re_review_and_history_in_temporary_ledger(http):
 store,base=http;payload=loaded(store)
 status,_,body=request(base,'/approve',payload);assert status==200 and strict(body)['appended']
 status,_,body=request(base,'/approve',payload);assert status==200 and strict(body)['duplicate'];assert len(store.ledger.read_text().splitlines())==1
 fresh=loaded(store);fresh['bbox']=[10,20,1000,1000]
 status,_,body=request(base,'/approve',fresh);assert status==409 and not strict(body).get('appended')
 fresh['re_review_ack']=True;status,_,body=request(base,'/approve',fresh);assert status==200
 lines=store.ledger.read_text().splitlines();assert len(lines)==2 and all(strict(line)['human_ack'] is True for line in lines)
 assert store.item(0)['approved_bbox']==[10,20,1000,1000] and store.progress(store.snapshot())['verified']==1

# test_explicit_approval_prerequisites: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store, change.
@pytest.mark.parametrize('change',[{'human_ack':False},{'reviewer':''},{'reviewer':None},{'image_rendered':False},{'case_id':'wrong'},{'source_sha256':'wrong'}])
def test_explicit_approval_prerequisites(store,change):
 payload=loaded(store);payload.update(change)
 with pytest.raises(ValueError):store.approve(payload)
 assert not store.ledger.exists()

# test_loading_item_without_image_is_not_approval: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store.
def test_loading_item_without_image_is_not_approval(store):
 payload=loaded(store);item=store.item(0);payload['image_receipt']=item['image_token']
 with pytest.raises(ValueError):store.approve(payload)
 assert not store.ledger.exists()

# test_competing_review_rejected_and_no_overwrite: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store.
def test_competing_review_rejected_and_no_overwrite(store):
 a,b=loaded(store),loaded(store);store.approve(a);b['bbox']=[1,1,1000,1000];b['re_review_ack']=True
 with pytest.raises(m.ReviewError,match='Another review'):store.approve(b)
 assert len(store.ledger.read_text().splitlines())==1

# test_pending_rejected_do_not_become_gt: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store.
def test_pending_rejected_do_not_become_gt(store):
 p=loaded(store);p.update(review_state='PENDING',notes='manual review needed');store.approve(p);assert not store.ledger.exists() and store.item(0)['review_state']=='PENDING'
 p=loaded(store);p.update(review_state='REJECTED',notes='proposal incomplete');store.approve(p);assert not store.ledger.exists() and store.progress(store.snapshot())['verified']==0

# test_corrupt_existing_history_fails_closed: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store.
def test_corrupt_existing_history_fails_closed(store):
 store.ledger.write_text('{"reviewer":NaN}\n')
 with pytest.raises(m.ReviewError,match='Invalid review history'):store.item(0)
 assert store.ledger.read_text()=='{"reviewer":NaN}\n'

# test_relative_windows_separator_and_path_escape: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: store.
def test_relative_windows_separator_and_path_escape(store):
 assert store.path(dict(image_path='.\\image.jpg')).name=='image.jpg'
 for p in ['../outside.jpg','C:\\data\\image.jpg','/etc/passwd']:
  with pytest.raises(ValueError):store.path(dict(image_path=p))

# test_serialization_failure_is_logged_and_returns_strict_500: 정상·오류 상황을 검증하는 회귀 테스트입니다.
# 입력 인수: http, monkeypatch, caplog.
def test_serialization_failure_is_logged_and_returns_strict_500(http,monkeypatch,caplog):
 store,base=http;monkeypatch.setattr(store,'item',lambda _:dict(unsupported=object()))
 with caplog.at_level(logging.ERROR):status,_,body=request(base,'/item/0')
 assert status==500 and strict(body)['error'] and 'JSON serialization failed' in caplog.text
