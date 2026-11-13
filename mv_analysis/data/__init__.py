# 한글 안내: Real-IAD 분석 파이프라인의 공통 기능입니다. 입력 자료와 설정의 기존 계약을 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Lazy public API; simple manifest audits do not import model/runtime dependencies."""
from importlib import import_module
_API={'ManifestIndex':('manifest','ManifestIndex'),'ManifestError':('manifest','ManifestError'),'SingleViewDataset':('datasets','SingleViewDataset'),'FiveViewDataset':('datasets','FiveViewDataset'),'get_adapter':('adapters','get_adapter'),'SPECS':('adapters','SPECS'),'single_view_collate':('collate','single_view_collate'),'detection_collate':('collate','detection_collate'),'five_view_collate':('collate','five_view_collate'),'flatten_five_view_batch':('collate','flatten_five_view_batch')}
__all__=list(_API)
# __getattr__: 요청한 공개 API 모듈만 늦게 import합니다. 단순 Manifest 검사에서 모델 런타임까지 불필요하게 불러오지 않습니다.
# 입력 인수: name.
def __getattr__(name):
 if name not in _API:raise AttributeError(name)
 module,attribute=_API[name];return getattr(import_module('.'+module,__name__),attribute)
