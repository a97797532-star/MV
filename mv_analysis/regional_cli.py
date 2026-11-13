# 한글 안내: Real-IAD 분석 파이프라인의 공통 기능입니다. 입력 자료와 설정의 기존 계약을 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Checkpointed background-aware brightness extension; old analyses remain untouched."""
import argparse,hashlib,json,os,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import cv2,numpy as np,pandas as pd
from .background_brightness import analyze,VERSION
from .core import read_image,binary_mask,save_json
cv2.setNumThreads(1)


# sample_rows: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df.
def sample_rows(df):
    # Reproducible median path per category/view/status: 300 images, no random runtime state.
    selected=[]
    for _,group in df.sort_values('image_path').groupby(['category','view','status']):selected.append(group.iloc[len(group)//2])
    return pd.DataFrame(selected).reset_index(drop=True)


# overlay: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: image, mask.
def overlay(image,mask):
    result=image.copy();tint=np.zeros_like(image);tint[:]=[20,180,20];result[mask]=cv2.addWeighted(image,.6,tint,.4,0)[mask]
    contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(result,contours,-1,(0,0,255),2)
    return cv2.cvtColor(result,cv2.COLOR_BGR2RGB)


# render_review: 자료를 그래프 또는 검수 화면으로 표시합니다.
# 입력 인수: root, out, df, policy.
def render_review(root,out,df,policy):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # Every category represented in six readable contact sheets. Additional low-confidence and priority cases.
    chosen=df.sort_values(['category','background_confidence']).groupby('category',sort=True).head(1)
    pages=[]
    for start in range(0,len(chosen),5):
        group=chosen.iloc[start:start+5];fig,axes=plt.subplots(len(group),4,figsize=(14,3.2*len(group)),squeeze=False)
        for axesrow,row in zip(axes,group.to_dict('records')):
            image=read_image(root/row['image_path']);masks,quality=__import__('mv_analysis.background_brightness',fromlist=['segment']).segment(image,True)
            axesrow[0].imshow(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));axesrow[0].set_title(f'{row["category"]}/{row["view"]}/{row["status"]}\n{quality["background_type"]}, {quality["segmentation_status"]}',fontsize=9)
            for ax,method in zip(axesrow[1:],['A','B','C']):
                if method in masks:ax.imshow(overlay(image,masks[method]))
                ax.set_title(f'Method {method}: candidate only')
            for ax in axesrow:ax.axis('off')
        fig.tight_layout();path=out/f'foreground_segmentation_examples_{start//5+1:02}.png';fig.savefig(path,dpi=110);plt.close(fig);pages.append(path.name)
    if pages:
        import shutil;shutil.copy2(out/pages[0],out/'foreground_segmentation_examples.png')
    rows=[]
    for bg,group in df.groupby('background_type'):
        rows.extend(group.sort_values('background_confidence',ascending=False).head(2).to_dict('records'))
    if rows:
        fig,axes=plt.subplots(len(rows),1,figsize=(8,3*len(rows)),squeeze=False)
        for ax,row in zip(axes[:,0],rows):
            ax.imshow(cv2.cvtColor(read_image(root/row['image_path']),cv2.COLOR_BGR2RGB));ax.set_title(f'{row["background_type"]}: {row["category"]}/{row["view"]}, confidence={row["background_confidence"]:.3f}');ax.axis('off')
        fig.tight_layout();fig.savefig(out/'background_type_examples.png',dpi=100);plt.close(fig)
    save_json(out/'review_pages.json',dict(pages=pages,scope='one lowest-confidence sample per category; additional examples by predicted background type',ground_truth_masks=False,agreement_is_accuracy=False))


# compare_groups: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: df, groupkeys.
def compare_groups(df,groupkeys):
    rows=[]
    # diff: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: x, y.
    def diff(x,y):
        if min(len(x),len(y))<2:return dict(difference=None,cohens_d=None,overlap=None)
        x=np.asarray(x,float);y=np.asarray(y,float);pooled=np.sqrt(((len(x)-1)*x.var(ddof=1)+(len(y)-1)*y.var(ddof=1))/(len(x)+len(y)-2));hx,_=np.histogram(x,np.linspace(0,256,33));hy,_=np.histogram(y,np.linspace(0,256,33))
        return dict(difference=float(y.mean()-x.mean()),cohens_d=float((y.mean()-x.mean())/pooled) if pooled>1e-10 else None,overlap=float(np.minimum(hx/hx.sum(),hy/hy.sum()).sum()))
    for key,ng in df[df.status=='NG'].groupby(groupkeys,dropna=False):
        key=(key,) if not isinstance(key,tuple) else key;ok=df[df.status=='OK']
        for col,value in zip(groupkeys,key):
            if col!='defect_type':ok=ok[ok[col]==value]
        pok=ok[ok.segmentation_status=='accepted_heuristic'];png=ng[ng.segmentation_status=='accepted_heuristic'];row=dict(zip(groupkeys,key));row.update(n_ok_all=len(ok),n_ng_all=len(ng),n_ok_product=len(pok),n_ng_product=len(png),ok_selection_fraction=len(pok)/len(ok) if len(ok) else None,ng_selection_fraction=len(png)/len(ng))
        for prefix,x,y in [('whole_all',ok.whole_mean,ng.whole_mean),('whole_paired',pok.whole_mean,png.whole_mean),('product',pok.product_mean.dropna(),png.product_mean.dropna())]:row.update({prefix+'_'+k:v for k,v in diff(x,y).items()})
        before=row['whole_paired_difference'];after=row['product_difference'];row['absolute_difference_reduction']=abs(before)-abs(after) if before is not None and after is not None else None
        row['interpretation']='insufficient_accepted_samples' if before is None or after is None else 'difference_decreased' if abs(after)<abs(before) else 'difference_persisted_or_increased';rows.append(row)
    return pd.DataFrame(rows)


# summarize: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: out, rows, source.
def summarize(out,rows,source):
    df=pd.DataFrame(rows);df.to_csv(out/'regional_brightness_per_image.csv',index=False)
    quality=[c for c in df if c.startswith(('background_','border_','foreground_','method_','segmentation_')) or c in ['image_path','category','view','status','split','product_touches_border','component_count','adaptive_lab_threshold','internal_background_candidate_fraction']]
    df[quality].to_csv(out/'foreground_segmentation_metrics.csv',index=False);df[df.segmentation_status!='accepted_heuristic'][quality].to_csv(out/'foreground_segmentation_failures.csv',index=False)
    bgcols=['image_path','category','view','status','split','background_type','background_confidence','border_gray_median','border_gray_variance','border_hsv_v_median','border_lab_l_median','product_touches_border']
    df[bgcols].to_csv(out/'background_classification.csv',index=False);df.groupby(['category','view','status','background_type']).size().rename('images').reset_index().to_csv(out/'background_distribution.csv',index=False)
    measures=[c for c in ['whole_mean','product_mean','background_mean','product_pixel_ratio','product_contrast','defect_local_difference'] if c in df]
    df.groupby(['category','view','status','defect_type','split','background_type','segmentation_status'])[measures].agg(['count','mean','std','median','min','max']).to_csv(out/'regional_brightness_summary.csv')
    df[df.status=='NG'][[c for c in df if c.startswith('defect_') or c in ['image_path','category','view','status','split','has_mask','segmentation_status']]].to_csv(out/'defect_local_contrast.csv',index=False)
    comparison=compare_groups(df,['category','defect_type','view']);comparison.to_csv(out/'brightness_before_after_comparison.csv',index=False);comparison.sort_values('absolute_difference_reduction',ascending=False).to_csv(out/'background_bias_ranking.csv',index=False)
    compare_groups(df,['category','defect_type','view','background_type']).to_csv(out/'background_stratified_comparison.csv',index=False)
    df.groupby(['category','view','status','background_type'])[measures].agg(['count','mean','std','median']).to_csv(out/'category_view_regional_comparison.csv')
    accepted=df[df.segmentation_status=='accepted_heuristic'];train=accepted[accepted.split=='train'];train.groupby(['category','view','status','background_type']).product_mean.quantile([.05,.5,.95]).unstack().to_csv(out/'train_product_augmentation_candidates.csv')
    train[train.status=='OK'].groupby(['category','view','background_type']).product_mean.quantile([.05,.5,.95]).unstack().to_csv(out/'train_normal_only_augmentation_candidates.csv')
    save_json(out/'regional_validation.json',dict(processed=len(df),segmentation_status_counts=df.segmentation_status.value_counts().to_dict(),background_counts=df.background_type.value_counts().to_dict(),accepted_product_statistics=len(accepted),uncertain_product_values_missing=bool(df.loc[df.segmentation_status!='accepted_heuristic','product_mean'].isna().all()),defect_status_counts=df.defect_status.value_counts().to_dict(),comparison_groups=len(comparison),ground_truth_foreground_available=False,method_agreement_is_not_ground_truth_iou=True,source_run=str(source)))
    original=pd.read_csv(source/'brightness_per_image.csv',usecols=['image_path','brightness']);parity=df[['image_path','whole_mean']].merge(original,on='image_path',validate='one_to_one');parity['absolute_difference']=(parity.whole_mean-parity.brightness).abs();parity.to_csv(out/'whole_brightness_reproduction.csv',index=False);save_json(out/'whole_brightness_reproduction.json',dict(images=len(parity),max_absolute_difference=float(parity.absolute_difference.max())))
    return df


# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
# 입력 인수: argv.
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--sample',action='store_true');p.add_argument('--compare-methods',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--batch-size',type=int,default=0);p.add_argument('--workers',type=int,default=1);p.add_argument('--finalize',action='store_true');p.add_argument('--validation-evidence',type=Path);a=p.parse_args(argv)
    source=json.loads((a.source_run/'run.json').read_text());root=Path(source['config']['root']);meta=pd.read_csv(a.source_run/'image_metadata_with_split.csv',keep_default_na=False)
    if a.sample:meta=sample_rows(meta)
    if not a.sample:
        if not a.validation_evidence:raise SystemExit('Full analysis requires reviewed sample evidence --validation-evidence')
        review=json.loads(a.validation_evidence.read_text())
        if not review.get('visual_review_completed') or review.get('algorithm_version')!=VERSION:raise SystemExit('Sample review missing or stale')
    policy=json.loads((a.source_run/'mask_policy.json').read_text());config=dict(source=str(a.source_run),root=str(root),sample=a.sample,compare_methods=a.compare_methods,algorithm_version=VERSION,algorithm_sha256=hashlib.sha256(Path(__file__).with_name('background_brightness.py').read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),metadata_sha256=hashlib.sha256((a.source_run/'image_metadata_with_split.csv').read_bytes()).hexdigest(),mask_policy_sha256=hashlib.sha256((a.source_run/'mask_policy.json').read_bytes()).hexdigest())
    out=a.output.resolve()
    if out==root or root in out.parents or out in root.parents:raise SystemExit('Output and dataset must not contain each other')
    if out.exists() and not a.resume:raise SystemExit('Existing output: choose fresh directory or --resume')
    out.mkdir(exist_ok=True,parents=True)
    import fcntl
    worker_lock=(out/'.regional_worker.lock').open('a')
    try:fcntl.flock(worker_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Another regional worker is active for this output')
    manifest=out/'regional_run.json'
    if manifest.exists() and json.loads(manifest.read_text())['config']!=config:raise SystemExit('Resume configuration/source mismatch')
    if not manifest.exists():save_json(manifest,dict(created=datetime.now(timezone.utc).isoformat(),config=config,versions=dict(opencv=cv2.__version__,numpy=np.__version__,pandas=pd.__version__),target=len(meta)))
    checkpoint=out/'regional_checkpoint.jsonl';done=set()
    if checkpoint.exists():
        with checkpoint.open('rb+') as f:
            while True:
                pos=f.tell();line=f.readline()
                if not line:break
                try:done.add(json.loads(line)['image_path'])
                except json.JSONDecodeError:
                    if f.read(1):raise
                    f.seek(pos);f.truncate();break
    pending=meta[~meta.image_path.isin(done)]
    if a.batch_size:pending=pending.iloc[:a.batch_size]
    # process: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: row.
    def process(row):
        try:
            stat=(root/row['image_path']).stat()
            if stat.st_size!=int(row['bytes']) or stat.st_mtime_ns!=int(row['mtime_ns']):raise ValueError('Source stat changed after metadata validation')
            image=read_image(root/row['image_path']);defect=binary_mask(read_image(root/row['mask_path'],True),policy) if row['status']=='NG' and row['mask_path'] else None
            result,_=analyze(image,row,defect,a.compare_methods);return result,None
        except Exception as exc:return None,dict(image_path=row['image_path'],error=str(exc))
    errors=[];start=time.time()
    with checkpoint.open('a') as stream,ThreadPoolExecutor(max_workers=max(1,min(4,a.workers))) as pool:
        records=pending.to_dict('records')
        for offset in range(0,len(records),20):
            for row,error in pool.map(process,records[offset:offset+20]):
                if error:errors.append(error)
                else:stream.write(json.dumps(row,allow_nan=False,default=str)+'\n');stream.flush();done.add(row['image_path'])
            print(f'regional brightness {len(done)}/{len(meta)}, errors this batch={len(errors)}, elapsed={time.time()-start:.1f}s',flush=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f');save_json(out/f'batch_{stamp}.json',dict(processed=len(pending),success=len(pending)-len(errors),errors=errors,completed=len(done),target=len(meta),elapsed_seconds=time.time()-start))
    if errors:raise RuntimeError('Image analysis errors; successful checkpoints preserved')
    if len(done)==len(meta) and (a.finalize or a.sample):
        rows=[]
        with checkpoint.open() as stream:
            for line in stream:rows.append(json.loads(line))
        df=summarize(out,rows,a.source_run)
        if a.sample:render_review(root,out,df,policy)
        print('Regional aggregate complete',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
