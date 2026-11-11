# 12종 모델 호환성 조사

## Resume verification (2026-11-10)

- User reports ordinary Windows CMD successfully accessed PyPI and installed packaging 26.3. This does not establish network access inside Codex.
- Directly verified: uv 0.12.11, existing .venv Python 3.12.14, packaging==26.3 as the only installed distribution. No virtual environment was recreated.
- An initial dry-run used the installed package and did not test networking. The forced refresh below contacted https://pypi.org/simple/packaging/ and failed with socket error 10013. HTTP retries were disabled.

```powershell
$env:UV_HTTP_RETRIES='0'
$env:UV_HTTP_TIMEOUT='15'
uv pip install --python .venv\Scripts\python.exe --dry-run --reinstall-package packaging --refresh-package packaging packaging -v
```

- This session has restricted networking and sandbox_approval=false (automatically denied). An approval escalation cannot obtain authorization here; no request was submitted for review. No security policy changes or sandbox bypasses were attempted.
- setup.ps1 -Resolve -Models, uv lock and uv sync --locked were not repeated after this failure. uv.lock is still absent; dependency conflict resolution remains unverified.
- validate_environment.py --dummy: exit 1, 33 failures. Python 3.12 and SQLite schema passed; 28 third-party imports and five tensor/detection/dummy checks failed because dependencies are absent. See outputs/environment_validation.json.
- uv pip check passed for ONE installed package only; this is not project dependency validation. pip itself is absent and is not required by uv.
- No training, dataset/model-weight downloads, paid API calls or key output occurred.
- Resume setup in an authorized network-enabled session using powershell -NoProfile -File scripts/setup.ps1 -Resolve -Models. The -Models switch enables dummy checks; it does not install the independent anomaly/detection projects. Those require separate lock/sync/import validation.
- CPU model execution verified: 0/12. torchvision detectors, YOLOS, RT-DETRv2, YOLO11 and four anomalib models remain CPU candidates, not verified runnable models. UniAD/HVQ-Trans require Python 3.12 porting or a separately designed legacy reproduction; WSL2 alone does not fix their historical dependency conflicts. ViTDet requires WSL2/Linux and detectron2 build validation. GPU requirements and current upstream compatibility were not rechecked in this blocked session.

The historical records below predate this resume. In particular, references to zero installed packages are superseded by the directly verified packaging 26.3 installation above.

조사일: 2026-11-10. **모든 모델: 설치 미완료, 실제 데이터 추론 미검증.** 네트워크 제한으로 버전 해결 자체가 실패했다. 아래 upstream 버전은 설치된 버전이 아니라 공식 소스의 요구사항이다. 지원됨은 설치·추론 성공을 의미하지 않는다.

## 이상 탐지

