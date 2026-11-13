# 한글 안내: 패키지 import와 CPU 더미 연산을 점검합니다. 데이터나 모델 가중치를 받지 않습니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Offline import/CPU/dummy validation. Never constructs pretrained models."""
import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import socket
import sys
from datetime import datetime,timezone
from pathlib import Path


# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dummy',action='store_true');args=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
    # blocked: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    def blocked(*args,**kwargs):raise RuntimeError('network disabled during environment validation')
    socket.socket.connect=blocked
    checks={};versions={}
    checks['python_3_12']=sys.version_info[:2]==(3,12)
    for name,dist in [('cv2','opencv-python'),('numpy','numpy'),('pandas','pandas'),('matplotlib','matplotlib'),('torch','torch'),('torchvision','torchvision'),('pytest','pytest'),('jupyter_core','jupyter-core'),('scipy','scipy'),('transformers','transformers')]:
        try:importlib.import_module(name);versions[dist]=importlib.metadata.version(dist);checks[name]=True
        except Exception as exc:checks[name]=str(exc)
    if args.dummy:
        try:
            import torch
            a=torch.arange(9,dtype=torch.float32).reshape(3,3)
            checks['cpu_tensor']=bool(torch.equal(a@torch.eye(3),a))
            from torchvision.ops import nms
            checks['torchvision_nms']=nms(torch.tensor([[0.,0.,2.,2.],[0.,0.,2.,2.]]),torch.tensor([.9,.8]),.5).tolist()==[0]
            import cv2,numpy as np
            dummy=np.zeros((64,64,3),np.uint8);checks['opencv_resize']=cv2.resize(dummy,(32,32)).shape==(32,32,3)
            checks['cuda_available_observation']=str(torch.cuda.is_available())
        except Exception as exc:checks['dummy_failure']=str(exc)
    failed=[k for k,v in checks.items() if v is not True and k!='cuda_available_observation']
    report=dict(time=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),python=sys.version,executable=sys.executable,versions=versions,checks=checks,failed=failed,models='12 model implementations absent; model creation/inference not validated')
    out=Path('outputs/environment')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    (out/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));print(f'Output: {out}')
    return int(bool(failed))

if __name__=='__main__':raise SystemExit(main())
