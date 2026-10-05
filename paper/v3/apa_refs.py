"""APA 7 reference list for the v3 manuscripts, as a natbib-compatible ``thebibliography``.

Computers & Education: Artificial Intelligence asks for APA 7 references; no maintained BibTeX style
implements APA 7 for natbib, so this module formats ``references.bib`` directly. Only cited keys are
listed (the guide requires the list and the citations to match), a cited key without an entry is an
error, and the list is sorted alphabetically by author surnames, then year. ``lang='vi'`` changes only
the in-text connectors ("và", "và cộng sự"); the entries themselves stay in APA form.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ACCENTS = {"'": '\u0301', '`': '\u0300', '^': '\u0302', '"': '\u0308', '~': '\u0303', 'v': '\u030c', 'c': '\u0327'}
CONNECT = {'en': {'and': 'and', 'etal': 'et~al.', 'long_and': ', and '},
           'vi': {'and': 'và', 'etal': 'và cộng sự', 'long_and': ' và '}}


def delatex(s: str) -> str:
    """Turn simple accent macros ({\\'a}, \\'{a}) into Unicode; XeLaTeX renders Unicode directly."""
    s = re.sub(r"\{\\([`'^\"~vc])\{?([A-Za-z])\}?\}",
               lambda m: unicodedata.normalize('NFC', m.group(2) + ACCENTS[m.group(1)]), s)
    s = re.sub(r"\\([`'^\"~vc])\{?([A-Za-z])\}?",
               lambda m: unicodedata.normalize('NFC', m.group(2) + ACCENTS[m.group(1)]), s)
    return s


def parse_bib(text: str) -> dict[str, dict]:
    entries, i = {}, 0
    while True:
        m = re.compile(r'@(\w+)\s*\{\s*([^,\s]+)\s*,').search(text, i)
        if not m:
            return entries
        kind, key, j = m.group(1).lower(), m.group(2), m.end()
        fields = {}
        while True:
            fm = re.compile(r'\s*(\w+)\s*=\s*').match(text, j)
            if not fm:
                end = text.index('}', j)
                j = end + 1
                break
            name, j = fm.group(1).lower(), fm.end()
            if text[j] == '{':
                depth, k = 0, j
                while True:
                    if text[k] == '{':
                        depth += 1
                    elif text[k] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                value, j = text[j + 1:k], k + 1
            elif text[j] == '"':
                k = text.index('"', j + 1)
                value, j = text[j + 1:k], k + 1
            else:
                vm = re.compile(r'[^,}\s]+').match(text, j)
                value, j = vm.group(0), vm.end()
            fields[name] = re.sub(r'\s+', ' ', value).strip()
            cm = re.compile(r'\s*,').match(text, j)
            if cm:
                j = cm.end()
        if key in entries:
            raise ValueError(f'duplicate bib key {key}')
        entries[key] = {'type': kind, **fields}
        i = j


def split_names(field: str) -> list[tuple[str, str]]:
    names = []
    for raw in re.split(r'\s+and\s+', field):
        raw = delatex(raw.strip())
        if raw == 'others':
            raise ValueError('"and others" is not allowed: APA 7 lists up to 20 authors')
        if ',' in raw:
            last, first = [p.strip() for p in raw.split(',', 1)]
        else:
            parts = raw.split()
            last, first = parts[-1], ' '.join(parts[:-1])
        names.append((last, first))
    return names


def initials(first: str) -> str:
    out = []
    for token in first.split():
        pieces = [p for p in token.split('-') if p]
        out.append('-'.join(p[0] + '.' for p in pieces))
    return ' '.join(out)


def apa_person(last: str, first: str) -> str:
    return f'{last}, {initials(first)}' if first else last


def apa_authors(names) -> str:
    people = [apa_person(*n) for n in names]
    if len(people) == 1:
        return people[0]
    if len(people) <= 20:
        return ', '.join(people[:-1]) + ', \\& ' + people[-1]
    return ', '.join(people[:19]) + ', \\ldots\\ ' + people[-1]


def apa_editors(names) -> str:
    people = [f'{initials(first)} {last}' for last, first in names]
    if len(people) == 1:
        return people[0] + ' (Ed.)'
    return ', '.join(people[:-1]) + ', \\& ' + people[-1] + ' (Eds.)'


def sentence_end(title: str) -> str:
    return title if title.rstrip().endswith(('?', '!', '.')) else title + '.'


def link(e: dict) -> str:
    if e.get('doi'):
        return f"\\url{{https://doi.org/{e['doi']}}}"
    if e.get('eprint'):
        return f"\\url{{https://doi.org/10.48550/arXiv.{e['eprint']}}}"
    if e.get('url'):
        return f"\\url{{{e['url']}}}"
    return ''


def pages(e: dict) -> str:
    return e['pages'].replace('--', '--') if e.get('pages') else ''


def entry_text(e: dict, year: str) -> str:
    kind = e['type']
    head = f"{apa_authors(split_names(e['author']))} ({year}). "
    title = delatex(e['title'])
    tail = link(e)
    if kind == 'article':
        volume = f"\\textit{{{e['volume']}}}" if e.get('volume') else ''
        issue = f"({e['number']})" if e.get('number') else ''
        locator = f", Article {e['articleno']}" if e.get('articleno') else (f", {pages(e)}" if e.get('pages') else '')
        body = f"{sentence_end(title)} \\textit{{{e['journal']}}}, {volume}{issue}{locator}."
    elif kind in ('inproceedings', 'incollection'):
        parts = []
        if e.get('series') and e.get('volume'):
            parts.append(f"{e['series']}, Vol.~{e['volume']}")
        elif e.get('volume'):
            parts.append(f"Vol.~{e['volume']}")
        if e.get('pages'):
            parts.append(f"pp.~{pages(e)}")
        paren = f" ({', '.join(parts)})" if parts else ''
        editors = apa_editors(split_names(e['editor'])) + ', ' if kind == 'incollection' and e.get('editor') else ''
        publisher = f" {e['publisher']}." if e.get('publisher') else ''
        body = f"{sentence_end(title)} In {editors}\\textit{{{e['booktitle']}}}{paren}.{publisher}"
    elif kind == 'book':
        body = f"\\textit{{{title}}}. {e['publisher']}."
    elif kind == 'dataset':
        head = '[dataset] ' + head
        body = f"\\textit{{{title}}} [Data set]. {e['publisher']}."
    elif kind == 'misc' and e.get('archiveprefix', '').lower() == 'arxiv':
        body = f"\\textit{{{title}}} [Preprint]. arXiv."
    else:
        raise ValueError(f"unsupported entry type {kind}")
    return head + body + (' ' + tail if tail else '')


def ascii_latex(text: str) -> str:
    """Accented Latin letters back to LaTeX accent macros, so the English source also compiles with pdfLaTeX."""
    inverse = {mark: macro for macro, mark in ACCENTS.items()}
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
            continue
        parts = unicodedata.normalize('NFD', ch)
        if len(parts) == 2 and parts[0].isascii() and parts[0].isalpha() and parts[1] in inverse:
            out.append('{\\%s%s}' % (inverse[parts[1]], parts[0]) if inverse[parts[1]] in "'`^\"~"
                       else '{\\%s{%s}}' % (inverse[parts[1]], parts[0]))
        else:
            out.append(ch)
    return ''.join(out)


def fold(s: str) -> str:
    s = unicodedata.normalize('NFKD', delatex(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).replace("'", '').lower()


def cited_keys(tex: str) -> list[str]:
    keys = []
    for m in re.finditer(r'\\(?:cite[a-zA-Z*]*|nocite)\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}', tex):
        for k in m.group(1).split(','):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def bibliography(tex: str, bib_path: Path, lang: str = 'en') -> tuple[str, dict]:
    entries = parse_bib(Path(bib_path).read_text(encoding='utf-8'))
    keys = cited_keys(tex)
    missing = [k for k in keys if k not in entries]
    if missing:
        raise SystemExit(f'Cited keys without a reference entry: {missing}')
    words = CONNECT[lang]
    items = []
    for k in keys:
        e = entries[k]
        names = split_names(e['author'])
        surnames = [n[0] for n in names]
        # APA 7: first author's surname, then initials, then the following authors, then year
        items.append({'key': k, 'e': e, 'surnames': surnames, 'year': e['year'],
                      'sort': (tuple((fold(last), fold(initials(first))) for last, first in names), e['year'],
                               fold(e['title']))})
    items.sort(key=lambda it: it['sort'])
    # APA: identical author lists in the same year get a, b, ... ; different lists with identical short forms must be resolved by hand
    by_list, by_short = {}, {}
    for it in items:
        by_list.setdefault((tuple(it['surnames']), it['year']), []).append(it)
    for group in by_list.values():
        for i, it in enumerate(group):
            it['label_year'] = it['year'] + ('abcdefghij'[i] if len(group) > 1 else '')
    for it in items:
        s = it['surnames']
        short = s[0] if len(s) == 1 else (f"{s[0]} {words['and']} {s[1]}" if len(s) == 2 else f"{s[0]} {words['etal']}")
        it['short'] = short
        by_short.setdefault((short, it['label_year']), []).append(it['key'])
        it['long'] = s[0] if len(s) == 1 else ', '.join(s[:-1]) + words['long_and'] + s[-1]
        if len(s) == 2:
            it['long'] = f"{s[0]} {words['and']} {s[1]}"
    clashes = {k: v for k, v in by_short.items() if len(v) > 1}
    if clashes:
        raise SystemExit(f'Ambiguous in-text citations (APA needs extra author names): {clashes}')
    lines = [f'\\begin{{thebibliography}}{{{len(items)}}}', '\\expandafter\\ifx\\csname url\\endcsname\\relax',
             '  \\def\\url#1{\\texttt{#1}}\\fi']
    for it in items:
        lines.append(f"\\bibitem[{{{it['short']}({it['label_year']}){it['long']}}}]{{{it['key']}}}")
        lines.append(entry_text(it['e'], it['label_year']))
        lines.append('')
    lines.append('\\end{thebibliography}')
    unused = sorted(set(entries) - set(keys))
    return '\n'.join(lines), {'cited': len(keys), 'unused_bib_entries': unused}


if __name__ == '__main__':
    import sys
    tex = Path(sys.argv[1]).read_text(encoding='utf-8')
    text, info = bibliography(tex, Path(__file__).with_name('references.bib'), sys.argv[2] if len(sys.argv) > 2 else 'en')
    print(text)
    print(info, file=sys.stderr)
