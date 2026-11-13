"""추가 기록형 실험 Recorder. 학습 코드는 팀원이 연결하며 합성 Run은 완료 학습으로 표시하지 않는다."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import csv
import fcntl
import json
import os
import platform
import subprocess
import time
import traceback
import uuid
import numpy as np
import psutil
import torch
from .contracts import atomic_json, digest, file_sha256, json_safe, validate_config, PROTOCOL

STATES = ('CREATED', 'RUNNING', 'COMPLETED', 'FAILED', 'INTERRUPTED', 'PARTIAL')
HISTORY = ('epoch', 'step', 'phase', 'metric', 'value', 'nonfinite', 'elapsed_seconds', 'time_utc')


def utc():
    return datetime.now(timezone.utc).isoformat()


def environment():
    """학습 장치의 관측값을 기록한다. GPU 부재를 임의의 GPU 사양으로 채우지 않는다."""
    gpu = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            gpu.append({'index': i, 'name': p.name, 'vram_bytes': p.total_memory})
    cpu=platform.processor() or platform.machine()
    if Path('/proc/cpuinfo').exists():
        cpu=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),cpu)
    return dict(python=platform.python_version(), system=platform.platform(),
        cpu=cpu, logical_cpus=psutil.cpu_count(),
        ram_bytes=psutil.virtual_memory().total, torch_version=torch.__version__,
        cuda_version=torch.version.cuda, gpu=gpu, torch_threads=torch.get_num_threads())


class ExperimentRecorder:
    """한 Run의 설정은 불변이다. 기존 결과 재사용은 명시적 resume과 설정 해시 일치가 필요하다."""
    @classmethod
    def create(cls, root, config):
        config = validate_config(config)
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now(timezone.utc).strftime('run_%Y%m%dT%H%M%S_')+uuid.uuid4().hex
        path = root/run_id
        path.mkdir(exist_ok=False)
        code={p.name:file_sha256(p) for p in Path(__file__).parent.glob('*.py')}
        config.update(infrastructure_sha256=digest(code), project_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()), run_id=run_id, evaluation_protocol=PROTOCOL, protocol_sha256=digest(PROTOCOL))
        atomic_json(path/'config.json', config, exclusive=True)
        atomic_json(path/'environment.json', environment(), exclusive=True)
        with (path/'training_history.csv').open('x', newline='') as stream:
            csv.DictWriter(stream, fieldnames=HISTORY).writeheader()
        atomic_json(path/'run.json', dict(run_id=run_id, status='CREATED', created_utc=utc(),
                    config_sha256=file_sha256(path/'config.json'), training_executed=False), exclusive=True)
        return cls(path)

    def __init__(self, run_dir):
        self.path = Path(run_dir)
        self.config = json.loads((self.path/'config.json').read_text())
        self.started = time.perf_counter()
        self._verify_config()

    @contextmanager
    def lock(self):
        with (self.path/'.recorder.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                self._verify_config()
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _verify_config(self):
        self.state = json.loads((self.path/'run.json').read_text())
        if file_sha256(self.path/'config.json') != self.state['config_sha256']:
            raise ValueError('Immutable config changed; create a new run')

    def _event(self, event, **details):
        with (self.path/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(json_safe(dict(time_utc=utc(), event=event, **details)),
                                    ensure_ascii=False, allow_nan=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())

    def start(self, *, resume=False):
        with self.lock():
            allowed = ('CREATED', 'PARTIAL', 'INTERRUPTED', 'FAILED') if resume else ('CREATED',)
            if self.state['status'] not in allowed:
                raise ValueError('Invalid start/resume transition')
            self.state.update(status='RUNNING', updated_utc=utc())
            atomic_json(self.path/'run.json', self.state)
            self._event('RESUMED' if resume else 'STARTED')
        return self

    @classmethod
    def resume(cls, run_dir, expected_config_sha256):
        obj = cls(run_dir)
        if obj.state['config_sha256'] != expected_config_sha256:
            raise ValueError('Resume config fingerprint mismatch')
        return obj.start(resume=True)

    def log(self, *, epoch, step, phase, metrics):
        """Loss는 long CSV로 기록한다. 없는 Loss는 보내지 않고 NaN/Inf는 null과 사건으로 남긴다."""
        if phase not in ('train', 'validation') or epoch < 0 or step < 0:
            raise ValueError('Invalid training history coordinates')
        with self.lock():
            if self.state['status'] != 'RUNNING':
                raise ValueError('Run must be RUNNING')
            with (self.path/'training_history.csv').open('a', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=HISTORY)
                for metric, value in metrics.items():
                    if value is None:
                        continue
                    value = float(value)
                    invalid = not np.isfinite(value)
                    writer.writerow(dict(epoch=epoch, step=step, phase=phase, metric=metric,
                        value='' if invalid else value, nonfinite=invalid,
                        elapsed_seconds=time.perf_counter()-self.started, time_utc=utc()))
                    if invalid:
                        self._event('NONFINITE_METRIC', metric=metric, epoch=epoch, step=step, phase=phase)
                stream.flush()
                os.fsync(stream.fileno())

    def artifact(self, name, value):
        """동일 Run의 측정 파일도 실수로 덮지 않도록 파일명은 한 번만 사용한다."""
        if Path(name).name != name or not name.endswith('.json') or name in ('config.json', 'environment.json', 'run.json'):
            raise ValueError('Use a safe artifact JSON basename')
        with self.lock():
            atomic_json(self.path/name, value, exclusive=True)

    def checkpoint(self, path, *, epoch=None, role='candidate'):
        """가중치를 생성/복사하지 않고 실제 파일 크기·SHA와 Validation 선택 역할을 기록한다."""
        p = Path(path)
        record = dict(path=str(p), sha256=file_sha256(p), bytes=p.stat().st_size,
                      epoch=epoch, role=role, time_utc=utc())
        with self.lock():
            current = json.loads((self.path/'artifacts.json').read_text()) if (self.path/'artifacts.json').exists() else {'checkpoints': []}
            current['checkpoints'].append(record)
            atomic_json(self.path/'artifacts.json', current)
        return record

    def predictions(self, records):
        """배열은 NPY sidecar로 저장한다. 예측 JSONL에 원본 영상이나 GT를 임의로 섞지 않는다."""
        with self.lock():
            if self.state['status']!='RUNNING':raise ValueError('Predictions require a RUNNING run')
            existing=self.path/'predictions.jsonl'
            seen=set()
            if existing.exists():
                with existing.open() as old:
                    for line in old:seen.add(json.loads(line)['image_id'])
            with existing.open('a') as stream:
                for source in records:
                    row = dict(source)
                    if not isinstance(row.get('image_id'),str) or not row['image_id'] or row['image_id'] in seen:raise ValueError('Duplicate/invalid prediction image_id; preserve previous records')
                    seen.add(row['image_id'])
                    row['data_kind'] = self.config['data_kind']
                    for key, value in list(row.items()):
                        if isinstance(value, np.ndarray):
                            relative = Path('arrays')/(uuid.uuid4().hex+'.npy')
                            (self.path/relative).parent.mkdir(exist_ok=True)
                            np.save(self.path/relative, value, allow_pickle=False)
                            row[key] = {'array_path': relative.as_posix(), 'sha256': file_sha256(self.path/relative)}
                    stream.write(json.dumps(json_safe(row), ensure_ascii=False, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())

    def evaluation(self, split, result):
        if split not in ('validation', 'test') or result.get('split') != split:
            raise ValueError('Evaluation split mismatch')
        if result.get('evaluation_ids_sha256')!=self.config['evaluation_ids_sha256'][split]:
            raise ValueError('Evaluation image set differs from frozen config')
        if result.get('threshold_policy',{}).get('validation_ids_sha256')!=self.config['evaluation_ids_sha256']['validation']:
            raise ValueError('Threshold was not calibrated on the frozen validation IDs')
        if result.get('data_kind') != self.config['data_kind'] or result.get('protocol_sha256') != digest(PROTOCOL):
            raise ValueError('Evaluation kind/protocol mismatch')
        with self.lock():
            current = json.loads((self.path/'metrics.json').read_text()) if (self.path/'metrics.json').exists() else {}
            if split in current:
                raise FileExistsError('Preserve previous evaluation; create another run')
            current[split] = result
            atomic_json(self.path/'metrics.json', current)

    def finalize(self, status='PARTIAL', *, training_executed=False, evidence=None):
        if status not in ('COMPLETED', 'FAILED', 'INTERRUPTED', 'PARTIAL'):
            raise ValueError('Unknown terminal status')
        if status == 'COMPLETED' and (self.config['data_kind'] == 'SYNTHETIC' or not training_executed or not evidence):
            raise ValueError('COMPLETED requires actual training evidence; synthetic runs stay PARTIAL')
        with self.lock():
            if self.state['status'] not in ('RUNNING', 'CREATED'):
                raise ValueError('Terminal run cannot be silently rewritten')
            self.state.update(status=status, training_executed=training_executed,
                              evidence=evidence, updated_utc=utc(), session_seconds=time.perf_counter()-self.started)
            atomic_json(self.path/'run.json', self.state)
            self._event(status, training_executed=training_executed)

    def __enter__(self):
        return self.start()

    def __exit__(self, kind, value, tb):
        if kind:
            with self.lock():
                self._event('EXCEPTION', exception_type=kind.__name__, message=str(value),
                            traceback=''.join(traceback.format_exception(kind, value, tb)))
            self.finalize('INTERRUPTED' if issubclass(kind, KeyboardInterrupt) else 'FAILED')
        elif self.state['status'] == 'RUNNING':
            self.finalize('PARTIAL')
        return False


def load_predictions(run_dir, *, lazy=True):
    """sidecar 변조와 경로 이탈을 검사하며 allow_pickle=False로만 복원한다."""
    root = Path(run_dir).resolve()
    path = root/'predictions.jsonl'
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        for key, value in list(row.items()):
            if isinstance(value, dict) and 'array_path' in value:
                p = (root/value['array_path']).resolve()
                if not p.is_relative_to(root) or file_sha256(p) != value['sha256']:
                    raise ValueError('Prediction sidecar path/hash mismatch')
                row[key] = value if lazy else np.load(p, allow_pickle=False)
                if lazy:row['_array_root']=str(root)
        rows.append(row)
    return rows
