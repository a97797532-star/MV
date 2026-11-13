# 한글 안내: Real-IAD 분석 파이프라인의 공통 기능입니다. 입력 자료와 설정의 기존 계약을 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Load preserved OpenCV utilities without changing the Windows source or global import names."""
import importlib.util
import sys
from pathlib import Path

_BASE=Path(__file__).resolve().parents[1]/'legacy/windows_snapshot/RealIAD_OpenCV_Analysis_Assignment_v2/RealIAD_OpenCV'
_CACHE={}

# _load: 자료를 불러와 다음 처리에 사용할 형태로 준비합니다.
# 입력 인수: name, filename.
def _load(name,filename):
    if name in _CACHE:return _CACHE[name]
    spec=importlib.util.spec_from_file_location(name,_BASE/filename)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);_CACHE[name]=module
    return module


# backend: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def backend():return _load('_mv_preserved_cv_backend','backend.py')


# core: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def core():
    if '_mv_preserved_core' in _CACHE:return _CACHE['_mv_preserved_core']
    prior=sys.modules.get('backend');sys.modules['backend']=backend()
    try:return _load('_mv_preserved_core','core.py')
    finally:
        if prior is None:sys.modules.pop('backend',None)
        else:sys.modules['backend']=prior


# coursework: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
def coursework():
    if '_mv_preserved_coursework' in _CACHE:return _CACHE['_mv_preserved_coursework']
    old={k:sys.modules.get(k) for k in ('core','backend')};sys.modules['backend']=backend();sys.modules['core']=core()
    try:return _load('_mv_preserved_coursework','coursework.py')
    finally:
        for name,value in old.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value


# notebook_function: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: name.
def notebook_function(name):
    """Extract a whitelisted pure helper; never execute notebook cells or training switches."""
    import ast,json
    if name not in {'extract_product_info'}:raise ValueError('Helper not allowlisted')
    key='_mv_notebook_'+name
    if key in _CACHE:return _CACHE[key]
    nb=json.loads((_BASE/'analysis_guide_demo_executed.ipynb').read_text())
    for cell in nb['cells']:
        if cell.get('cell_type')!='code':continue
        try:tree=ast.parse(''.join(cell.get('source',[])))
        except SyntaxError:continue
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name==name:
                scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(_BASE/name),'exec'),scope)
                _CACHE[key]=scope[name];return scope[name]
    raise ValueError('Preserved notebook helper missing')
