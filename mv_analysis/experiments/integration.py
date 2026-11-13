"""팀원 구현 인터페이스만 정의한다. 실제 모델/학습/전처리 연결은 의도적으로 미구현이다."""

class ModelIntegration:
    def build_model(self, config):
        """TODO: 고정 공식 커밋, weights 출처·SHA, 생성API와 장치 계약을 확인하고 실제 모델을 반환한다."""
        raise NotImplementedError('팀원이 공식 모델 생성 API를 연결해야 합니다.')

    def preprocessing(self, samples, config):
        """TODO: 기존 Dataset의 이미지/타깃을 공식 입력에 연결한다. 이중 Crop·Normalize를 검증한다."""
        raise NotImplementedError('팀원이 공식 전처리와 공통 Adapter의 담당 범위를 연결해야 합니다.')

    def training_step(self, model, batch, recorder):
        """TODO: 실제 Loss만 Recorder에 기록한다. PatchCore는 memory bank 구축 단계로 별도 구현한다."""
        raise NotImplementedError('팀원이 실제 학습 단계 또는 memory bank 구축을 구현해야 합니다.')

    def predict_original(self, model, batch):
        """TODO: score 또는 boxes/classes/confidence를 원본 좌표로 복원해 공통 예측 계약으로 반환한다."""
        raise NotImplementedError('팀원이 공식 모델 forward와 출력 변환을 구현해야 합니다.')

    def run_validation(self, model, loader, recorder):
        """TODO: Validation 예측으로만 Threshold를 고정하고 평가 결과·체크포인트 선택 근거를 기록한다."""
        raise NotImplementedError('팀원이 모델별 Validation 호출을 연결해야 합니다.')
