# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Render the existing resolution Markdown and figures, without reading source images."""
import argparse
import json
import os
import re
import unicodedata
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/mv-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('markdown',type=Path)
p.add_argument('pdf',type=Path)
p.add_argument('--footer',default='전체 151,050장 · 학습/속도 측정 미실시')
p.add_argument('--figure-prefix',default='해상도 비교')
p.add_argument('--table-note',default='해상도별 동일 영상 가중 통계. valid는 해당 지표의 유효 관측 수. 상세 단위와 분모는 본문 참조.')
p.add_argument('--table-rows',type=int,default=19)
p.add_argument('--table-cell-width',type=int,default=0)
a=p.parse_args()
if a.pdf.exists():raise SystemExit('Select a new PDF path; existing files are preserved')
font=FontProperties(fname='/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
plt.rcParams.update({'pdf.fonttype':42,'axes.unicode_minus':False})
pages=[]
# wrap: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: text, width.
def wrap(text,width):
    lines=[];line='';n=0
    for c in text.replace('−','-'):
        size=2 if unicodedata.east_asian_width(c) in 'WF' else 1
        if c=='\n' or n+size>width:
            lines.append(line);line='';n=0
            if c=='\n':continue
        line+=c;n+=size
    lines.append(line);return lines

# clean: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: text.
def clean(text):
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text).replace('`','').replace('**','')

title='Real-IAD 해상도 상세 분석';body=[];rows=[]
with PdfPages(a.pdf) as book:
    # finish: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    # 입력 인수: fig, kind, source.
    def finish(fig,kind,source):
        fig.text(.04,.025,f'{a.footer} | {len(pages)+1}',fontproperties=font,fontsize=8)
        book.savefig(fig);plt.close(fig);pages.append(dict(kind=kind,title=title,source=source))
    # flush: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
    def flush():
        global body,rows
        if body:
            lines=[]
            for paragraph in body:lines.extend(wrap(clean(paragraph),96));lines.append('')
            for start in range(0,len(lines),42):
                fig=plt.figure(figsize=(8.27,11.69));fig.text(.065,.96,title,fontproperties=font,fontsize=14,va='top')
                fig.text(.065,.91,'\n'.join(lines[start:start+42]),fontproperties=font,fontsize=9,va='top',linespacing=1.55)
                finish(fig,'text',str(a.markdown))
            body=[]
        if rows:
            # Wrap semantic names so all numerical columns remain legible.
            aliases={'high_frequency_proxy_retention':'HF proxy\nratio','local_contrast_retention':'Local contrast\nratio',
                     'psnr_db':'PSNR\n(dB)','edge_recall':'Edge recall\n(ratio)','edge_f1':'Edge F1\n(ratio)',
                     'rgb_rmse':'RGB RMSE\n(intensity)','ssim_drop_512_to_256':'SSIM drop\n512 to 256',
                     'rgb_rmse_increase':'RGB RMSE\nincrease','short_under2':'Short side\n<2px',
                     'short_under4':'Short side\n<4px','area_under16':'Area\n<16px2',
                     'short_median':'Short median\n(px)',
                     'detection_occurrence_rate':'Any detection\n(ratio)',
                     'conditional_pixel_weighted_retention':'Conditional pixel\nretention (ratio)',
                     'available_positive_masks':'Available\npositive masks',
                     't256_output_pixels_median':'256 support\nmedian (px)',
                     't512_output_pixels_median':'512 support\nmedian (px)',
                     't256_small_component_survival':'256 small ID\nsurvival (ratio)',
                     't512_small_component_survival':'512 small ID\nsurvival (ratio)',
                     'all_observed_defects_preserved':'All observed\nmask views kept',
                     'observed_positive_products':'Products with\npositive masks',
                     'all_five_quality_pass_rate':'All5 views\nQC pass (ratio)',
                     'any_no_candidate_rate':'Any view no\ncandidate (ratio)',
                     'mixed_fallback_rate':'Mixed fallback\n(ratio)',
                     'mean_side_range':'Mean side\nrange (pixels)',
                     'median_output_pixels':'Output positive\npixels median',
                     'source_id_survival':'Source ID\nsurvival (ratio)',
                     'small_id_survival':'Small source ID\nsurvival (ratio)'}
            header=[aliases.get(c,c.replace('_','\n')) for c in rows[0]]
            for start in range(1,len(rows),a.table_rows):
                fig,ax=plt.subplots(figsize=(11.69,8.27));ax.axis('off')
                fig.text(.035,.95,title,fontproperties=font,fontsize=15,va='top')
                cells=rows[start:start+a.table_rows]
                if a.table_cell_width:
                    cells=[['\n'.join(wrap(value,a.table_cell_width)) for value in row] for row in cells]
                table=ax.table(cellText=cells,colLabels=header,loc='center',cellLoc='center')
                table.auto_set_font_size(False);table.set_fontsize(8 if len(header)<=8 else 7)
                table.scale(1,1.8)
                for (r,c),cell in table.get_celld().items():
                    if r==0:cell.set_height(cell.get_height()*max(1.8,max(v.count('\n')+1 for v in header)*.65));cell.set_facecolor('#eaf0f6')
                    elif a.table_cell_width:cell.set_height(cell.get_height()*max(1,max(v.count('\n')+1 for v in cells[r-1])*.8))
                fig.text(.035,.08,a.table_note,fontproperties=font,fontsize=9)
                finish(fig,'table',str(a.markdown))
            rows=[]
    source=a.markdown.read_text().splitlines()
    skip_lines=set()
    for i,line in enumerate(source):
        if i in skip_lines:continue
        image=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line.strip())
        if image:
            flush();path=(a.markdown.parent/image.group(2)).resolve()
            if not path.is_file():raise SystemExit(f'Missing report figure: {path}')
            caption_index=next((j for j in range(i+1,len(source)) if source[j].strip()),None)
            caption=source[caption_index] if caption_index is not None else '해상도별 관측 결과. 본문 참조.'
            if caption_index is not None and not caption.startswith(('#','!','|')):skip_lines.add(caption_index)
            fig=plt.figure(figsize=(11.69,8.27));ax=fig.add_axes([.025,.20,.95,.70]);ax.imshow(plt.imread(path));ax.axis('off')
            fig.text(.035,.96,a.figure_prefix+' · '+image.group(1),fontproperties=font,fontsize=13,va='top')
            fig.text(.035,.15,'\n'.join(wrap(clean(caption),139)),fontproperties=font,fontsize=9,va='top')
            finish(fig,'figure',str(path))
        elif line.startswith('#'):
            flush();title=line.lstrip('# ')
        elif line.startswith('|'):
            if body:flush()
            values=[c.strip() for c in line.strip('|').split('|')]
            if not all(re.fullmatch('[-: ]+',v or '-') for v in values):rows.append(values)
        elif not line.strip():
            if rows:flush()
        elif line.strip() and not line.startswith('```'):
            if rows:flush()
            body.append(line)
    flush()
a.pdf.with_suffix('.pages.json').write_text(json.dumps(dict(pages=pages),ensure_ascii=False,indent=2))
print(json.dumps(dict(pdf=str(a.pdf),pages=len(pages),figures=sum(p['kind']=='figure' for p in pages),metric_recalculations=0),ensure_ascii=False))
