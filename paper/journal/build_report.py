"""Build editable manuscripts and vector PDFs from verified, frozen experiment outputs."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re

import fitz
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                               Spacer, Flowable, KeepTogether, LongTable, TableStyle, PageBreak)

import build_assets as assets

ROOT, HERE, RUN = assets.ROOT, assets.HERE, assets.RUN
OUT = ROOT/'output/pdf'
TMP = ROOT/'tmp/pdfs/journal'
MARGIN = 25 * mm
WIDTH = A4[0] - 2 * MARGIN
HEIGHT = A4[1] - 2 * MARGIN
POLICY_NAMES = dict(zip(assets.POLICIES, assets.NAMES))
WORLD_NAMES = dict(zip(assets.WORLDS, assets.WORLD_NAMES))
FIGURES = {
    'architecture': ('figure_1_architecture', 1,
        'Training artifacts and browser decision flow. Only retained past responses enter the learner-state update. The application does not observe latent simulator skills.',
        'Luồng huấn luyện và quyết định trong trình duyệt. Mô hình chỉ cập nhật từ các phản hồi quá khứ hợp lệ; ứng dụng không thấy kỹ năng ẩn trong simulator.'),
    'protocol': ('figure_2_protocol', 2,
        'Fixed-design experiment and sampling units. Repeated rollouts share learner seeds and trained fits; they are not independent human participants.',
        'Thiết kế thực nghiệm và đơn vị lấy mẫu. Các rollout dùng chung seed người học và mô hình, không phải các sinh viên độc lập.'),
    'prediction_policy': ('figure_3_prediction_policy', 3,
        'Prediction and selection have different outcomes. A: validation negative log-likelihood, lower is better. B: nominal expected probe gain; bars show 95% learner-bootstrap intervals conditional on three fixed fits.',
        'Dự báo và chọn bài được đo riêng. A: tổn thất log âm trên validation, thấp hơn là tốt hơn. B: tăng trưởng probe danh định, với khoảng 95% bootstrap người học có điều kiện trên ba lần fit.'),
    'stress': ('figure_4_stress_contrasts', 4,
        'Paired probe-gain contrasts across all five environments. Points compare aware/probe with each named comparator. Bars are conditional 95% intervals; zero means no observed mean difference. No multiplicity adjustment is applied.',
        'Tương phản tăng trưởng probe ghép cặp trong năm môi trường. Điểm là aware/probe trừ chính sách đối chiếu; thanh là khoảng 95% có điều kiện. Không hiệu chỉnh nhiều so sánh.'),
}
REFERENCES = [
    ('Cheng, X., Zhuang, G., Xie, Y., Wang, J., Liu, Y., Guan, Q., Fang, L., & Pan, S.', '2026',
     'UniER: A unified benchmark for item-level and path-level exercise recommendation', 'arXiv. Preprint', 'https://arxiv.org/abs/2605.16750'),
    ('Corbett, A. T., & Anderson, J. R.', '1994',
     'Knowledge tracing: Modeling the acquisition of procedural knowledge', 'User Modeling and User-Adapted Interaction, 4, 253-278', 'https://doi.org/10.1007/BF01099821'),
    ('Girard, S., Minn, S., Bouzeghoub, A., & Vie, J.-J.', '2026',
     'Counterfactual learning of new adaptive instructional policies using logged data', 'arXiv. Preprint version', 'https://arxiv.org/abs/2606.23015'),
    ('Minn, S.', '2022', 'AI-assisted knowledge assessment techniques for adaptive learning environments',
     'Computers and Education: Artificial Intelligence, 3, Article 100050', 'https://doi.org/10.1016/j.caeai.2022.100050'),
    ('Ozyurt, Y., Almaci, T., Feuerriegel, S., & Sachan, M.', '2025',
     'Personalized exercise recommendation with semantically-grounded knowledge tracing',
     'Advances in Neural Information Processing Systems, 38', 'https://proceedings.neurips.cc/paper_files/paper/2025/hash/13707aad517ddd6c09ea02e0f55e1e7a-Abstract-Conference.html'),
    ('Piech, C., Spencer, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L., & Sohl-Dickstein, J.', '2015',
     'Deep knowledge tracing', 'Advances in Neural Information Processing Systems, 28', 'https://arxiv.org/abs/1506.05908'),
    ('Shi, Y., Chi, M., Barnes, T., & Price, T. W.', '2022',
     'Code-DKT: A code-based knowledge tracing model for programming tasks', 'arXiv. Preprint', 'https://arxiv.org/abs/2206.03545'),
    ('van Hasselt, H., Guez, A., & Silver, D.', '2016',
     'Deep reinforcement learning with double Q-learning', 'Proceedings of the AAAI Conference on Artificial Intelligence, 30(1), 2094-2100',
     'https://doi.org/10.1609/aaai.v30i1.10295'),
]
EQUATIONS = {
    'emission': (1, [r'q_1=1-s-0.05d+(s+0.05d)\rho,',
                      r'q_0=g-0.05d+(1-g+0.05d)\rho.']),
    'bayes': (2, [r'b^{+}=\frac{b^{*}q_1^{y}(1-q_1)^{1-y}}{p^{y}(1-p)^{1-y}}.']),
    'ddqn': (3, [r'a^{*}=\operatorname{argmax}_{a\in\mathcal{A}(x^{\prime})}Q_{\theta}(x^{\prime},a),',
                  r'Y=r+\gamma(1-\mathrm{done})Q_{\bar{\theta}}(x^{\prime},a^{*}).']),
    'gain': (4, [r'G=\frac{1}{3}\sum_{k=1}^{3}[(0.2+0.7M_{T,k})-(0.2+0.7M_{0,k})].']),
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interval(metric):
    return f"[{100*metric['ci95'][0]:.2f}, {100*metric['ci95'][1]:.2f}]"


def prepare():
    s = assets.load()
    protocol = read(RUN/'protocol.json')
    checkpoint = read(RUN/'ddqn_aware-101.json')
    catalog = read(ROOT/'app/static/data/catalog-v2.json')['exercises']
    demo = read(ROOT/'harness/demo_validation.json')
    for report in demo['reports']:
        assert digest(ROOT/report['path']) == report['sha256'], report['path']
    parity = read(ROOT/'app/test_outputs/policy_browser_report.json')
    nominal = {r['policy']: r for r in s['rows'] if r['world'] == 'nominal'}
    contrast = lambda world, right: next(c for c in s['contrasts'] if c['world'] == world and c['right'] == right)
    repair = [100*r['practice_success']['mean'] for r in s['rows'] if r['world'] == 'repair_only']
    n_worlds = len({r['world'] for r in s['rows']})
    vals = {
        'rollouts': f"{len(s['rows'])*len(s['seeds'])*s['settings']['evaluation_learners']:,}",
        'learners': f"{n_worlds*s['settings']['evaluation_learners']:,}",
        'tasks': str(len(catalog)), 'cases': str(sum(len(t['tests']) for t in catalog)),
        'parameters': f"{checkpoint['training']['parameters']:,}",
        'steps': f"{s['settings']['training_steps']:,}",
        'train_histories': str(s['settings']['model_train_episodes']),
        'validation_histories': str(s['settings']['model_validation_episodes']),
        'bootstraps': f"{int(re.search(r'^(\d+)',protocol['uncertainty']).group(1)):,}",
        'practice_zpd': f"{nominal['zpd']['practice_success']['mean']*100:.2f}",
        'repair_min': f'{min(repair):.2f}', 'repair_max': f'{max(repair):.2f}',
        'result_rows': str(len(s['rows'])),
        'q_error': f"{max(v['q'] for v in parity['parity_max_errors']):.3g}",
        'software_checks': str(demo['unit_policy_backend_checks']),
        'experiment_seconds': f"{s['elapsed_seconds']:.1f}",
    }
    for key, policy in [('aware','ddqn_aware'),('naive','ddqn_naive'),('weakest','weakest')]:
        vals['gain_'+key] = f"{100*nominal[policy]['probe_gain']['mean']:.2f}"
    for key, world, right in [('naive','nominal','ddqn_naive'),('weakest','nominal','weakest'),
                              ('prereq','prerequisites','ddqn_naive'),('forget','forgetting','ddqn_success')]:
        c = contrast(world,right)
        if key in ['naive','weakest']:
            vals['delta_'+key], vals['ci_'+key] = f"{100*c['mean']:.2f}", interval(c)
        else:
            vals[key+'_delta'], vals[key+'_ci'] = f"{100*c['mean']:.2f}", interval(c)
    tables = {
        'settings': ('1', 'Training and evaluation settings', 'Cấu hình huấn luyện và đánh giá',
            ['Setting / Cấu hình','Value / Giá trị'], [
                ['Catalog / executable tests',f"{vals['tasks']} tasks / {vals['cases']} cases"],
                ['History length / attempt cap',f"{checkpoint['horizon']} / {checkpoint['max_attempts']}"],
                ['Filter histories per seed',f"{vals['train_histories']} train; {vals['validation_histories']} validation"],
                ['Training seeds',', '.join(map(str,s['seeds']))],
                ['Network / parameters',f"28-64-64-12 ReLU / {vals['parameters']}"],
                ['Transitions / networks',f"{vals['steps']} per network / 9 networks"],
                ['Replay / batch / warm-up','12,000 / 64 / 512 transitions'],
                ['Update / target copy','Every 4 / 400 transitions'],
                ['Optimizer / learning rate','Adam / 0.001; Huber loss; norm clip 5'],
                ['Discount / exploration','0.99; epsilon 1 to 0.05 over 75% of budget'],
                ['Evaluation',f"7 policies; 5 worlds; {s['settings']['evaluation_learners']} learners/world"],
                ['Sampling / intervals',f"{vals['learners']} learner identities; {vals['bootstraps']} paired bootstraps"],
                ['Recorded framework',f"PyTorch {s['torch']}; one CPU thread"],
            ], [180,WIDTH-180]),
        'nll': ('2', 'Validation negative log-likelihood per response', 'Tổn thất log âm validation trên mỗi phản hồi',
            ['Seed','Naive','Repeat-aware','Aware - naive'],
            [[str(seed),f"{s['fits'][str(seed)]['naive']['validation_nll']:.6f}",
              f"{s['fits'][str(seed)]['aware']['validation_nll']:.6f}",
              f"{s['fits'][str(seed)]['aware']['validation_nll']-s['fits'][str(seed)]['naive']['validation_nll']:.6f}"] for seed in s['seeds']],
            [61,123,134,WIDTH-318]),
        'nominal': ('3', 'Nominal policy outcomes', 'Kết quả chính sách trong môi trường danh định',
            ['Policy','Gain (pp)','95% CI (pp)','Practice (%)'],
            [[POLICY_NAMES[p],f"{100*nominal[p]['probe_gain']['mean']:.2f}",interval(nominal[p]['probe_gain']),
              f"{100*nominal[p]['practice_success']['mean']:.2f}"] for p in assets.POLICIES],
            [177,60,128,WIDTH-365]),
        'full': ('A.1', 'Complete policy-environment outcomes', 'Toàn bộ kết quả theo chính sách và môi trường',
            ['Environment','Policy','Gain (pp)','95% CI (pp)','Practice (%)'],
            [[WORLD_NAMES[w], POLICY_NAMES[p],f"{100*r['probe_gain']['mean']:.2f}",interval(r['probe_gain']),
              f"{100*r['practice_success']['mean']:.2f}"] for w in assets.WORLDS for p in assets.POLICIES
             for r in s['rows'] if r['world']==w and r['policy']==p],
            [70,137,49,111,WIDTH-367]),
    }
    return s, vals, tables


def resolve(template, values):
    result = re.sub(r'\{\{([a-z_]+)\}\}', lambda m: values[m.group(1)], template)
    assert '{{' not in result and '}}' not in result
    return result


def plain(text):
    return text.replace('–','-').replace('—','; ').replace('−','-').replace('\u2011','-')


def esc(text):
    return html.escape(plain(text),quote=False)


def container_parts(text):
    """APA journal name/volume are italic; issue, pages and article numbers are not."""
    for boundary in [', 253-', ', Article ', '(1),']:
        if boundary in text:
            at=text.index(boundary)
            return text[:at],text[at:]
    return text,''


def tex_escape(text):
    table = {'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$',
             '#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}',
             '^':r'\textasciicircum{}','×':r'\ensuremath{\times}',
             '→':r'\ensuremath{\rightarrow}','≤':r'\ensuremath{\leq}',
             'γ':r'\ensuremath{\gamma}'}
    return ''.join(table.get(c,c) for c in plain(text))


def equations():
    plt.rcParams.update({'mathtext.fontset':'stix','font.family':'STIXGeneral'})
    for key,(number,lines) in EQUATIONS.items():
        height = 22*len(lines) + 8
        fig = plt.figure(figsize=(WIDTH/72,height/72))
        for i,line in enumerate(lines):
            fig.text(.46,(height-15-i*22)/height,'$'+line+'$',ha='center',va='center',fontsize=11)
        fig.text(1,.5,f'({number})',ha='right',va='center',fontsize=11)
        fig.savefig(TMP/f'equation_{key}.pdf',facecolor='white')
        plt.close(fig)


class VectorPanel(Flowable):
    """Reserve layout space; insert the source PDF as vector graphics after pagination."""
    def __init__(self, source, locations, width=WIDTH, max_height=None):
        super().__init__()
        self.source, self.locations, self.width = source, locations, width
        with fitz.open(source) as doc:
            self.height = width * doc[0].rect.height / doc[0].rect.width
        if max_height and self.height > max_height:
            self.width *= max_height/self.height
            self.height = max_height
        self.hAlign = 'CENTER'

    def draw(self):
        x,y = self.canv.absolutePosition(0,0)
        self.locations.append((self.canv.getPageNumber()-1,x,y,self.width,self.height,self.source))


class ManuscriptDoc(BaseDocTemplate):
    """Allow nearby prose to fill a page while an intact figure awaits the next page."""
    def filterFlowables(self, flowables):
        if not hasattr(self,'frame') or len(flowables)<2 or self.frame._atTop:
            return
        block=flowables[0]
        if not getattr(block,'is_figure',False) or getattr(block,'deferrals',0)>=3:
            return
        available=self.frame._y-self.frame._y1p
        block.wrapOn(self.canv,self.frame._aW,available)
        if block._H<=available:
            return
        candidate=flowables[1]
        if not isinstance(candidate,Paragraph):
            return
        count=1
        if candidate.style.name!='body' or available<2*14.5+8:
            return
        prose=flowables[1:1+count]
        del flowables[1:1+count]
        flowables[0:0]=prose
        block.deferrals=getattr(block,'deferrals',0)+1


def styles():
    for name,file in [('Body','times.ttf'),('BodyBold','timesbd.ttf'),('BodyItalic','timesi.ttf')]:
        pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='BodyItalic',boldItalic='BodyBold')
    base = dict(fontName='Body',fontSize=11,leading=14.5,textColor=colors.black)
    return {
        'body': ParagraphStyle('body',**base,alignment=TA_JUSTIFY,spaceAfter=5,allowWidows=0,allowOrphans=0),
        'title': ParagraphStyle('title',fontName='BodyBold',fontSize=18,leading=21,spaceAfter=8,alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle',fontName='BodyItalic',fontSize=11,leading=14,spaceAfter=16,alignment=TA_CENTER),
        'h2': ParagraphStyle('h2',fontName='BodyBold',fontSize=12,leading=15,spaceBefore=12,spaceAfter=5,keepWithNext=True),
        'h3': ParagraphStyle('h3',fontName='BodyItalic',fontSize=11,leading=14.5,spaceBefore=9,spaceAfter=4,keepWithNext=True),
        'caption': ParagraphStyle('caption',fontName='Body',fontSize=9.5,leading=12,spaceAfter=8),
        'table_caption': ParagraphStyle('tc',fontName='Body',fontSize=9.5,leading=12,spaceBefore=8,spaceAfter=5,keepWithNext=True),
        'cell': ParagraphStyle('cell',fontName='Body',fontSize=9.3,leading=11.5,spaceAfter=0),
        'number': ParagraphStyle('number',fontName='Body',fontSize=9.3,leading=11.5,spaceAfter=0,alignment=TA_RIGHT),
        'ref': ParagraphStyle('ref',fontName='Body',fontSize=10,leading=12.5,spaceAfter=6,leftIndent=14,firstLineIndent=-14,allowWidows=0,allowOrphans=0),
    }


def pdf_report(document,lang,tables):
    st = styles(); story=[]; locations=[]
    paragraphs = re.split(r'\n\s*\n',document.strip())
    for index,p in enumerate(paragraphs):
        p=p.strip()
        if p.startswith('# '):
            story.append(Paragraph(esc(p[2:]),st['title']))
        elif index==1:
            story.append(Paragraph(esc(p),st['subtitle']))
        elif p.startswith('### '):
            story.append(Paragraph(esc(p[4:]),st['h3']))
        elif p.startswith('## '):
            if p in ['## References','## Tài liệu tham khảo']:continue
            if 'Appendix A.' in p or 'Phụ lục A.' in p:
                story.append(PageBreak())
            story.append(Paragraph(esc(p[3:]),st['h2']))
        elif p.startswith('[FIGURE:'):
            key=p[8:-1];stem,num,en,vi=FIGURES[key]
            caption=f"<b>{'Figure' if lang=='en' else 'Hình'} {num}.</b> {esc(en if lang=='en' else vi)}"
            block=KeepTogether([Spacer(1,7),VectorPanel(HERE/'figures'/f'{stem}.pdf',locations),
                                Spacer(1,5),Paragraph(caption,st['caption'])])
            block.is_figure=True
            story.append(block)
        elif p.startswith('[EQUATION:'):
            key=p[10:-1]
            story.append(KeepTogether([Spacer(1,3),VectorPanel(TMP/f'equation_{key}.pdf',locations),Spacer(1,5)]))
        elif p.startswith('[TABLE:'):
            key=p[7:-1];num,en,vi,header,rows,widths=tables[key]
            caption=f"<b>{'Table' if lang=='en' else 'Bảng'} {num}.</b> {esc(en if lang=='en' else vi)}."
            if key=='settings':header=['Setting','Value'] if lang=='en' else ['Cấu hình','Giá trị']
            if key=='full':widths=[80,128,50,111,WIDTH-369]
            numeric_start={'settings':2,'nll':1,'nominal':1,'full':2}[key]
            cell_style=lambda j: st['number'] if j>=numeric_start else st['cell']
            cells=[[Paragraph('<b>'+esc(x)+'</b>',cell_style(j)) for j,x in enumerate(header)]]
            for i,row in enumerate(rows):
                cells.append([Paragraph(esc('' if key=='full' and j==0 and i%7 else x),cell_style(j)) for j,x in enumerate(row)])
            chunks=[cells]
            rules=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),
                   ('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),2.25 if key=='full' else 4),
                   ('BOTTOMPADDING',(0,0),(-1,-1),2.25 if key=='full' else 4),('LINEABOVE',(0,0),(-1,0),.7,colors.black),
                   ('LINEBELOW',(0,0),(-1,0),.45,colors.black),('LINEBELOW',(0,-1),(-1,-1),.7,colors.black)]
            for chunk_index,chunk in enumerate(chunks):
                if chunk_index:story.append(PageBreak())
                label=caption+(' (continued)' if chunk_index and lang=='en' else ' (tiếp theo)' if chunk_index else '')
                table=LongTable(chunk,colWidths=widths,repeatRows=1,hAlign='LEFT')
                chunk_rules=list(rules)
                if key=='full':
                    chunk_rules.extend([('LINEABOVE',(0,i),(-1,i),.3,colors.grey) for i in [8,15,22,29] if i<len(chunk)])
                table.setStyle(TableStyle(chunk_rules))
                story.extend([Paragraph(label,st['table_caption']),table,Spacer(1,9)])
        elif p=='[REFERENCES]':
            references=[Paragraph('References' if lang=='en' else 'Tài liệu tham khảo',st['h2'])]
            for authors,year,title,container,url in REFERENCES:
                if container.startswith('arXiv.'):
                    text=f'{esc(authors)} ({year}). <i>{esc(title)}</i> [Preprint]. arXiv. '
                else:
                    italic,suffix=container_parts(container)
                    text=f'{esc(authors)} ({year}). {esc(title)}. <i>{esc(italic)}</i>{esc(suffix)}. '
                text+=f'<br/><link href="{html.escape(url,quote=True)}" color="#246188">{esc(url)}</link>'
                references.append(Paragraph(text,st['ref']))
            story.append(KeepTogether(references))
        else:
            story.append(Paragraph(esc(p),st['body']))

    title=paragraphs[0][2:]
    temporary=TMP/f'layout_{lang}.pdf'
    doc=ManuscriptDoc(str(temporary),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=MARGIN,bottomMargin=MARGIN,
                         title=title,author='',subject='Controlled simulation; research manuscript draft')
    def footer(canvas,document):
        canvas.setFont('BodyItalic',8.5);canvas.setFillColor(colors.HexColor('#555555'))
        label='Adaptive programming practice' if lang=='en' else 'Luyện tập lập trình thích nghi'
        if document.page>1:
            canvas.drawString(MARGIN,A4[1]-15*mm,label)
            canvas.drawRightString(A4[0]-MARGIN,A4[1]-15*mm,'Research draft' if lang=='en' else 'Bản thảo nghiên cứu')
        canvas.setFont('Body',9)
        canvas.drawCentredString(A4[0]/2,13*mm,str(document.page))
    frame=Frame(MARGIN,MARGIN,WIDTH,HEIGHT,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='text')
    doc.addPageTemplates(PageTemplate(id='manuscript',frames=[frame],onPage=footer))
    doc.build(story)
    result=fitz.open(temporary)
    for page,x,y,w,h,source in locations:
        with fitz.open(source) as vector:
            result[page].show_pdf_page(fitz.Rect(x,A4[1]-y-h,x+w,A4[1]-y),vector,0)
    result.set_metadata({'title':title,'author':'','subject':'Controlled simulation; research manuscript draft',
                         'creator':'RetryLab reproducible report builder','producer':'ReportLab + PyMuPDF (not native LaTeX)'})
    path=OUT/f'retrylab-journal-{lang}.pdf'
    result.save(path,garbage=4,deflate=True);result.close()
    placements=[{'page':page+1,'x':x,'y_from_top':A4[1]-y-h,'width':w,'height':h,
                 'source':source.name} for page,x,y,w,h,source in locations]
    (HERE/f'layout_{lang}.json').write_text(json.dumps({'page_size_pt':A4,'margins_mm':[25,25,25,25],
          'frame_padding_pt':0,'body_font_pt':11,'body_leading_pt':14.5,'vector_placements':placements},indent=2)+'\n',encoding='utf-8')
    return path


def tikz_figure(key,s):
    """Self-contained editable vector figures for a standalone TeX document."""
    if key in ['architecture','protocol']:
        if key=='architecture':
            rows=[['Synthetic histories','Bayesian filter','Double DQN','Frozen artifacts'],
                  ['Past responses','Belief + history','Masked Q values','Next exercise']]
            detail=[['300 train + 100 validation','Naive / repeat-aware','28--64--64--12','Catalog + weights'],
                    ['Item + binary outcome','28 state values','Highest legal Q','12 Python tasks']]
        else:
            rows=[['Fit and train','Freeze design','Evaluate','Quantify uncertainty']]
            detail=[['3 seeds; 9 networks','Fixed final checkpoint','7 policies; 5 worlds','Paired learner bootstrap']]
        code=[r'\begin{tikzpicture}[>=stealth, every node/.style={font=\scriptsize}, box/.style={draw=blue!55!black,rounded corners,align=center,text width=2.85cm,minimum height=1.3cm}]']
        for j,row in enumerate(rows):
            for i,title in enumerate(row):
                code.append(r'\node[box] (n%d%d) at (%.2f,%.2f) {\textbf{%s}\\%s};'%(j,i,i*3.45,-j*2.0,title,detail[j][i]))
                if i:
                    code.append(r'\draw[->] (n%d%d) -- (n%d%d);'%(j,i-1,j,i))
        if key=='architecture':
            code.extend([r'\draw[->] (n03.south) -- ++(0,-.3) -| (n12.north);',
                         r'\draw[->] (n13.south) -- ++(0,-.5) -| (n10.south);',
                         r'\node[align=center] at (5.2,-3.3) {Browser worker grades code; history updates beliefs, not network weights.\\Latent simulator skills are evaluator-only quantities.};'])
        else:
            code.append(r'\node[align=center] at (5.2,-1.3) {1,500 distinct synthetic learners; 31,500 correlated rollouts.\\Conditional uncertainty; no human learning-effect estimate.};')
        code.append(r'\end{tikzpicture}')
        return '\n'.join(code)
    if key=='prediction_policy':
        code=[r'\begin{tikzpicture}',r'\begin{axis}[width=.36\textwidth,height=5.6cm,title={A: Response NLL},xtick={0,1},xticklabels={Naive,Aware},xmin=-.2,xmax=1.2,ymin=.61,ymax=.665,grid=major,font=\scriptsize,legend style={font=\tiny,at={(.98,.98)},anchor=north east}]']
        for seed,color in zip(s['seeds'],['blue!65!black','green!40!black','orange!80!black']):
            f=s['fits'][str(seed)]
            code.append(r'\addplot[color=%s,mark=*] coordinates {(0,%.8f) (1,%.8f)};\addlegendentry{Seed %s}'%(color,f['naive']['validation_nll'],f['aware']['validation_nll'],seed))
        code.extend([r'\end{axis}',r'\begin{axis}[at={(6.35cm,0)},anchor=south west,width=.57\textwidth,height=5.6cm,title={B: Nominal probe gain (pp)},xmin=10,xmax=23,ymin=-.5,ymax=6.5,y dir=reverse,ytick={0,1,2,3,4,5,6},yticklabels={Random,Difficulty,Weakest,Target 0.7,Naive/probe,Aware/probe,Aware/correct},grid=major,font=\scriptsize]'])
        for i,p in enumerate(assets.POLICIES):
            r=next(r for r in s['rows'] if r['world']=='nominal' and r['policy']==p)['probe_gain']
            color='orange!80!black' if p=='ddqn_aware' else 'blue!65!black'
            code.append(r'\addplot[color=%s,mark=none] coordinates {(%.6f,%d) (%.6f,%d)};'%(color,r['ci95'][0]*100,i,r['ci95'][1]*100,i))
            code.append(r'\addplot[color=%s,only marks,mark=*] coordinates {(%.6f,%d)};'%(color,r['mean']*100,i))
        code.extend([r'\end{axis}',r'\end{tikzpicture}']);return '\n'.join(code)
    code=[r'\begin{tikzpicture}',r'\begin{axis}[width=.94\textwidth,height=7cm,xmin=-3,xmax=3.5,ymin=-.5,ymax=4.5,y dir=reverse,ytick={0,1,2,3,4},yticklabels={Nominal,Repair only,Slow transfer,Forgetting,Prerequisites},xlabel={Aware/probe minus comparator (percentage points)},grid=major,font=\small,legend style={font=\scriptsize,at={(.5,1.02)},anchor=south,legend columns=3}]',r'\addplot[gray,dashed,forget plot] coordinates {(0,-.5) (0,4.5)};']
    for offset,right,label,color,mark in [(-.2,'ddqn_naive','vs naive','blue!65!black','*'),(0,'weakest','vs weakest','orange!80!black','square*'),(.2,'ddqn_success','vs correctness','green!40!black','triangle*')]:
        for i,w in enumerate(assets.WORLDS):
            r=next(c for c in s['contrasts'] if c['world']==w and c['right']==right)
            code.append(r'\addplot[color=%s,mark=none,forget plot] coordinates {(%.6f,%.2f) (%.6f,%.2f)};'%(color,r['ci95'][0]*100,i+offset,r['ci95'][1]*100,i+offset))
        coords=' '.join('(%.6f,%.2f)'%(next(c for c in s['contrasts'] if c['world']==w and c['right']==right)['mean']*100,i+offset) for i,w in enumerate(assets.WORLDS))
        code.append(r'\addplot[color=%s,only marks,mark=%s] coordinates {%s};\addlegendentry{%s}'%(color,mark,coords,label))
    code.extend([r'\end{axis}',r'\end{tikzpicture}']);return '\n'.join(code)


def tex_report(document,s,tables):
    chunks=[r'''% Generated from paper/journal/manuscript_en.md and verified frozen outputs.
% Self-contained: no external figures or bibliography files required.
\documentclass[preprint,11pt,authoryear]{elsarticle}
\usepackage{geometry}
\geometry{a4paper,margin=25mm}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath,amsmath,booktabs,longtable,array}
\usepackage{tikz,pgfplots}
\pgfplotsset{compat=1.18}
\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue]{hyperref}
\usepackage{microtype}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlength{\emergencystretch}{3em}
\makeatletter
\let\ps@pprintTitle\ps@plain
\makeatother
\begin{document}''']
    paragraphs=re.split(r'\n\s*\n',document.strip())
    abstract_at=paragraphs.index('## Abstract')
    keywords=next(p for p in paragraphs if p.startswith('Keywords: '))
    chunks.extend([r'\begin{frontmatter}',r'\title{'+tex_escape(paragraphs[0][2:])+r': '+tex_escape(paragraphs[1])+'}',
                   r'\begin{abstract}',tex_escape(paragraphs[abstract_at+1]),r'\end{abstract}',
                   r'\begin{keyword}',r' \sep '.join(tex_escape(x.strip()) for x in keywords[10:].split(';')),
                   r'\end{keyword}',r'\end{frontmatter}',r'\fontsize{11}{14.5}\selectfont'])
    for index,p in enumerate(paragraphs):
        if index<=abstract_at+1 or p==keywords:continue
        if p.startswith('# '):
            chunks.append(r'{\LARGE\bfseries '+tex_escape(p[2:])+r'\par}')
        elif index==1:
            chunks.append(r'{\large\itshape '+tex_escape(p)+r'\par}\medskip')
        elif p.startswith('### '):
            chunks.append(r'\subsection*{'+tex_escape(p[4:])+'}')
        elif p.startswith('## '):
            if 'Appendix A.' in p:chunks.append(r'\clearpage')
            chunks.append(r'\section*{'+tex_escape(p[3:])+'}')
        elif p.startswith('[FIGURE:'):
            key=p[8:-1];stem,num,en,vi=FIGURES[key]
            chunks.extend([r'\begin{figure}[htbp]\centering',tikz_figure(key,s),r'\caption{'+tex_escape(en)+r'}\end{figure}'])
        elif p.startswith('[TABLE:'):
            key=p[7:-1];num,en,vi,header,rows,widths=tables[key]
            spec=''.join(r'p{%.3f\textwidth}'%(w/WIDTH-.024) for w in widths)
            chunks.extend([r'\begingroup\small\setlength{\tabcolsep}{3pt}',r'\begin{longtable}{'+spec+'}',
                           r'\multicolumn{%d}{l}{\textbf{Table %s.} %s}\\'%(len(header),num,tex_escape(en)),r'\toprule',
                           ' & '.join(r'\textbf{'+tex_escape(c)+'}' for c in header)+r'\\\midrule\endfirsthead',
                           ' & '.join(r'\textbf{'+tex_escape(c)+'}' for c in header)+r'\\\midrule\endhead',
                           r'\bottomrule\endfoot'])
            chunks.extend(' & '.join(tex_escape(c) for c in row)+r'\\' for row in rows)
            chunks.extend([r'\end{longtable}\endgroup'])
        elif p.startswith('[EQUATION:'):
            number,lines=EQUATIONS[p[10:-1]]
            chunks.append(r'\begin{equation}\begin{gathered}'+'\\'.join(lines)+r'\end{gathered}\tag{'+str(number)+r'}\end{equation}')
        elif p=='[REFERENCES]':
            chunks.append(r'\begin{list}{}{\setlength{\leftmargin}{1.3em}\setlength{\itemindent}{-1.3em}}')
            for authors,year,title,container,url in REFERENCES:
                italic,suffix=container_parts(container)
                body=(r'\textit{'+tex_escape(title)+r'} [Preprint]. arXiv.' if container.startswith('arXiv.') else
                      tex_escape(title)+r'. \textit{'+tex_escape(italic)+'}'+tex_escape(suffix)+'.')
                chunks.append(r'\item '+tex_escape(authors)+f' ({year}). '+body+r' \url{'+url+'}.')
            chunks.append(r'\end{list}')
        else:chunks.append(tex_escape(p))
    chunks.append(r'\end{document}')
    assert '\t' not in '\n'.join(chunks), 'Unexpected escaped tab in generated TeX'
    (ROOT/'paper/topic4_policy.tex').write_text('\n\n'.join(chunks)+'\n',encoding='utf-8')


def resolved_markdown(document,lang,tables):
    for key,(stem,num,en,vi) in FIGURES.items():
        cap=f"{'Figure' if lang=='en' else 'Hình'} {num}. {en if lang=='en' else vi}"
        document=document.replace(f'[FIGURE:{key}]',f'![{cap}](figures/{stem}.svg)\n\n{cap}')
    for key,(num,en,vi,header,rows,widths) in tables.items():
        table=f"{'Table' if lang=='en' else 'Bảng'} {num}. {en if lang=='en' else vi}.\n\n"
        table+='| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'
        table+='\n'.join('| '+' | '.join(row)+' |' for row in rows)
        document=document.replace(f'[TABLE:{key}]',table)
    for key,(num,lines) in EQUATIONS.items():
        document=document.replace(f'[EQUATION:{key}]','$$\n\\begin{gathered}'+'\\\\'.join(lines)+r'\end{gathered}\tag{'+str(num)+'}\n$$')
    refs='\n\n'.join(f'{a} ({y}). '+(f'*{t}* [Preprint]. arXiv.' if c.startswith('arXiv.') else
                    f'{t}. *{container_parts(c)[0]}*{container_parts(c)[1]}.')+f' {u}' for a,y,t,c,u in REFERENCES)
    document=document.replace('[REFERENCES]',refs)
    assert not re.search(r'\[(?:FIGURE|TABLE|EQUATION):|\{\{',document)
    (HERE/f'report_{lang}.md').write_text(document+'\n',encoding='utf-8')


def main():
    OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    assets.main()
    s,values,tables=prepare()
    equations()
    outputs=[];audits={}
    for lang in ['en','vi']:
        document=resolve((HERE/f'manuscript_{lang}.md').read_text(encoding='utf-8'),values)
        if lang=='en':
            abstract=document.split('## Abstract\n\n')[1].split('\n\nKeywords:')[0]
            audits['abstract_words_en']=len(abstract.split())
            audits['keywords_en']=len(document.split('Keywords: ')[1].split('\n')[0].split(';'))
            assert audits['abstract_words_en']<=250 and 1<=audits['keywords_en']<=7
            tex_report(document,s,tables)
        resolved_markdown(document,lang,tables)
        outputs.append(pdf_report(document,lang,tables))
    highlights=[
        'Repeat-aware state estimation improves response prediction in three fitted seeds.',
        'Better response likelihood does not ensure better exercise selection.',
        'A weakest-skill rule exceeds the learned policy in the nominal simulator.',
        'Independent probes separate practice correctness from simulated transfer.',
        'A shared task catalog links trained policies to an inspectable application.',
    ]
    assert 3<=len(highlights)<=5 and max(map(len,highlights))<=85
    (HERE/'highlights.txt').write_text('\n'.join(highlights)+'\n',encoding='utf-8')
    (HERE/'tables/report_values.json').write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    (HERE/'references/bibliography.json').write_text(json.dumps(REFERENCES,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'figure_captions.txt').write_text('\n\n'.join(f'Figure {v[1]}. {v[2]}' for v in FIGURES.values())+'\n',encoding='utf-8')
    audit={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Document generation and artifact consistency; not new experiment',
           'checks':{'frozen_run_verified':True,'rollout_means_match_summary':True,'demo_evidence_hashes_match':True,
                     'all_tokens_resolved':True,'highlights_characters':list(map(len,highlights)),**audits},
           'rendering':'ReportLab text/tables + PyMuPDF vector insertion; not native LaTeX compilation',
           'files':{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in outputs+[ROOT/'paper/topic4_policy.tex']}}
    (HERE/'report_build.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
