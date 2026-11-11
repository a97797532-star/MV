"""Independently parse/extract/render a generated PDF with an isolated PDFium installation."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('--tool-path',type=Path,default=Path('/tmp/mv-pdf-tools'));p.add_argument('--render-dir',type=Path);a=p.parse_args();sys.path.insert(0,str(a.tool_path))
import pypdfium2 as pdfium
from importlib.metadata import version
import numpy as np
pages=json.loads(a.pdf.with_suffix('.pages.json').read_text())['pages'];doc=pdfium.PdfDocument(str(a.pdf));render_indices={0,1,len(doc)-1,len(doc)//2}
for kind in ['text','table','figure']:
 match=next((i for i,r in enumerate(pages) if r['kind']==kind),None)
 if match is not None:render_indices.add(match)
output=a.render_dir or Path('outputs/pdfium_review')/a.pdf.stem;output.mkdir(parents=True,exist_ok=False);text_count=0;korean_pages=0;rendered=[]
for index in range(len(doc)):
 page=doc[index];textpage=page.get_textpage();text=textpage.get_text_bounded();textpage.close();text_count+=len(text);korean_pages+=int(any('\uac00'<=c<='\ud7a3' for c in text))
 if index in render_indices:
  bitmap=page.render(scale=1.2);pil=bitmap.to_pil();array=np.asarray(pil);nonwhite=float(np.mean(np.min(array[:,:,:3],axis=2)<245));target=output/f'page_{index+1:03}.png';pil.save(target);rendered.append(dict(page=index+1,path=str(target),nonwhite_pixel_fraction=nonwhite));pil.close();bitmap.close()
 page.close()
count=len(doc);doc.close();evidence=dict(renderer='PDFium via pypdfium2',renderer_version=version('pypdfium2'),page_count=count,manifest_page_count=len(pages),page_count_matches=count==len(pages),extracted_text_characters=text_count,pages_with_extractable_korean=korean_pages,all_pages_have_korean=korean_pages==count,rendered_pages=rendered,blank_render_detected=any(r['nonwhite_pixel_fraction']<.001 for r in rendered));evidence['success']=evidence['page_count_matches'] and evidence['all_pages_have_korean'] and not evidence['blank_render_detected'];a.pdf.with_suffix('.render_validation.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False));print(json.dumps(evidence,indent=2,ensure_ascii=False));raise SystemExit(not evidence['success'])
