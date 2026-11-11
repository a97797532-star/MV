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
a=p.parse_args()
if a.pdf.exists():raise SystemExit('Select a new PDF path; existing files are preserved')
font=FontProperties(fname='/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
plt.rcParams.update({'pdf.fonttype':42,'axes.unicode_minus':False})
pages=[]
def wrap(text,width):
    lines=[];line='';n=0
    for c in text.replace('−','-'):
        size=2 if unicodedata.east_asian_width(c) in 'WF' else 1
        if c=='\n' or n+size>width:
            lines.append(line);line='';n=0
            if c=='\n':continue
        line+=c;n+=size
    lines.append(line);return lines

def clean(text):
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text).replace('`','').replace('**','')

title='Real-IAD 해상도 상세 분석';body=[];rows=[]
with PdfPages(a.pdf) as book:
    def finish(fig,kind,source):
        fig.text(.04,.025,f'전체 151,050장 · 학습/속도 측정 미실시 | {len(pages)+1}',fontproperties=font,fontsize=8)
        book.savefig(fig);plt.close(fig);pages.append(dict(kind=kind,title=title,source=source))
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
                     'short_median':'Short median\n(px)'}
            header=[aliases.get(c,c.replace('_','\n')) for c in rows[0]]
            for start in range(1,len(rows),19):
                fig,ax=plt.subplots(figsize=(11.69,8.27));ax.axis('off')
                fig.text(.035,.95,title,fontproperties=font,fontsize=15,va='top')
                table=ax.table(cellText=rows[start:start+19],colLabels=header,loc='center',cellLoc='center')
                table.auto_set_font_size(False);table.set_fontsize(8 if len(header)<=8 else 7)
                table.scale(1,1.8)
                for (r,c),cell in table.get_celld().items():
                    if r==0:cell.set_height(cell.get_height()*1.8);cell.set_facecolor('#eaf0f6')
                fig.text(.035,.08,'해상도별 동일 영상 가중 통계. valid는 해당 지표의 유효 관측 수. 상세 단위와 분모는 본문 참조.',fontproperties=font,fontsize=9)
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
            fig.text(.035,.96,'해상도 비교 · '+image.group(1),fontproperties=font,fontsize=13,va='top')
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
