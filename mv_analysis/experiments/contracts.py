"""실험·예측 계약과 엄격한 JSON 도구. 기존 데이터 로더 계약은 수정하지 않는다."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import math
import os
import re
import tempfile
import numpy as np

PROTOCOL = {
    'version': 'mv-evaluation-v1', 'anomaly_direction': 'higher_is_NG',
    'threshold_rule': 'validation_max_f1_highest_threshold_on_tie',
    'pixel_scope': 'GT_DECLARED_ORIGINAL_REGION', 'empty_ng_policy': 'exclude_pixel_and_detection',
    'aupro_fpr_limit': 0.3, 'aupro_thresholds': 256, 'aupro_connectivity': 8, 'pixel_histogram_bins': 2048, 'pixel_range_source': 'validation_only',
    'aupro_integration': 'linear_interpolation_normalized_by_fpr_limit',
    'detection_iou_thresholds': [round(.5+.05*i, 2) for i in range(10)],
    'detection_max_dets': [1, 10, 100], 'detection_count_iou': .5, 'detection_calibration_grid': '0:0.01:1',
    'nms_policy': 'already_applied_upstream_declared_per_run',
    'box_format': 'XYXY_EXCLUSIVE_ORIGINAL_PIXELS', 'class_ids': 'canonical_zero_based',
}
REQUIRED_CONFIG = (
    'experiment_id', 'model_name', 'model_family', 'official_repo', 'official_commit',
    'project_commit', 'manifest_sha256', 'annotation_sha256', 'class_mapping_sha256',
    'evaluation_set_sha256', 'evaluation_ids_sha256', 'split_version', 'crop_policy_version', 'model_adapter_version',
    'seed', 'device', 'batch_size', 'epochs', 'optimizer', 'scheduler', 'learning_rate',
    'input_resolution', 'normalization', 'checkpoint_path', 'checkpoint_sha256',
    'data_kind', 'comparison_track', 'nms_policy', 'reproduce_command',
)


def json_safe(value):
    """수치 결측은 null로 기록한다. NaN/Inf 발생 사건은 Recorder가 별도 남긴다."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(json_safe(value), sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value, *, exclusive=False):
    """동일 파일시스템 임시 파일을 사용한다. 불변 설정의 기존 파일은 덮지 않는다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(json_safe(value), stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temp, path)  # 동시 생성 시 한 프로세스만 성공한다.
            os.unlink(temp)
        else:
            os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def registry():
    return json.loads((Path(__file__).resolve().parents[2]/'configs/experiments/model_registry.json').read_text())


def validate_config(config):
    missing = set(REQUIRED_CONFIG)-set(config)
    if missing:
        raise ValueError('Missing experiment fields: '+','.join(sorted(missing)))
    model = registry().get(config['model_name'])
    if model is None or config['model_family'] != model['model_family']:
        raise ValueError('Unknown model/family')
    if (config['official_repo'], config['official_commit']) != (model['official_repo'], model['official_commit']):
        raise ValueError('Official source differs from pinned team registry')
    if config['data_kind'] not in ('REAL', 'SYNTHETIC'):
        raise ValueError('Explicit REAL/SYNTHETIC data kind required')
    if config['comparison_track'] not in ('OFFICIAL_BASELINE', 'COMMON_INPUT', 'OPTIMIZED'):
        raise ValueError('Unknown comparison track')
    for key in ('manifest_sha256', 'annotation_sha256', 'class_mapping_sha256', 'evaluation_set_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', config[key]):
            raise ValueError('SHA-256 required: '+key)
    ids=config['evaluation_ids_sha256']
    if set(ids)!={'validation','test'} or any(not re.fullmatch('[0-9a-f]{64}',v) for v in ids.values()) or digest(ids)!=config['evaluation_set_sha256']:
        raise ValueError('Frozen validation/test evaluation IDs fingerprint required')
    if config['batch_size'] < 1 or config['epochs'] < 0:
        raise ValueError('Invalid batch size/epochs')
    if config['nms_policy'] != PROTOCOL['nms_policy']:
        raise ValueError('Declare the common NMS handoff contract')
    return dict(config)


def index_records(records, *, split=None):
    """빠진 예측을 정상으로 채우지 않기 위해 ID 중복과 Split을 엄격하게 검사한다."""
    result = {}
    for row in records:
        key = row.get('image_id')
        if not isinstance(key, str) or not key or key in result:
            raise ValueError('Invalid/duplicate image_id')
        if split is not None and row.get('split') != split:
            raise ValueError('Evaluation split mismatch')
        result[key] = row
    return result


def aligned_records(gt, predictions, split):
    ground = index_records(gt, split=split)
    predicted = index_records(predictions, split=split)
    if set(ground) != set(predicted):
        raise ValueError('Prediction IDs must exactly match the declared evaluation set')
    for key in ground:
        if predicted[key].get('coordinate_space') != 'original':
            raise ValueError('Restore predictions to original coordinates first')
    return [(ground[k], predicted[k]) for k in sorted(ground)]


@dataclass(frozen=True)
class ThresholdPolicy:
    """Validation 출처와 평가 규약 해시를 함께 고정하는 이진 판정 정책."""
    image: float | None = None
    pixel: float | None = None
    pixel_score_range: tuple | None = None
    detection: float | None = None
    source_split: str = 'validation'
    validation_ids_sha256: str = ''
    validation_product_hashes: tuple = ()
    protocol_sha256: str = ''
    data_kind: str = 'REAL'

    def validate(self, data_kind):
        if data_kind not in ('REAL','SYNTHETIC'):
            raise ValueError('Explicit REAL/SYNTHETIC evaluation required')
        if self.source_split != 'validation' or self.protocol_sha256 != digest(PROTOCOL):
            raise ValueError('Threshold must be frozen on validation under the same protocol')
        if self.data_kind != data_kind or not re.fullmatch('[0-9a-f]{64}', self.validation_ids_sha256):
            raise ValueError('Threshold provenance/data kind mismatch')
        if self.pixel_score_range is not None:
            if len(self.pixel_score_range)!=2 or not np.isfinite(self.pixel_score_range).all() or self.pixel_score_range[1]<=self.pixel_score_range[0]:
                raise ValueError('Invalid frozen pixel score range')
        for value in (self.image, self.pixel, self.detection):
            if value is not None and not np.isfinite(value):
                raise ValueError('Finite threshold or explicit N/A required')
        return self

    def validate_cohort(self, pairs, split):
        if any(not g.get('product_id') for g,p in pairs):
            raise ValueError('Declared product_id is required for leakage checks')
        if split=='validation' and digest([g['image_id'] for g,p in pairs])!=self.validation_ids_sha256:
            raise ValueError('Validation cohort differs from threshold calibration cohort')
        if split=='test' and set(self.validation_product_hashes)&{digest(g['product_id']) for g,p in pairs}:
            raise ValueError('Declared product groups leak between validation and test')

    def to_dict(self):
        return asdict(self)
