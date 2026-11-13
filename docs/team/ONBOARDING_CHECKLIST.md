# 팀원 최초 설치 및 데이터 로더 체크리스트

현재 구현 범위는 [진행 상태](PROJECT_STATUS.md)를 먼저 읽는다. 아래 명령은 개인 Fork를 Clone한 **WSL2 Ubuntu MV 루트**에서 실행한다. clone·Git 작성자·origin/upstream 설정은 [Fork 가이드](GITHUB_FORK_WORKFLOW.md)를 따른다. 팀원 4명의 실제 설치 성공은 각자가 결과를 남긴 뒤에만 인정한다.

## 설치 순서

uv가 없다면 [Ubuntu 설치 문서](../INSTALL_LINUX.md)의 공식 설치 스크립트 검토 절차를 따른다. [공식 uv 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)도 참고한다. 시스템 Python이나 다른 팀원의 lock을 임의로 교체하지 않는다.

```bash
uv --version
uv python install 3.12
uv sync --locked
uv run --locked python --version
uv run --locked python scripts/validate_environment.py --dummy
uv run --locked pytest -q
```

| 명령 | 목적/변경 | 성공 확인 | 실패 확인 |
|---|---|---|---|
| uv --version | uv 설치 확인 | 버전 출력 | PATH/터미널 재시작 |
| uv python install 3.12 | 3.12 런타임 확보, 이미 있으면 재사용 | 설치 또는 이미 설치 메시지 | 네트워크/디스크, lock 삭제 금지 |
| uv sync --locked | pyproject/uv.lock 그대로 .venv 구축 | 설치/Checked 후 종료 0 | 전체 오류 보존, DNS·wheel·플랫폼·디스크 구분 |
| uv run --locked python --version | 프로젝트 Python 확인 | Python 3.12.x | 다른 VIRTUAL_ENV/프로젝트 위치 확인 |
| validate_environment --dummy | CPU PyTorch/OpenCV/import 확인, 새 결과 디렉터리 생성 | JSON failed=[] | 해당 import/버전 오류를 기록 |
| pytest -q | 합성 데이터와 회귀 테스트 | passed 및 종료 0 | 실패 파일/로그 전달, 임의 skip 금지 |

`uv run pytest`도 프로젝트 pytest를 실행하지만 재현 문서에서는 lock 변경 방지를 위해 `--locked`를 붙인다. `bash scripts/setup.sh`는 Python 탐색→잠금 설치→더미 검증→pytest를 수행하는 기존 대안이다. Python이 없으면 위 install을 먼저 한다. 오프라인 캐시가 준비돼 있으면 `uv run --offline ...`을 쓸 수 있으나 새 팀원의 cold install 성공을 보장하지 않는다.

## 데이터 준비 및 Canonical 파일 수령

```bash
export REALIAD_DATA_ROOT="/본인/Real-IAD/루트"
test -d "$REALIAD_DATA_ROOT"
uv run --locked python -m mv_analysis.cli --data-root "$REALIAD_DATA_ROOT" --split-policy windows-project-v1 validate-data
```

export는 현재 터미널의 데이터 위치만 지정한다. test는 존재 확인이며 성공 시 출력이 없다. CLI는 새 outputs 실행에 파일 구조/매핑 검사를 기록한다. 이미지 디코딩 전수 성공과 혼동하지 않는다. 실패하면 데이터 루트 바로 아래 품목 폴더인지, 권한·복사 완료·경로 철자가 맞는지 확인한다. **이 마지막 전체 CLI 명령은 이번 문서 작업에서 재실행하지 않았다.** 환경변수만 설정해도 누락된 Canonical 테이블이 자동 배포되지는 않는다.

관리자가 접근 제한 팀 채널로 승인된 파일 목록·SHA-256·정책 버전·검증 상태를 전달해야 한다. [관리자 배포 절차](MAINTAINER_GUIDE.md)를 따른다. 수령 대상:

