"""실제 모델 없이 공통 평가·기록·좌표·보고의 성공/실패 계약을 검증한다."""
import copy,json,sys
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
import torch
from mv_analysis.experiments.contracts import PROTOCOL,digest,file_sha256,ThresholdPolicy,atomic_json
from mv_analysis.experiments.recorder import ExperimentRecorder,load_predictions
from mv_analysis.experiments.demo import example_config,synthetic_records,synthetic_predictions
from mv_analysis.experiments.anomaly import binary_metrics,aupro,calibrate_anomaly,evaluate_anomaly
from mv_analysis.experiments.detection import calibrate_detection,evaluate_detection
from mv_analysis.experiments.geometry import restore_boxes,restore_map,validate_boxes
from mv_analysis.experiments.benchmark import benchmark,synchronize
from mv_analysis.experiments.reports import generate_experiment_report,compare_models,pareto_indices
from mv_analysis.experiments.visualization import visualize_anomaly,visualize_detection
from mv_analysis.experiments.integration import ModelIntegration
torch.set_num_threads(1)

@pytest.fixture
def anomaly_data():
 vg,_=synthetic_records('validation');vp=synthetic_predictions(vg,'anomaly');tg,images=synthetic_records('test');tp=synthetic_predictions(tg,'anomaly')
 policy=calibrate_anomaly(vg,vp,data_kind='SYNTHETIC');return vg,vp,tg,tp,policy,images

@pytest.fixture
def detection_data():
 vg,_=synthetic_records('validation');vp=synthetic_predictions(vg,'detection');tg,images=synthetic_records('test');tp=synthetic_predictions(tg,'detection');classes={'AK':0,'BX':1}
 policy=calibrate_detection(vg,vp,classes,data_kind='SYNTHETIC');return vg,vp,tg,tp,classes,policy,images


def test_run_unique_and_recovery(tmp_path):
 a=ExperimentRecorder.create(tmp_path,example_config('PatchCore')).start();b=ExperimentRecorder.create(tmp_path,example_config('PatchCore'));assert a.path!=b.path
 a.log(epoch=0,step=1,phase='train',metrics={'loss_total':1.,'learning_rate':.01});a.finalize('INTERRUPTED')
 c=ExperimentRecorder.resume(a.path,a.state['config_sha256']);assert c.state['status']=='RUNNING';assert len((a.path/'training_history.csv').read_text().splitlines())==3
 with pytest.raises(ValueError):ExperimentRecorder.resume(a.path,'bad')
 with pytest.raises(ValueError):c.finalize('COMPLETED',training_executed=True,evidence={'fake':True})
 c.finalize('PARTIAL');assert c.state['status']=='PARTIAL'


def test_loss_nonfinite_and_prediction_sidecars(tmp_path):
 r=ExperimentRecorder.create(tmp_path,example_config('UniAD')).start();r.log(epoch=0,step=1,phase='train',metrics={'loss_total':float('nan'),'gradient_norm':float('inf')})
 assert 'NONFINITE_METRIC' in (r.path/'events.jsonl').read_text();assert 'nan' not in (r.path/'training_history.csv').read_text().lower()
 r.predictions([dict(image_id='one',split='test',score_map=np.ones((3,3)))])
 rows=load_predictions(r.path,lazy=False);assert rows[0]['score_map'].shape==(3,3)
 lazy=load_predictions(r.path,lazy=True);assert 'array_path' in lazy[0]['score_map']
 r.artifact('benchmark.json',{'missing':float('inf')});assert json.loads((r.path/'benchmark.json').read_text())['missing'] is None
 with pytest.raises(FileExistsError):r.artifact('benchmark.json',{})
 with pytest.raises(ValueError):r.artifact('../config.json',{})


