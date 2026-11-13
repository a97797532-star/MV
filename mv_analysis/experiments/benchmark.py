"""순수 모델과 전처리+모델+후처리 시간을 분리하는 CPU/CUDA 벤치마크. 학습은 하지 않는다."""
from pathlib import Path
import threading
import time
import numpy as np
import psutil
import torch
from .contracts import digest, file_sha256
from .recorder import environment


def synchronize(device):
    """CUDA 비동기 실행을 타이머 양끝에서 동기화한다. 실제 GPU 검증은 별도 필요하다."""
    if torch.device(device).type == 'cuda':
        torch.cuda.synchronize(device)


class RssSampler:
    def __init__(self, interval=.005):
        self.interval=interval;self.process=psutil.Process();self.stop_event=threading.Event()
        self.baseline=self.process.memory_info().rss;self.peak=self.baseline

    def __enter__(self):
        def sample():
            while not self.stop_event.wait(self.interval):
                self.peak=max(self.peak,self.process.memory_info().rss)
        self.thread=threading.Thread(target=sample,daemon=True);self.thread.start();return self

    def __exit__(self,*args):
        self.peak=max(self.peak,self.process.memory_info().rss);self.stop_event.set();self.thread.join()


def summarize_ms(seconds,batch_size):
    values=np.asarray(seconds,float)*1000
    return dict(mean_ms=float(values.mean()),p50_ms=float(np.median(values)),p95_ms=float(np.quantile(values,.95)),
                samples_ms=values.tolist(),repetitions=len(values),batch_size=batch_size,
                throughput_images_s=float(batch_size*len(values)/(values.sum()/1000)),
                fps=float(batch_size*len(values)/(values.sum()/1000)))


def load_timed(factory,device='cpu'):
    """실제 팀원 모델 factory를 받을 때만 사용한다. 로드 시간은 정상 추론 시간에 더하지 않는다."""
    synchronize(device);start=time.perf_counter();model=factory();synchronize(device)
    return model,time.perf_counter()-start


def tensor_leaves(value):
    """배치 dict/list 안의 텐서를 순회해 실제 입력 장치를 확인한다."""
    if isinstance(value,torch.Tensor):return [value]
    if isinstance(value,dict):return [t for v in value.values() for t in tensor_leaves(v)]
    if isinstance(value,(list,tuple)):return [t for v in value for t in tensor_leaves(v)]
    return []


def validate_device(model,value,device):
    """CPU 모델을 CUDA 결과로 기록하는 오표기를 차단한다."""
    tensors=tensor_leaves(value)
    if not tensors:raise ValueError('At least one tensor model input is required for device verification')
    tensors+=list(model.parameters()) if isinstance(model,torch.nn.Module) else []
    for tensor in tensors:
        if tensor.device.type!=device.type or (device.type=='cuda' and device.index is not None and tensor.device.index!=device.index):
            raise ValueError('Actual input/model device differs from benchmark device')


