# 한글 안내: Real-IAD 분석 파이프라인의 공통 기능입니다. 입력 자료와 설정의 기존 계약을 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Read-only Real-IAD analysis; no model training or network calls."""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mv-matplotlib")
