"""PatchCore 담당자 확장 지점. 공식 모델이나 학습 루프를 구현한 코드가 아니다."""
from mv_analysis.experiments.integration import ModelIntegration


class Integration(ModelIntegration):
    """TODO: 같은 폴더의 전처리/학습/평가 계약과 체크리스트를 따라 실제 구현을 연결한다.

    공식 소스: https://github.com/amazon-science/patchcore-inspection
    고정 커밋: fcaa92f124fb1ad74a7acf56726decd4b27cbcad
    성공 기준: 실제 forward·학습 단계·Validation·Test·Benchmark와 보고서 검증.
    공통 합성 테스트는 실제 PatchCore 학습 성공을 뜻하지 않는다.
    """
    model_name = 'PatchCore'


def build_model(config):
    """TODO(담당자): config를 공식 생성 API에 연결하고 weights 출처/해시를 기록한다.

    입력: 고정 실험 config. 출력: 실제 모델. 현재는 명시적 NotImplementedError다.
    주의: 이 함수를 호출해도 가짜 모델이나 성공 상태를 반환하지 않는다.
    관련 테스트: 공통 미구현 계약 테스트 + 담당자가 추가할 실제 모델 Smoke.
    """
    return Integration().build_model(config)