def test_context_failed_interrupted_and_tampered_config(tmp_path):
 r=ExperimentRecorder.create(tmp_path,example_config('YOLO11'))
 with pytest.raises(RuntimeError):
  with r:raise RuntimeError('synthetic failure')
 assert json.loads((r.path/'run.json').read_text())['status']=='FAILED'
 report=generate_experiment_report(r.path);assert 'FAILED' in report.read_text() and 'NOT_MEASURED' in report.read_text()
 q=ExperimentRecorder.create(tmp_path,example_config('YOLO11'))
 with pytest.raises(KeyboardInterrupt):
  with q:raise KeyboardInterrupt()
 assert json.loads((q.path/'run.json').read_text())['status']=='INTERRUPTED'
 config=json.loads((q.path/'config.json').read_text());config['seed']=999;atomic_json(q.path/'config.json',config)
 with pytest.raises(ValueError):ExperimentRecorder(q.path)


def test_image_metrics_and_na():
 r=binary_metrics([0,1],[.1,.9],.5);assert r['auroc']==1 and r['ap']==1 and r['f1']==1
 assert binary_metrics([1,1],[.2,.8])['auroc'] is None
 assert binary_metrics([],[])['ap'] is None
 assert binary_metrics([0,0],[.2,.8])['ap'] is None
 with pytest.raises(ValueError):binary_metrics([0],[float('inf')])


def test_anomaly_pixels_aupro_and_missing_ng(anomaly_data):
 vg,vp,tg,tp,policy,_=anomaly_data;r=evaluate_anomaly(tg,tp,policy,split='test',data_kind='SYNTHETIC')
 assert r['image']['n']==10 and r['image']['auroc']==1 and r['pixel']['auroc']==1 and r['pixel']['ap']==1 and r['pixel']['f1']==1 and r['aupro']['value']==1
 assert r['pixel_images']==8 and {v['reason'] for v in r['pixel_exclusions']}=={'NG_MISSING','NG_PRESENT_EMPTY'}
 assert r['pixel']['method'].startswith('HISTOGRAM_APPROX')
 mask=np.zeros((5,5),bool);mask[1,1]=1;score=mask.astype(float)
 assert aupro([(mask,score,np.ones_like(mask))])['value']==1
 assert aupro([])['value'] is None
 assert aupro([(mask,score,mask)])['value'] is None


def test_threshold_provenance_test_leakage_and_missing_predictions(anomaly_data):
 vg,vp,tg,tp,p,_=anomaly_data
 with pytest.raises(ValueError):calibrate_anomaly(tg,tp,data_kind='SYNTHETIC')
 with pytest.raises(ValueError):evaluate_anomaly(tg,tp,replace(p,source_split='test'),split='test',data_kind='SYNTHETIC')
 with pytest.raises(ValueError):evaluate_anomaly(tg,tp,p,split='test',data_kind='REAL')
 with pytest.raises(ValueError):evaluate_anomaly(tg,tp[:-1],p,split='test',data_kind='SYNTHETIC')
 bad=copy.deepcopy(tg);bad[0]['product_id']=vg[0]['product_id']
 with pytest.raises(ValueError):evaluate_anomaly(bad,tp,p,split='test',data_kind='SYNTHETIC')
 tp=copy.deepcopy(tp);tp[0]['score']=float('nan')
 with pytest.raises(ValueError):evaluate_anomaly(tg,tp,p,split='test',data_kind='SYNTHETIC')


def test_unobserved_score_map_not_filled_as_normal(anomaly_data):
 _,_,gt,pred,policy,_=anomaly_data;pred=copy.deepcopy(pred);pred[0]['score_map'][0,0]=np.nan
 r=evaluate_anomaly(gt,pred,policy,split='test',data_kind='SYNTHETIC');assert any(v['reason']=='UNOBSERVED_OR_NONFINITE_IN_GT_SCOPE' for v in r['pixel_exclusions'])
 gt=copy.deepcopy(gt);gt[0]['evaluation_mask']=np.ones((24,24),bool);gt[0]['evaluation_mask'][0,0]=False
 r=evaluate_anomaly(gt,pred,policy,split='test',data_kind='SYNTHETIC');assert r['pixel_images']==8


