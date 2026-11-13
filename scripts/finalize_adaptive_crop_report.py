# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Clarify policy fallback vs geometric full-frame use; recompute aggregates only."""
import os,sys,json
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib');sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from report_adaptive_crop_gate import table
B=Path('outputs/adaptive_crop_gate_v1');M=B/'metrics';F=B/'figures';P=Path('reports/ADAPTIVE_CROP_QUALITY_GATE_REPORT.md')
# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
 d=pd.read_csv(M/'per_image_evaluation.csv');rows=[]
 for (cohort,method,pid),g in d.groupby(['gate_cohort','method','product_id']):
  p=g[g.original_pixels>0];rows.append(dict(gate_cohort=cohort,method=method,product_id=pid,views=len(g),any_gate_FAIL=g.quality_status.eq('FAIL').any(),all_five_gate_PASS=g.quality_status.eq('PASS').all(),any_C=g.selected_policy.eq('C').any(),mixed_C=0<int(g.selected_policy.eq('C').sum())<len(g),any_full_frame=g.full_frame.any(),mixed_full_frame=0<int(g.full_frame.sum())<len(g),side_variance=g.side.var(ddof=0),side_range=g.side.max()-g.side.min(),positive_mask_views=len(p),all_observed_defects_preserved=p.mask_state.eq('preserved').all() if len(p) else None,all_five_product_preservation='UNVERIFIED'))
 p=pd.DataFrame(rows);p.to_csv(M/'five_view_product_metrics.csv',index=False);s=p.groupby(['gate_cohort','method']).agg(products=('product_id','size'),any_gate_FAIL_rate=('any_gate_FAIL','mean'),all_five_gate_PASS_rate=('all_five_gate_PASS','mean'),any_C_policy_rate=('any_C','mean'),mixed_C_policy_rate=('mixed_C','mean'),any_full_rate=('any_full_frame','mean'),mixed_full_rate=('mixed_full_frame','mean'),mean_side_variance=('side_variance','mean'),mean_side_range=('side_range','mean'),observed_positive_products=('all_observed_defects_preserved','count'),all_observed_defects_preserved=('all_observed_defects_preserved','mean')).reset_index();s.to_csv(M/'five_view_summary.csv',index=False)
 methods=['fixed_full','fixed_center896','fixed_grabcut10','research_risk_full','research_review_center','research_validated_scope','deployment_default'];short={'fixed_full':'Full1024','fixed_center896':'Center896','fixed_grabcut10':'GC90+10','research_risk_full':'Research-A','research_review_center':'Research-B','research_validated_scope':'Research-C','deployment_default':'Deployment'};g=s[s.gate_cohort.eq('final_holdout')].set_index('method').loc[methods]
 fig,axes=plt.subplots(1,2,figsize=(14,6));axes[0].bar([short[x] for x in g.index],g.all_observed_defects_preserved);axes[0].set(ylabel='All observed mask views preserved (ratio)',ylim=(0,1.05));plot=g[['mixed_C_policy_rate','mixed_full_rate']].copy();plot.index=[short[x] for x in plot.index];plot.plot.bar(ax=axes[1]);axes[1].set(ylabel='Mixed-policy or full-frame products (ratio)',xlabel='Method')
 for ax in axes:ax.tick_params(axis='x',rotation=45,labelsize=8)
 fig.suptitle('Final60 declared products /30 with positive masks: C policy differs from full1024 geometry');fig.tight_layout(rect=(0,0,1,.94));fig.savefig(F/'five_views.png',dpi=135,bbox_inches='tight');plt.close(fig)
 t=P.read_text();start=t.index('| method | products |',t.index('## 14.'));end=t.index('\n\n',start);cols=['method','products','any_gate_FAIL_rate','all_five_gate_PASS_rate','mixed_C_policy_rate','mixed_full_rate','observed_positive_products','all_observed_defects_preserved'];t=t[:start]+table(s[s.gate_cohort.eq('final_holdout')&s.method.isin(['research_review_center','fixed_grabcut10','fixed_center896','deployment_default'])][cols])+t[end:]
 summary=pd.read_csv(M/'policy_summary.csv');f=summary[summary.gate_cohort.eq('final_holdout')].set_index('method').loc[methods];plot=f[['C_rate','full_frame_rate']].copy();plot.index=[short[x] for x in plot.index];fig,ax=plt.subplots(figsize=(12,6));plot.plot.bar(ax=ax);ax.set(ylabel='Images (fraction)',xlabel='Method');fig.suptitle('Final n=300: explicit C policy vs geometric full1024 crop');fig.tight_layout();dest=F/'fallback_vs_full_geometry.png';fig.savefig(dest,dpi=135,bbox_inches='tight');plt.close(fig)
 section='### C 정책 선택과 실제 원본 전체 사용의 차이'
 if section not in t:t+='\n\n'+section+'\n\n![Fallback versus full frame](../'+str(dest)+')\n\nFinal300장 연구 Gate의 C 선택은38장(12.6667%)이며, A로 선택됐지만 실제 Crop이1024인24장을 더하면 전체 원본 사용62장(20.6667%)이다. 실제 Crop이1024이면 확대 효과는0이다. 근거: [policy_summary.csv](../outputs/adaptive_crop_gate_v1/metrics/policy_summary.csv).\n'
 P.write_text(t);index=json.loads((B/'figure_index.json').read_text());entry=dict(path=str(dest),name='fallback_vs_full_geometry',caption='C policy and actual full1024 geometry must be separated; n300.',source=str(M/'policy_summary.csv'))
 if not any(x['name']==entry['name'] for x in index):index.append(entry)
 (B/'figure_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2));print(s[s.gate_cohort.eq('final_holdout')&s.method.eq('research_review_center')].to_json(orient='records'))
if __name__=='__main__':main()
