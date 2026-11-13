# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Summarize frozen resolution CSVs; decode only selected illustrations, never rerun metrics.

All figures/tables stay in the ignored output directory. Only source and reports
are Git candidates. Existing inputs and reports are never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault('MPLCONFIGDIR', '/tmp/mv-matplotlib')
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties

METRICS = ['psnr_db', 'ssim', 'edge_recall', 'edge_f1',
           'local_contrast_retention', 'high_frequency_proxy_retention', 'rgb_rmse']
UNITS = ['dB', 'ratio [-1,1]', 'ratio [0,1]', 'ratio [0,1]',
         'restored/native ratio', 'Laplacian energy ratio', 'intensity [0,255]']


# digest: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path.
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, default=Path('outputs/windows_preserved_20261111_v1'))
    p.add_argument('--data-root', type=Path, default=Path('dataset'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    pdf = a.report.with_suffix('.pdf')
    if a.output.exists() or a.report.exists() or pdf.exists():
        raise SystemExit('Choose new output/report names; existing results are preserved')
    inputs = [a.run/'per_view_information_loss.csv', a.run/'per_image_stepwise_changes.csv',
              a.run/'resolution_scientific_validation.json',
              Path('outputs/spatial_20261111_v7/defect_bboxes.csv'),
              Path('outputs/defect_resolution_review_20261111_v7/defect_jpg_resolution_review.csv')]
    before = {str(v): digest(v) for v in inputs}
    if not json.loads(inputs[2].read_text())['success']:
        raise SystemExit('Input scientific validation did not pass')
    a.output.mkdir(parents=True)
    df = pd.read_csv(inputs[0], usecols=['image_path','category','view','status','target','has_mask',*METRICS])
    step = pd.read_csv(inputs[1])
    boxes = pd.read_csv(inputs[3])
    roi = pd.read_csv(inputs[4])
    checks = dict(rows=len(df)==453150, images=df.image_path.nunique()==151050,
                  unique=not df.duplicated(['image_path','target']).any(),
                  targets=set(df.target)=={256,512,1024},
                  step_images=len(step)==151050 and step.image_path.nunique()==151050)
    if not all(checks.values()):
        raise SystemExit(f'Input scope failed: {checks}')
    print('Loaded frozen metrics: 453150 rows; no metric recalculation', flush=True)
    tables = {}
    for label, keys in [('overall',['target']), ('category',['category','target']),
                         ('view',['view','target']), ('status',['status','target']),
                         ('category_view_status',['category','view','status','target'])]:
        rows = []
        for key, group in df.groupby(keys, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            for metric in METRICS:
                s = group[metric]
                rows.append(dict(zip(keys,key)) | dict(metric=metric, images=len(group),
                    valid=s.notna().sum(), missing=s.isna().sum(), mean=s.mean(), std=s.std(),
                    minimum=s.min(), p01=s.quantile(.01), p05=s.quantile(.05),
                    p25=s.quantile(.25), median=s.median(), p75=s.quantile(.75),
                    p95=s.quantile(.95), p99=s.quantile(.99), maximum=s.max()))
        tables[label] = pd.DataFrame(rows)
        tables[label].to_csv(a.output/f'{label}_statistics.csv', index=False)
    native = df[df.target==1024]
    metadata = native[['image_path','category','view','status']]
    st = step.drop(columns=['category','view','status'], errors='ignore').merge(metadata, on='image_path', validate='one_to_one')
    stepcols = ['ssim_drop_512_to_256','rgb_rmse_increase']
    st.groupby(['category','view','status'])[stepcols].agg(['count','mean','median','std','min','max']).to_csv(a.output/'stepwise_group_statistics.csv')
    st[stepcols].describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]).to_csv(a.output/'stepwise_distribution.csv')
    ssim_wide = df.pivot(index='image_path',columns='target',values='ssim')
    aligned = step.set_index('image_path').loc[ssim_wide.index]
    checks['step_difference_consistent'] = bool(np.allclose(aligned.ssim_drop_512_to_256,
        ssim_wide[512]-ssim_wide[256], rtol=1e-10,atol=1e-10))
    selections = []
    for target in [512,256]:
        group = df[df.target==target]
        for direction, ordered in [('high_loss',group.nsmallest(3,'ssim')),
                                   ('low_loss_nonconstant',group[group.ssim<.999999].nlargest(3,'ssim'))]:
            for rank, row in enumerate(ordered.to_dict('records'),1):
                selections.append(row | dict(selection=direction,rank=rank))
    chosen = pd.DataFrame(selections)
    chosen.to_csv(a.output/'extreme_review_images.csv',index=False)
    figures = []
    # save: 결과를 지정한 출력 위치에 기록합니다.
    # 입력 인수: fig, name, caption.
    def save(fig, name, caption):
        path = a.output/(name+'.png')
        fig.savefig(path,dpi=145,bbox_inches='tight');plt.close(fig)
        figures.append(dict(path=str(path),title=name.replace('_',' '),caption=caption))
    colors={256:'#d55e00',512:'#0072b2',1024:'#009e73'}
    for metric,unit in zip(METRICS,UNITS):
        fig,axes=plt.subplots(1,2,figsize=(13,4.5))
        for target in [256,512,1024]:
            values=np.sort(df.loc[df.target==target,metric].dropna().values)
            axes[0].plot(values,np.arange(1,len(values)+1)/len(values),label=f'{target}: n={len(values):,}',color=colors[target])
            if target!=1024:
                axes[1].hist(values,bins=65,density=True,alpha=.48,label=f'{target}: n={len(values):,}',color=colors[target])
        axes[0].set(ylabel='Empirical cumulative proportion',xlabel=f'{metric} ({unit})')
        axes[1].set(ylabel='Density (inverse x unit)',xlabel=f'{metric} ({unit})')
        for ax in axes: ax.legend(fontsize=8);ax.grid(alpha=.2)
        fig.suptitle(f'{metric}: full-image distribution / 151,050 images per target')
        save(fig,f'distribution_{metric}',f'전체 영상당 동일 가중치 ECDF와 분포. 각 해상도 151,050장, 결측은 범례의 유효 n에서 제외한다. {metric}는 '+('작을수록 복원 오차가 작다.' if metric=='rgb_rmse' else '영상 유사성 또는 보존 지표이며 모델 정확도가 아니다.'))
    for key in ['category','view','status']:
        fig,axes=plt.subplots(2,2,figsize=(15,10))
        for ax,metric in zip(axes.flat,['ssim','edge_recall','local_contrast_retention','high_frequency_proxy_retention']):
            pivot=df[df.target!=1024].groupby([key,'target'])[metric].mean().unstack()
            if key=='category': pivot=pivot.sort_values(256)
            x=np.arange(len(pivot))
            for target in [512,256]: ax.plot(x,pivot[target],'.-',label=str(target),color=colors[target])
            counts=df[df.target==256].groupby(key).size()
            labels=[f'{v}\nn={counts[v]:,}' for v in pivot.index]
            ax.set_xticks(x,labels,rotation=90 if key=='category' else 0,fontsize=7)
            ax.set(ylabel=f'Mean {metric} (ratio)',xlabel=key);ax.legend();ax.grid(alpha=.2)
        fig.suptitle(f'{key}: 512 vs 256 / 151,050 images per target');fig.tight_layout()
        save(fig,f'{key}_comparison',f'{key}별 동일 영상 가중 평균. 각 그룹의 표본 수를 표시한다. 품목 구성·촬영 배경·결함 유형이 섞여 있으므로 그룹 차이로 결함 검출 성능을 추정할 수 없다.')
    fig,axes=plt.subplots(1,2,figsize=(13,4.5))
    for ax,col in zip(axes,stepcols):
        ax.hist(st[col],bins=80,color='#0072b2');ax.set(xlabel=col+(' (SSIM ratio)' if col.startswith('ssim') else ' (intensity [0,255])'),ylabel='Images (count)');ax.grid(alpha=.2)
    fig.suptitle('Additional loss: 512 vs 256 relative to native / n=151,050')
    save(fig,'stepwise_distribution','원본 대비 두 해상도 지표의 차이다. 별도로 저장된 512 영상을 기준으로 한 직접 단계별 PSNR/SSIM과 혼동하지 않는다. 양수이면 256에서 추가 손실이 증가한다.')
    # Only these selected images are decoded to illustrate already measured values.
    boxgroups = {k:g for k,g in boxes.groupby('image_path')}
    decoded = set()
    for i,row in enumerate(chosen.drop_duplicates('image_path').to_dict('records')):
        path=a.data_root/row['image_path'];image=cv2.imread(str(path));decoded.add(row['image_path'])
        if image is None: raise RuntimeError(f'Cannot render selected case: {path}')
        h,w=image.shape[:2];fig,axes=plt.subplots(2,4,figsize=(16,8))
        # Crop centered on a supplied box, otherwise on the strongest displayed residual.
        restored256=cv2.resize(cv2.resize(image,(256,256),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
        residual=np.abs(image.astype(float)-restored256.astype(float)).mean(axis=2)
        if row['image_path'] in boxgroups:
            box=boxgroups[row['image_path']].sort_values('bbox_area').iloc[0]
            cx,cy=int((box.x0+box.x1)/2),int((box.y0+box.y1)/2);crop_note='smallest supplied bbox center'
        else:
            cy,cx=np.unravel_index(np.argmax(residual),residual.shape);crop_note='maximum 256 residual center; not necessarily defect'
        x=max(0,min(w-192,cx-96));y=max(0,min(h-192,cy-96))
        for ri,target in enumerate([512,256]):
            small=cv2.resize(image,(target,target),interpolation=cv2.INTER_AREA)
            recon=cv2.resize(small,(w,h),interpolation=cv2.INTER_LINEAR)
            diff=np.abs(image.astype(float)-recon.astype(float)).mean(axis=2)
            axes[ri,0].imshow(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));axes[ri,0].set_title('Native 1024; yellow = crop')
            axes[ri,0].add_patch(plt.Rectangle((x,y),192,192,fill=False,color='yellow'))
            axes[ri,1].imshow(cv2.cvtColor(small,cv2.COLOR_BGR2RGB),interpolation='nearest');axes[ri,1].set_title(f'Reduced {target} (native pixel grid)')
            axes[ri,2].imshow(cv2.cvtColor(recon,cv2.COLOR_BGR2RGB));axes[ri,2].set_title(f'{target} restored to 1024')
            im=axes[ri,3].imshow(diff,cmap='inferno',vmin=0,vmax=32);axes[ri,3].set_title('Mean |RGB difference| [0,255]; clip32');fig.colorbar(im,ax=axes[ri,3],fraction=.04)
        for ax in axes.flat:ax.set(xlabel='x (native/panel pixels)',ylabel='y (native/panel pixels)')
        measured=df[(df.image_path==row['image_path']) & (df.target==row['target'])].iloc[0]
        fig.suptitle(f"n=1 / {row['selection']} / {row['category']} {row['status']} {row['view']} / ranked at {row['target']}: SSIM={measured.ssim:.6f}\n{row['image_path']}",fontsize=10)
        fig.tight_layout();save(fig,f'case_{i+1:02}_full','기존 수치로 선정한 극단 사례이며 모집단의 대표 비율을 의미하지 않는다. 차이맵 색 범위는 모든 사례 0~32로 고정해 비교한다. 축은 각 패널의 픽셀 좌표다.')
        fig,axes=plt.subplots(1,4,figsize=(14,4))
        arrays=[image,cv2.resize(cv2.resize(image,(512,512),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR),restored256]
        for ax,array,title in zip(axes,arrays,['Native crop','512 restored crop','256 restored crop']):
            ax.imshow(cv2.cvtColor(array[y:y+192,x:x+192],cv2.COLOR_BGR2RGB),interpolation='nearest');ax.set_title(title)
        maskpath=path.with_suffix('.png')
        if maskpath.exists():
            mask=cv2.imread(str(maskpath),cv2.IMREAD_GRAYSCALE);axes[3].imshow(mask[y:y+192,x:x+192]>0,cmap='gray',vmin=0,vmax=1);axes[3].set_title('Provided defect mask >0')
        else: axes[3].text(.1,.5,'No provided mask',transform=axes[3].transAxes);axes[3].set_title('Annotation availability')
        for ax in axes:ax.set(xlabel='crop x (native pixels)',ylabel='crop y (native pixels)')
        fig.suptitle(f"n=1 / 192x192 crop / {row['category']} {row['view']} / {crop_note}");fig.tight_layout()
        save(fig,f'case_{i+1:02}_crop','192×192 원본 좌표에서 동일 영역을 확대한 비교다. 마스크는 결함 위치 확인에만 쓰며 제품 전체 영역 정답으로 쓰지 않는다. 마스크가 없는 NG도 원래 상태를 유지한다.')
    # Annotation-linked geometry uses all existing boxes, not newly extracted labels.
    risk=[]
    for target in [1024,512,256]:
        short=np.minimum(boxes.x1-boxes.x0,boxes.y1-boxes.y0)*target/1024
        area=boxes.bbox_area*(target/1024)**2
        risk.append(dict(target=target,boxes=len(boxes),images=boxes.image_path.nunique(),
                         short_under2=int((short<2).sum()),short_under4=int((short<4).sum()),
                         area_under16=int((area<16).sum()),short_median=short.median()))
    risk=pd.DataFrame(risk);risk.to_csv(a.output/'bbox_projected_size_risk.csv',index=False)
    joined=roi.merge(df[['image_path','target','rgb_rmse','edge_recall']],on=['image_path','target'],validate='one_to_one')
    joined.to_csv(a.output/'existing_roi_whole_comparison.csv',index=False)
    roi_summary=joined.groupby('target')[['roi_rgb_rmse','background_rgb_rmse','rgb_rmse','roi_edge_recall','edge_recall','roi_contrast_retention']].agg(['count','mean','median','std','min','max'])
    roi_summary.to_csv(a.output/'existing_roi_summary.csv')
    fig,axes=plt.subplots(1,3,figsize=(15,4.5))
    for target in [512,256]:
        g=joined[joined.target==target];n=g.roi_rgb_rmse.notna().sum()
        axes[0].scatter(g.rgb_rmse,g.roi_rgb_rmse,s=7,alpha=.45,label=f'{target}: valid ROI n={n}',color=colors[target])
        axes[1].scatter(g.edge_recall,g.roi_edge_recall,s=7,alpha=.45,label=str(target),color=colors[target])
    axes[0].set(xlabel='Whole RGB RMSE (intensity)',ylabel='Defect ROI RGB RMSE (intensity)')
    axes[1].set(xlabel='Whole exact-pixel edge recall (ratio)',ylabel='Defect ROI edge recall (ratio)')
    axes[2].bar(risk.target.astype(str),risk.short_under2,color=['#009e73','#0072b2','#d55e00']);axes[2].set(xlabel='Resolution (pixels per side)',ylabel='Boxes with projected short side <2px (count)')
    for ax in axes:ax.grid(alpha=.2)
    axes[0].legend(fontsize=7);axes[1].legend();fig.suptitle(f'Existing defect ROI sample: {joined.image_path.nunique()} images / all {len(boxes):,} boxes');fig.tight_layout()
    save(fig,'defect_roi_and_bbox_risk','ROI는 기존 336개 마스크 연결 이미지 표본(해상도당 유효 335개)이며 전체 NG의 대표성을 보장하지 않는다. 박스 위험은 제공 위치 정답이 있고 클래스가 확정된 전체 60,629개 박스의 기하학적 축소값이며 실제 검출 실패율이 아니다.')
    print(f'Aggregation and {len(figures)} figures complete; decoded only {len(decoded)} selected JPGs',flush=True)
    # Self-contained interpretation with links to exact CSVs and all visual evidence.
    overall=tables['overall'];means=overall.pivot(index='target',columns='metric',values='mean')
    # mdtable: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: frame.
    def mdtable(frame):
        cols=list(frame.columns);lines=['| '+' | '.join(map(str,cols))+' |','| '+' | '.join(['---']*len(cols))+' |']
        for row in frame.itertuples(index=False,name=None):
            lines.append('| '+' | '.join(f'{v:.6f}' if isinstance(v,(float,np.floating)) else str(v) for v in row)+' |')
        return '\n'.join(lines)
    relative=lambda path: os.path.relpath(path,a.report.parent)
    report=['# Real-IAD 전체 해상도 정보 손실 상세 분석',
        f'작성 시각: {datetime.now(timezone.utc).isoformat()}. 기존 산출물 재집계만 수행했다. 전체 해상도 계산·모델 학습·Push는 수행하지 않았다.',
        '## 1. 회의용 핵심 결론',
        '전체 151,050장, 30품목, C1~C5, OK 72,840장·NG 78,210장을 해상도별 동일 가중치로 비교했다. 각 해상도 151,050행, 합계 453,150행과 단계별 151,050행의 유일성과 기존 검증을 확인했다.',
        mdtable(means[METRICS].reset_index()),
        '1024는 자기 자신과 비교하는 기준점이다. PSNR 120 dB는 무손실 비교의 저장 상한이며 카메라의 실측 품질이 아니다. 512와 256의 낮아진 SSIM·경계 일치는 복원 영상 변화이며 결함 검출 정확도의 감소량이 아니다.',
        '## 2. 범위·분모·재현 정책',
        f'원본 계산 CSV: `{inputs[0]}`. 전체 NG를 포함하고 마스크 없는 NG를 제거하지 않았다. 제공 마스크 51,329장과 NG 78,210장은 다른 분모다. 마스크 미제공 NG 26,881장을 정상으로 바꾸거나 빈 마스크를 만들지 않았다.',
        '영상마다 하나의 관측값으로 집계한다. 전체 평균은 영상 가중치이며 품목 균등 평균이 아니다. 동일 제품의 5시점은 상호 독립 표본이 아니므로 본 보고서는 통계적 유의성·인과관계를 주장하지 않는다.',
        '## 3. 지표 정의와 해석',
        'INTER_AREA로 1024→512/256 축소 후 INTER_LINEAR로 원본 1024 좌표에 복원했다. 전체 원본은 1024×1024이므로 이번 입력에 비정사각형 변형 사례는 없다.',
        'PSNR은 전체 BGR 채널 MSE와 255 범위 기준이다. RGB 채널 순서 변경은 채널 전체 MSE를 바꾸지 않는다. SSIM은 그레이스케일 Gaussian 11×11, sigma 1.5, data range 255다. Edge Recall/F1은 Canny 100/200의 같은 픽셀 위치 일치이며 미세한 경계 이동에도 민감하다.',
        '국소 대비 보존율은 11×11 국소 표준편차 평균의 복원/원본 비율이다. 고주파 보존 대리값은 Laplacian 제곱 에너지 비율이며 FFT 대역별 에너지의 직접 측정이 아니다. 1−비율을 대리 손실로 읽을 수 있으나 의미 있는 결함 정보의 손실률로 해석할 수 없다. 비율의 분모가 0인 두 검은 이미지의 3해상도 결과 6행은 결측으로 유지했다.',
        '## 4. 전체 분포·중앙값·분위수·극단값',
        f'[전체 통계 CSV]({relative(a.output/"overall_statistics.csv")})는 n/유효 n/결측/평균/표준편차/최소/P01/P05/P25/중앙값/P75/P95/P99/최대를 제공한다. 세 해상도와 모든 지표를 포함한다.',
        mdtable(overall[overall.target!=1024][['target','metric','valid','mean','median','p05','p95','minimum','maximum']]),
        '## 5. 품목별·C1~C5별·OK/NG별 비교',
        '아래 품목 순위는 256의 평균 SSIM이 낮은 순이다. 품목별 질감·형상·배경 복잡도를 반영하며 모델 난이도 순위로 확정할 수 없다.',
        mdtable(tables['category'].query('target==256 and metric=="ssim"').sort_values('mean')[['category','images','mean','median','p05','p95']]),
        mdtable(tables['view'].query('target!=1024 and metric=="ssim"')[['view','target','images','mean','median','p05','p95']]),
        mdtable(tables['status'].query('target!=1024 and metric=="ssim"')[['status','target','images','mean','median','p05','p95']]),
        'OK/NG 전체 차이에는 품목·시점·불량 유형·촬영 조건의 혼합이 포함된다. 같은 품목·시점·상태의 세부 표로 확인하며, 결함 때문에 차이가 났다고 단정하지 않는다.',
        '## 6. 512→256의 추가 손실',
        mdtable(st[stepcols].describe(percentiles=[.05,.5,.95]).reset_index()),
        'ssim_drop_512_to_256은 원본 기준 SSIM512−SSIM256이며 rgb_rmse_increase는 RMSE256−RMSE512다. per_image_stepwise_changes.csv에는 직접 512 영상을 기준으로 계산한 target256 지표도 함께 있으므로 두 기준을 구분한다.',
        '## 7. 손실 상·하위 실제 영상 검수',
        mdtable(chosen[['category','status','view','target','selection','rank','ssim','rgb_rmse']]),
        '각 해상도에서 SSIM 손실 상위 3개와 비상수 영상 중 손실 하위 3개를 선정했다. 완전 검은 영상 등 SSIM=1 사례는 저손실 검수 후보에서 제외했다. 이는 눈으로 확인할 극단 사례 선정이며 임의 추출된 대표 표본이 아니다. 아래 원본·축소·복원·고정 범위 차이맵과 동일 영역 확대를 함께 본다.',
        '## 8. 기존 마스크·Bounding Box 연결',
        mdtable(risk),
        f'박스 {len(boxes):,}개는 8방향 연결 성분과 검증된 >0 마스크 정책으로 이미 생성된 결과를 읽었다. NG 전체가 아니라 제공 마스크와 확정 클래스가 있는 영상에 한한다. 길이를 target/1024, 면적을 그 제곱으로 환산했다. 박스 단변 2px 미만은 검토 우선순위 신호이지 실제 결함 소실·검출 실패 판정이 아니다.',
        '기존 결함 ROI 검수는 336이미지×2해상도=672행, 빈 마스크 1이미지를 제외한 670개 유효 관측이다. 마스크는 JPG의 결함 위치를 지정하는 용도다. ROI RGB 복원 오차와 전체 영상 오차를 비교해 전체 평균이 작은 영역의 변화를 희석할 수 있는지 살펴본다.',
        '## 9. 해상도별 장단점과 실험 가설',
        '1024는 원본 세부 정보를 유지하지만 영상당 픽셀 수가 512의 4배, 256의 16배다. 이는 입력 픽셀 수 비율이며 실제 메모리·추론 시간 측정값이 아니다. 512는 픽셀 수와 세부 정보 보존의 중간 후보이며, 256은 더 적은 입력 픽셀을 쓰지만 경계·고주파 변화와 작은 박스 위험을 함께 검토해야 한다.',
        '검증할 가설: (1) 작은 결함 클래스는 256보다 512/1024 또는 타일링에서 검출·분할 지표가 나을 수 있다. (2) SSIM이 낮은 질감 품목은 고해상도 유지의 이득이 클 수 있다. (3) 배경 변화가 전체 지표를 지배하는 품목은 제품·결함 ROI 지표가 모델 결과와 더 관련될 수 있다. (4) 5시점 결합이 한 시점의 세부 손실을 보완할 수 있으나 실제 제품 단위 평가가 필요하다.',
        '동일 제품 단위 분할·시드·증강·모델·학습 예산을 고정하고 256/512/1024를 비교한다. 이상탐지는 image/pixel AUROC와 AUPRO, 객체탐지는 클래스별 AP와 작은 객체 recall을 함께 평가한다. 운영 장치에서 실제 지연·최대 메모리도 측정한다. 이번 작업에서 모델을 학습하거나 최적 해상도를 결정하지 않았다.',
        '## 10. 한계·미완료·회의 결정 항목',
        '고주파는 Laplacian 대리값이며 주파수 대역별 FFT 분석은 하지 않았다. ROI 표본은 전체 주석 영상의 전수 ROI 분석이 아니다. 자동 마스크는 제공 정답의 경계 정책에 의존하고 물리적 결함의 완전성을 독립 검증하지 않았다. 검은 영상 두 장은 에너지 비율 분모가 0이며 추후 학습 사용 여부를 결정해야 한다.',
        '회의에서 결정할 사항: ① 초기 기준 입력 해상도와 고해상도 예외 품목 ② 작은 결함용 타일링/ROI 전략 ③ 제품 단위 평가와 클래스별 최소 recall 기준 ④ 검은 영상·라벨 경로 충돌의 학습 제외 정책 ⑤ 제한된 장치에서 비교할 속도·메모리 예산. 모델 성능·추론 속도·최적 해상도는 미검증이다.',
        '## 11. 시각화와 해석']
    for f in figures:
        report.extend([f'### {f["title"]}',f'![{f["title"]}]({relative(Path(f["path"]))})',f['caption']])
    report.append('## 12. 전체 결과 파일과 재현')
    for file in sorted(a.output.glob('*.csv')):
        report.append(f'- [{file.name}]({relative(file)})')
    report.extend(['집계·시각화 재현 명령(새 출력 이름 필요):',
        f'```bash\nuv run --offline python scripts/report_resolution_detail.py --run {a.run} --data-root {a.data_root} --output outputs/resolution_detail_NEW --report reports/RESOLUTION_DETAILED_NEW.md\n```',
        '실행 환경: Python 3.12 + 기존 uv.lock 고정 의존성. PNG/CSV/선정 이미지 파생물은 로컬 outputs/에 보관하며 GitHub 대상에는 코드·문서(PDF 포함)만 남긴다. PDF에는 그래프가 내장되어 단독 회의 자료로 사용할 수 있다. Push는 수행하지 않았다.',
        f'무결성 근거: [integrity.json]({relative(a.output/"integrity.json")}). 입력 5개 파일의 SHA-256을 집계 전후 비교한다. 원본 JPG/PNG는 선택 사례 시각화에서 읽기만 했다.'])
    a.report.write_text('\n\n'.join(report),encoding='utf-8')
    # Meeting PDF: readable Korean narrative + numerical tables + every figure.
    font=FontProperties(fname='/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
    plt.rcParams.update({'pdf.fonttype':42,'axes.unicode_minus':False})
    pages=[]
    # wrap: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: text, width.
    def wrap(text,width=94):
        import unicodedata
        lines=[];line='';count=0
        for char in text:
            size=2 if unicodedata.east_asian_width(char) in 'WF' else 1
            if char=='\n' or count+size>width:
                lines.append(line);line='';count=0
                if char=='\n':continue
            line+=char;count+=size
        lines.append(line);return lines
    with PdfPages(pdf) as book:
        buffer=[];title='Real-IAD 해상도 상세 분석'
        # textflush: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
        def textflush():
            nonlocal buffer
            for start in range(0,len(buffer),42):
                fig=plt.figure(figsize=(8.27,11.69));fig.text(.07,.95,title,fontproperties=font,fontsize=15,va='top')
                fig.text(.07,.90,'\n'.join(buffer[start:start+42]),fontproperties=font,fontsize=9,va='top',linespacing=1.55)
                fig.text(.07,.03,f'해상도 분석 | {len(pages)+1} | 전체 151,050장 · 모델 성능 미측정',fontproperties=font,fontsize=8)
                book.savefig(fig);plt.close(fig);pages.append(dict(kind='text',title=title,source=str(a.report)))
            buffer=[]
        for paragraph in report:
            if paragraph.startswith('## 11.'):break
            if paragraph.startswith('#'):
                textflush();title=paragraph.lstrip('# ')
            elif paragraph.startswith('|'):
                # Tables are provided as independent readable PDF pages below.
                continue
            else:
                buffer.extend(wrap(paragraph.replace('`','')));buffer.append('')
        textflush()
        display_tables=[('전체 지표 평균',means[METRICS].reset_index()),
            ('전체 지표 분포',overall[['target','metric','valid','mean','median','p05','p95']]),
            ('품목별 256 SSIM 분포',tables['category'].query('target==256 and metric=="ssim"')[['category','images','mean','median','p05','p95']]),
            ('시점별 SSIM 분포',tables['view'].query('metric=="ssim"')[['view','target','images','mean','median','p05','p95']]),
            ('OK/NG별 SSIM 분포',tables['status'].query('metric=="ssim"')[['status','target','images','mean','median','p05','p95']]),
            ('작은 박스의 투영 크기 위험',risk)]
        for title,frame in display_tables:
            for start in range(0,len(frame),18):
                part=frame.iloc[start:start+18].copy()
                cells=[[f'{v:.5f}' if isinstance(v,(float,np.floating)) else str(v) for v in row] for row in part.itertuples(index=False,name=None)]
                fig,ax=plt.subplots(figsize=(11.69,8.27));ax.axis('off')
                fig.text(.04,.94,title,fontproperties=font,fontsize=17)
                tab=ax.table(cellText=cells,colLabels=list(frame.columns),loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(8);tab.scale(1,1.7)
                fig.text(.04,.04,f'전체 151,050장/해상도. 결측은 valid에서 제외. | {len(pages)+1}',fontproperties=font,fontsize=9)
                book.savefig(fig);plt.close(fig);pages.append(dict(kind='table',title=title,source=str(a.output)))
        for f in figures:
            fig=plt.figure(figsize=(11.69,8.27));ax=fig.add_axes([.03,.19,.94,.73]);ax.imshow(plt.imread(f['path']));ax.axis('off')
            fig.text(.04,.96,'해상도 분석 · '+f['title'],fontproperties=font,fontsize=14,va='top')
            fig.text(.04,.15,'\n'.join(wrap(f['caption'],135)),fontproperties=font,fontsize=9,va='top')
            fig.text(.04,.025,f'출처: {f["path"]} | {len(pages)+1}',fontproperties=font,fontsize=7)
            book.savefig(fig);plt.close(fig);pages.append(dict(kind='figure',title=f['title'],source=f['path']))
    pdf.with_suffix('.pages.json').write_text(json.dumps(dict(pages=pages),ensure_ascii=False,indent=2))
    after={str(v):digest(v) for v in inputs}
    checks['input_sha256_unchanged']=before==after
    inventory=[dict(path=str(v),bytes=v.stat().st_size,sha256=digest(v)) for v in [*sorted(a.output.glob('*.csv')),*sorted(a.output.glob('*.png')),a.report,pdf]]
    evidence=dict(success=all(checks.values()),checks=checks,input_sha256_before=before,input_sha256_after=after,
                  metric_recalculations=0,selected_jpg_decodes=len(decoded),pdf_pages=len(pages),
                  figures=len(figures),generated_files=inventory,full_scope_images=151050,metric_rows=453150,
                  native_metric_note='PSNR identity is capped at 120dB; energy ratios undefined for two constant images',
                  push_performed=False)
    (a.output/'integrity.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in evidence.items() if k not in ['generated_files','input_sha256_before','input_sha256_after']},ensure_ascii=False,indent=2),flush=True)
    if not evidence['success']:raise SystemExit(1)


if __name__=='__main__':
    main()
