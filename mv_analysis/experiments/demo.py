"""공식 모델이 아닌 합성 예측과 작은 CPU 연산으로 공통 인프라만 검증한다."""
from pathlib import Path
import json
import subprocess
import time
import numpy as np
import torch
from .contracts import registry,digest,PROTOCOL
from .recorder import ExperimentRecorder
from .anomaly import calibrate_anomaly,evaluate_anomaly
from .detection import calibrate_detection,evaluate_detection
from .benchmark import benchmark,load_timed
from .visualization import visualize_anomaly,visualize_detection,select_cases
from .reports import generate_experiment_report,compare_models


def synthetic_records(split):
    """OK/NG 5시점, 양성·빈·미제공 마스크를 명시한 원본 격자 자료다."""
    gt=[];images={}
    for status in ('OK','NG'):
        for view in range(1,6):
            id=f'{split}_{status}_C{view}';mask=np.zeros((24,24),bool)
            if status=='NG' and view!=5:mask[8:11,10:13]=True
            missing=status=='NG' and view==4;empty=status=='NG' and view==5
            state='MISSING' if status=='OK' or missing else 'PRESENT_EMPTY' if empty else 'PRESENT_POSITIVE'
            boxes=[[10,8,13,11]] if status=='NG' and not missing and not empty else []
            gt.append(dict(image_id=id,product_id=split+'/'+status,category='synthetic_product',view=f'C{view}',split=split,
                status=status,mask_status=state,mask=None if state=='MISSING' else mask,
                boxes=boxes,labels=[0] if boxes else [],original_hw=(24,24),
                detection_status='OK_NEGATIVE' if status=='OK' else 'MISSING_ANNOTATION' if missing else 'EMPTY_NG_REVIEW' if empty else 'SUPERVISED_VALID'))
            image=np.full((24,24,3),180,np.uint8);image[5:19,5:19]=90;image[mask]=230;images[id]=image
    return gt,images


def synthetic_predictions(gt,family,seed=17,include_errors=False):
    rng=np.random.default_rng(seed);pred=[]
    for g in gt:
        row=dict(image_id=g['image_id'],split=g['split'],coordinate_space='original')
        if family=='anomaly':
            score_map=rng.uniform(0,.15,g['original_hw']).astype(np.float32)
            if g.get('mask') is not None:score_map[np.asarray(g['mask'])]=.85
            row.update(score=.8 if g['status']=='NG' else .1,score_map=score_map)
        else:
            row.update(boxes=list(g['boxes']),labels=list(g['labels']),scores=[.9]*len(g['boxes']))
            # 정상 시점 한 장에 합성 FP를 추가해 실패 표/그림도 실제로 생성한다.
            if g['status']=='OK' and g['view']=='C2':row.update(boxes=[[1,1,4,4]],labels=[1],scores=[.4])
        if include_errors:
            if family=='anomaly':
                if g['status']=='NG' and g['view']=='C3':
                    row['score']=.05
                    if g.get('mask') is not None:row['score_map'][g['mask']]=.05
                if g['status']=='OK' and g['view']=='C2':row['score']=.9;row['score_map'][15:17,15:17]=.95
            elif g['status']=='NG' and g['view']=='C2' and row['boxes']:row['labels']=[1];row['scores']=[.95]
        pred.append(row)
    return pred


def example_config(model_name,*,data_kind='SYNTHETIC'):
    if data_kind!='SYNTHETIC':raise ValueError('Demo config is synthetic only; real trainers must provide actual artifact hashes')
    source=registry()[model_name]
    project=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    ids={split:digest(sorted(g['image_id'] for g in synthetic_records(split)[0])) for split in ('validation','test')}
    return dict(experiment_id='shared-infrastructure-demo',model_name=model_name,**source,
        project_commit=project,manifest_sha256=digest('SYNTHETIC_MANIFEST'),annotation_sha256=digest('SYNTHETIC_GT'),
        class_mapping_sha256=digest({'AK':0,'BX':1}),evaluation_set_sha256=digest(ids),evaluation_ids_sha256=ids,
        split_version='synthetic-fixed-v1',crop_policy_version='no_crop_synthetic',model_adapter_version='synthetic-demo-v1',
        seed=17,device='cpu',batch_size=1,epochs=0,optimizer=None,scheduler=None,learning_rate=None,
        input_resolution=[24,24],normalization='synthetic RGB float01',checkpoint_path=None,checkpoint_sha256=None,
        data_kind=data_kind,comparison_track='COMMON_INPUT',nms_policy=PROTOCOL['nms_policy'],
        reproduce_command='uv run --locked python scripts/experiments/smoke_test_reporting.py')