| 모델 | 공식/선택 구현 | Python/PyTorch/CUDA 근거 | 필수 의존성과 가중치 | Windows/CPU 및 현재 검증 |
|---|---|---|---|---|
| PatchCore | [저자 구현](https://github.com/amazon-science/patchcore-inspection), 선택: anomalib Patchcore | anomalib main Python >=3.10, CPU extra torch >=2.10 / torchvision >=0.25; 실제 배포판 미해결 | torch, timm, lightning, 지표; 사전학습 CNN + 정상 특징 memory bank 필요 | anomalib CPU 경로 후보. 미설치, import/생성/추론 미검증. 원본 FAISS 환경과 분리 |
| EfficientAD-S | [anomalib EfficientAd](https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/models/image/efficient_ad.html), model_size S | anomalib 공통 조건; 저자 공식 코드 공개 여부 확정 못함 | 학생/교사 PDN, 교사 가중치; 학습 절차의 Imagenette 사용 주의 | CPU 경로 후보. constructor/학습 준비 시 가중치·데이터 다운로드 가능하여 호출 안 함. 미설치/미검증 |
| UniAD | [저자 구현](https://github.com/zhiyuanyou/UniAD) | requirements: torch 1.5.0, torchvision 0.6.0+cu90; Python 범위 명시 확인 못함; Python 3.12 그대로 사용 불가 | numpy 1.19.5, scipy 1.5.4, sklearn 0.24.2, einops 0.4.1, tensorboardX, CNN/학습 checkpoint | 공식 셸·분산 GPU 스크립트 중심. Windows/CPU 원본 실행 미검증. WSL2 독립 환경 또는 Python 3.12 포팅 검토. 미설치 |
| HVQ-Trans | [저자 구현](https://github.com/RuiyingLu/HVQ-Trans) | requirements: torch 1.11.0+cu113 / torchvision 0.12.0+cu113; Python 범위 미확인; 3.12용 해당 wheel 없음 | numpy 1.22.4, pandas 2.0.3, einops 0.4.1, tensorboardX, backbone/checkpoint | Windows/CPU 미검증. WSL2 독립 환경 후보; 원본 의존성 문자열도 검토 필요. 미설치 |
| Dinomaly | [저자 구현](https://github.com/guojiajeremy/Dinomaly), 선택: anomalib Dinomaly | 원본 torch 1.12.0+cu113 / torchvision 0.13.0+cu113, 구형 수치 패키지. anomalib 통합은 저자 README에서 2.1.0 명시 | DINOv2 가중치, timm, torch; 원본과 anomalib의 세부 동작 차이 비교 필요 | anomalib의 Python 3.12 CPU 경로 후보. 미설치/미검증. Dinomaly2로 대체하지 않음 |
| INP-Former | [저자 구현](https://github.com/luow23/INP-Former), 선택 후보: anomalib InpFormer | 원본 README Python 3.8.12; requirements torch 2.0.0+cu118 / torchvision 0.15.1+cu118. anomalib main에서 InpFormer export 확인 | DINOv2 register encoder, timm 0.9.12, kornia 0.7.3, adeval 1.1.0(원본); 가중치 필요 | 원본 GPU 실험 중심, CPU 미검증. anomalib 배포판의 클래스 존재를 설치 후 확인해야 함. 미설치 |

[anomalib main 모델 exports](https://github.com/open-edge-platform/anomalib/blob/main/src/anomalib/models/image/__init__.py)에는 Patchcore/EfficientAd/Dinomaly/InpFormer가 있고, UniAD/HVQ-Trans는 없다. UniNet 등 유사 이름 모델로 대체하지 않았다. main은 고정 릴리스가 아니므로 실제 설치 버전에서 재확인해야 한다. [anomalib main 메타데이터](https://github.com/open-edge-platform/anomalib/blob/main/pyproject.toml)

원본 요구사항 근거: [UniAD](https://github.com/zhiyuanyou/UniAD/blob/main/requirements.txt), [HVQ-Trans](https://github.com/RuiyingLu/HVQ-Trans/blob/master/requirements.txt), [Dinomaly](https://github.com/guojiajeremy/Dinomaly/blob/master/requirements.txt), [INP-Former](https://github.com/luow23/INP-Former/blob/main/requirements.txt). 이 파일들을 루트에 무조건 설치하면 Python/torch/numpy 충돌 위험이 있다. upstream의 과거 버전을 현재 설치 버전으로 보고하지 않았다.

## 불량 탐지

| 모델 | 공식/선택 구현 | 의존성/버전 조건 | 가중치 | Windows/CPU 및 현재 검증 |
|---|---|---|---|---|
| Faster R-CNN | [torchvision](https://github.com/pytorch/vision) | Python 3.12용 torch/torchvision 호환 wheel 쌍, C++ NMS/ROI 연산자 | 랜덤 생성은 weights=None 및 weights_backbone=None, 실제 검사는 학습 가중치 필요 | Windows/CPU 후보. 생성·더미 검증 실행했으나 torch 부재로 실패 |
| RetinaNet | [torchvision](https://github.com/pytorch/vision) | 위와 동일; 추가 탐지 프레임워크 불필요 | 위와 동일 | 생성·더미 검증 실행했으나 torch 부재로 실패 |
| YOLO11 | [Ultralytics](https://github.com/ultralytics/ultralytics), [YOLO11 문서](https://docs.ultralytics.com/models/yolo11/) | 별도 detection 프로젝트, Python 3.12 대상 resolver 미검증 | yolo11n.yaml은 랜덤 구성, .pt 경로는 자동 다운로드 가능 | Windows/CPU 후보. 미설치/import/생성/추론 미검증. YOLO26 등으로 대체하지 않음 |
| RT-DETRv2 | [저자 구현](https://github.com/lyuwenyu/RT-DETR), 선택: [Transformers RTDetrV2](https://huggingface.co/docs/transformers/model_doc/rt_detr_v2) | torch/transformers, CPU 시 custom CUDA kernel 비활성 경로 확인; Python 3.12 대상 resolver 미검증 | config 생성 + use_pretrained_backbone=False 사용, from_pretrained 호출 안 함 | Windows/CPU 후보. 클래스 import 검사 실패(transformers 부재). 모델 생성·추론 미검증. v1과 구분 |
| YOLOS | [저자 구현](https://github.com/hustvl/YOLOS), 선택: [Transformers](https://huggingface.co/docs/transformers/model_doc/yolos) | torch/transformers/scipy, Python 3.12 대상 resolver 미검증 | YolosConfig로 랜덤 생성, 실제 검사용 checkpoint 필요 | 축소 config 더미 검사 시도했으나 torch 부재로 실패. 공식 크기/실데이터 미검증 |
| ViTDet | [저자 구현 detectron2/projects/ViTDet](https://github.com/facebookresearch/detectron2/tree/main/projects/ViTDet) | detectron2, torch/torchvision, 빌드 도구. 공식 설치 문서 Linux/macOS, Python >=3.7 / torch >=1.8(최소 조건일 뿐 3.12 호환 보장 아님) | MAE/ViT 사전학습 + 탐지 head checkpoint | Windows 공식 지원 없음. WSL2/Linux 별도 프로젝트 후보, 미설치. Transformers VitDet backbone만으로 완전한 탐지기로 인정하지 않음 |

[detectron2 설치 지원 범위](https://detectron2.readthedocs.io/en/latest/tutorials/install.html). WSL2에서도 torch/CUDA/compiler/소스 commit을 맞춘 뒤 설치·검증해야 한다. 현재 WSL2 설치 또는 설정 변경은 하지 않았다.

## 설치 결정

- 루트: Faster R-CNN/RetinaNet/RT-DETRv2/YOLOS를 위한 torchvision + transformers, 공통 평가·API·대시보드 준비.
- environments/anomaly: anomalib만 별도 의존성 해결. 실제 버전에서 Patchcore/EfficientAd/Dinomaly/InpFormer import 검증 필요.
- environments/detection: YOLO11 ultralytics 분리. 루트의 torch 및 cv2 변형과 독립적으로 재현.
- environments/specialized: UniAD/HVQ-Trans의 Python 3.12 포팅 또는 과거 재현용 별도 Python, ViTDet의 WSL2 프로젝트 계획만 준비. 프로젝트 기본 Python 3.12를 몰래 낮추지 않음.
- mmdetection/mmcv: 지정 모델에 반드시 필요하지 않아 미설치. [MMCV Windows 빌드 문서](https://mmcv.readthedocs.io/en/latest/get_started/build.html)가 있어 Windows 전체 불가능으로 단정하지 않음. 특정 torch/CUDA/MSVC 조합의 wheel·확장 빌드 검증이 필요하며 현재 미검증.

12종 모두 실제 데이터 추론 미검증. 현재 설치 성공 0종, import 성공 0종, 모델 생성 성공 0종, 더미 추론 성공 0종이다. 환경 템플릿은 실행 보증이 아니다.
