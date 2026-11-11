# Ubuntu 환경 이전 및 설치 장애 진단

2026-11-11, WSL2 Ubuntu 24.04.4 LTS x86_64, kernel 6.18.33.2-microsoft-standard-WSL2, Python 3.12.14, uv 0.12.8. 기존 Windows 파일·문서·lock은 보존했다. 데이터·모델·가중치를 다운로드하지 않았다. 설치 과정의 openai 패키지는 기존 의존성 유지에 따른 SDK 설치이며 API 호출은 없었다.

## 구분된 실패 원인

| 구분 | 실제 증거 | 판정 |
|---|---|---|
| 초기 Linux 호환성 | `The current Python platform is not compatible with the lockfile's supported environments: platform_machine == 'AMD64' and sys_platform == 'win32'` | 원래 lock이 Windows 전용. Linux 범위 확장으로 해결 |
| DNS/네트워크 | `failed to lookup address information: Temporary failure in name resolution`, PyPI python-dotenv 및 files.pythonhosted.org 다운로드 | 샌드박스 네트워크 실패 확인. 네트워크 허용 실행으로 재개 |
| Matplotlib wheel | matplotlib==3.11.2 manylinux wheel에서 위 DNS 메시지 | wheel 호환성 실패가 아닌 DNS 실패 |
| PyTorch CPU wheel | offline sync: torch==2.15.0+cpu `Network connectivity is disabled, but the requested data wasn't found in the cache` | 중단 시 캐시 미완성. ABI/버전 충돌 근거 없음 |
| 디스크 | 초기 742GiB, 복구 시 약 740GiB available | 디스크 부족 증거 없음 |
| 메모리/동시성 | 이전 설치 중 loadavg 103.12, available 약 1.1GiB, swap 사용 관측. 복구 시 load <1, available 7.7GiB | 리소스 압박 확인. OOM 종료 증거는 없어 OOM으로 단정하지 않음 |
| 의존성 충돌 | Linux/Windows lock resolve 성공, 기존 패키지 버전 변경 0, 최종 sync 성공 | 현재 미해결 충돌 없음 |
| interruption | 기존 설치 session ID 소멸, venv 일부 패키지만 존재 | 중단된 세션의 최종 종료 원인은 미확정. 중단을 설치 성공으로 보고하지 않음 |

다운로드 동시성을 줄여 재시도할 경우 프로젝트 루트에서 다음과 같이 실행한다. 이 옵션은 버전/lock을 바꾸지 않는다.

```bash
UV_CONCURRENT_DOWNLOADS=1 UV_CONCURRENT_INSTALLS=1 UV_CONCURRENT_BUILDS=1 uv sync --locked
```

캐시가 완성된 후 실제 `uv sync --locked --offline`가 7개 잔여 패키지를 설치하며 성공했다. 이어서 `uv sync --locked`가 `Checked 170 packages`로 성공했다. Windows용 의존성을 포함한 lock 항목 수와 Linux에 설치되는 패키지 수는 다를 수 있다. 잠금 버전의 변경/추가는 [lock_comparison.json](lock_comparison.json)을 따른다. 초기 설정은 [보존된 pyproject](../docs/archive/pyproject.windows.toml), [Windows lock](../docs/archive/uv.windows.lock)에 있다.

## 환경 검증

실제 validation: `outputs/environment/20261111T031122681825Z/validation.json`. Python/OpenCV/NumPy/Pandas/Matplotlib/torch/torchvision/pytest/Jupyter/SciPy/Transformers import, CPU tensor, torchvision NMS, OpenCV resize가 성공했고 failed=[]였다. CUDA false는 CPU 기본 환경의 정상 관측이다. 12종 모델 생성·더미 추론·CUDA 실험은 미검증이다.

| 패키지 | 실제 import 버전 |
|---|---|
| torch | 2.15.0+cpu |
| torchvision | 0.29.2+cpu |
| opencv-python | 5.0.0.93 |
| numpy | 2.5.4 |
| pandas | 3.1.1 |
| matplotlib | 3.11.2 |
| pytest | 9.2.0 |
| jupyter-core | 5.9.1 |

최초 pytest는 결측 Cohen d에 abs를 적용해 1 failed/5 passed였다. 결측값을 수치형 NaN으로 명확히 변환하도록 고쳤고 후속 실행은 6 passed, 실제 파일명 구분자 및 미주석 NG 검증을 추가한 실행은 7 passed였다. 최종 검증은 실행 로그의 최신 값을 따른다. Matplotlib의 홈 캐시 권한 경고는 /tmp/mv-matplotlib 캐시를 사용하도록 수정했다. 원본 데이터나 기존 결과를 바꾼 조치는 없다.


추가 원본 조사: 마운트된 Windows 원본의 분석 소스/Notebook/모델별 독립 환경 정의를 legacy/windows_snapshot에 보존했다. Windows 원본은 수정하지 않았고 별도 모델 환경은 설치하지 않았다. 전체 split 재현 및 같은 방법의 영상 지표 비교는 [Windows 비교](WINDOWS_RESULT_COMPARISON.md)를 참조한다.


최종 고정 설치 재검증: uv sync --locked는173개 resolve/170개 설치상태 확인으로0종료했다. 새 source의 실제100장 smoke와 환경dummy가0종료했고 pytest22개가11.29초에 통과했다. 기존 lock SHA256은1370be94aad3bb25c53b5b4bf945dc562508671a57116587ec2b70a2d6a66b32로 동일하다. PDF 독립 렌더 검증 도구 pypdfium2==5.15.2는 /tmp/mv-pdf-tools에 별도 설치했으며 프로젝트 의존성과 lock에 추가하지 않았다.