def run_synthetic_demo(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);torch.set_num_threads(1)
    classes={'AK':0,'BX':1};summaries=[]
    for model,source in registry().items():
        recorder=ExperimentRecorder.create(root,example_config(model)).start()
        family=source['model_family']
        if model!='PatchCore':
            for epoch in range(3):
                recorder.log(epoch=epoch,step=epoch,phase='train',metrics=dict(loss_total=1/(epoch+1),loss_auxiliary=.2/(epoch+1),learning_rate=.001,gradient_norm=1.+epoch*.1,epoch_seconds=.01+epoch*.001))
                recorder.log(epoch=epoch,step=epoch,phase='validation',metrics=dict(loss_total=.8/(epoch+1),image_auroc=.8+epoch*.05))
        else:
            recorder.artifact('memory_bank.json',dict(status='NOT_BUILT',reason='No actual PatchCore training; losses are N/A'))
        policy=None;test_gt=None;test_images=None;test_predictions=None
        for split in ('validation','test'):
            gt,images=synthetic_records(split);pred=synthetic_predictions(gt,family,include_errors=True)
            if split=='validation':
                policy=calibrate_anomaly(gt,pred,data_kind='SYNTHETIC') if family=='anomaly' else calibrate_detection(gt,pred,classes,data_kind='SYNTHETIC')
                recorder.artifact('thresholds.json',policy.to_dict())
            metrics=evaluate_anomaly(gt,pred,policy,split=split,data_kind='SYNTHETIC') if family=='anomaly' else evaluate_detection(gt,pred,classes,policy,split=split,data_kind='SYNTHETIC')
            recorder.evaluation(split,metrics);recorder.predictions(pred)
            if split=='test':test_gt,test_images,test_predictions=gt,images,pred
        # 이 Conv는 공식12모델 구현이 아니다. 지연/메모리 측정 코드의 CPU 실행 검증용이다.
        tiny,load_seconds=load_timed(lambda:torch.nn.Conv2d(3,2,3,padding=1).eval())
        mock=recorder.path/'synthetic_checkpoint.bin';mock.write_bytes(b'SYNTHETIC_METADATA_ONLY_NOT_MODEL_WEIGHTS')
        recorder.checkpoint(mock,role='SYNTHETIC_NOT_TRAINED')
        bench=benchmark(tiny,[torch.zeros(1,3,24,24)],input_ids=['synthetic_fixed_input'],warmup=2,repetitions=5,
                        checkpoint=mock,model_load_seconds=load_seconds)
        bench['subject']='SYNTHETIC_TINY_CONV_NOT_OFFICIAL_MODEL';recorder.artifact('benchmark.json',bench)
        cases=select_cases(test_gt,test_predictions,metrics,3);recorder.artifact('review_cases.json',{'cases':cases})
        selected={c['image_id'] for c in cases}|{test_gt[0]['image_id'],test_gt[-1]['image_id']}
        for g,p in zip(test_gt,test_predictions):
            if g['image_id'] not in selected:continue
            output=recorder.path/'figures'/'cases'/(g['image_id']+'.png')
            if family=='anomaly':visualize_anomaly(test_images[g['image_id']],g,p,model_name=model,threshold=policy.pixel,output=output,data_kind='SYNTHETIC')
            else:visualize_detection(test_images[g['image_id']],g,p,classes,policy,model_name=model,output=output,data_kind='SYNTHETIC')
        recorder.finalize('PARTIAL',training_executed=False,evidence={'scope':'SYNTHETIC_INFRASTRUCTURE_ONLY'})
        report=generate_experiment_report(recorder.path)
        summaries.append(dict(model=model,run_dir=str(recorder.path),report=str(report),image_auroc=metrics.get('image',{}).get('auroc'),map50=metrics.get('map50'),status='PARTIAL',data_kind='SYNTHETIC'))
        print(f'SYNTHETIC: {model} / report generated',flush=True)
    comparison=compare_models(root,root/'MODEL_COMPARISON_SYNTHETIC.md',include_synthetic=True,allow_partial=True)
    result=dict(status='SYNTHETIC_INFRASTRUCTURE_PASSED',actual_model_training=False,runs=summaries,comparison=str(comparison))
    (root/'smoke_validation.json').write_text(json.dumps(result,indent=2));return result
