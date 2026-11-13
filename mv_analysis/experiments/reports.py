"""실제 Run 산출물에서 그래프와 상대 경로 Markdown을 생성한다. 없는 값은 N/A다."""
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .contracts import digest, atomic_json, file_sha256, PROTOCOL, validate_config


def read_json(path,default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else ({} if default is None else default)


def display(value):
    if value is None:return 'N/A'
    if isinstance(value,float):return f'{value:.6g}' if np.isfinite(value) else 'N/A'
    return str(value).replace('|','/').replace('\n',' ')


def table(values):
    return '\n'.join(['| 항목 | 관측값 |','|---|---|']+[f'| {k} | {display(v)} |' for k,v in values.items()])


def save_plot(fig,path,title,n,run_id):
    fig.suptitle(f'{title}\nn={n} | {run_id}',fontsize=8)
    fig.tight_layout(rect=(0,0,1,.90));fig.savefig(path,dpi=120,bbox_inches='tight');plt.close(fig)


def diagnostics(history,events):
    notes=[]
    if history.empty:notes.append('학습 이력 없음: 실제 학습 또는 Loss를 측정하지 않았다.')
    nonfinite=[e for e in events if e.get('event')=='NONFINITE_METRIC']
    if nonfinite:notes.append(f'관측: NaN/Inf 기록 {len(nonfinite)}건. 값은 결측으로 보존하며 정상 Loss로 채우지 않았다.')
    for metric in history.metric.unique() if len(history) else []:
        rows=history[history.metric.eq(metric)].copy();rows['value']=pd.to_numeric(rows.value,errors='coerce');rows=rows.dropna(subset=['value'])
        train=rows[rows.phase.eq('train')];val=rows[rows.phase.eq('validation')]
        if 'loss' in metric and len(train)>1:
            notes.append(f'관측: {metric} Train 처음 {train.value.iloc[0]:.6g} → 마지막 {train.value.iloc[-1]:.6g}. Loss 감소는 모델 성능 개선 증명이 아니다.')
            if len(val)>1 and val.value.iloc[-1]>val.value.min() and train.value.iloc[-1]<train.value.iloc[0]:
                notes.append(f'가설: {metric}의 Validation 악화와 Train 감소가 함께 관측돼 과적합 검토가 필요하다.')
        if metric in ('gradient_norm','epoch_seconds') and len(rows)>2:
            median=rows.value.median()
            if median>0 and rows.value.max()>median*10:notes.append(f'검토 신호: {metric} 최대값이 중앙값의10배 초과. 원인이나 gradient explosion을 확정하지 않는다.')
    if len(history):
        val=history[history.phase.eq('validation') & history.metric.isin(['image_auroc','pixel_auroc','map50_95','f1','aupro'])].copy()
        val['value']=pd.to_numeric(val.value,errors='coerce');val=val.dropna(subset=['value'])
        for metric,g in val.groupby('metric'):
            best=g.loc[g.value.idxmax()];notes.append(f'관측: Validation {metric} 최고값 {best.value:.6g}, epoch={best.epoch}. Test로 선정하지 않았다.')
    return notes


def generate_experiment_report(run_dir):
    root=Path(run_dir);config=read_json(root/'config.json');state=read_json(root/'run.json');env=read_json(root/'environment.json')
    if not config or not state:raise ValueError('Not a recorded run')
    metrics=read_json(root/'metrics.json');bench=read_json(root/'benchmark.json');artifacts=read_json(root/'artifacts.json')
    history=pd.read_csv(root/'training_history.csv') if (root/'training_history.csv').exists() else pd.DataFrame()
    events=[json.loads(v) for v in (root/'events.jsonl').read_text().splitlines()] if (root/'events.jsonl').exists() else []
    version=1
    while (root/('report.md' if version==1 else f'report_{version}.md')).exists():version+=1
    name='report.md' if version==1 else f'report_{version}.md';folder=root/'figures'/f'report_{version}';folder.mkdir(parents=True,exist_ok=False)
    figures=[];missing=[];prefix=f'{config["data_kind"]} | {config["model_name"]}'
    def line_plot(key,selected,title,ylabel):
        if selected.empty:missing.append(dict(plot=key,reason='NOT_MEASURED'));return
        fig,ax=plt.subplots(figsize=(6,4))
        for (phase,metric),g in selected.groupby(['phase','metric']):
            values=pd.to_numeric(g.value,errors='coerce');ax.plot(g.epoch,values,marker='.',label=phase+'/'+metric)
        ax.set_xlabel('epoch [index]');ax.set_ylabel(ylabel);ax.legend(fontsize=6)
        path=folder/(key+'.png');save_plot(fig,path,prefix+' | '+title,len(selected),config['run_id']);figures.append((title,path,'관측 이력만 표시. 합성 Run의 곡선은 실제 학습 결과가 아니다.'))
    if len(history):
        for key,mask,title,unit in [
            ('loss',history.metric.str.contains('loss'),'Train / Validation loss','loss [model-specific]'),
            ('loss_components',history.metric.str.contains('loss')&~history.metric.eq('loss_total'),'Loss components','loss [model-specific]'),
            ('learning_rate',history.metric.eq('learning_rate'),'Learning rate','learning rate'),
            ('gradient_norm',history.metric.eq('gradient_norm'),'Gradient norm','L2 norm'),
            ('epoch_seconds',history.metric.eq('epoch_seconds'),'Epoch duration','time [s]'),
            ('validation_metrics',history.phase.eq('validation')&~history.metric.str.contains('loss')&~history.metric.isin(['epoch_seconds','learning_rate','gradient_norm']),'Validation metrics','metric [0..1]')]:
            line_plot(key,history[mask],title,unit)
    else:missing.append(dict(plot='training_curves',reason='NO_TRAINING_HISTORY'))
    for split,result in metrics.items():
        if result['task']=='anomaly':
            for level in ('image','pixel'):
                for key,x,y,title in [('roc','fpr','tpr','ROC'),('pr','recall','precision','PR')]:
                    curve=result[level].get(key)
                    if curve:
                        fig,ax=plt.subplots(figsize=(5,4));ax.plot(curve[x],curve[y]);ax.set_xlabel(x+' [fraction]');ax.set_ylabel(y+' [fraction]')
                        path=folder/f'{split}_{level}_{key}.png';save_plot(fig,path,prefix+f' | {split} {level} {title}',result[level]['n'],config['run_id']);figures.append((f'{split} {level} {title}',path,'동일 GT 범위에서 계산. Pixel 곡선은 고정 Validation 구간 2048-bin 근사다.'))
                    else:missing.append(dict(plot=f'{split}_{level}_{key}',reason='NO_VALID_GT_OR_SINGLE_CLASS'))
            pro=result.get('aupro',{}).get('curve')
            if pro:
                fig,ax=plt.subplots(figsize=(5,4));ax.plot(pro['fpr'],pro['pro']);ax.set_xlabel('FPR [fraction]');ax.set_ylabel('mean region recall [fraction]');path=folder/f'{split}_aupro.png';save_plot(fig,path,prefix+' | '+split+' AUPRO',result['aupro']['region_count'],config['run_id']);figures.append(('AUPRO',path,'영역 동일 가중, FPR0~0.3 정규화. 실제 모델 검출률과 혼용하지 않는다.'))
        else:
            cm=result.get('confusion')
            if cm:
                fig,ax=plt.subplots(figsize=(6,5));arr=np.array(cm['matrix']);im=ax.imshow(arr,cmap='Blues');fig.colorbar(im,ax=ax);ax.set_xticks(range(len(cm['labels'])),cm['labels'],rotation=45,ha='right');ax.set_yticks(range(len(cm['labels'])),cm['labels']);ax.set_xlabel('predicted class');ax.set_ylabel('GT class')
                for i in range(len(arr)):
                    for j in range(len(arr)):ax.text(j,i,str(arr[i,j]),ha='center',va='center',fontsize=7)
                path=folder/f'{split}_confusion.png';save_plot(fig,path,prefix+' | '+split+' confusion',result['evaluated_images'],config['run_id']);figures.append(('Confusion matrix',path,'GT행/예측열, BACKGROUND 행은FP·열은FN. 클래스무관 IoU 매칭 표다.'))
        for key in ('category','view'):
            values=result.get('by_'+key,{})
            if values:
                names=list(values);scores=[values[n].get('f1') for n in names];valid=[(n,v) for n,v in zip(names,scores) if v is not None]
                if valid:
                    fig,ax=plt.subplots(figsize=(max(6,len(valid)*.25),4));ax.bar([n for n,v in valid],[v for n,v in valid]);ax.tick_params(axis='x',rotation=60);ax.set_xlabel(key);ax.set_ylabel('F1 [0..1]');path=folder/f'{split}_{key}.png';save_plot(fig,path,prefix+f' | {split} {key}',sum(v.get('n',0) for v in values.values()),config['run_id']);figures.append((f'{split} {key}',path,'고정 Validation Threshold의 그룹별 F1. 단일/소량 표본은 일반화 근거가 부족하다.'))
    raw=[json.loads(v) for v in (root/'predictions.jsonl').read_text().splitlines()] if (root/'predictions.jsonl').exists() else []
    if any('score' in row for row in raw):
        vals=[row['score'] for row in raw if row.get('score') is not None]
        fig,ax=plt.subplots(figsize=(6,4));ax.hist(vals,bins=min(20,max(2,len(vals))));ax.set_xlabel('anomaly image score');ax.set_ylabel('images [count]');path=folder/'scores.png';save_plot(fig,path,prefix+' | score distribution',len(vals),config['run_id']);figures.append(('Score distribution',path,'예측 점수의 분포이며 정답 라벨이나 성능 그 자체가 아니다.'))
    if bench.get('model_only'):
        fig,ax=plt.subplots(figsize=(6,4))
        for mode in ('model_only','end_to_end'):ax.hist(bench[mode]['samples_ms'],alpha=.5,label=mode)
        ax.set_xlabel('batch latency [ms]');ax.set_ylabel('measurements [count]');ax.legend();path=folder/'latency.png';save_plot(fig,path,prefix+' | latency',bench['repetitions'],config['run_id']);figures.append(('Latency distribution',path,'전처리/후처리를 분리했다. 다른 GPU나 batch/input 집합과 속도 순위를 합치지 않는다.'))
    if events:
        types=sorted({e['event'] for e in events});counts=[sum(e['event']==t for e in events) for t in types]
        fig,ax=plt.subplots(figsize=(6,4));ax.bar(types,counts);ax.tick_params(axis='x',rotation=40);ax.set_xlabel('event type');ax.set_ylabel('events [count]');path=folder/'stability_events.png';save_plot(fig,path,prefix+' | run / stability events',len(events),config['run_id']);figures.append(('Run / stability events',path,'NaN/Inf·중단·예외 등 관측 사건이다. 사건이 없다고 실제 학습 안정성이 입증된 것은 아니다.'))
    notes=diagnostics(history,events)
    sections=[f'# {config["data_kind"]} 실험 보고서 — {config["model_name"]}',
        f'Run `{config["run_id"]}` / 상태 **{state["status"]}** / 실제 학습 실행 `{state["training_executed"]}`',
        'SYNTHETIC이면 모든 점수·Loss·예측 예시는 인프라 검증용이며 실제 모델 성능으로 해석하면 안 된다.',
        '## 1. 실험 개요',table({k:config[k] for k in ('experiment_id','run_id','model_family','data_kind','comparison_track')}),
        '## 2. 모델 및 공식 구현',table({k:config[k] for k in ('model_name','official_repo','official_commit','project_commit')}),
        '## 3. 데이터와 Manifest 버전',table({k:config[k] for k in ('manifest_sha256','annotation_sha256','evaluation_set_sha256','class_mapping_sha256','split_version','crop_policy_version','model_adapter_version')}),
        '## 4. 학습 환경',table(env),
        '## 5. 학습 설정',table({k:config[k] for k in ('seed','device','batch_size','epochs','optimizer','scheduler','learning_rate','input_resolution','normalization')}),
        '기록된 checkpoint 메타데이터(가중치 파일은 별도 전달):',table({str(i):dict(v,path=Path(v['path']).name) for i,v in enumerate(artifacts.get('checkpoints',[]))}),
        '## 6. Loss 분석','\n'.join('- '+n for n in notes) or 'N/A: 학습 진단 자료 없음.']
    for number,split in ((7,'validation'),(8,'test')):
        r=metrics.get(split);summary={}
        if r:
            if r['task']=='anomaly':summary={f'{level}_{k}':r[level].get(k) for level in ('image','pixel') for k in ('n','auroc','ap','precision','recall','f1')};summary['pixel_method']=r['pixel'].get('method');summary['pixel_score_range']=r['pixel'].get('score_range');summary['scores_below_validation_range']=r['pixel'].get('scores_below_validation_range');summary['scores_above_validation_range']=r['pixel'].get('scores_above_validation_range');summary['aupro']=r['aupro']['value'];summary['pixel_exclusions']=len(r['pixel_exclusions']);summary['positive_pixels_outside_fixed_scope']=r['positive_pixels_outside_fixed_scope']
            else:summary={k:r.get(k) for k in ('images','evaluated_images','map50','map50_95','precision','recall','f1','tp','fp','fn')};summary['exclusions']=len(r['exclusions'])
            summary['threshold_policy']={k:v for k,v in r['threshold_policy'].items() if k!='validation_product_hashes'};summary['validation_product_count']=len(r['threshold_policy'].get('validation_product_hashes',[]))
        sections.extend([f'## {number}. {split.title()} 성능',table(summary) if r else 'NOT_MEASURED'])
    sections+=['## 9. 클래스별 성능',table(metrics.get('test',{}).get('per_class',{})) or 'N/A',
               '## 10. 품목·시점별 성능',table({k:{m:v.get(m) for m in ('n','auroc','ap','precision','recall','f1')} for k,v in metrics.get('test',{}).get('by_category',{}).items()}),table({k:{m:v.get(m) for m in ('n','auroc','ap','precision','recall','f1')} for k,v in metrics.get('test',{}).get('by_view',{}).items()}),
               '## 11. 예측 이미지와 그래프']
    for title,path,interpretation in figures:sections.extend([f'### {title}',f'![{title}]({path.relative_to(root).as_posix()})',interpretation])
    case_dirs=[p for p in (root/'figures').glob('cases*') if p.is_dir()]
    latest=max(case_dirs,key=lambda p:int(p.name.rsplit('_v',1)[1]) if '_v' in p.name and p.name.rsplit('_v',1)[1].isdigit() else 0) if case_dirs else root/'figures'/'cases'
    for path in sorted(latest.glob('*.png')):
        sections.extend([f'![prediction example]({path.relative_to(root).as_posix()})','내부 검토용 예측 예시. 제목의 SYNTHETIC/REAL 출처와 GT 제공 여부를 확인한다.'])
    sections+=['## 12. FP/FN 및 실패 사례',table({k:metrics.get('test',{}).get(k) for k in ('tp','fp','fn','pixel_exclusions','exclusions')}),
               '## 13. 추론 속도',table({k:bench.get(k) for k in ('subject','model_only','end_to_end','stages','model_load_seconds','hardware_sha256','batch_size','warmup','repetitions','input_set_sha256')}),
               '## 14. 모델 크기',table({k:bench.get(k) for k in ('parameters','trainable_parameters','checkpoint','memory_bank_bytes','search_index_bytes')}),
               '## 15. 메모리',table({k:bench.get(k) for k in ('peak_cpu_rss_bytes','cpu_rss_baseline_bytes','cpu_rss_delta_bytes','rss_measurement','gpu_memory')}),
               '## 16. 실패와 한계',f'상태: {state["status"]}. 실제 GPU·공식 모델 통합 여부는 별도 확인한다. 미측정 값은 N/A다.',
               table({'missing_plots':missing,'events':events}),
               '## 17. 재현 명령어','```bash',config['reproduce_command'],'```',
               '[설정](config.json) · [환경](environment.json) · [학습 이력](training_history.csv)']
    (root/name).write_text('\n\n'.join(sections)+'\n')
    atomic_json(folder/'figure_index.json',{'figures':[str(p.relative_to(root)) for _,p,_ in figures],'missing':missing})
    return root/name


def comparison_key(config):
    return tuple(config.get(k) for k in ('model_family','data_kind','comparison_track','manifest_sha256','annotation_sha256','class_mapping_sha256','evaluation_set_sha256','split_version','crop_policy_version','model_adapter_version','protocol_sha256','infrastructure_sha256'))


def pareto_indices(performance,cost):
    """높은 성능·낮은 비용을 선호하는 비지배 후보만 고른다. 최종 모델 채택 판정이 아니다."""
    return [i for i,(p,c) in enumerate(zip(performance,cost)) if not any(q>=p and d<=c and (q>p or d<c) for j,(q,d) in enumerate(zip(performance,cost)) if i!=j)]


def compare_models(runs_root,output=None,*,include_synthetic=False,allow_partial=False):
    root=Path(runs_root);groups={};excluded=[]
    if not root.is_dir():raise ValueError('Run root does not exist')
    for config_path in sorted(root.rglob('config.json')):
        p=config_path.parent
        if not (p/'run.json').exists():continue
        c=read_json(p/'config.json');s=read_json(p/'run.json');m=read_json(p/'metrics.json');b=read_json(p/'benchmark.json')
        reason=None
        try:validate_config(c)
        except (ValueError,KeyError,TypeError):
            excluded.append(dict(run_id=c.get('run_id',p.name),reason='INVALID_OR_OLD_CONFIG_CONTRACT'));continue
        if s.get('config_sha256')!=file_sha256(p/'config.json'):reason='CONFIG_HASH_MISMATCH'
        elif c.get('protocol_sha256')!=digest(PROTOCOL):reason='EVALUATION_PROTOCOL_MISMATCH'
        elif c['data_kind']=='SYNTHETIC' and not include_synthetic:reason='SYNTHETIC_EXCLUDED_FROM_REAL_COMPARISON'
        elif s.get('status')!='COMPLETED' and not (allow_partial and s.get('status')=='PARTIAL'):reason='RUN_NOT_COMPLETED'
        elif not {'validation','test'}<=set(m):reason='MISSING_VALIDATION_OR_TEST'
        if reason:excluded.append(dict(run_id=c['run_id'],reason=reason));continue
        if any(v.get('protocol_sha256')!=c['protocol_sha256'] or v.get('data_kind')!=c['data_kind'] or v.get('evaluation_ids_sha256')!=c.get('evaluation_ids_sha256',{}).get(split) for split,v in m.items()):
            excluded.append(dict(run_id=c['run_id'],reason='METRICS_CONTRACT_MISMATCH'));continue
        key=comparison_key(c)+tuple(m[split].get('evaluation_coverage_sha256') for split in ('validation','test'));score=m['validation'].get('image',{}).get('auroc') if c['model_family']=='anomaly' else m['validation'].get('map50_95')
        if score is None:excluded.append(dict(run_id=c['run_id'],reason='NO_VALIDATION_SELECTION_METRIC'));continue
        groups.setdefault(key,[]).append(dict(config=c,state=s,metrics=m,benchmark=b,path=p,selection_score=score))
    target=Path(output) if output else Path('reports/experiments/MODEL_COMPARISON.md')
    if output and target.exists():raise FileExistsError('Preserve existing comparison')
    if not output:
        i=2
        while target.exists():target=Path(f'reports/experiments/MODEL_COMPARISON_{i}.md');i+=1
    target.parent.mkdir(parents=True,exist_ok=True);figures=target.parent/('figures_'+uuid.uuid4().hex[:10]);figures.mkdir()
    lines=['# 모델 비교 보고서','직접 비교는 데이터·주석·평가집합·프로토콜·비교조건이 같은 그룹 안에서만 허용한다. SYNTHETIC은 실제 성능과 분리한다.',
           '대표 Run: Validation Image AUROC(이상탐지) 또는 Validation mAP50-95(검출) 최대, 동률이면 run_id 사전순. Test 점수로 선택하지 않는다.']
    summary=[]
    for group_number,(key,runs) in enumerate(groups.items(),1):
        selected={}
        for r in sorted(runs,key=lambda r:(-r['selection_score'],r['config']['run_id'])):selected.setdefault(r['config']['model_name'],r)
        rows=list(selected.values());lines += [f'## 그룹 {group_number}: {key[0]} / {key[1]} / {key[2]}',f'동일 조건 해시: `{digest(key)}`',
            '| model | run | image AUROC / mAP50-95 | image AP / mAP50 | pixel AUROC | pixel AP | AUPRO | F1 | benchmark subject |',
            '|---|---|---:|---:|---:|---:|---:|---:|---|']
        for r in rows:
            c=r['config'];m=r['metrics']['test'];a=m.get('image',{});p=m.get('pixel',{});main=a.get('auroc') if key[0]=='anomaly' else m.get('map50_95')
            lines.append('| '+' | '.join(display(v) for v in [c['model_name'],c['run_id'],main,a.get('ap') if key[0]=='anomaly' else m.get('map50'),p.get('auroc'),p.get('ap'),m.get('aupro',{}).get('value'),a.get('f1') if key[0]=='anomaly' else m.get('f1'),r['benchmark'].get('subject')])+' |')
            summary.append(dict(group=digest(key),model=c['model_name'],run_id=c['run_id'],data_kind=c['data_kind'],metric=main))
        for size_key,title in [('parameters','Parameter count'),('checkpoint','Checkpoint size [bytes]')]:
            measured=[]
            for r in rows:
                value=r['benchmark'].get(size_key)
                if size_key=='checkpoint':value=value.get('bytes') if value else None
                if value is not None:measured.append((r['config']['model_name'],value))
            if measured:
                fig,ax=plt.subplots(figsize=(7,4));ax.bar([v[0] for v in measured],[v[1] for v in measured]);ax.tick_params(axis='x',rotation=45);ax.set_xlabel('model');ax.set_ylabel(title);path=figures/f'group{group_number}_{size_key}_comparison.png';save_plot(fig,path,f'{key[1]} | {title}',len(measured),str(digest(key))[:12]);lines.append(f'![{title}]({path.relative_to(target.parent).as_posix()})')
            else:lines.append(title+': NOT_MEASURED')
        hardware={}
        for r in rows:
            b=r['benchmark']
            if not b.get('hardware_sha256'):continue
            h=(b['hardware_sha256'],b['batch_size'],b['input_set_sha256'],b['precision'])
            hardware.setdefault(h,[]).append(r)
        lines.append(f'속도 비교는 {len(hardware)}개 하드웨어·batch·입력 집합·dtype 그룹으로 분리했다. 서로 다른 그룹의 속도를 한 순위로 합치지 않는다.')
        for hi,(h,subset) in enumerate(hardware.items()):
            labels=[r['config']['model_name'] for r in subset];performance=[r['metrics']['test'].get('image',{}).get('auroc') if key[0]=='anomaly' else r['metrics']['test'].get('map50_95') for r in subset]
            lat=[r['benchmark']['model_only']['p50_ms'] for r in subset]
            for mode,cost,unit,title in [
                ('latency',lat,'model-only p50 [ms/batch]','Performance vs latency / Pareto'),
                ('size',[r['benchmark'].get('checkpoint',{}).get('bytes') if r['benchmark'].get('checkpoint') else None for r in subset],'checkpoint [bytes]','Performance vs checkpoint size'),
                ('vram',[max([v['peak_allocated_bytes'] for v in r['benchmark'].get('gpu_memory',{}).values() if v] or [0]) if any(r['benchmark'].get('gpu_memory',{}).values()) else None for r in subset],'peak allocated VRAM [bytes]','Peak GPU VRAM')]:
                valid=[i for i in range(len(subset)) if cost[i] is not None and performance[i] is not None]
                if not valid:lines.append(f'{title}: NOT_MEASURED');continue
                fig,ax=plt.subplots(figsize=(6,4));xx=[cost[i] for i in valid];yy=[performance[i] for i in valid]
                if mode=='vram':ax.bar([labels[i] for i in valid],xx);ax.set_ylabel(unit);ax.set_xlabel('model')
                else:
                    ax.scatter(xx,yy);front=pareto_indices(yy,xx)
                    for j,i in enumerate(valid):ax.annotate(labels[i],(xx[j],yy[j]),fontsize=7)
                    if mode=='latency':
                        for j in front:ax.scatter(xx[j],yy[j],facecolors='none',edgecolors='red',s=130)
                    ax.set_xlabel(unit);ax.set_ylabel('Image AUROC' if key[0]=='anomaly' else 'mAP50-95')
                path=figures/f'group{group_number}_hardware{hi}_{mode}.png';save_plot(fig,path,f'{key[1]} | {title}',len(valid),str(h[0])[:12]);lines.extend([f'![{title}]({path.relative_to(target.parent).as_posix()})','동일 hardware·batch·입력 집합에서의 관측이다. 합성 점은 모델 채택 근거가 아니다.'])
    lines+=['## 제외·미완료 Run',table({v['run_id']:v['reason'] for v in excluded}) or '없음','## 한계','실제 모델 성능과 다른 GPU의 속도를 혼합하지 않는다. 학습 GPU가 다르면 학습 시간/학습 Peak VRAM은 동일 하드웨어 순위가 아니다.']
    target.write_text('\n\n'.join(lines)+'\n');pd.DataFrame(summary).to_csv(figures/'comparison_rows.csv',index=False)
    atomic_json(figures/'comparison_validation.json',dict(groups=len(groups),selected_runs=len(summary),excluded=excluded,synthetic_included=include_synthetic,partial_included=allow_partial))
    return target
