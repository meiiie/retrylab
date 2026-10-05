"""Render the Vietnamese Markdown report; this is not a LaTeX compilation."""
from html import escape
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle, KeepTogether, CondPageBreak

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'output/pdf/retrylab-de4-bao-cao.pdf'


def inline(text):
    text=escape(text.replace('—','-').replace('–','-').replace('\u2011','-'))
    text=re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#2455ac">\1</link>',text)
    text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
    return re.sub(r'`([^`]+)`',r'<font name="Mono">\1</font>',text)


def main():
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold','C:/Windows/Fonts/arialbd.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Italic','C:/Windows/Fonts/ariali.ttf'))
    pdfmetrics.registerFont(TTFont('Mono','C:/Windows/Fonts/consola.ttf'))
    pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
    body=ParagraphStyle('body',fontName='Arial',fontSize=10,leading=15,spaceAfter=9,splitLongWords=True,allowWidows=0,allowOrphans=0)
    title=ParagraphStyle('title',parent=body,fontName='Arial-Bold',fontSize=22,leading=28,spaceAfter=20,keepWithNext=True)
    heading=ParagraphStyle('heading',parent=body,fontName='Arial-Bold',fontSize=14,leading=20,spaceBefore=15,spaceAfter=10,keepWithNext=True)
    cell=ParagraphStyle('cell',parent=body,fontSize=8,leading=11,spaceAfter=0)
    code_style=ParagraphStyle('code',fontName='Mono',fontSize=8,leading=11,spaceAfter=12,backColor=colors.HexColor('#f3f5f7'),borderPadding=8)
    lines=(ROOT/'paper/DE_4_BAO_CAO_VA_DEMO.md').read_text(encoding='utf-8').splitlines()
    story=[]
    index=0
    while index<len(lines):
        line=lines[index]
        if not line.strip():
            index+=1
            continue
        if line.startswith('```'):
            block=[]
            index+=1
            while index<len(lines) and not lines[index].startswith('```'):
                block.append(lines[index]); index+=1
            story.append(KeepTogether([Preformatted('\n'.join(block),code_style)]))
            index+=1
            continue
        if line.startswith('|'):
            rows=[]
            while index<len(lines) and lines[index].startswith('|'):
                parts=[part.strip() for part in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',part) for part in parts):
                    rows.append([Paragraph(inline(part),cell) for part in parts])
                index+=1
            width=499
            widths=([115,198,186] if len(rows[0])==3 else [width/len(rows[0])]*len(rows[0]))
            table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f8')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
                ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),8),
                ('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d4dbe4'))]))
            story.extend([table,Spacer(1,12)])
            continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]),title))
        elif line.startswith('## '):
            story.append(CondPageBreak(140 if line.startswith('## 8.') else 90))
            story.append(Paragraph(inline(line[3:]),heading))
        else:
            story.append(Paragraph(inline(line),body))
        index+=1
    def page(canvas,doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d4dbe4'))
        canvas.line(48,45,547,45)
        canvas.setFont('Arial',8)
        canvas.setFillColor(colors.HexColor('#627080'))
        canvas.drawString(48,30,'RetryLab | Đề 4 | Prototype và thực nghiệm mô phỏng | 26/09/2026')
        canvas.drawRightString(547,30,str(doc.page))
        canvas.restoreState()
    document=SimpleDocTemplate(str(TARGET),pagesize=(595,842),leftMargin=48,rightMargin=48,topMargin=45,bottomMargin=58,
        title='RetryLab - Đề 4: Báo cáo và kịch bản demo',author='RetryLab project')
    document.build(story,onFirstPage=page,onLaterPages=page)
    (ROOT/'paper/topic4_render_status.json').write_text(json.dumps({
        'latex_source':'paper/topic4_policy.tex','native_latex_compilation':'failed: Unable to find standard directories for platform',
        'pdf':'output/pdf/retrylab-de4-bao-cao.pdf','pdf_source':'paper/DE_4_BAO_CAO_VA_DEMO.md',
        'pdf_renderer':'ReportLab; Vietnamese companion report, not compiled English LaTeX manuscript'},indent=2)+'\n',encoding='utf-8')
    print(TARGET)


if __name__=='__main__':
    main()
