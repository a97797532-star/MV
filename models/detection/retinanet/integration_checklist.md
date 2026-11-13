# RetinaNet — 팀원 구현 계약

공식 소스: https://github.com/pytorch/vision

고정 commit: `4260301135e34180d865426765487113f84e7707`. 임의로 최신 HEAD로 바꾸지 않는다. 실제 모델 통합은 **UNVERIFIED / TODO**다. 담당자 이름은 팀에서 정한다.

## 담당자 완료 기준

- [ ] 공식 저장소·commit·라이선스 확인
- [ ] GPU PC 별도 환경과 Python/torch/CUDA/GPU/VRAM 기록
- [ ] 동일 Canonical Manifest/annotation/classes/Split 해시 확인
- [ ] 공통 Dataset과 단일/5시점 계약 연결
- [ ] 전처리 왕복 좌표·범위·dtype·중복 Normalize/Crop 검증
- [ ] 실제 모델 forward 성공
- [ ] backward 또는 모델 고유 학습 단계 성공
- [ ] 소수 Train/Validation Smoke 성공
- [ ] 실제 학습/체크포인트 저장과 SHA 기록
- [ ] Validation으로 checkpoint/Threshold 선택
- [ ] 고정 Test 평가 및 제외 항목 기록
- [ ] 동일 하드웨어 추론 Benchmark
- [ ] 실제 예측 시각화와 Markdown 생성
- [ ] 추론/연결 코드·설정·보고서 PR, weights는 별도 전달

체크박스를 자동 승인하지 않는다. 미완료·실패·미검증은 해당 상태로 남긴다. 공통 합성 테스트 통과만으로 실제 모델 구현 완료라고 선언하지 않는다.
