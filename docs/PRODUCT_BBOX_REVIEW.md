# Real-IAD 제품 전체 BBox 검수 도구

프로젝트 루트 `~/MV`의 Ubuntu 터미널에서 실행한다. 원본 이미지·제안 CSV는 읽기 전용이며 승인 이력만 별도 JSONL에 추가한다. 자동 제안은 GT가 아니다.

## 실행과 접속

```bash
cd ~/MV
uv run --offline python scripts/review_product_bboxes.py --check
uv run --offline python scripts/review_product_bboxes.py --port 8768
```

`--check`는 600개 제안의 표준 JSON 직렬화, 원본 파일 접근, BBox 좌표와 검수 이력을 확인한다. 정상 출력은 `total: 600`, `all_items_strict_json: true`, `all_originals_accessible: true`다. 실제 사람이 승인하기 전 `verified`는 0이다.

서버 실행 후 Windows 브라우저에서 `http://127.0.0.1:8768`을 연다. 정상 실행 시 터미널에 이 주소와 항목 수가 출력된다. 서버는 `127.0.0.1`에만 바인딩한다. `Address already in use`이면 다른 포트를 사용한다. 기존 8766·8767 프로세스를 임의로 종료하지 않는다. 이미 실행 중인 Python 서버에는 코드 수정이 자동 반영되지 않는다. 본인이 실행한 기존 서버를 정상 종료·재실행하거나 새로운 포트를 사용해야 한다. 페이지가 오래된 상태면 `Ctrl+F5`로 새로 고친다.

데이터가 다른 위치에 있다면 코드 대신 다음 설정을 사용한다.

```bash
uv run --offline python scripts/review_product_bboxes.py --port 8768 --data-root /실제/Ubuntu/데이터경로
```

`--data-root` 생략 시 `REALIAD_DATA_ROOT`, 그마저 없으면 프로젝트 `dataset/`을 사용한다. 제안 CSV의 `image_path`는 데이터 루트 기준 상대 경로다. 상대 경로의 Windows 역슬래시는 정규화하되 `C:\...` 절대 경로를 임의 매핑하지 않는다. 잘못된 루트를 고친 뒤 다시 실행하며 원본 파일을 이동할 필요는 없다.

## 검수 순서

1. 원본 이미지, 이미지 번호/600, 품목, 시점, OK/NG, 제품 ID가 표시되는지 확인한다.
2. 파란 점선 자동 제안과 녹색 실선 현재 BBox를 비교한다. 마스크나 그림자만 감싸지 말고 제품 전체와 돌출 부품을 포함한다.
3. 마우스로 드래그하면 새 BBox가 생성되고 XYXY 좌표가 실시간으로 표시된다. `자동 제안 BBox 복원`은 CSV를 수정하지 않는다.
4. 검수자 이름/ID를 2자 이상 입력하고 직접 확인 체크박스를 선택한다. 이미지 로딩·Canvas 렌더링·좌표 검사가 성공하기 전에는 승인할 수 없다. 박스를 바꾸거나 다른 항목을 불러오면 직접 확인은 해제된다.
5. `승인 · 저장` 후 저장 완료 상태와 검수 진행률을 확인한다. 자동으로 다음 이미지로 넘어가지 않으므로 결과를 읽고 `다음`을 누른다.
6. 판단이 어려우면 `검수 보류`, 자동 제안이 잘못됐다면 `제안 거부`를 선택하고 이유를 적는다. 둘 다 GT가 아니며 진행률의 승인 수에 포함되지 않는다.
7. 승인된 항목을 바꾸려면 재검수 체크박스와 직접 확인을 모두 선택한다. 기존 승인은 삭제되지 않고 새 이력이 추가된다.

좌표는 원본 1024×1024 기준 `[x0,y0,x1,y1]`이며 유한한 숫자, 양수 면적, 이미지 내부 범위를 요구한다. Canvas의 CSS 종횡비를 유지해 포인터 좌표를 원본으로 환산한다. 잘못된 좌표나 이미지 실패는 화면 오류로 표시되며 승인을 차단한다.

## 오류 복구