def test_no_pixel_maps_are_na(anomaly_data):
 _,_,g,p,policy,_=anomaly_data;p=[{k:v for k,v in r.items() if k!='score_map'} for r in p]
 r=evaluate_anomaly(g,p,policy,split='test',data_kind='SYNTHETIC');assert r['pixel']['auroc'] is None and r['aupro']['value'] is None


def test_detection_coco_map_counts_and_exclusion(detection_data):
 _,_,gt,pred,classes,policy,_=detection_data;r=evaluate_detection(gt,pred,classes,policy,split='test',data_kind='SYNTHETIC')
 assert r['map50']==pytest.approx(1) and r['map50_95']==pytest.approx(1) and r['tp']==3 and r['fp']==0 and r['fn']==0
 assert r['evaluated_images']==8 and len(r['exclusions'])==2 and r['per_class']['BX']['ap'] is None
 policy=replace(policy,detection=.3);r=evaluate_detection(gt,pred,classes,policy,split='test',data_kind='SYNTHETIC');assert r['fp']==1 and r['confusion']['matrix'][-1][1]==1


def test_detection_wrong_class_and_empty_predictions(detection_data):
 _,_,g,p,classes,policy,_=detection_data;p=copy.deepcopy(p)
 for row in p:row['labels']=[1]*len(row['labels'])
 r=evaluate_detection(g,p,classes,policy,split='test',data_kind='SYNTHETIC');assert r['map50']==0 and r['tp']==0 and r['fn']==3 and r['fp']==3
 for row in p:row.update(boxes=[],labels=[],scores=[])
 r=evaluate_detection(g,p,classes,policy,split='test',data_kind='SYNTHETIC');assert r['map50']==0 and r['fn']==3
 only=[r for r in g if r['status']=='OK'];pp=[r for r in p if r['image_id'] in {x['image_id'] for x in only}]
 assert evaluate_detection(only,pp,classes,policy,split='test',data_kind='SYNTHETIC')['map50'] is None


@pytest.mark.parametrize('mutation',['box','score','class','coordinate'])
def test_detection_invalid_inputs(detection_data,mutation):
 _,_,g,p,c,t,_=detection_data;p=copy.deepcopy(p);row=next(r for r in p if r['boxes'] and r['scores'][0]>.5)
 if mutation=='box':row['boxes'][0][2]=999
 elif mutation=='score':row['scores'][0]=float('inf')
 elif mutation=='class':row['labels'][0]=99
 else:row['coordinate_space']='model_input'
 with pytest.raises(ValueError):evaluate_detection(g,p,c,t,split='test',data_kind='SYNTHETIC')


def test_inverse_geometry_and_categorical_map():
 boxes,keep,audit=restore_boxes([[.5,.5,.5,.5]],original_hw=(100,100),crop_xyxy=(10,20,50,60),input_hw=(80,80),scale_xy=(2,2),box_format='cxcywh',normalized=True)
 np.testing.assert_allclose(boxes,[[20,30,40,50]]);assert keep.tolist()==[True]
 clipped,keep,audit=restore_boxes([[-5,0,10,10],[90,90,100,100]],original_hw=(100,100),crop_xyxy=(10,20,50,60),input_hw=(80,80),scale_xy=(2,2))
 assert audit['clipped']==2 and audit['removed']==1 and len(clipped)==1
 values,observed=restore_map(np.ones((8,8)),original_hw=(20,20),crop_xyxy=(2,3,10,11),input_hw=(8,8));assert np.isnan(values[0,0]) and observed.sum()==64
 mask,_=restore_map(np.ones((8,8)),original_hw=(20,20),crop_xyxy=(2,3,10,11),input_hw=(8,8),categorical=True);assert mask.dtype==bool and mask.sum()==64
 with pytest.raises(ValueError):restore_boxes([],original_hw=(100,100),crop_xyxy=(1,1,9,9),input_hw=(80,80),scale_xy=(2,2))
 with pytest.raises(ValueError):validate_boxes([[0,0,2,2]],[True],(8,8),{0,1})