- 승인된 Crop Manifest: 현재 갱신 파일 `outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv`(v2 검증 범위는 진행 상태 문서 참조).
- 클래스 파생 테이블: `outputs/filename_class_resolution_v1/image_metadata_with_split.csv`, `defect_bboxes.csv`.
- 클래스 매핑: `outputs/spatial_20261111_v7/classes.json`.
- 원본 JPG/PNG는 팀원의 적법한 로컬 사본으로 준비한다. 원본은 Git으로 배포하지 않는다.

CSV 이름이 최신이라는 이유만으로 선택하지 말고 관리자 해시와 대조한다. 각 팀원은 받은 파일의 실제 위치를 아래 경로 변수로 지정한다. 원본 CSV에 적힌 다른 PC의 절대 경로를 편집하지 않는다.

```bash
sha256sum outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv
```

MV 루트에서 파일을 읽어 SHA를 표시하는 명령이며 파일을 바꾸지 않는다. 관리자 전달값과 같아야 한다. 파일이 없으면 Git 오류가 아니라 별도 산출물 미수령이다.

## 실제 로더 확인

아래는 위 상대 경로로 파일을 받은 경우다. 다른 경로면 **생성한 코드 예제의 경로 인수만** 로컬로 바꾼다. 모델 가중치를 받거나 학습하지 않는다.

```bash
uv run --locked python - <<'PY'
import os
from mv_analysis.data import ManifestIndex, SingleViewDataset, FiveViewDataset, get_adapter
from mv_analysis.data.collate import five_view_collate
from torch.utils.data import DataLoader
index = ManifestIndex(
    'outputs/adaptive_crop_full_v1/preprocessing_metadata_reviewed_v2.csv',
    annotations='outputs/filename_class_resolution_v1/image_metadata_with_split.csv',
    bboxes='outputs/filename_class_resolution_v1/defect_bboxes.csv',
    classes='outputs/spatial_20261111_v7/classes.json',
    data_root=os.environ['REALIAD_DATA_ROOT'], require_complete=True,
)
pid = index.data.product_id.iloc[0]
ids = index.data.loc[index.data.product_id.eq(pid), 'image_id']
single = SingleViewDataset(index, image_ids=ids, adapter=get_adapter('EfficientAD-S'))
sample = single[0]
print(sample['image'].shape, sample['image'].dtype, sample['mask_status'])
five = FiveViewDataset(single)
batch = next(iter(DataLoader(five, batch_size=1, collate_fn=five_view_collate)))
print(batch['images'].shape, batch['views'])
PY
```

이 예제는 저장된 좌표·라벨·5시점 순서를 확인한다. 예상 결과는 이미지 `(3,256,256)`, float32, 배치 `(1,5,3,256,256)`, C1~C5 순서다. EfficientAD의 **독립 입력 변환 검증**이며 실제 모델 학습/forward 성공과 다르다. 실패하면 환경변수, 보조 테이블4개, 파일 식별자, Split 일치, 이미지·마스크 실재 여부와 Adapter 이름을 확인한다. NG+MISSING을 빈 정상 라벨로 바꾸지 않는다.

## 개인 완료 기록

- [ ] Git·개인 Fork·upstream을 확인했다.
- [ ] Python3.12와 lock 고정 환경 설치를 확인했다.
- [ ] dummy failed=[]와 pytest 결과를 기록했다.
- [ ] Canonical 파일의 권한·버전·해시를 확인했다.
- [ ] 본인의 데이터 경로로 실제 이미지와 5시점을 로드했다.
- [ ] 마스크 없는 NG의 의미를 이해했다.
- [ ] 개인 기능 브랜치에서 PR 비교 화면까지 확인했다.

4명의 실행 날짜·OS·Python·pytest·로더 결과·담당자를 팀 제한 기록에 남긴다. 미실행한 사람을 성공으로 처리하지 않는다. 개인 절대 경로나 인증정보를 공개 PR에 첨부하지 않는다.
