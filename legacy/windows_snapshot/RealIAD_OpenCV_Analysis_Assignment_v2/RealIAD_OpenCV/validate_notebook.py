"""기본 분석·과제 스킵 경로를 IPython으로 순서 실행. TCP 커널 불필요."""
from pathlib import Path
import sys
import nbformat
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.utils.capture import capture_output
sys.path.insert(0,str(Path.cwd()))
shell=TerminalInteractiveShell.instance()
nb=nbformat.read('analysis_guide.ipynb',as_version=4);nbformat.validate(nb)
count=0
for i,cell in enumerate(nb.cells):
    if cell.cell_type!='code':continue
    with capture_output(stdout=True,stderr=True,display=True) as captured:
        result=shell.run_cell(cell.source,store_history=True)
    if result.error_before_exec or result.error_in_exec:
        print(captured.stdout,captured.stderr)
        raise RuntimeError(f'Notebook cell {i} failed: {result.error_before_exec or result.error_in_exec}')
    count+=1;cell.execution_count=count;cell.outputs=[]
    if captured.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
    if captured.stderr:cell.outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
    for out in captured.outputs:
        cell.outputs.append(nbformat.v4.new_output('display_data',data=out.data,metadata=out.metadata))
    print(f'PASS cell {i} ({count} code cells)',flush=True)
nbformat.validate(nb);nbformat.write(nb,'analysis_guide_demo_executed.ipynb')
print(f'PASS: all {count} code cells executed sequentially. Assignment switches remain False; no training performed.')
