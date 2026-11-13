"""GPU나 실제 모델 없이 합성 자료로 평가·보고 인프라를 점검한다."""
from pathlib import Path
import argparse,json,sys,uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from mv_analysis.experiments.demo import run_synthetic_demo
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
 root=a.output or Path('outputs/experiments')/('SYNTHETIC_SMOKE_'+uuid.uuid4().hex[:12])
 if root.exists():raise SystemExit('Output exists; preserve previous smoke run')
 result=run_synthetic_demo(root);print(json.dumps(result,indent=2))
