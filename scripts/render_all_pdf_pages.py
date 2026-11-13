# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Render EVERY page for review, inspect text bounds, create contact sheets."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,'/tmp/mv-pdf-tools')
import pypdfium2 as pdfium
import numpy as np
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False);doc=pdfium.PdfDocument(str(a.pdf));result=[];out_of_bounds=[];sheet_paths=[];thumbs=[]
for i in range(len(doc)):
 page=doc[i];w,h=page.get_size();tp=page.get_textpage();text=tp.get_text_bounded()
 for n in range(tp.count_chars()):
  c=tp.get_text_range(n,1)
  if not c.strip():continue
  x0,y0,x1,y1=tp.get_charbox(n)
  if x0<-.75 or y0<-.75 or x1>w+.75 or y1>h+.75:out_of_bounds.append(dict(page=i+1,character_index=n))
 bitmap=page.render(scale=1.2);im=bitmap.to_pil().convert('RGB');pixels=np.asarray(im);nonwhite=float(np.mean(np.min(pixels,axis=2)<245));dest=a.output/f'page_{i+1:03}.png';im.save(dest)
 thumb=im.copy();thumb.thumbnail((380,480));canvas=Image.new('RGB',(400,510),'white');canvas.paste(thumb,((400-thumb.width)//2,25));ImageDraw.Draw(canvas).text((10,5),f'PAGE {i+1}',fill='black');thumbs.append(canvas)
 if len(thumbs)==9 or i==len(doc)-1:
  contact=Image.new('RGB',(1200,1530),(225,225,225))
  for j,t in enumerate(thumbs):contact.paste(t,((j%3)*400,(j//3)*510))
  target=a.output/f'contact_{len(sheet_paths)+1:02}.png';contact.save(target);sheet_paths.append(str(target));thumbs=[]
 result.append(dict(page=i+1,render=str(dest),nonwhite_fraction=nonwhite,korean=any('\uac00'<=c<='\ud7a3' for c in text),text_characters=len(text)));im.close();bitmap.close();tp.close();page.close()
doc.close();evidence=dict(success=not out_of_bounds and all(r['nonwhite_fraction']>.001 and r['korean'] for r in result),pages=len(result),all_pages_rendered=True,text_out_of_page=out_of_bounds,pages_rendered=result,contact_sheets=sheet_paths,visual_review='Pending agent contact-sheet inspection; rendering alone is not visual review')
a.pdf.with_suffix('.all_pages_validation.json').write_text(json.dumps(evidence,indent=2));print(json.dumps({k:v for k,v in evidence.items() if k!='pages_rendered'},indent=2));raise SystemExit(not evidence['success'])