- `JSON 파싱 실패`: 서버 응답 또는 서버 버전을 확인한다. 과거 서버는 빈 CSV 셀을 `NaN`으로 보내 브라우저가 초기화에 실패했다. 수정 서버는 `null`을 보내고 엄격한 JSON만 응답한다.
- `서버 응답이 없습니다`: Ubuntu 터미널에서 서버가 실행 중인지, 포트가 맞는지 확인하고 `다시 불러오기`를 누른다.
- `이미지 로딩 실패`: `/image/0` 응답, `--data-root`, 파일 접근 권한을 확인한다. 손상·지원되지 않는 이미지 디코딩도 별도 오류로 표시한다.
- `Another review changed this item`: 다른 창에서 검수 상태가 바뀌었다. 새로 불러온 뒤 현재 승인 BBox를 다시 확인한다.
- `Invalid review history`: 기존 이력이 손상됐거나 승인 당시 원본 해시와 다르다. 서버 로그를 확인하고 이력을 보존한 상태에서 조사한다. 도구가 임의로 기록을 삭제·무시하지 않는다.
- 요청이 오래 걸리면 시간 초과를 표시한다. 다시 불러오기나 연속 탐색의 오래된 응답은 현재 이미지에 덮어쓰지 않는다.

## 승인 이력과 중복·동시 수정

기본 승인 Ledger는 `outputs/object_aware_crop_v1/review/human_approved_gt.jsonl`이다. 일반 도구의 보류·거부는 같은 폴더의 `human_review_events.jsonl`에 기록한다. Adaptive 도구의 기존 이벤트 `outputs/adaptive_crop_gate_v1/review/review_events.jsonl`도 함께 읽어 최신 상태를 계산한다. `review_crop_gate_bboxes.py`도 같은 웹 구현을 사용하며 두 도구의 승인 이력을 공유한다.

이미지 응답을 실제로 제공한 서버 확인 토큰, 표시 완료 확인, 원본 SHA-256, 항목 ID, 검수자, 사람 확인, 유효 좌표가 있어야 승인 요청을 수락한다. 이것은 로딩 누락을 방지하는 절차이며 사람이 실제로 눈으로 봤다는 사실을 서버가 증명하지는 못한다. 사람이 직접 확인해야 한다.

동일 검수자·좌표·메모·상태의 재전송은 성공 응답과 `duplicate: true`를 반환하고 이력을 추가하지 않는다. 바뀐 승인은 명시적 재검수와 현재 revision을 요구한다. 다른 창의 오래된 revision은 HTTP409로 거부한다. 프로세스 간 파일 잠금과 append/fsync를 사용하며 기존 줄을 덮어쓰지 않는다. 최신 검수 이벤트가 현재 상태를 결정하고 과거 기록은 남는다.

## 실행한 검증

- 과거 방식은 실제 600개 행 모두에서 비표준 JSON을 생성했다. 수정 후 실제 600개 `/item/{i}` 응답이 엄격한 JSON 검사를 통과했다.
- `/`, `/review.js`, `/item/0`, `/image/0` 실제 HTTP 검증 통과. 첫 이미지 응답은 원본과 같은 JPEG 252,858바이트였다.
- 600개 원본 경로 접근과 600개 제안 BBox 좌표 검사 통과. 제안 CSV 및 실제 승인·검수 이력의 검증 전후 해시/존재 상태가 동일했다.
- 전체 pytest **73 passed**, 실패0, NumPy 테스트 매개변수 관련 deprecation warning1. 승인·중복·재검수·경합·손상 이력·잘못된 요청 검사는 임시 데이터와 임시 Ledger에서만 수행했다.
- Node 화면 모의 검사 **31개 통과**: 정보 표시, 이미지/박스 그리기 호출, 좌표 환산·드래그·복원, 승인 비활성화, JSON·이미지 오류, 오래된 응답 무시를 확인했다.
- JavaScript 구문 검사 통과. 실제 Chromium/Windows 브라우저 검증은 **UNVERIFIED**다. 이 환경에 브라우저/자동화 도구가 설치돼 있지 않아 모의 검사를 실제 브라우저 검증으로 간주하지 않았다.

```bash
uv run --offline pytest -q
node --check scripts/product_bbox_review.js
node tests/product_bbox_review_ui.cjs
```

테스트는 프로젝트 루트에서 실행한다. HTTP 테스트는 임시 포트의 로컬 소켓을 사용한다. 샌드박스가 소켓을 차단하면 `Operation not permitted`가 발생하므로 허용된 로컬 실행 환경에서 재실행해야 한다. 실패를 성공으로 간주하지 않는다.

실제 600개 API의 읽기 전용 검증 기록: `outputs/bbox_review_fix_20261112_v1/validation.json`. 재검증 스크립트 `scripts/validate_bbox_review_server.py`는 완료된 검증 디렉터리를 덮어쓰지 않으므로 다른 실행 버전을 지정하도록 경로를 바꾼 뒤 사용한다. 원본 이미지·CSV·실제 Ledger에는 쓰지 않는다.
