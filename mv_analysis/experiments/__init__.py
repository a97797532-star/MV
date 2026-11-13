"""공통 실험 API. 모델별 학습 구현은 팀원 책임이며 여기서 모델을 생성하지 않는다."""
from .contracts import PROTOCOL,ThresholdPolicy
from .recorder import ExperimentRecorder,load_predictions
from .anomaly import calibrate_anomaly,evaluate_anomaly
from .detection import calibrate_detection,evaluate_detection
from .benchmark import benchmark
from .reports import generate_experiment_report,compare_models
