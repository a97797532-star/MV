"""기존 Run의 Markdown을 새 버전으로 생성하며 이전 보고서를 덮지 않는다."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from mv_analysis.experiments import generate_experiment_report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();print(generate_experiment_report(a.run_dir))
