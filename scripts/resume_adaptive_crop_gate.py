# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Resume the existing adaptive gate version without repeating images or retuning it."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'outputs/adaptive_crop_gate_v1'
# count: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: p.
def count(p):
 if not p.exists():return 0
 return len({json.loads(line)['image_path'] for line in p.read_text().splitlines() if line})
# call: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: script.
def call(script,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,check=True)
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 # The original hashed runner is preserved; recovery fixes only its freeze export.
 call('adaptive_crop_gate_experiment.py','smoke')
 if not (B/'frozen_policy.json').exists():
  call('adaptive_crop_gate_experiment.py','features');call('freeze_adaptive_crop_gate_recovery.py')
 if count(B/'checkpoints/features.jsonl')<2550:call('adaptive_crop_gate_experiment.py','final')
 if not (B/'dry_run_manifest.jsonl').exists():call('adaptive_crop_gate_experiment.py','dry-run')
 if count(B/'dry_run_manifest.jsonl')!=2550:raise RuntimeError('Incomplete existing manifest: preserve and investigate; never overwrite')
 if count(B/'checkpoints/evaluation.jsonl')<2550 or not (B/'evaluation_complete.json').exists():call('adaptive_crop_gate_experiment.py','evaluate')
 print('Existing2550 image checkpoints and frozen policy ready; no retuning, no dataset crops')
if __name__=='__main__':main()
