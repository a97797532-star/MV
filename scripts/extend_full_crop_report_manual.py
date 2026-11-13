# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Append human crop review workflow without changing existing crop coordinates."""
import os,json,shutil
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
B=Path('outputs/adaptive_crop_full_v1');F=B/'figures';R=Path('reports');p=R/'FULL_DATASET_ADAPTIVE_CROP_REPORT.md';text=p.read_text()
if '## 21. 사람이 판단하는 Crop 검수' in text:raise SystemExit('Manual section already exists; preserve')
q=json.loads((B/'manual_crop_review_queue.json').read_text());reasons=q['reason_counts'];fig,ax=plt.subplots(figsize=(13,6));names=['Image gate risks','A product loss','Center product loss','Old gate product loss','Optional second Crop mask loss','Previous review sample'];ax.barh(names,list(reasons.values()));ax.set(xlabel='Images (count), non-exclusive reasons');fig.suptitle('Human crop priority queue n1757 /903 declared products /30 categories')
for i,v in enumerate(reasons.values()):ax.text(v+4,i,str(v),va='center')
fig.tight_layout();fig.savefig(F/'manual_review_reason_counts.png',dpi=145,bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(15,6));ax.axis('off');nodes=[(.02,'Frozen base metadata\n151050 full-frame rows'),(.27,'Priority review CSV\n1757 images'),(.52,'Human checks + drag\nImage / GT / mask references'),(.77,'Separate APPROVED_CROP\nledger, currently0')]
for x,label in nodes:
 ax.add_patch(FancyBboxPatch((x,.49),.2,.24,boxstyle='round,pad=.012',facecolor='#edf2f6',edgecolor='#506170'));ax.text(x+.1,.61,label,ha='center',va='center',fontsize=10)
 if x<.77:ax.annotate('',xy=(x+.245,.61),xytext=(x+.205,.61),arrowprops=dict(arrowstyle='->',lw=1.5))
ax.text(.5,.24,'Export new reviewed metadata:151050 rows; only explicit human approvals override C.\nOriginal metadata and product VERIFIED_GT ledger remain unchanged.\nNo crop image files are generated.',ha='center',va='center',fontsize=12);fig.suptitle('Human review is separate from automatic gate and product GT; no real crop approvals yet');fig.tight_layout();fig.savefig(F/'human_crop_review_workflow.png',dpi=145,bbox_inches='tight');plt.close(fig)
text+='''\n\n## 21. 사람이 판단하는 Crop 검수\n\n사용자 요청에 따라 사람이 판단해야 하는 이미지를 별도 manual_crop_review.csv로 분리했다. 1,757장/903선언제품/30품목이며 자동 위험·관측 제품 BBox 손실·선택적 추가CenterCrop 결함 손실·미계산 대표 표본의 합집합이다. 이 목록 전체가 현재 C 원본 유지에서 실패했다는 뜻은 아니다. 전체148500장 미계산 특징의 위험을 전부 탐지했다고도 주장하지 않는다.\n\n검수 화면은 원본과 현재 Crop, 자동 후보, 제공된 제품 GT/마스크를 보여주며 정사각형 또는 직사각형 드래그로 범위를 조절한다. 현재 범위 보존 점검과 사람 직접 확인 후에만 APPPROVED_CROP가 아닌 정확한 상태 APPROVED_CROP로 별도 이력을 남긴다. 제품 VERIFIED_GT를 만들거나 기존605개 제품 검수 이력을 수정하지 않는다. 관측 손실 또는 GT 미제공 경고에는 추가 확인이 필요하고 범위를 바꾸면 해당 좌표와 일치하는 점검이 필요하다.\n\n실행: uv run --offline python scripts/review_crop_ranges.py --port 8769. 브라우저 http://127.0.0.1:8769 에서 검수한다. 다음 미승인 및 번호 이동으로 재개할 수 있다. 실제 브라우저 화면은 이 환경에서 UNVERIFIED지만 실제1757행 JSON·원본 이미지·마스크RGBA·보존 점검 API와 Node 화면 모의 검사를 수행했다.\n\n실제 Crop 승인0개다. 사람이 승인한 뒤 ‘검수 반영한 새 전처리 CSV 만들기’를 누르면 preprocessing_metadata_reviewed_v1.csv 등 새 버전이 생성된다. 전체151050행을 유지하며 승인한 행만 HUMAN_CROP 또는 사람이 확인한 C로 반영한다. 미검수·보류·거부 행은 기준 원본C다. 기존 preprocessing_metadata.csv를 덮어쓰지 않는다. 전처리 시 새 반영 CSV 하나를 읽는다. 실제 수동 작업을 agent가 대신 완료한 것처럼 보고하지 않는다.\n\n직사각형은 gain_x/gain_y와 면적 기반 선형 기하 확대율을 기록하고 Resize/Normalize는 모델별로 남긴다. Test에서 GT 참조로 수정한 행은 정답 보조 검수와 평가 오염 검토 플래그를 남긴다. 자동 Gate의 독립 안전 성능으로 세지 않는다.\n\n[검수 목록](../outputs/adaptive_crop_full_v1/manual_crop_review.csv), [검수 사용법](../docs/MANUAL_CROP_REVIEW.md), [검수 도구](../scripts/review_crop_ranges.py).\n\n![Human crop review reasons](../outputs/adaptive_crop_full_v1/figures/manual_review_reason_counts.png)\n\n원인별 집합은 겹치므로 합산하지 않는다. 최종 합집합은1757장이다. 추가CenterCrop 마스크 손실은 현재 원본C의 손실이 아니다. 근거: manual_crop_review_queue.json.\n\n![Human crop review workflow](../outputs/adaptive_crop_full_v1/figures/human_crop_review_workflow.png)\n\n기준CSV·제품GT·수동Crop 이력을 분리했다. 명시적 승인만 새 전체 전처리CSV에 반영하고 Crop 이미지 파일은 생성하지 않는다. 실제 승인0개 기준 흐름이다.\n'''
text=text.replace('APPPROVED_CROP가 아닌 정확한 상태 APPROVED_CROP로','APPROVED_CROP로');p.write_text(text)
index=json.loads((B/'figure_index.json').read_text());index += [dict(path=str(F/n),name=n,caption='Human crop review only; real approvals0',source=str(B/'manual_crop_review_queue.json')) for n in ['manual_review_reason_counts.png','human_crop_review_workflow.png']];(B/'figure_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2))
# Preserve our first authored PDF draft before generating the final version.
draft=B/'review_drafts/before_manual_workflow';draft.mkdir(parents=True,exist_ok=True)
for f in R.glob('FULL_DATASET_ADAPTIVE_CROP_REPORT.*'):
 if f.suffix!='.md':shutil.move(str(f),draft/f.name)
print('Added human review section and2 figures; base metadata unchanged')
