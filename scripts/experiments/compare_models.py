"""동일 데이터·평가 조건의 Run만 비교하고 다른 GPU·합성 결과는 분리한다."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from mv_analysis.experiments import compare_models
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runs-root',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--include-synthetic',action='store_true');p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
 print(compare_models(a.runs_root,a.output,include_synthetic=a.include_synthetic,allow_partial=a.allow_partial))
