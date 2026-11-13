# HVQ-Trans — 팀원 구현 계약

공식 소스: https://github.com/RuiyingLu/HVQ-Trans

고정 commit: `12fbfa96b906d1462cbfc1787e47e2fc17468134`. 임의로 최신 HEAD로 바꾸지 않는다. 실제 모델 통합은 **UNVERIFIED / TODO**다. 담당자 이름은 팀에서 정한다.

## TODO(담당자): 모델 생성과 학습 단계

- 연결 위치: `integration.py`의 Integration / 공통 ModelIntegration의 build_model·training_step.
- 목적: 공식 생성 API·Loss·학습 단계를 공통 Run에 연결한다. 이 폴더에는 실제 Train Loop가 없다.
- 입력: 고정 config, 승인된 공통 Dataset, 모델별 batch. 출력: 실제 모델, 실제 제공 Loss/관측값, Validation 예측, checkpoint 메타데이터.
- 참고: 위 commit의 공식 README·entrypoint·Loss 구현. 모델별 함수 이름은 조사 후 문서화한다. 미확인 학습 명령을 실행 가능하다고 기재하지 않는다.
- 학습 정책: Train의 OK만 기본 학습; NG는 검증/평가로 유지.
- Loss는 모델이 실제 제공하는 이름만 `recorder.log(epoch=...,step=...,phase="train",metrics=...)`에 기록한다. 제공하지 않는 classification/regression/reconstruction 값을 만들지 않는다.
- Validation Loss/metric, learning_rate, gradient_norm, epoch_seconds는 실제 측정한 경우만 기록한다. 제공되지 않으면 N/A다.
- checkpoint는 Git 제외 위치에 저장하고 Recorder.checkpoint로 실제 bytes/SHA를 기록한다. Validation으로 선택하며 Test 최고 점수로 대표 checkpoint를 고르지 않는다.
- 실제 학습이 없으면 COMPLETED 금지. 모델 학습 종료를 확인한 담당자가 training_executed와 실행 근거를 기록한다.

## 성공 조건

공식 소스/환경/장치 기록, forward 성공, backward 또는 해당 모델 학습 단계 성공, 소수Train/Val Smoke, 실제학습·Validation 선택·고정Test·재현명령·실행로그. 관련 테스트: Recorder/미구현/실패Run 테스트와 담당자가 추가할 모델 런타임 테스트.
