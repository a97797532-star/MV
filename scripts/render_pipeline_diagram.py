# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Render the analysis data flow and annotation denominators for the final report."""
import argparse,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
if a.output.exists():raise SystemExit('Preserve existing figure; choose a new output')
font=FontProperties(fname='/usr/share/fonts/truetype/nanum/NanumGothic.ttf');fig,ax=plt.subplots(figsize=(11,12));ax.set(xlim=(0,12),ylim=(0,14));ax.axis('off')
# box: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: x, y, w, h, text, color.
def box(x,y,w,h,text,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.12',facecolor=color,edgecolor='#64748b',linewidth=1));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontproperties=font,fontsize=11,linespacing=1.6)
# arrow: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: x, y, u, v.
def arrow(x,y,u,v):ax.add_patch(FancyArrowPatch((x,y),(u,v),arrowstyle='-|>',mutation_scale=15,color='#475569',linewidth=1.3))
box(2.5,12,7,1.1,'입력: JPG 151,050장 / 제공 PNG 51,329개\nOK 72,840 / NG 78,210 / C1-C5 각30,210장','#dbeafe')
box(2.5,10.2,7,1.0,'무결성·메타데이터·5시점·기존 Windows 분할 검증\n선언된 제품 키와 실제 물리 제품 identity를 구분','#e0f2fe');arrow(6,12,6,11.25)
box(.3,7.6,5.2,1.5,'모든 JPG 151,050장\n전체 밝기 + 1024/512/256 영상 손실\n주석 없는 NG 26,881장도 포함','#dcfce7');arrow(4.2,10.2,3,9.2)
box(6.4,7.6,5.2,1.5,'제공된 NG 위치 마스크 51,329개\n검증된 grayscale >0, 8연결 성분\n미제공 NG는 정상/빈 정답으로 바꾸지 않음','#ffedd5');arrow(7.8,10.2,9,9.2)
box(.3,4.9,5.2,1.7,'JPG만으로 배경·추정 제품 영역 분리\n색상/조명 모델 · GrabCut · 경계 방법\n품질 불확실/실패: 제품 통계는 결측\n추정 전경은 제품 정답 마스크가 아님','#fef9c3');arrow(2.9,7.6,2.9,6.7)
box(6.4,4.9,5.2,1.7,'위치 빈도: 기존 분할 Train의 제공 마스크만\nknown / positive 분모를 구분\nBBox: 제공 주석 + 확인된 불량 유형\n정상 OK는 빈 탐지 라벨, 클래스 혼동 방지','#fce7f3');arrow(9,7.6,9,6.7)
box(2.5,2.3,7,1.5,'영역별 통계·동일 표본 전후 비교·선택 편향 점검\n결함 국소 주변은 품질 통과 제품 내부에서 계산\n증강 후보는 Train만, Validation/Test 원본 유지','#ede9fe');arrow(3,4.9,4.5,3.9);arrow(9,4.9,7.5,3.9)
box(2.5,.4,7,1.0,'실제 수치 + 그래프 + 실제 이미지 검수 + 한계\nMarkdown / 상세 PDF / 공유 코드·이미지·집계표','#dbeafe');arrow(6,2.3,6,1.5)
fig.suptitle('Real-IAD 분석 흐름과 주석 범위',fontproperties=font,fontsize=20,color='#173b62');fig.tight_layout();a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=130);plt.close(fig)
