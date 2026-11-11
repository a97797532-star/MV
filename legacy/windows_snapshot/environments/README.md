# 독립 환경 사용

이 디렉터리들은 uv workspace가 아니다. 각 프로젝트의 lock과 .venv가 독립적이다.

- anomaly: anomalib, Patchcore/EfficientAd(S)/Dinomaly/InpFormer 지원 확인 후 선택. 실제 설치 버전에서 클래스 import를 먼저 확인한다.
- detection: ultralytics YOLO11. yolo11n.yaml로 생성하면 .pt 다운로드를 피할 수 있지만 실제 생성/추론은 현재 미검증이다.
- export: 향후 ONNX/CPU Runtime 검증 시 사용. 지금 설치하지 않는다.
- specialized: 구형 연구 코드/ViTDet 격리 계획.

필요한 환경만 다음과 같이 설치한다(현재 네트워크 제한에서는 실패).

```powershell
Set-Location environments/anomaly
uv venv --python 3.12
uv lock
uv sync --locked
uv run --locked python -c "from anomalib.models import Patchcore, EfficientAd, Dinomaly, InpFormer"
```

위 명령은 constructor를 호출하지 않는다. import 성공만으로 모델 생성/추론을 검증했다고 보고하지 않는다. 해당 클래스가 배포판에 없으면 설치 버전과 upstream commit을 비교하고, 요구한 모델을 다른 것으로 대체하지 않는다.
