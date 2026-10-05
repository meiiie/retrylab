"""Validate generated report artifacts and render every page for visual review."""
import hashlib
import json
from pathlib import Path
import re

import fitz
from PIL import Image, ImageDraw
from reportlab.lib.units import mm

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TMP=ROOT/'tmp/pdfs/journal'


def check():
    report={'scope':'Artifact/layout checks; assistant visual inspection recorded separately','documents':{}}
    build=json.loads((HERE/'report_build.json').read_text(encoding='utf-8'))
    for path,expected in build['files'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    for lang in ['en','vi']:
        path=ROOT/f'output/pdf/retrylab-journal-{lang}.pdf'
        doc=fitz.open(path);text='\n'.join(page.get_text() for page in doc)
        layout=json.loads((HERE/f'layout_{lang}.json').read_text(encoding='utf-8'))
        margin=25*mm
        assert '{{' not in text and '[FIGURE:' not in text and '[TABLE:' not in text
        assert '\ufffd' not in text and '\u25a0' not in text
        for value in ['17.91','18.85','19.16','-1.24','31,500','1,500']:
            assert value in text,(lang,value)
        assert all(len(page.get_images())==0 for page in doc),'Raster image found in report'
        problems=[];fonts={};used_fonts=set();thumbnails=[]
        for index,page in enumerate(doc):
            for b in page.get_text('dict')['blocks']:
                for line in b.get('lines',[]):
                    for span in line['spans']:
                        used_fonts.add(span['font'])
                        x0,y0,x1,y1=span['bbox']
                        if x0<margin-1 or x1>page.rect.width-margin+1 or y0<20 or y1>page.rect.height-15:
                            problems.append({'page':index+1,'text':span['text'],'box':span['bbox']})
            for font in page.get_fonts(full=True):
                fonts[font[0]]=font[3].split('+')[-1]
            png=TMP/f'{lang}-page-{index+1:02d}.png'
            page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(png)
            im=Image.open(png).convert('RGB');im.thumbnail((360,510))
            thumb=Image.new('RGB',(380,550),'#e1e5e8');thumb.paste(im,((380-im.width)//2,26))
            ImageDraw.Draw(thumb).text((12,8),f'{lang.upper()} / {index+1}',fill='black')
            thumbnails.append(thumb)
        assert not problems,problems
        assert len(layout['vector_placements'])==8
        for panel in layout['vector_placements']:
            assert abs(panel['x']-margin)<.01
            assert abs(panel['width']-(doc[0].rect.width-2*margin))<.01
            assert panel['y_from_top']>=margin-.01
            assert panel['y_from_top']+panel['height']<=doc[0].rect.height-margin+.01
            if panel['source'].startswith('figure_'):
                num=panel['source'].split('_')[1]
                prefix='Figure' if lang=='en' else 'Hình'
                assert re.search(r'^'+prefix+r' '+num+r'\.',doc[panel['page']-1].get_text(),re.M),f'Caption not on figure page: {panel}'
            else:
                with fitz.open(TMP/panel['source']) as eq:
                    assert abs(eq[0].rect.width-panel['width'])<.01,'Equation magnification changed'
        # ReportLab declares an unused default Helvetica resource. Check visible text fonts.
        font_sizes=[len(doc.extract_font(xref)[3]) for xref,name in fonts.items() if name in used_fonts]
        assert all(n>0 for n in font_sizes),'Unembedded font found'
        for group,start in enumerate(range(0,len(thumbnails),6),1):
            chunk=thumbnails[start:start+6]
            canvas=Image.new('RGB',(380*3,550*((len(chunk)+2)//3)),'white')
            for j,im in enumerate(chunk):canvas.paste(im,((j%3)*380,(j//3)*550))
            canvas.save(TMP/f'{lang}-contact-{group}.png')
        (TMP/f'{lang}-extracted.txt').write_text(text,encoding='utf-8')
        report['documents'][lang]={'path':str(path),'pages':len(doc),'all_fonts_embedded':True,
                                   'raster_images':0,'text_boundary_violations':0,
                                   'all_pages_rendered':True,'verified_horizontal_margins_mm':25,
                                   'figures_and_captions_same_page':True,'equation_scale':1,
                                   'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    for svg in (HERE/'figures').glob('*.svg'):
        text=svg.read_text(encoding='utf-8')
        assert '<image' not in text and '<text' in text,svg
    report['editable_svg_count']=len(list((HERE/'figures').glob('*.svg')))
    report['passed']=True
    (HERE/'report_qa.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':check()