def test_cpu_benchmark_checkpoint_and_cuda_sync(tmp_path,monkeypatch):
 model=torch.nn.Linear(4,2).eval();checkpoint=tmp_path/'synthetic.bin';checkpoint.write_bytes(b'SYNTHETIC')
 r=benchmark(model,[torch.ones(1,4)],input_ids=['fixed'],warmup=1,repetitions=3,checkpoint=checkpoint)
 assert r['parameters']==10 and r['trainable_parameters']==10 and r['checkpoint']['bytes']==9
 assert r['model_only']['p95_ms']>=r['model_only']['p50_ms'] and r['end_to_end']['throughput_images_s']>0
 assert r['peak_cpu_rss_bytes']>=r['cpu_rss_baseline_bytes'] and r['gpu_memory']['model_only'] is None
 called=[];monkeypatch.setattr(torch.cuda,'synchronize',lambda d:called.append(str(d)));synchronize('cuda:0');assert called==['cuda:0']
 with pytest.raises(ValueError):benchmark(model,[torch.ones(2,4)],input_ids=['x'],warmup=1,repetitions=2,batch_size=1)
 with pytest.raises(ValueError):benchmark(model.train(),[torch.ones(1,4)],input_ids=['x'])


def test_recorder_evaluation_frozen_ids(tmp_path,anomaly_data):
 vg,vp,tg,tp,policy,_=anomaly_data;r=ExperimentRecorder.create(tmp_path,example_config('UniAD')).start();metrics=evaluate_anomaly(tg,tp,policy,split='test',data_kind='SYNTHETIC');r.evaluation('test',metrics)
 with pytest.raises(FileExistsError):r.evaluation('test',metrics)
 q=ExperimentRecorder.create(tmp_path,example_config('UniAD')).start();bad=copy.deepcopy(metrics);bad['evaluation_ids_sha256']=digest('wrong')
 with pytest.raises(ValueError):q.evaluation('test',bad)


def test_visualization_and_report_links(tmp_path,anomaly_data,detection_data):
 vg,vp,tg,tp,policy,images=anomaly_data;r=ExperimentRecorder.create(tmp_path/'runs',example_config('UniAD')).start()
 r.log(epoch=0,step=0,phase='train',metrics={'loss_total':1.,'learning_rate':.01});r.log(epoch=0,step=0,phase='validation',metrics={'loss_total':.8})
 r.evaluation('validation',evaluate_anomaly(vg,vp,policy,split='validation',data_kind='SYNTHETIC'));r.evaluation('test',evaluate_anomaly(tg,tp,policy,split='test',data_kind='SYNTHETIC'))
 path=r.path/'figures/cases/one.png';visualize_anomaly(images[tg[0]['image_id']],tg[0],tp[0],model_name='UniAD',threshold=policy.pixel,output=path,data_kind='SYNTHETIC');r.finalize('PARTIAL')
 report=generate_experiment_report(r.path);second=generate_experiment_report(r.path);assert second!=report
 import re
 for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',report.read_text()):assert (report.parent/target).exists()
 assert 'SYNTHETIC' in report.read_text() and path.stat().st_size>0
 _,_,g,p,c,t,im=detection_data;visualize_detection(im[g[0]['image_id']],g[0],p[0],c,t,model_name='YOLO11',output=tmp_path/'detection.png',data_kind='SYNTHETIC')


