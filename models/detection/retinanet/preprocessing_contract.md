# RetinaNet — 팀원 구현 계약

공식 소스: https://github.com/pytorch/vision

고정 commit: `4260301135e34180d865426765487113f84e7707`. 임의로 최신 HEAD로 바꾸지 않는다. 실제 모델 통합은 **UNVERIFIED / TODO**다. 담당자 이름은 팀에서 정한다.

## 입력과 변환 책임

- 기존 `ManifestIndex`/`SingleViewDataset`/`FiveViewDataset`를 사용한다. 최종 Crop과 Split을 바꾸지 않는다.
- 공통 입력: RGB CHW float32, native0..1. NG 미주석 마스크는 None이며 빈 정상 마스크가 아니다.
- 현재 독립 Adapter: resize=`delegated`, size=`None`, 외부정규화=`none`, pixel_scale=`1.0`.
- 학습 타깃 형식: `xyxy`, normalized=`False`, class_offset=`1`. 모델 예측 출력 형식은 이 값과 같다고 추정하지 말고 실제 forward로 확인한다.
- 마스크 기하 변환은 NEAREST. 원본 XYXY exclusive에서 Crop 원점 이동·Clip·Scale·Pad를 일관 적용한다.
- 모델 내부 Resize=`short800/max1333, padding32`, 내부정규화=`ImageNet in model`. 공식 mapper/processor와 두 번 적용하지 않는다.
- 공식 추가 Crop 정보: `none`. manifest-preserving Adapter는 추가CenterCrop을 거부한다. 공식기준선과 공통입력조건이 다르면 별도 track으로 기록한다.

## TODO(담당자)

목적: `ModelIntegration.preprocessing(samples,config)`에 공식 전처리 연결. 입력: 공통 샘플 목록. 출력: 공식 forward가 받는 batch와 역변환 메타데이터. 참고: 위 고정 소스의 Dataset/transform/mapper와 reports/MODEL_INPUT_REQUIREMENTS.md. 주의: RGB/BGR, 범위, dtype, AMP, 클래스 offset, 배치구조를 실제 확인한다. 성공: 한 배치 shape·dtype·값범위·마스크/BBox 정합과 왕복 좌표 테스트 통과. 관련 테스트: tests/test_data_loading.py, tests/test_experiment_infrastructure.py.
