# 특수 모델 환경 계획

공통 Python 3.12 조건을 유지하기 위해 검증되지 않은 과거 의존성을 설치하지 않았다.

- UniAD: 저자 torch 1.5.0 / torchvision 0.6.0+cu90와 3.12 충돌. Linux 셸·분산 실행을 WSL2에서 검토. 원본 Python 범위 확정 후 uv 별도 프로젝트로 기록하거나 3.12 포팅 필요.
- HVQ-Trans: torch 1.11.0+cu113 / torchvision 0.12.0+cu113와 3.12 충돌. requirements opencv-python==4.9.0도 실제 배포 버전 명세 확인 필요. --no-deps/강제 override로 우회하지 않는다.
- ViTDet: detectron2 공식 지원 Linux/macOS. WSL2/Linux에서 소스 commit, torch/torchvision, compiler와 CUDA 확장 일치 검증 후 독립 uv 프로젝트/lock 생성. Transformers의 ViTDet backbone만으로 완전한 detector 구현이라 주장하지 않는다.

원본의 재현을 위해 Python 3.8/3.9 등이 필요할 수 있으나 이번에는 설치하거나 프로젝트 Python을 낮추지 않았다. 과거 재현과 Python 3.12 포팅 중 하나를 선택하고 실행 검증을 마친 뒤 해당 환경의 pyproject/lock을 생성한다. WSL2/관리자 권한 시스템 변경은 수행하지 않았다.