def test_comparison_manifest_hardware_synthetic_and_validation_selection(tmp_path,anomaly_data):
 vg,vp,tg,tp,policy,_=anomaly_data
 def create(name,manifest,selection,gpu,test_score):
  config=example_config(name);config['manifest_sha256']=manifest;r=ExperimentRecorder.create(tmp_path/'runs',config).start()
  val=evaluate_anomaly(vg,vp,policy,split='validation',data_kind='SYNTHETIC');test=evaluate_anomaly(tg,tp,policy,split='test',data_kind='SYNTHETIC');val['image']['auroc']=selection;test['image']['auroc']=test_score
  r.evaluation('validation',val);r.evaluation('test',test);r.artifact('benchmark.json',dict(hardware_sha256=gpu,batch_size=1,input_set_sha256='fixed',precision='float32',model_only=dict(p50_ms=1),gpu_memory={}))
  r.finalize('PARTIAL');return r
 a=create('UniAD',digest('a'),.8,'GPU-A',1.);b=create('UniAD',digest('a'),.9,'GPU-A',.2);c=create('Dinomaly',digest('a'),.8,'GPU-B',.5);d=create('INP-Former',digest('b'),.8,'GPU-A',1.)
 path=compare_models(tmp_path/'runs',tmp_path/'excluded.md');assert 'SYNTHETIC_EXCLUDED' in path.read_text()
 report=compare_models(tmp_path/'runs',tmp_path/'compare.md',include_synthetic=True,allow_partial=True);text=report.read_text()
 assert b.config['run_id'] in text and a.config['run_id'] not in text
 assert '그룹 2' in text and '2개 하드웨어' in text
 assert pareto_indices([.8,.9,.7],[2,3,3])==[0,1]
 with pytest.raises(FileExistsError):compare_models(tmp_path/'runs',tmp_path/'compare.md')


def test_no_model_implementation_is_faked():
 for method,args in [('build_model',({},)),('preprocessing',([],{})),('training_step',(None,None,None)),('predict_original',(None,None)),('run_validation',(None,None,None))]:
  with pytest.raises(NotImplementedError):getattr(ModelIntegration(),method)(*args)


def test_aupro_keeps_vertical_fpr_segments_and_equal_region_weight():
 mask=np.zeros((8,8),bool);mask[1,1]=True;mask[5:7,5:7]=True
 score=np.full((8,8),.5);score[mask]=0;score[1,1]=1
 result=aupro([(mask,score,np.ones_like(mask))])
 assert result['region_count']==2 and result['value']==pytest.approx(.5)


def test_class_map_and_original_grid_rejected(detection_data,anomaly_data):
 _,_,g,p,c,t,_=detection_data
 with pytest.raises(ValueError):evaluate_detection(g,p,{'AK':1,'BX':2},t,split='test',data_kind='SYNTHETIC')
 _,_,g,p,t,_=anomaly_data;p=copy.deepcopy(p);p[0]['score_map']=np.zeros((4,4))
 with pytest.raises(ValueError):evaluate_anomaly(g,p,t,split='test',data_kind='SYNTHETIC')


def test_sidecar_tamper_and_protocol_mismatch(tmp_path,anomaly_data):
 r=ExperimentRecorder.create(tmp_path,example_config('UniAD')).start();r.predictions([{'image_id':'one','score_map':np.zeros((4,4))}])
 row=json.loads((r.path/'predictions.jsonl').read_text());(r.path/row['score_map']['array_path']).write_bytes(b'broken')
 with pytest.raises(ValueError):load_predictions(r.path)
 _,_,g,p,t,_=anomaly_data
 with pytest.raises(ValueError):evaluate_anomaly(g,p,replace(t,protocol_sha256='wrong'),split='test',data_kind='SYNTHETIC')


