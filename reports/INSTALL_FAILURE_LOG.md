# 관측한 설치 실패 원문

다음은 이번 세션에서 실제 도구 출력으로 확보한 오류다. 민감정보는 포함하지 않는다. 뒤의 성공 기록이 앞의 실패 사실을 지우지는 않는다. 중단된 설치의 마지막 종료 메시지는 확보되지 않아 성공/실패 원인을 추정하지 않았다.

## 첫 uv sync --locked — 원래 Windows lock

```text
Using CPython 3.12.14
Creating virtual environment at: .venv
Resolved 94 packages in 7ms
error: The current Python platform is not compatible with the lockfile's supported environments: `platform_machine == 'AMD64' and sys_platform == 'win32'`
```

## Linux 범위 추가 후 uv lock — DNS

```text
error: Request failed after 3 retries in 4.4s
  Caused by: Failed to fetch: `https://pypi.org/simple/python-dotenv/`
  Caused by: error sending request for url (https://pypi.org/simple/python-dotenv/)
  Caused by: client error (Connect)
  Caused by: dns error
  Caused by: failed to lookup address information: Temporary failure in name resolution
```

## uv sync --locked — Matplotlib wheel DNS

```text
  × Failed to download `matplotlib==3.11.2`
  ├─▶ Request failed after 3 retries in 4.8s
  ├─▶ Failed to fetch:
  │   `https://files.pythonhosted.org/packages/b8/90/2b3fd67ee273163faeda6d514be70b5596eaa0fd77b60ffc294ad0b34f5f/matplotlib-3.11.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`
  ├─▶ error sending request for url
  │   (https://files.pythonhosted.org/packages/b8/90/2b3fd67ee273163faeda6d514be70b5596eaa0fd77b60ffc294ad0b34f5f/matplotlib-3.11.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl)
  ├─▶ client error (Connect)
  ├─▶ dns error
  ╰─▶ failed to lookup address information: Temporary failure in name resolution

hint: `matplotlib` (v3.11.2) was included because `realiad-five-view` (v0.1.0) depends on `matplotlib`
```

## interruption 복구 후 uv sync --locked --offline — CPU torch 캐시 미완성

```text
Resolved 173 packages in 0.75ms
  × Failed to download `torch==2.15.0+cpu`
  ╰─▶ Network connectivity is disabled, but the
      requested data wasn't found in the cache for:
      `https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl`

hint: `torch` (v2.15.0+cpu) was included because `realiad-five-view` (v0.1.0) depends on `torch`
```

## 최종 복구 — 실제 성공

네트워크 허용 설치를 재개한 후 다음 offline sync가 성공했다.

```text
Resolved 173 packages in 0.79ms
Installed 7 packages in 302ms
 + openai==3.48.0
 + opencv-python==5.0.0.93
 + pillow==13.0.0
 + plotly==7.1.0
 + psutil==7.2.2
 + scipy==1.18.1
 + torch==2.15.0+cpu
```

이어진 `uv sync --locked`:

```text
Resolved 173 packages in 0.72ms
Checked 170 packages in 0.96ms
```

이어진 `uv pip check`:

```text
Checked 170 packages in 75ms
All installed packages are compatible
```

CPU PyTorch wheel과 Matplotlib은 최종 import 및 연산 검증에 통과했다. 상세 환경은 [환경 이전 보고서](ENVIRONMENT_MIGRATION_REPORT.md)를 참조한다. 이 진단 이후 잠금 파일 재생성이나 버전 변경은 하지 않았다.