def benchmark(model, inputs, *, input_ids, device='cpu', batch_size=1, warmup=3, repetitions=20,
              preprocess=None, postprocess=None, checkpoint=None, memory_bank_bytes=None,
              search_index_bytes=None, model_load_seconds=None, precision='float32'):
    if warmup<1 or repetitions<2 or batch_size<1 or not inputs or len(inputs)!=len(input_ids):
        raise ValueError('Benchmark needs explicit inputs, warmup>=1 and repeats>=2')
    device=torch.device(device)
    if device.type=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no GPU benchmark performed')
    if isinstance(model,torch.nn.Module) and model.training:raise ValueError('Call model.eval() before benchmarking')
    prep=preprocess or (lambda x:x);post=postprocess or (lambda x:x)
    def check_batch(value):
        # 가변 크기 검출의 list[Tensor]와 일반 Tensor의 실제 배치 수를 확인한다.
        if isinstance(value,torch.Tensor):n=int(value.shape[0])
        elif isinstance(value,dict):
            tensors=tensor_leaves(value);n=int(tensors[0].shape[0]) if tensors else None
        elif isinstance(value,tuple) and value and isinstance(value[0],torch.Tensor) and value[0].ndim>=4:n=int(value[0].shape[0])
        else:n=len(value) if isinstance(value,(list,tuple)) else None
        if n is None or n!=batch_size:raise ValueError('Declared batch size differs from model inputs')
        validate_device(model,value,device)
    stage_times={'preprocess':[],'model':[],'postprocess':[]};mode={};gpu={}
    module_parameters=list(model.parameters()) if isinstance(model,torch.nn.Module) else []
    original_training=model.training if isinstance(model,torch.nn.Module) else None
    with torch.inference_mode(),RssSampler() as ram:
        for name in ('model_only','end_to_end'):
            prepared=[prep(v) for v in inputs] if name=='model_only' else None
            for i in range(warmup):
                x=prepared[i%len(inputs)] if prepared is not None else prep(inputs[i%len(inputs)])
                check_batch(x);prediction=model(x)
                if name=='end_to_end':post(prediction)
                synchronize(device)
            if device.type=='cuda':torch.cuda.reset_peak_memory_stats(device)
            times=[]
            for i in range(repetitions):
                raw=inputs[i%len(inputs)];synchronize(device);start=time.perf_counter()
                if name=='model_only':
                    x=prepared[i%len(inputs)];check_batch(x);model(x);synchronize(device)
                else:
                    x=prep(raw);check_batch(x);synchronize(device);a=time.perf_counter()
                    prediction=model(x);synchronize(device);b=time.perf_counter()
                    post(prediction);synchronize(device);c=time.perf_counter()
                    stage_times['preprocess'].append(a-start);stage_times['model'].append(b-a);stage_times['postprocess'].append(c-b)
                times.append(time.perf_counter()-start)
            mode[name]=summarize_ms(times,batch_size)
            gpu[name]=dict(peak_allocated_bytes=int(torch.cuda.max_memory_allocated(device)),peak_reserved_bytes=int(torch.cuda.max_memory_reserved(device))) if device.type=='cuda' else None
    info=environment();hardware=dict(device_type=device.type,cpu=info['cpu'],logical_cpus=info['logical_cpus'],torch_threads=info['torch_threads'],torch_version=info['torch_version'],cuda_version=info['cuda_version'],gpu=info['gpu'])
    hardware['selected_gpu']=info['gpu'][device.index if device.index is not None else torch.cuda.current_device()] if device.type=='cuda' else None
    size=None if checkpoint is None else dict(bytes=Path(checkpoint).stat().st_size,sha256=file_sha256(checkpoint))
    return dict(status='MEASURED',device=str(device),hardware=hardware,hardware_sha256=digest(hardware),
        input_set_sha256=digest(list(input_ids)),batch_size=batch_size,warmup=warmup,repetitions=repetitions,
        precision=precision,input_shapes=[list(v.shape) if isinstance(v,torch.Tensor) else 'variable_list' for v in inputs],
        model_only=mode['model_only'],end_to_end=mode['end_to_end'],
        stages={k:summarize_ms(v,batch_size) for k,v in stage_times.items()},
        parameters=sum(p.numel() for p in module_parameters) if isinstance(model,torch.nn.Module) else None,
        trainable_parameters=sum(p.numel() for p in module_parameters if p.requires_grad) if isinstance(model,torch.nn.Module) else None,
        checkpoint=size,memory_bank_bytes=memory_bank_bytes,search_index_bytes=search_index_bytes,
        model_load_seconds=model_load_seconds,peak_cpu_rss_bytes=ram.peak,cpu_rss_baseline_bytes=ram.baseline,
        cpu_rss_delta_bytes=max(0,ram.peak-ram.baseline),rss_measurement='sampled_process_RSS_5ms_not_exact_model_memory',
        gpu_memory=gpu,original_model_training=original_training,training_executed=False)