@pytest.mark.parametrize('path',sorted(Path('models').glob('*/*/integration.py')))
def test_all_twelve_team_model_stubs_remain_explicitly_unimplemented(path):
 import importlib.util
 spec=importlib.util.spec_from_file_location('team_model_'+path.parent.name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 with pytest.raises(NotImplementedError):module.build_model({})


def test_cuda_branch_is_synchronized_and_peak_reset_only_mocked(monkeypatch):
 import importlib
 b=importlib.import_module('mv_analysis.experiments.benchmark');calls=[]
 monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
 monkeypatch.setattr(torch.cuda,'synchronize',lambda d:calls.append('sync'))
 monkeypatch.setattr(torch.cuda,'reset_peak_memory_stats',lambda d:calls.append('reset'))
 monkeypatch.setattr(torch.cuda,'max_memory_allocated',lambda d:123)
 monkeypatch.setattr(torch.cuda,'max_memory_reserved',lambda d:456)
 monkeypatch.setattr(b,'validate_device',lambda model,value,device:None)
 monkeypatch.setattr(b,'environment',lambda:dict(cpu='mock',logical_cpus=1,torch_threads=1,torch_version='mock',cuda_version='mock',gpu=[{'index':0,'name':'MOCK_GPU','vram_bytes':1024}]))
 r=b.benchmark(torch.nn.Identity().eval(),[torch.ones(1,4)],input_ids=['mock'],device='cuda:0',warmup=1,repetitions=2)
 assert calls.count('reset')==2 and calls.count('sync')>=12
 assert r['gpu_memory']['model_only']['peak_allocated_bytes']==123
 assert r['hardware']['selected_gpu']['name']=='MOCK_GPU'
 # 실제 CUDA tensor나 GPU를 사용한 검증으로 보고하지 않는다.


def test_unannotated_ng_does_not_hide_invalid_prediction(detection_data):
 _,_,g,p,c,t,_=detection_data;p=copy.deepcopy(p);missing=next(v['image_id'] for v in g if v['detection_status']=='MISSING_ANNOTATION');row=next(v for v in p if v['image_id']==missing);row.update(boxes=[[0,0,999,999]],labels=[0],scores=[1.])
 with pytest.raises(ValueError):evaluate_detection(g,p,c,t,split='test',data_kind='SYNTHETIC')


def test_lazy_gt_scope_and_mask_preserve_original_pixel_contract(tmp_path,anomaly_data):
 import cv2
 _,_,g,p,t,_=anomaly_data;g=copy.deepcopy(g);row=next(v for v in g if v['mask_status']=='PRESENT_POSITIVE');path=tmp_path/'original_gt.png';cv2.imwrite(str(path),row['mask'].astype(np.uint8)*255);st=path.stat();row['mask']={'original_mask_path':str(path),'source_fingerprint':f'{st.st_size}:{st.st_mtime_ns}'};row['evaluation_mask']={'crop_xyxy':[0,0,24,24]}
 r=evaluate_anomaly(g,p,t,split='test',data_kind='SYNTHETIC');assert r['pixel']['auroc']==1 and len(r['pixel_evaluated_image_ids'])==8
 row['mask']['source_fingerprint']='bad'
 with pytest.raises(ValueError):evaluate_anomaly(g,p,t,split='test',data_kind='SYNTHETIC')


def test_duplicate_predictions_and_schema_hashes_rejected(tmp_path):
 r=ExperimentRecorder.create(tmp_path,example_config('PatchCore')).start();r.predictions([dict(image_id='one',split='test',score=.2)])
 with pytest.raises(ValueError):r.predictions([dict(image_id='one',split='test',score=.3)])
 c=example_config('PatchCore');c['official_commit']='bad'
 with pytest.raises(ValueError):ExperimentRecorder.create(tmp_path,c)
 c=example_config('PatchCore');c['evaluation_set_sha256']=digest('other')
 with pytest.raises(ValueError):ExperimentRecorder.create(tmp_path,c)


def test_visualization_exclusive_pixel_edges_and_no_overwrite(tmp_path,detection_data,monkeypatch):
 import mv_analysis.experiments.visualization as view
 _,_,gt,pred,classes,policy,images=detection_data;captured=[];original=view.plt.subplots
 def spy(*args,**kwargs):
  fig,ax=original(*args,**kwargs);captured.append(ax);return fig,ax
 monkeypatch.setattr(view.plt,'subplots',spy);dest=tmp_path/'exclusive.png'
 view.visualize_detection(images[gt[0]['image_id']],gt[0],pred[0],classes,policy,model_name='YOLO11',output=dest,data_kind='SYNTHETIC')
 assert tuple(captured[0].images[0].get_extent())==(0,24,24,0)
 before=dest.read_bytes()
 with pytest.raises(FileExistsError):view.visualize_detection(images[gt[0]['image_id']],gt[0],pred[0],classes,policy,model_name='YOLO11',output=dest,data_kind='SYNTHETIC')
 assert before==dest.read_bytes()
