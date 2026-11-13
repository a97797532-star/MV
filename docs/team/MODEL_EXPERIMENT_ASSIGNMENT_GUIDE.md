# 4인 팀의 12개 모델 구현·결과 제출 안내

실제 담당자는 팀에서 합의한다. 아래는 작업량·GPU지원·프레임워크 숙련도에 맞춰 조정할 수 있는 **배분 예시**이며 개인에게 확정 배정한 것이 아니다.

| 역할 예시 | 모델 3개 | 검토 역할 예시 |
|---|---|---|
| 팀원 A | PatchCore, Faster R-CNN, RetinaNet | 원본 좌표/검출 클래스 계약 |
| 팀원 B | EfficientAD-S, YOLO11, RT-DETRv2 | 추론·NMS·지연 측정 |
| 팀원 C | UniAD, HVQ-Trans, YOLOS | 재구성/픽셀 평가·결측 주석 |
| 팀원 D | Dinomaly, INP-Former, ViTDet | Transformer 환경·입력/추가Crop |

GPU PC의 VRAM과 CUDA지원 여부를 먼저 확인한다. Transformer 작업이 몰리면 모델을 재분배한다. 원본Test를 반복 소모해 전처리를 조정하지 않는다.

## 시작 문서

- [실험 규약](../experiments/EXPERIMENT_PROTOCOL.md)
- [공식 Clone→모델 환경→학습 준비 단계](MODEL_EXPERIMENT_WORKFLOW.md)
- [모델 작업 영역](../../models/README.md): 각 모델의5개 문서와integration.py
- [Fork→Branch→PR](GITHUB_FORK_WORKFLOW.md)

공통 데이터 로더·평가기·Recorder·Benchmark·보고서 생성기는 재사용한다. 모델별 환경은 독립적으로 관리하고 루트uv.lock을 임의로 바꾸지 않는다. 공식repo/commit은 고정레지스트리와 일치시킨다.

## 모델별 완료 기준

1. 공식 소스 commit/라이선스 확인
2. 본인 GPU PC의 독립 환경 설치, GPU명·VRAM·CUDA·torch·Python 기록
3. 동일 Canonical Manifest/주석/클래스/Split 해시 확인
4. 기존 Dataset 연결 및 전처리·좌표 왕복 검증
5. 실제 forward 성공
6. backward 또는 모델 고유 학습 단계 성공(PatchCore는memory bank)
7. 소수 Train/Validation Smoke Test
8. 실제 학습과 checkpoint 메타데이터 기록
9. Validation으로 checkpoint/Threshold 선택
10. 고정 Test 평가 및 주석 제외 수 기록
11. 동일 장비 Benchmark 또는 추후 공통 장비 재측정
12. 실제 예측 시각화·Markdown 생성·PR 리뷰

체크하지 않은 것은 TODO/UNVERIFIED로 남긴다. 공통 합성 Smoke는 이12개 실제모델을 학습했다는 의미가 아니다. 담당자는 config/환경/이력/metrics/predictions/benchmark/artifacts/report를 같은 Run스키마로 보관한다.

## GitHub에 제출할 것

- 추론/공식모델 연결 코드, 실행설정, 필요한 테스트
- 실제 결과 Markdown, 공유 가능한 통계 그래프
- source commit, 데이터/프로토콜 해시, 가중치 파일명·bytes·SHA-256
- 미측정·실패·제외 항목, 재현 명령과 GPU 환경

**학습한 가중치·checkpoint·memory bank·검색 인덱스는 GitHub에 올리지 않는다.** 팀이 정한 별도 저장소/전달 채널에서 수령한다. 비밀 다운로드 URL이나토큰은 코드·보고서·로그에 기록하지 않는다. 담당자가 공유 가능한 표/그래프만 선택해 PR에 포함하고 outputs/를 통째로 Stage하지 않는다.

## 리뷰 시 확인

공통 로더 변경은 별도 합의한다. 입력Adapter와공식processor가이중Resize/Normalize/Crop을하지않는지, NG미주석을정상으로바꾸지않는지, GT를정책선택에섞지않는지 확인한다. report의SYNTHETIC/REAL과학습완료상태, 비교그룹과장비, 원본좌표,Threshold출처를 확인한다. Test점수로대표Run을선택한PR은수정을요청한다.
