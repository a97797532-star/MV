# 신규 분석 교차 검증

동일 합성 원본·selected_manifest·seed·분할·해상도·grid를 사용했습니다.
클래스 밝기·박스 라벨·해상도 CSV 11개와 train-only 히트맵 배열 20개가 수치 허용오차 안에서 일치했습니다.
성분 ID의 번호와 실행 시간은 비교에서 제외합니다. geometry·성분 소실·배열 값은 비교합니다.
각 backend 16 tests 통과, 기본 노트북 15 code cells 순서 실행 통과.
실제 Real-IAD 전수 분석·증강·학습·탐지 성능은 검증하지 않았습니다.
