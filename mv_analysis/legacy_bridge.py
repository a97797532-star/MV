"""Load preserved OpenCV utilities without changing the Windows source or global import names."""
import importlib.util
import sys
from pathlib import Path

_BASE=Path(__file__).resolve().parents[1]/'legacy/windows_snapshot/RealIAD_OpenCV_Analysis_Assignment_v2/RealIAD_OpenCV'
_CACHE={}

def _load(name,filename):
    if name in _CACHE:return _CACHE[name]
    spec=importlib.util.spec_from_file_location(name,_BASE/filename)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);_CACHE[name]=module
    return module


def backend():return _load('_mv_preserved_cv_backend','backend.py')


def core():
    if '_mv_preserved_core' in _CACHE:return _CACHE['_mv_preserved_core']
    prior=sys.modules.get('backend');sys.modules['backend']=backend()
    try:return _load('_mv_preserved_core','core.py')
    finally:
        if prior is None:sys.modules.pop('backend',None)
        else:sys.modules['backend']=prior


def coursework():
    if '_mv_preserved_coursework' in _CACHE:return _CACHE['_mv_preserved_coursework']
    old={k:sys.modules.get(k) for k in ('core','backend')};sys.modules['backend']=backend();sys.modules['core']=core()
    try:return _load('_mv_preserved_coursework','coursework.py')
    finally:
        for name,value in old.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value


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
