# 한글 안내: 제품 BBox를 사람이 검수하는 로컬 서버입니다. 명시적 승인만 Ledger에 추가합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Local-only human product BBox review, strict JSON and append-only approval history."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import math
import os
from pathlib import Path, PureWindowsPath
import secrets
import threading
from urllib.parse import urlsplit, parse_qs
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROPOSALS = ROOT / 'outputs/object_aware_crop_v1/review/product_bbox_proposals.csv'
LOG = logging.getLogger('product_bbox_review')
ASSETS = Path(__file__).parent
HTML = (ASSETS / 'product_bbox_review.html').read_text() if (ASSETS / 'product_bbox_review.html').exists() else ''


# json_safe: NaN·무한대·Pandas 결측을 null로 바꿔 브라우저가 읽을 수 있는 표준 JSON 값을 만듭니다.
# 입력 인수: value.
def json_safe(value):
    """Normalize only unsupported scalars; retain existing API strings/lists/numbers."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return json_safe(float(value))
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (str, bool, int)):
        return value
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


# json_bytes: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: value.
def json_bytes(value):
    return json.dumps(json_safe(value), ensure_ascii=False, allow_nan=False).encode('utf-8')


# reject_constant: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: value.
def reject_constant(value):
    raise ValueError(f'Non-standard JSON constant: {value}')


# bbox: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: value, width, height.
def bbox(value, width=1024, height=1024):
    if isinstance(value, str):
        value = json.loads(value, parse_constant=reject_constant)
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('Expected four XYXY coordinates')
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.number)) for v in value):
        raise ValueError('BBox coordinates must be finite numbers')
    result = [float(v) for v in value]
    if not all(math.isfinite(v) for v in result):
        raise ValueError('BBox coordinates must be finite numbers')
    x0, y0, x1, y1 = result
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('Box must have positive area inside original frame')
    return result


# validated_approval: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: proposal, payload.
def validated_approval(proposal, payload):
    if payload.get('human_ack') is not True:
        raise ValueError('Human review acknowledgement required')
    reviewer = payload.get('reviewer')
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 2:
        raise ValueError('Reviewer name/id must contain at least two characters')
    box = bbox(payload.get('bbox'), proposal.get('width', 1024), proposal.get('height', 1024))
    return dict(case_id=proposal['case_id'], image_path=proposal['image_path'], bbox=box,
                status='VERIFIED_GT', reviewer=reviewer.strip(), human_ack=True,
                reviewed_utc=datetime.now(timezone.utc).isoformat(), notes=str(payload.get('notes') or ''))


# ReviewError: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
class ReviewError(ValueError):
    # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
    # 입력 인수: message, status.
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ReviewStore: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
class ReviewStore:
    # __init__: 입력 설정과 필요한 상태를 준비합니다. 잘못된 조건은 본문의 검증 규칙을 따릅니다.
    # 입력 인수: proposals, data_root, ledger, event_ledger, extra_ledgers.
    def __init__(self, proposals, data_root, ledger=None, event_ledger=None, extra_ledgers=()):
        self.proposals = Path(proposals).resolve()
        self.data_root = Path(data_root).expanduser().resolve()
        self.rows = pd.read_csv(self.proposals).to_dict('records')
        if len({r['case_id'] for r in self.rows}) != len(self.rows):
            raise ValueError('Duplicate case IDs in proposals')
        self.ledger = Path(ledger) if ledger else self.proposals.with_name('human_approved_gt.jsonl')
        self.event_ledger = Path(event_ledger) if event_ledger else self.proposals.with_name('human_review_events.jsonl')
        self.read_ledgers = list(dict.fromkeys([self.ledger, self.event_ledger, *map(Path, extra_ledgers)]))
        self.lock = threading.RLock()
        self.receipts = {}
        self.hash_cache = {}

    # row: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: index.
    def row(self, index):
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self.rows):
            raise ReviewError('Image index out of range', 404)
        return self.rows[index]

    # path: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: row.
    def path(self, row):
        raw = str(row['image_path']).replace('\\', '/')
        # Existing metadata uses dataset-relative POSIX paths. Never guess a Windows mapping.
        if PureWindowsPath(raw).drive or Path(raw).is_absolute():
            raise ReviewError('image_path must be relative to --data-root; Windows absolute paths are not mapped implicitly')
        path = (self.data_root / raw).resolve()
        if not path.is_relative_to(self.data_root):
            raise ReviewError('Image path escapes dataset root')
        if not path.is_file():
            raise ReviewError('Source image missing under configured data root', 404)
        return path

    # source_hash: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: row.
    def source_hash(self, row):
        p = self.path(row)
        stat = p.stat()
        key = (str(p), stat.st_size, stat.st_mtime_ns)
        if key not in self.hash_cache:
            self.hash_cache[key] = hashlib.sha256(p.read_bytes()).hexdigest()
        return self.hash_cache[key]

    # write_lock: 검증한 결과를 출력 형식으로 기록합니다.
    @contextmanager
    def write_lock(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.ledger.with_suffix(self.ledger.suffix + '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    # snapshot: 저장 이력에서 현재 상태를 읽어 구성합니다.
    def snapshot(self):
        rows = {r['image_path']: r for r in self.rows}
        events = []
        for path in self.read_ledgers:
            if not path.exists():
                continue
            for n, line in enumerate(path.read_text().splitlines(), 1):
                try:
                    event = json.loads(line, parse_constant=reject_constant)
                    if event.get('image_path') not in rows:
                        continue
                    r = rows[event['image_path']]
                    if event.get('case_id') != r['case_id']:
                        raise ValueError('Case ID mismatch')
                    if event.get('status') == 'VERIFIED_GT':
                        validated_approval(r, event)
                        if event.get('source_sha256') != self.source_hash(r):
                            raise ValueError('Approval source image hash mismatch')
                    elif event.get('status') not in ['PENDING', 'REJECTED']:
                        raise ValueError('Unknown review state')
                    events.append(event)
                except Exception as exc:
                    LOG.error('Invalid existing review record %s:%d: %s', path, n, exc)
                    # Fail closed instead of treating corrupt history as an unreviewed image.
                    raise ReviewError('Invalid review history; inspect server log; approval disabled', 409) from exc
        states = {}
        for e in sorted(events, key=lambda e: e.get('reviewed_utc', '')):
            states[e['image_path']] = e
        return states

    # progress: 현재 처리 또는 검수 진행 건수를 집계합니다.
    # 입력 인수: states.
    def progress(self, states):
        counts = {k: 0 for k in ['PROPOSAL', 'PENDING', 'REJECTED', 'VERIFIED_GT']}
        for r in self.rows:
            counts[states.get(r['image_path'], {}).get('status', 'PROPOSAL')] += 1
        return dict(total=len(self.rows), verified=counts['VERIFIED_GT'], remaining=len(self.rows)-counts['VERIFIED_GT'], states=counts)

    # revision: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: event.
    @staticmethod
    def revision(event):
        return hashlib.sha256(json_bytes(event)).hexdigest() if event else '0'

    # item: 해당 검수 항목의 상태와 표시 정보를 준비합니다.
    # 입력 인수: index.
    def item(self, index):
        row = self.row(index)
        states = self.snapshot()
        event = states.get(row['image_path'])
        digest = self.source_hash(row)
        token = secrets.token_urlsafe(24)
        with self.lock:
            # Keep a bounded set of recent display receipts, without writing approval data.
            if len(self.receipts) >= 2048:
                for key in list(self.receipts)[:1024]:
                    del self.receipts[key]
            self.receipts[token] = dict(index=index, case_id=row['case_id'], source_hash=digest,
                                        revision=self.revision(event), served=False)
        return row | dict(total=len(self.rows), review_state=event['status'] if event else 'PROPOSAL',
                          approved_bbox=event['bbox'] if event and event['status']=='VERIFIED_GT' else None,
                          review_revision=self.revision(event), reviewed_by=event.get('reviewer') if event else None,
                          image_token=token, source_sha256=digest, progress=self.progress(states))

    # image: 해당 항목의 원본 이미지 응답을 처리합니다.
    # 입력 인수: index, token.
    def image(self, index, token=None):
        row = self.row(index)
        data = self.path(row).read_bytes()
        # An existing file is insufficient: verify actual decoding before permitting approval.
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            if im.size != (1024, 1024):
                raise ReviewError('Expected original1024x1024 image')
        digest = hashlib.sha256(data).hexdigest()
        if token:
            with self.lock:
                receipt = self.receipts.get(token)
                if not receipt or receipt['index'] != index or receipt['source_hash'] != digest:
                    raise ReviewError('Image receipt is stale; reload the image', 409)
                receipt['served'] = True
        return data

    # approve: 검수 조건을 확인하고 승인 요청을 처리합니다.
    # 입력 인수: payload.
    def approve(self, payload):
        index = payload.get('index')
        row = self.row(index)
        state = payload.get('review_state', 'VERIFIED_GT')
        if state == 'VERIFIED_GT':
            record = validated_approval(row, payload)
        elif state in ['PENDING', 'REJECTED']:
            reviewer = payload.get('reviewer')
            if not isinstance(reviewer, str) or len(reviewer.strip()) < 2 or not str(payload.get('notes') or '').strip():
                raise ReviewError('Reviewer and reason required for pending/rejected state')
            record = dict(case_id=row['case_id'], image_path=row['image_path'], status=state,
                          reviewer=reviewer.strip(), notes=str(payload['notes']), human_ack=False,
                          reviewed_utc=datetime.now(timezone.utc).isoformat())
        else:
            raise ReviewError('Unknown review state')
        with self.write_lock():
            token = payload.get('image_receipt')
            receipt = self.receipts.get(token) if isinstance(token, str) else None
            if not receipt or not receipt['served'] or receipt['index'] != index or payload.get('image_rendered') is not True:
                raise ReviewError('A successfully loaded and rendered image is required')
            digest = self.source_hash(row)
            if payload.get('case_id') != row['case_id'] or receipt['source_hash'] != digest or payload.get('source_sha256') != digest:
                raise ReviewError('Image identity changed; reload before review', 409)
            states = self.snapshot()
            previous = states.get(row['image_path'])
            if previous and previous['status']==state and previous['reviewer']==record['reviewer'] and previous.get('bbox')==record.get('bbox') and previous.get('notes','')==record.get('notes',''):
                return dict(saved=row['case_id'], status=state, duplicate=True, appended=False,
                            review_revision=self.revision(previous), progress=self.progress(states))
            if payload.get('expected_revision') != self.revision(previous) or receipt['revision'] != self.revision(previous):
                raise ReviewError('Another review changed this item; reload before saving', 409)
            if previous and previous['status']=='VERIFIED_GT' and payload.get('re_review_ack') is not True:
                raise ReviewError('Explicit re-review acknowledgement required; existing approval will be preserved', 409)
            record.update(source_sha256=digest, previous_revision=self.revision(previous))
            target = self.ledger if state=='VERIFIED_GT' else self.event_ledger
            target.parent.mkdir(parents=True, exist_ok=True)
            encoded = json_bytes(record).decode()
            with target.open('a') as stream:
                stream.write(encoded+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            states[row['image_path']] = record
            return dict(saved=row['case_id'], status=state, duplicate=False, appended=True,
                        review_revision=self.revision(record), progress=self.progress(states))


# make_server: 후속 처리가 사용할 객체나 결과를 생성합니다.
# 입력 인수: store, port.
def make_server(store, port=0):
    # Handler: 관련 입력과 상태를 묶어 관리하는 구성 요소입니다.
    class Handler(BaseHTTPRequestHandler):
        # send: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
        # 입력 인수: status, content, kind, headers.
        def send(self, status, content, kind='application/json; charset=utf-8', headers=None):
            try:
                data = content if isinstance(content, bytes) else json_bytes(content)
            except Exception:
                LOG.exception('JSON serialization failed for %s', self.path)
                status, kind = 500, 'application/json; charset=utf-8'
                data = json_bytes(dict(error='JSON serialization failed; inspect server log'))
            self.send_response(status)
            for name, value in {'Content-Type':kind, 'Content-Length':str(len(data)), 'Cache-Control':'no-store',
                                'X-Content-Type-Options':'nosniff', **(headers or {})}.items():
                self.send_header(name,value)
            self.end_headers()
            self.wfile.write(data)

        # do_GET: 로컬 HTTP 요청을 검증하고 해당 응답 경로로 전달합니다.
        def do_GET(self):
            try:
                url = urlsplit(self.path)
                if url.path=='/':
                    self.send(200, HTML.encode(), 'text/html; charset=utf-8');return
                if url.path=='/review.js':
                    self.send(200,(ASSETS/'product_bbox_review.js').read_bytes(),'text/javascript; charset=utf-8');return
                if url.path=='/progress':
                    self.send(200,store.progress(store.snapshot()));return
                parts=url.path.strip('/').split('/')
                if len(parts)!=2 or parts[0] not in ['item','image']:
                    raise ReviewError('Not found',404)
                index=int(parts[1]);store.row(index)
                if parts[0]=='item':self.send(200,store.item(index))
                else:
                    token=parse_qs(url.query).get('token',[None])[0]
                    data=store.image(index,token)
                    self.send(200,data,'image/jpeg',{'X-Review-Receipt':token or ''})
            except ReviewError as exc:self.send(exc.status,dict(error=str(exc)))
            except Exception as exc:
                LOG.exception('GET failed: %s',self.path)
                self.send(400,dict(error=str(exc)))

        # do_POST: 로컬 HTTP 요청을 검증하고 해당 응답 경로로 전달합니다.
        def do_POST(self):
            try:
                if self.path!='/approve':raise ReviewError('Not found',404)
                # Same-origin local UI only; reject cross-site HTML form/JSON submissions.
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ReviewError('application/json required',415)
                origin=self.headers.get('Origin')
                if origin and origin!=f'http://{self.headers.get("Host")}':raise ReviewError('Cross-origin request rejected',403)
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=10000:raise ReviewError('Invalid payload size')
                payload=json.loads(self.rfile.read(n),parse_constant=reject_constant)
                if not isinstance(payload,dict):raise ReviewError('Expected JSON object')
                self.send(200,store.approve(payload))
            except ReviewError as exc:self.send(exc.status,dict(error=str(exc)))
            except Exception as exc:
                LOG.exception('POST validation/storage failed: %s',self.path)
                self.send(400,dict(error=str(exc)))
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--proposals',type=Path,default=DEFAULT_PROPOSALS)
    p.add_argument('--data-root',type=Path,default=Path(os.getenv('REALIAD_DATA_ROOT',str(ROOT/'dataset'))))
    p.add_argument('--ledger',type=Path)
    p.add_argument('--events-ledger',type=Path)
    p.add_argument('--port',type=int,default=8766)
    p.add_argument('--check',action='store_true')
    a=p.parse_args();logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    extras=[]
    if a.proposals.resolve()==DEFAULT_PROPOSALS:
        extras=[ROOT/'outputs/adaptive_crop_gate_v1/review/review_events.jsonl']
    store=ReviewStore(a.proposals,a.data_root,a.ledger,a.events_ledger,extras)
    if a.check:
        for row in store.rows:
            json_bytes(row);store.path(row);bbox(row['proposal_bbox'])
        print(json_bytes(store.progress(store.snapshot())|dict(all_originals_accessible=True,all_proposals_valid=True,all_items_strict_json=True)).decode());return
    server=make_server(store,a.port)
    print(f'Internal human review only: http://127.0.0.1:{server.server_port} / {len(store.rows)} items. No automatic GT.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
