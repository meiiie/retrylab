"""Render the supported manuscript LaTeX subset with ReportLab, without TeX.

This is an explicitly limited fallback renderer. Unknown commands/environments
raise errors. The scientific source is read only. The manifest identifies the
conversion method and the exact source hash; it never claims TeX compilation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import unicodedata

import fitz
from matplotlib import mathtext
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties
from PIL import Image as PILImage, ImageDraw
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    KeepTogether, PageBreak, CondPageBreak,
)


HERE = Path(__file__).resolve().parent
PREVIEW = HERE / "preview"
BODY_FONT_SIZE = 10.6
MARGIN = 26 * 72 / 25.4
PAGE_WIDTH, PAGE_HEIGHT = A4
WIDTH = PAGE_WIDTH - 2 * MARGIN
COUNTS = Counter()
MATH_IMAGES = {}
CITATIONS = {}
LABELS = {}
REFERENCED_KEYS = set()
rcParams["mathtext.fontset"] = "stix"


def group(text, position, left="{", right="}"):
    while position < len(text) and text[position].isspace():
        position += 1
    if position >= len(text) or text[position] != left:
        raise ValueError(f"Expected {left!r} at: {text[position:position+90]!r}")
    level = 1
    start = position + 1
    position += 1
    while position < len(text):
        ch = text[position]
        if ch == "\\":
            position += 2
            continue
        if ch == left:
            level += 1
        elif ch == right:
            level -= 1
            if not level:
                return text[start:position], position + 1
        position += 1
    raise ValueError(f"Unclosed group beginning {text[start:start+90]!r}")


def strip_comments(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def normalize_math(expression):
    expression = re.sub(r"\\label\s*\{[^}]+\}", "", expression)
    expression = re.sub(r"\\E\b", r"\\mathbb{E}", expression)
    expression = re.sub(r"\\1\b", r"\\mathbb{I}", expression)
    expression = re.sub(r"\\NLL\b", r"\\operatorname{NLL}", expression)
    expression = re.sub(r"\\mathcal\s+([A-Za-z])", r"\\mathcal{\1}", expression)
    expression = expression.replace(r"\mid", r"\,|\,")
    expression = expression.replace(r"\textnormal", r"\mathrm")
    expression = expression.replace(r"\tfrac", r"\frac")
    expression = expression.replace(r"\dfrac", r"\frac")
    expression = re.sub(r"\\ge(?![A-Za-z])", r"\\geq", expression)
    expression = re.sub(r"\\le(?![A-Za-z])", r"\\leq", expression)
    return re.sub(r"\s+", " ", expression).strip()


def math_image(expression, size=BODY_FONT_SIZE, display=False):
    expression = normalize_math(expression)
    key = sha256(f"stix|{size}|{expression}".encode()).hexdigest()[:20]
    path = PREVIEW / "math" / f"{key}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    dpi = 220
    try:
        if not path.exists():
            mathtext.math_to_image(
                "$" + expression + "$", str(path),
                prop=FontProperties(family="STIXGeneral", size=size),
                dpi=dpi, format="png", color="black",
            )
    except Exception as exc:
        raise ValueError(f"Unsupported or invalid math: {expression!r}") from exc
    with PILImage.open(path) as pic:
        w, h = pic.size
    width, height = w * 72 / dpi, h * 72 / dpi
    if display and width > WIDTH - 38:
        factor = (WIDTH - 38) / width
        if factor < 0.72:
            raise ValueError(f"Display math too wide: {expression!r}")
        width *= factor
        height *= factor
    MATH_IMAGES[key] = {"expression": expression, "source_size_pt": size,
                        "display": display, "path": str(path)}
    return path, width, height


IGNORABLE_INLINE = {
    "noindent", "small", "footnotesize", "scriptsize", "normalsize",
    "centering", "raggedright", "raggedleft", "protect", "leavevmode",
}


def inline(text, size=BODY_FONT_SIZE):
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "$":
            end = i + 1
            while end < len(text) and (text[end] != "$" or text[end-1] == "\\"):
                end += 1
            if end == len(text):
                raise ValueError("Unclosed inline math")
            path, width, height = math_image(text[i+1:end], size)
            out.append(f'<img src="{escape(str(path), quote=True)}" width="{width:.3f}" height="{height:.3f}" valign="middle"/>')
            COUNTS["inline_math"] += 1
            i = end + 1
        elif ch == "{":
            value, i = group(text, i)
            out.append(inline(value, size))
        elif ch == "}":
            raise ValueError(f"Unexpected closing brace: {text[max(0,i-25):i+25]}")
        elif ch == "\\":
            match = re.match(r"\\([A-Za-z]+|.)", text[i:], re.S)
            if not match:
                raise ValueError("Dangling backslash")
            command = match.group(1)
            i += len(match.group(0))
            COUNTS["command:" + command] += 1
            if command in {"textbf", "textit", "emph", "texttt", "textrm", "textnormal"}:
                value, i = group(text, i)
                tag = {"textbf": "b", "textit": "i", "emph": "i", "texttt": "font", "textrm": "font", "textnormal": "font"}[command]
                attribute = ' name="Courier"' if command == "texttt" else (' name="Body"' if tag == "font" else "")
                out.append(f"<{tag}{attribute}>{inline(value,size)}</{tag}>")
            elif command in {"url", "href"}:
                url, i = group(text, i)
                url = url.replace(r"\_", "_").replace(r"\%", "%").replace(r"\&", "&")
                if command == "href":
                    label, i = group(text, i)
                    label = inline(label, size)
                else:
                    label = escape(url)
                out.append(f'<a href="{escape(url,quote=True)}" color="#21486a">{label}</a>')
            elif command in {"cite", "citep", "citet"}:
                value, i = group(text, i)
                keys = [x.strip() for x in value.split(",")]
                missing = set(keys) - CITATIONS.keys()
                if missing:
                    raise ValueError(f"Undefined citations: {missing}")
                REFERENCED_KEYS.update(keys)
                out.append("[" + ", ".join(str(CITATIONS[x]) for x in keys) + "]")
            elif command == "label":
                _, i = group(text, i)
            elif command in {"ref", "eqref"}:
                label, i = group(text, i)
                if label not in LABELS:
                    raise ValueError(f"Undefined label: {label}")
                value = str(LABELS[label])
                out.append("(" + value + ")" if command == "eqref" else value)
            elif command in IGNORABLE_INLINE:
                pass
            elif command in {"%", "&", "_", "#", "$", "{", "}"}:
                out.append(escape(command))
            elif command in {"'", '"', "`", "^", "~", "=", ".", "c", "v", "H", "u"}:
                accents = {"'":"\u0301", '"':"\u0308", "`":"\u0300", "^":"\u0302",
                           "~":"\u0303", "=":"\u0304", ".":"\u0307", "c":"\u0327",
                           "v":"\u030c", "H":"\u030b", "u":"\u0306"}
                if i < len(text) and text[i] == "{":
                    base, i = group(text, i)
                else:
                    base, i = text[i:i+1], i+1
                if len(base) != 1:
                    raise ValueError(f"Unsupported accent argument {base!r}")
                out.append(escape(unicodedata.normalize("NFC", base + accents[command])))
            elif command in {"o", "O", "ss", "ae", "AE"}:
                out.append({"o":"ø", "O":"Ø", "ss":"ß", "ae":"æ", "AE":"Æ"}[command])
            elif command == "\\":
                out.append("<br/>")
                if i < len(text) and text[i] == "[":
                    _, i = group(text, i, "[", "]")
            elif command in {",", ";", ":", " ", "quad", "qquad", "enspace", "thinspace"}:
                out.append(" ")
            elif command == "!":
                pass
            elif command in {"LaTeX", "TeX"}:
                out.append(command)
            elif command in {"textbackslash", "textasciitilde"}:
                out.append("\\" if command == "textbackslash" else "~")
            else:
                raise ValueError(f"Unsupported inline command \\{command} near {text[max(0,i-40):i+80]!r}")
        else:
            start = i
            while i < len(text) and text[i] not in "$\\{}":
                i += 1
            literal = text[start:i].replace("~", " ").replace("``", '"').replace("''", '"')
            # TeX ligatures are represented as ASCII hyphens in this fallback.
            out.append(escape(literal))
    return "".join(out)


def register_fonts():
    fonts = Path("C:/Windows/Fonts")
    files = {"Body": "times.ttf", "Body-Bold": "timesbd.ttf",
             "Body-Italic": "timesi.ttf", "Body-BoldItalic": "timesbi.ttf"}
    for name, filename in files.items():
        path = fonts / filename
        if not path.exists():
            raise FileNotFoundError(f"Required serif font unavailable: {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                  italic="Body-Italic", boldItalic="Body-BoldItalic")


def styles():
    common = dict(fontName="Body", fontSize=BODY_FONT_SIZE,
                  leading=14.0, textColor=colors.HexColor("#171717"),
                  splitLongWords=True, allowWidows=0, allowOrphans=0, autoLeading="max")
    def style(name, **kw):
        return ParagraphStyle(name, **(common | kw))
    return {
        "body": style("body", alignment=TA_JUSTIFY, spaceAfter=6),
        "title": style("title", fontName="Body-Bold", fontSize=19, leading=22.5,
                       alignment=TA_CENTER, spaceAfter=13),
        "meta": style("meta", fontSize=10.4, leading=13.8, alignment=TA_CENTER, spaceAfter=3),
        "center": style("center", fontSize=9.2, leading=12, alignment=TA_CENTER, spaceAfter=8),
        "abstract": style("abstract", fontSize=10, leading=13.2, alignment=TA_JUSTIFY,
                          leftIndent=14, rightIndent=14, spaceAfter=8),
        "h1": style("h1", fontName="Body-Bold", fontSize=12.5, leading=16,
                    spaceBefore=13, spaceAfter=6, keepWithNext=False),
        "h2": style("h2", fontName="Body-Bold", fontSize=11, leading=14,
                    spaceBefore=9, spaceAfter=4, keepWithNext=False),
        "caption": style("caption", fontSize=9.2, leading=12, spaceBefore=8,
                         spaceAfter=5, keepWithNext=True),
        "table": style("table", fontSize=8.8, leading=11.5, alignment=TA_LEFT),
        "tablenum": style("tablenum", fontSize=8.8, leading=11.5, alignment=TA_RIGHT),
        "tablecenter": style("tablecenter", fontSize=8.8, leading=11.5, alignment=TA_CENTER),
        "reference": style("reference", fontSize=9, leading=12, spaceAfter=6,
                           leftIndent=18, firstLineIndent=-18),
        "list": style("list", leftIndent=15, firstLineIndent=-11, spaceAfter=5),
        "eqnum": style("eqnum", fontSize=10, leading=12, alignment=TA_RIGHT),
    }


def split_unescaped(text, delimiter):
    parts, start, depth, index = [], 0, 0, 0
    while index < len(text):
        if text.startswith(delimiter, index) and depth == 0:
            parts.append(text[start:index])
            index += len(delimiter)
            start = index
            continue
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    parts.append(text[start:])
    return parts


class Renderer:
    def __init__(self, source):
        self.source = source
        self.styles = styles()
        self.story = []
        self.section = self.subsection = self.equation = self.table = self.figure = 0
        self.appendix = False
        self.paragraph_count = 0

    def paragraph(self, text, kind="body"):
        if text.strip():
            size = self.styles[kind].fontSize
            self.story.append(Paragraph(inline(text.strip(), size), self.styles[kind]))
            self.paragraph_count += 1

    def heading(self, text, subsection=False, starred=False):
        section_label = chr(64 + self.section) if self.appendix else str(self.section)
        if subsection:
            self.subsection += 1
            prefix = f"{section_label}.{self.subsection} " if not starred else ""
        else:
            if not starred:
                self.section += 1
                COUNTS["numbered_sections"] += 1
            self.subsection = 0
            section_label = chr(64 + self.section) if self.appendix else str(self.section)
            prefix = f"{section_label} " if not starred else ""
        # Reserve heading and several lines, without keeping an entire long
        # scientific paragraph on the same page as its heading.
        self.story.append(CondPageBreak(64 if subsection else 84))
        self.paragraph(prefix + text, "h2" if subsection else "h1")

    def display(self, text, numbered=True):
        rows = split_unescaped(text, r"\\")
        for row in rows:
            row = row.strip().replace("&", "")
            if not row:
                continue
            if numbered:
                self.equation += 1
            for label in re.findall(r"\\label\{([^}]+)\}", row):
                LABELS[label] = self.equation
            path, width, height = math_image(row, 11.5, True)
            cells = [[Image(str(path), width=width, height=height),
                      Paragraph(f"({self.equation})" if numbered else "", self.styles["eqnum"])]]
            table = Table(cells, colWidths=[WIDTH - 30, 30])
            table.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN", (0,0), (0,0), "CENTER"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING", (0,0), (-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ]))
            self.story.append(table)

    def parse_table(self, text):
        self.table += 1
        caption = ""
        cap = re.search(r"\\caption\s*", text)
        if cap:
            caption, end = group(text, cap.end())
            text = text[:cap.start()] + text[end:]
        for label in re.findall(r"\\label\{([^}]+)\}", text):
            LABELS[label] = self.table
        text = re.sub(r"\\label\{[^}]+\}", "", text)
        match = re.search(r"\\begin\{tabular\}", text)
        if not match:
            raise ValueError("Table without supported tabular environment")
        spec, start = group(text, match.end())
        finish = text.find(r"\end{tabular}", start)
        if finish < 0:
            raise ValueError("Unclosed tabular")
        outside = text[:match.start()] + text[finish+len(r"\end{tabular}"):]
        outside = re.sub(r"\\(?:centering|small|footnotesize|scriptsize|normalsize)\b", "", outside)
        if outside.strip():
            raise ValueError(f"Unsupported table material outside tabular: {outside!r}")
        spec = re.sub(r"@\{[^}]*\}", "", spec).replace("|", "")
        columns = []
        pos = 0
        while pos < len(spec):
            if spec[pos].isspace():
                pos += 1
            elif spec[pos] in "lcr":
                columns.append(spec[pos]); pos += 1
            elif spec[pos] in "pmb":
                _, pos = group(spec, pos+1)
                columns.append("l")
            else:
                raise ValueError(f"Unsupported column specification: {spec!r}")
        content = text[start:finish]
        content = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)\b", "", content)
        rows = []
        for raw in split_unescaped(content, r"\\"):
            raw = re.sub(r"^\s*\[[^]]*\]", "", raw).strip()
            if not raw:
                continue
            cells = [c.strip() for c in split_unescaped(raw, "&")]
            if len(cells) != len(columns):
                raise ValueError(f"Table columns mismatch ({len(columns)} expected): {cells!r}")
            rows.append(cells)
        if not rows:
            raise ValueError("Empty table")
        # A wide first column handles model/protocol names; the remaining
        # columns have equal, adequate widths for numeric results and headers.
        n = len(columns)
        if n >= 5:
            first = WIDTH * (0.30 if n <= 6 else 0.26)
            widths = [first] + [(WIDTH-first)/(n-1)]*(n-1)
        else:
            lengths = [max(len(re.sub(r"\\[A-Za-z]+|[{}$]", "", row[c])) for row in rows) for c in range(n)]
            weights = [max(8, min(40, length)) for length in lengths]
            widths = [WIDTH * w / sum(weights) for w in weights]
        if caption:
            self.paragraph(f"\\textbf{{Table {self.table}.}} " + caption, "caption")
        output_rows = []
        for row_index, row in enumerate(rows):
            output_row = []
            for col, cell in enumerate(row):
                kind = "tablecenter" if columns[col] == "c" else ("tablenum" if columns[col] == "r" else "table")
                if row_index == 0:
                    cell = r"\textbf{" + cell + "}"
                output_row.append(Paragraph(inline(cell, 8.8), self.styles[kind]))
            output_rows.append(output_row)
        table = Table(output_rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("LINEABOVE", (0,0), (-1,0), 0.8, colors.black),
            ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
            ("LINEBELOW", (0,-1), (-1,-1), 0.8, colors.black),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 3.5),
            ("RIGHTPADDING", (0,0), (-1,-1), 3.5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        self.story.extend([table, Spacer(1, 7)])
        COUNTS["table_rows"] += len(rows)

    def parse_figure(self, text):
        self.figure += 1
        caption = ""
        cap = re.search(r"\\caption\s*", text)
        if cap:
            caption, end = group(text, cap.end())
            text = text[:cap.start()] + text[end:]
        for label in re.findall(r"\\label\{([^}]+)\}", text):
            LABELS[label] = self.figure
        text = re.sub(r"\\label\{[^}]+\}", "", text)
        match = re.search(r"\\includegraphics(?:\[([^]]*)\])?", text)
        if not match:
            raise ValueError("Figure requires one includegraphics")
        relative, end = group(text, match.end())
        outside = text[:match.start()] + text[end:]
        outside = re.sub(r"\\(?:centering|small|footnotesize)\b", "", outside)
        if outside.strip():
            raise ValueError(f"Unsupported figure material: {outside!r}")
        path = self.source.parent / relative
        if not path.exists():
            raise FileNotFoundError(path)
        with PILImage.open(path) as image:
            iw, ih = image.size
        target_width = WIDTH
        if match.group(1):
            options = match.group(1).replace(" ", "")
            widthmatch = re.fullmatch(r"width=(?:(\d*\.?\d+)?)\\(?:linewidth|textwidth)", options)
            if not widthmatch:
                raise ValueError(f"Unsupported image options {options!r}")
            target_width *= float(widthmatch.group(1) or "1")
        image = Image(str(path), width=target_width, height=target_width*ih/iw)
        items = [image]
        if caption:
            items.append(Paragraph(inline(f"\\textbf{{Figure {self.figure}.}} " + caption, 9.2), self.styles["caption"]))
        self.story.extend([KeepTogether(items), Spacer(1, 8)])

    def parse(self, body):
        # Bibliography keys are known before any in-text citations are parsed.
        for index, key in enumerate(re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", body), 1):
            if key in CITATIONS:
                raise ValueError(f"Duplicate bibliography key {key}")
            CITATIONS[key] = index
        # Resolve ordinary forward references before prose is converted.
        for environment in ("table", "figure", "equation"):
            pattern = r"\\begin\{" + environment + r"\}.*?\\end\{" + environment + r"\}"
            for index, matched in enumerate(re.finditer(pattern, body, re.S), 1):
                for label in re.findall(r"\\label\{([^}]+)\}", matched.group(0)):
                    LABELS[label] = index
        position, paragraph = 0, []
        def flush():
            if paragraph:
                self.paragraph(" ".join(paragraph))
                paragraph.clear()
        while position < len(body):
            while position < len(body) and body[position].isspace():
                if body.startswith("\n\n", position):
                    flush()
                position += 1
            if position >= len(body):
                break
            if body.startswith(r"\maketitle", position):
                flush(); position += len(r"\maketitle")
                continue
            appendix = re.match(r"\\appendix\b", body[position:])
            if appendix:
                flush()
                self.appendix = True
                self.section = self.subsection = 0
                position += appendix.end()
                COUNTS["appendix"] += 1
                continue
            heading = re.match(r"\\(section|subsection)(\*)?", body[position:])
            if heading:
                flush()
                value, position = group(body, position + heading.end())
                self.heading(value, heading.group(1) == "subsection", bool(heading.group(2)))
                continue
            begin = re.match(r"\\begin\{([^}]+)\}(?:\[[^]]*\])?", body[position:])
            if begin:
                flush()
                environment = begin.group(1)
                start = position + begin.end()
                endtoken = r"\end{" + environment + "}"
                end = body.find(endtoken, start)
                if end < 0:
                    raise ValueError(f"Unclosed environment {environment}")
                content = body[start:end]
                position = end + len(endtoken)
                COUNTS["environment:" + environment] += 1
                if environment == "abstract":
                    self.paragraph(r"\textbf{Abstract}", "abstract")
                    for chunk in re.split(r"\n\s*\n", content):
                        self.paragraph(chunk, "abstract")
                    self.story.append(Spacer(1, 5))
                elif environment == "center":
                    self.paragraph(content, "center")
                elif environment in {"equation", "equation*", "align", "align*", "gather", "gather*"}:
                    self.display(content, not environment.endswith("*"))
                elif environment == "table":
                    self.parse_table(content)
                elif environment == "figure":
                    self.parse_figure(content)
                elif environment in {"itemize", "enumerate"}:
                    prefix = content.split(r"\item", 1)[0]
                    if prefix.strip():
                        raise ValueError("Unsupported content before first list item")
                    for index, item in enumerate(content.split(r"\item")[1:], 1):
                        self.paragraph((f"{index}. " if environment == "enumerate" else "- ") + item.strip(), "list")
                elif environment == "thebibliography":
                    _, first = group(content, 0)
                    self.heading("References", starred=True)
                    entries = re.split(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", content[first:])
                    if entries[0].strip():
                        raise ValueError("Unsupported bibliography prefix")
                    for key, entry in zip(entries[1::2], entries[2::2]):
                        self.paragraph(f"[{CITATIONS[key]}] " + entry.strip(), "reference")
                elif environment in {"proposition", "proof"}:
                    title = "Proposition" if environment == "proposition" else "Proof"
                    self.paragraph(r"\textbf{" + title + ".} " + content)
                else:
                    raise ValueError(f"Unsupported environment: {environment}")
                continue
            if body.startswith(r"\[", position):
                flush()
                end = body.find(r"\]", position+2)
                if end < 0:
                    raise ValueError("Unclosed display math")
                self.display(body[position+2:end], False)
                position = end + 2
                continue
            breakmatch = re.match(r"\\(?:newpage|clearpage)\b", body[position:])
            if breakmatch:
                flush(); self.story.append(PageBreak()); position += breakmatch.end()
                continue
            # Accumulate one ordinary line. Blank lines delimit prose blocks.
            end = body.find("\n", position)
            if end < 0:
                end = len(body)
            paragraph.append(body[position:end])
            position = end
        flush()


def document_command(source, command):
    match = re.search(r"\\" + re.escape(command) + r"\s*", source)
    if not match:
        return ""
    return group(source, match.end())[0]


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#aaa9a5"))
    canvas.setLineWidth(0.35)
    canvas.line(MARGIN, 48, PAGE_WIDTH-MARGIN, 48)
    canvas.setFont("Body", 8.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(MARGIN, 35, "Programming retries: predictive-update audit")
    canvas.drawRightString(PAGE_WIDTH-MARGIN, 35, str(document.page))
    canvas.restoreState()


def inspect_and_preview(pdf):
    document = fitz.open(pdf)
    pages = []
    image_paths = []
    overflow = []
    extracted = []
    for index, page in enumerate(document):
        text = page.get_text()
        extracted.append(text)
        for block in page.get_text("blocks"):
            x0, y0, x1, y1 = block[:4]
            if x0 < -0.5 or y0 < -0.5 or x1 > PAGE_WIDTH + 0.5 or y1 > PAGE_HEIGHT + 0.5:
                overflow.append({"page": index+1, "bbox": [x0,y0,x1,y1]})
        path = PREVIEW / f"page-{index+1:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.55,1.55), alpha=False).save(path)
        image_paths.append(path)
        pages.append({"page": index+1, "text_characters": len(text), "preview": str(path)})
    for start in range(0, len(image_paths), 4):
        thumbs = []
        for path in image_paths[start:start+4]:
            with PILImage.open(path) as opened:
                image = opened.convert("RGB")
                image.thumbnail((595,842))
                thumbs.append(image.copy())
        sheet = PILImage.new("RGB", (1214, (len(thumbs)+1)//2*878), "#dedede")
        draw = ImageDraw.Draw(sheet)
        for i, pic in enumerate(thumbs):
            x, y = 12+(i%2)*601, 24+(i//2)*878
            draw.text((x,y-18), f"Page {start+i+1}", fill="black")
            sheet.paste(pic, (x,y))
        sheet.save(PREVIEW/f"contact-{start//4+1:02d}.png")
    (PREVIEW/"extracted_text.txt").write_text("\n\n".join(extracted), encoding="utf-8")
    if overflow:
        raise ValueError(f"Text/image blocks outside page: {overflow}")
    return pages, overflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=HERE/"manuscript.tex")
    parser.add_argument("--status", choices=["draft", "final"], default="draft")
    args = parser.parse_args()
    source = args.source.resolve()
    original = source.read_bytes()
    text = strip_comments(original.decode("utf-8-sig"))
    begin, end = r"\begin{document}", r"\end{document}"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError("Expected one document environment")
    body = text.split(begin,1)[1].split(end,1)[0]
    if text.split(end,1)[1].strip():
        raise ValueError("Unexpected material after document")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    register_fonts()
    renderer = Renderer(source)
    title = document_command(text, "title")
    renderer.paragraph(title, "title")
    for field in ("author", "date"):
        renderer.paragraph(document_command(text, field), "meta")
    renderer.story.append(Spacer(1, 11))
    renderer.parse(body)
    pdf = HERE / "manuscript.pdf"
    document = SimpleDocTemplate(
        str(pdf), pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=56, bottomMargin=61,
        title=re.sub(r"\\\\|[{}]", " ", title),
        author="Anonymous working manuscript",
        subject="Research manuscript; ReportLab fallback rendering of LaTeX source",
        creator="render_paper.py / ReportLab (not a LaTeX compiler)",
    )
    document.build(renderer.story, onFirstPage=footer, onLaterPages=footer)
    if source.read_bytes() != original:
        raise RuntimeError("Source changed during rendering; rerun against final source")
    pages, overflow = inspect_and_preview(pdf)
    manifest = {
        "status": args.status,
        "source": str(source), "source_sha256": sha256(original).hexdigest(),
        "pdf": str(pdf), "pdf_sha256": sha256(pdf.read_bytes()).hexdigest(),
        "engine": "ReportLab limited-LaTeX-subset fallback with matplotlib mathtext images",
        "reportlab_version": reportlab.Version,
        "renderer_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "latex_compiled": False,
        "reason": "Native LaTeX compiler could not find standard directories on this host; no local TeX installation used",
        "source_scientific_text_rewritten": False,
        "unsupported_commands_policy": "Raise an explicit error; do not silently omit unsupported source passages",
        "intentional_format_differences": [
            "Preamble layout/package commands are not executed; scientific body is parsed by supported subset",
            "Equations rendered by matplotlib mathtext rather than a TeX engine",
            "Mathematical expressions are embedded raster images and are not selectable PDF text; editable expressions remain in the TeX source",
            "Scientific serif layout, table sizing, pagination and footer are set by ReportLab",
            "TeX hyphen ligatures preserved as ASCII hyphens",
        ],
        "page_count": len(pages), "pages": pages,
        "numbered_sections": COUNTS["numbered_sections"], "equations": renderer.equation,
        "tables": renderer.table, "figures": renderer.figure,
        "paragraphs": renderer.paragraph_count,
        "bibliography_entries": len(CITATIONS),
        "cited_keys": sorted(REFERENCED_KEYS),
        "parser_counts": dict(COUNTS),
        "unique_math_images": len(MATH_IMAGES),
        "page_bounds_violations": overflow,
        "visual_inspection": "Pending external image inspection of this exact rendered version",
    }
    (HERE/"render_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"pdf":str(pdf), "pages":len(pages), "tables":renderer.table,
                      "source_sha256":manifest["source_sha256"], "latex_compiled":False}, indent=2))


if __name__ == "__main__":
    main()
