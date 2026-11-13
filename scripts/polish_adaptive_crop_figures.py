# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Presentation-only improvements; never recompute image or mask measurements."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
from pathlib import Path
import pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path('outputs/adaptive_crop_gate_v1');M=B/'metrics';F=B/'figures'
methods=['fixed_full','fixed_center896','fixed_grabcut10','research_risk_full','research_review_center','research_validated_scope','deployment_default'];short={'fixed_full':'Full1024','fixed_center896':'Center896','fixed_grabcut10':'GC90+10','research_risk_full':'Research-A','research_review_center':'Research-B','research_validated_scope':'Research-C','deployment_default':'Deployment'}
s=pd.read_csv(M/'policy_summary.csv');g=s[s.gate_cohort.eq('final_holdout')].set_index('method').loc[methods]
fig,ax=plt.subplots(figsize=(12,6));offsets=[(-25,80),(0,60),(0,0),(15,110),(15,-45),(-40,40),(-25,0)]
for (name,r),(dx,dy) in zip(g.iterrows(),offsets):
 ax.scatter(r.magnification_mean,r.retention*100,s=55);ax.annotate(short[name],(r.magnification_mean,r.retention*100),xytext=(dx,dy),textcoords='offset points',arrowprops=dict(arrowstyle='-',color='gray'),fontsize=9)
ax.set(xlabel='Mean geometric linear gain1024/crop side (ratio)',ylabel='Defect pixel weighted retention (%)',ylim=(98,102),xlim=(.99,1.19));fig.suptitle('Final n=300 / positive masks100: all methods retain100% here, risk recall cannot be estimated');fig.tight_layout();fig.savefig(F/'pareto.png',dpi=135,bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(14,6))
for ax,name,key in zip(axes,['small_defect','outer_defect'],['small_mask','outer_mask']):
 by=pd.read_csv(M/f'summary_by_{name}.csv');g=by[by.gate_cohort.eq('final_holdout')&by[key].eq(True)].set_index('method').loc[methods];ax.bar([short[x] for x in g.index],g.retention*100);ax.set(ylabel='Defect pixel retention (%)',ylim=(0,105),title=f'{name}: positive mask images n={int(g.positive_masks.iloc[0])}');ax.tick_params(axis='x',rotation=45)
fig.suptitle('Final300 subset analysis: small total mask <1024px; outer positive within128px border');fig.tight_layout();fig.savefig(F/'small_outer.png',dpi=135,bbox_inches='tight');plt.close(fig)
t=pd.read_csv(M/'feature_extraction_timing.csv').groupby('gate_cohort').elapsed_ms.agg(['count','median']);fig,ax=plt.subplots(figsize=(12,6));ax.bar([f'{k}\nn={int(r["count"])}' for k,r in t.iterrows()],t['median']);ax.set(ylabel='Median feature extraction time (ms/image)',xlabel='Cohort');ax.tick_params(axis='x',rotation=20,labelsize=8);fig.suptitle('Offline build n=2550,3 CPU workers; cache reuse varies, JPEG I/O excluded');fig.tight_layout();fig.savefig(F/'offline_cost.png',dpi=135,bbox_inches='tight');plt.close(fig)
p=Path('reports/ADAPTIVE_CROP_QUALITY_GATE_REPORT.md');lines=p.read_text().splitlines();out=[]
for line in lines:
 if line.startswith('수치 근거:'):
  while out and not out[-1].strip():out.pop()
  out[-1]+=' '+line
 else:out.append(line)
p.write_text('\n'.join(out)+'\n');print('Polished3 statistical charts and kept figure sources with captions; no metric recomputation')
