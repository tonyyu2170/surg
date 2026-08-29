"""Build docs/final_report.docx from docs/final_report.md for Google Docs.

Usage:  .venv/bin/python scripts/build_report_docx.py
Needs:  uv pip install --python .venv/bin/python pypandoc_binary   (not a project dependency)

Portrait US Letter, Arial 11, tables forced to full text width at 9 pt with bold header rows,
TeX-math disabled (two $ amounts in one paragraph would otherwise become math), first H1 -> title.
Written 2026-08-26 for the advisor deliverable; pandoc reference.docx is regenerated on the fly.
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile

import pypandoc

S = pathlib.Path(tempfile.mkdtemp()); ref = S/"ref.docx"; tmp = S/"ref_portrait.docx"
if not ref.exists():
    subprocess.run([pypandoc.get_pandoc_path(), "-o", str(ref), "--print-default-data-file", "reference.docx"], check=True)
TW = 12240 - 2*1296
ARIAL = '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri" w:eastAsia="Calibri"/>'
MONO = ARIAL.replace("Calibri", "Roboto Mono")
BORDERS = ('<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblBorders>'
  + ''.join(f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="999999"/>' for e in ("top","left","bottom","right","insideH","insideV"))
  + '</w:tblBorders><w:tblCellMar><w:top w:w="20" w:type="dxa"/><w:left w:w="60" w:type="dxa"/><w:bottom w:w="20" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>')
def set_size(block, hp):
    block = re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{hp}"/>', block)
    return re.sub(r'<w:szCs w:val="\d+"\s*/>', f'<w:szCs w:val="{hp}"/>', block)
with zipfile.ZipFile(ref) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/styles.xml":
            x = data.decode()
            x = re.sub(r'<w:rFonts [^>]*/>', ARIAL, x)
            for sid in ("VerbatimChar", "SourceCode"):
                m = re.search(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', x, re.DOTALL)
                if m: x = x.replace(m.group(0), m.group(0).replace(ARIAL, MONO))
            m = re.search(r'<w:style [^>]*w:styleId="VerbatimChar".*?</w:style>', x, re.DOTALL)   # inline code: 10 pt
            if m:
                blk = m.group(0)
                x = x.replace(blk, set_size(blk, 20) if "<w:sz " in blk else blk.replace("</w:rPr>", '<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>', 1))
            dd = re.search(r'<w:docDefaults>.*?</w:docDefaults>', x, re.DOTALL).group(0)
            x = x.replace(dd, set_size(dd, 22))
            for sid, hp in (("Title", 44), ("Heading1", 32), ("Heading2", 26), ("Heading3", 23), ("Heading4", 22)):
                m = re.search(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', x, re.DOTALL)
                if m:
                    blk = m.group(0)
                    blk2 = set_size(blk, hp) if "<w:sz " in blk else blk.replace("</w:rPr>", f'<w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/></w:rPr>', 1)
                    x = x.replace(blk, blk2)
            tbl = re.search(r'<w:style w:type="table"[^>]*w:styleId="Table">.*?</w:style>', x, re.DOTALL).group(0)
            x = x.replace(tbl, re.sub(r'<w:tblPr>.*?</w:tblPr>', BORDERS, tbl, flags=re.DOTALL))
            data = x.encode()
        elif item.filename == "word/document.xml":
            data = data.decode().replace('</w:sectPr>', '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1296" w:right="1296" w:bottom="1296" w:left="1296" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>').encode()
        zout.writestr(item, data)

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
md = (root/"docs/final_report.md").read_text()
md = re.sub(r'!\[[^\]]*\]\(', '![](', md)
md = md.replace("{.pair}", "")  # attr_list class used only by the HTML renderer
# Internal links in the markdown use GitHub's heading slugs, which pandoc's gfm reader also uses for
# the docx bookmarks, so they pass through untouched; only the "§3.1" shorthand below needs mapping.
def _slug(h):
    h = re.sub(r"[^\w\s-]", "", h.lower()).strip()
    return re.sub(r"[\s]+", "-", h)   # gfm ids keep a leading number: "2. Datasets" -> "2-datasets"
_secs = {}
for line in md.splitlines():
    m = re.match(r"^(#{2,3})\s+(.*)$", line)
    if m:
        txt = m.group(2).strip()
        k = re.match(r"(\d+)\.", txt)
        if k and m.group(1) == "##": _secs[k.group(1)] = _slug(txt)
        k = re.match(r"(\d+\.\d+)\s", txt)
        if k and m.group(1) == "###": _secs[k.group(1)] = _slug(txt)
# "§3.1" in the text links to section 3.1 (review round 8); "§2.2" (a PJM manual section), "§202(c)" and
# "(§0 to 11)" (note N's sections) have no matching heading or are ranges and stay plain text.
def _seclink(m):
    return f"[§{m.group(1)}](#{_secs[m.group(1)]})" if m.group(1) in _secs else m.group(0)
_out, _fence = [], False
for line in md.splitlines():
    if line.startswith("```"): _fence = not _fence
    if not _fence and not line.startswith("#"):
        line = re.sub(r"§(\d+(?:\.\d+)?)(?! to \d)", _seclink, line)
    _out.append(line)
md = "\n".join(_out) + "\n"
def reweight(block):
    rows = block.splitlines()
    if len(rows) < 2 or not re.fullmatch(r'\|[\s:\-|]+\|', rows[1].strip()): return block
    cells = [[c.strip() for c in re.split(r'(?<!\\)\|', r.strip().strip('|'))] for r in rows if r.strip().startswith('|')]
    ncol = len(cells[0]); body = [r for r in cells[2:] if len(r) == ncol] or cells[:1]
    w = [max(5, min(70, sum(len(r[j]) for r in body) / len(body))) for j in range(ncol)]
    rows[1] = '|' + '|'.join('-' * max(3, round(x)) for x in w) + '|'
    return '\n'.join(rows)
md = '\n\n'.join(reweight(b) if b.lstrip().startswith('|') else b for b in md.split('\n\n'))
raw = S/"raw.docx"
pypandoc.convert_text(md, "docx", format="gfm-tex_math_dollars-tex_math_gfm", outputfile=str(raw),
    extra_args=[f"--resource-path={root/'docs'}", f"--reference-doc={tmp}", "--dpi=150", "--shift-heading-level-by=-1"])

CELL_SZ = [18]
def canon_rpr(rpr, bold):
    rstyle = re.search(r'<w:rStyle [^>]*/>', rpr or "")
    i = bool(re.search(r'<w:i\s*/>', rpr or "")); b = bold or bool(re.search(r'<w:b\s*/>', rpr or ""))
    return "<w:rPr>" + (rstyle.group(0) if rstyle else "") + ("<w:b/>" if b else "") + ("<w:i/>" if i else "") + f'<w:sz w:val="{CELL_SZ[0]}"/><w:szCs w:val="{CELL_SZ[0]}"/></w:rPr>'
def fix_runs(xml, bold):
    def run(m):
        inner = m.group(1); rpr = re.search(r'<w:rPr>.*?</w:rPr>', inner, re.DOTALL)
        new = canon_rpr(rpr.group(0) if rpr else "", bold)
        inner = inner.replace(rpr.group(0), new, 1) if rpr else new + inner
        return "<w:r>" + inner + "</w:r>"
    return re.sub(r'<w:r>(.*?)</w:r>', run, xml, flags=re.DOTALL)
def col_widths(t):
    # Content-driven widths. Each column first gets the room its longest single word needs at the
    # table's font size (so bold headers and code names never break mid-word); the leftover text
    # width is then shared in proportion to the column's mean cell length. A column whose longest
    # cell is <= 3 characters (the '#' column) is fixed at NUM_COL.
    rows = [re.findall(r'<w:tc>.*?</w:tc>', r, re.DOTALL) for r in re.findall(r'<w:tr>.*?</w:tr>', t, re.DOTALL)]
    ncol = max(len(r) for r in rows)
    texts = [[re.sub(r'<[^>]+>', '', c) for c in r] for r in rows if len(r) == ncol]
    pt = 8 if ncol >= 7 else 9
    minw, mean = [], []
    for j in range(ncol):
        body = [len(r[j]) for r in texts[1:]] or [len(texts[0][j])]
        if max(body) <= 3:
            minw.append(None); mean.append(0); continue
        longest = min(10, max((len(wd) for r in texts for wd in r[j].split()), default=1))  # words over 10 chars may wrap
        minw.append(round(longest * 0.6 * pt * 20 + 120))
        mean.append(max(4, min(40, sum(body) / len(body))) ** 2)   # squared: prose columns take most of the spare width
    fixed = sum(NUM_COL if x is None else x for x in minw)
    spare = max(0, TW - fixed); tot = sum(mean) or 1
    w = [None if x is None else x + spare * m / tot for x, m in zip(minw, mean)]
    flex = sum(x for x in w if x is not None); nfixed = sum(1 for x in w if x is None)
    scale = (TW - nfixed * NUM_COL) / flex if flex else 1
    return [NUM_COL if x is None else round(x * scale) for x in w]
NUM_COL = 450
# Hand-set widths (inches, summing to 6.7) for the tables whose content-driven widths read badly in
# Google Docs (review round 7): keyed by the first two header cells.
OVERRIDES = {
    ("Threshold", "5-min intervals above it"): [1.0, 1.425, 1.425, 1.425, 1.425],
    ("5-minute intervals with congestion above", "2023"): [2.7, 1.0, 1.0, 1.0, 1.0],
    ("Node size", "100 A service"): [3.1, 1.2, 1.2, 1.2],
    ("Source", "What it is"): [0.75, 2.15, 2.65, 1.15],
}
HEADER_RULE = '<w:tcBorders><w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/></w:tcBorders>'
LINK = '<w:color w:val="1155CC"/>'; UL = '<w:u w:val="single"/>'   # Google-Docs link blue + underline
def fix_table(m):
    t = m.group(0)
    widths = col_widths(t)
    heads = tuple(re.sub(r'<[^>]+>', '', c) for c in re.findall(r'<w:tc>.*?</w:tc>', re.search(r'<w:tr>.*?</w:tr>', t, re.DOTALL).group(0), re.DOTALL))
    if heads[:2] in OVERRIDES: widths = [round(i * 1440) for i in OVERRIDES[heads[:2]]]
    CELL_SZ[0] = 16 if len(widths) >= 7 else 18
    t = re.sub(r'<w:tblGrid>.*?</w:tblGrid>', '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{x}"/>' for x in widths) + '</w:tblGrid>', t, count=1, flags=re.DOTALL)
    def fix_row(rm):
        row = rm.group(0); i = [0]
        def fix_cell(cm):
            cell = cm.group(0); j = min(i[0], len(widths) - 1); i[0] += 1
            tcw = f'<w:tcW w:w="{widths[j]}" w:type="dxa"/>'
            cell = re.sub(r'<w:tcW [^>]*/>', '', cell, count=1)
            if re.search(r'<w:tcPr\s*/>', cell): return re.sub(r'<w:tcPr\s*/>', '<w:tcPr>' + tcw + '</w:tcPr>', cell, count=1)
            if '<w:tcPr>' in cell: return cell.replace('<w:tcPr>', '<w:tcPr>' + tcw, 1)
            return cell.replace('<w:tc>', '<w:tc><w:tcPr>' + tcw + '</w:tcPr>', 1)
        return re.sub(r'<w:tc>.*?</w:tc>', fix_cell, row, flags=re.DOTALL)
    t = re.sub(r'<w:tr>.*?</w:tr>', fix_row, t, flags=re.DOTALL)
    t = re.sub(r'<w:tblW [^/]*/>', f'<w:tblW w:w="{TW}" w:type="dxa"/>', t, count=1)
    if '<w:tblW' not in t: t = t.replace('<w:tblPr>', f'<w:tblPr><w:tblW w:w="{TW}" w:type="dxa"/>', 1)
    t = re.sub(r'<w:tblLayout [^/]*/>', '', t).replace('</w:tblPr>', '<w:tblLayout w:type="fixed"/></w:tblPr>', 1)
    longest = max((len(re.sub(r'<[^>]+>', '', c)) for c in re.findall(r'<w:tc>.*?</w:tc>', t, re.DOTALL)), default=0)
    if longest <= 150:
        t = re.sub(r'<w:tr>(?!<w:trPr>)', '<w:tr><w:trPr><w:cantSplit/></w:trPr>', t)
        t = t.replace('<w:trPr><w:tblHeader', '<w:trPr><w:cantSplit/><w:tblHeader')
    first = re.search(r'<w:tr>.*?</w:tr>', t, re.DOTALL)
    if first:
        hdr = fix_runs(first.group(0), True)
        hdr = re.sub(r'(<w:tcPr>(?:<w:tcW [^>]*/>)?)(?:<w:tcBorders>.*?</w:tcBorders>)?', lambda g: g.group(1) + HEADER_RULE, hdr, flags=re.DOTALL)
        t = t.replace(first.group(0), hdr, 1)
    rs = first.end() if first else 0
    return t[:rs] + fix_runs(t[rs:], False)
out = root/"docs/final_report.docx"
with zipfile.ZipFile(raw) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            x = re.sub(r'<w:tbl>.*?</w:tbl>', fix_table, data.decode(), flags=re.DOTALL)
            # Keep only the bookmarks that internal links point to: Google Docs draws an icon beside every
            # bookmark, so the ~17 link targets get one and the other headings stay clean.
            targets = set(re.findall(r'<w:hyperlink w:anchor="([^"]*)"', x))
            keep_ids = set()
            for bm in re.finditer(r'<w:bookmarkStart\b[^>]*/>', x):
                i = re.search(r'w:id="(\d+)"', bm.group(0)); nm = re.search(r'w:name="([^"]*)"', bm.group(0))
                if i and nm and nm.group(1) in targets: keep_ids.add(i.group(1))
            x = re.sub(r'<w:bookmark(?:Start|End)\b[^>]*/>', lambda m, keep=keep_ids: m.group(0) if re.search(r'w:id="(\d+)"', m.group(0)).group(1) in keep else '', x)
            # Every link (external and internal, code text included) in Google-Docs blue with an underline.
            def style_links(m):
                def run(r):
                    body = r.group(1); rpr = re.search(r'<w:rPr>.*?</w:rPr>', body, re.DOTALL)
                    if rpr:
                        p = re.sub(r'<w:color [^>]*/>|<w:u [^>]*/>', '', rpr.group(0))
                        p = p.replace('<w:sz ', LINK + '<w:sz ', 1) if '<w:sz ' in p else p.replace('</w:rPr>', LINK + '</w:rPr>', 1)
                        body = body.replace(rpr.group(0), p.replace('</w:rPr>', UL + '</w:rPr>', 1), 1)
                    else:
                        body = '<w:rPr>' + LINK + UL + '</w:rPr>' + body
                    return '<w:r>' + body + '</w:r>'
                return m.group(1) + re.sub(r'<w:r>(.*?)</w:r>', run, m.group(2), flags=re.DOTALL) + '</w:hyperlink>'
            x = re.sub(r'(<w:hyperlink [^>]*>)(.*?)</w:hyperlink>', style_links, x, flags=re.DOTALL)
            def shrink_code(m):  # the repo tree has 112-character lines; 7 pt Courier fits 6.7 in
                para = m.group(0)
                para = re.sub(r'<w:sz w:val="\d+"\s*/>', '', para); para = re.sub(r'<w:szCs w:val="\d+"\s*/>', '', para)
                para = re.sub(r'<w:rPr>', '<w:rPr><w:sz w:val="14"/><w:szCs w:val="14"/>', para)
                para = re.sub(r'<w:r>(?!<w:rPr>)', '<w:r><w:rPr><w:sz w:val="14"/><w:szCs w:val="14"/></w:rPr>', para)
                return para
            x = re.sub(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="SourceCode"\s*/>(?:(?!</w:p>).)*?</w:p>', shrink_code, x, flags=re.DOTALL)
            # keep each figure on the same page as its caption (the paragraph that follows it)
            def keep(m):
                p = m.group(0)
                if '<w:drawing>' not in p: return p
                if '<w:pPr>' in p: return p.replace('<w:pPr>', '<w:pPr><w:keepNext/>', 1)
                return p.replace('<w:p>', '<w:p><w:pPr><w:keepNext/></w:pPr>', 1)
            x = re.sub(r'<w:p>.*?</w:p>', keep, x, flags=re.DOTALL)
            # Every top-level section (H1) starts a new page, except "0. Orientation", which stays on page 1.
            # pandoc puts the heading's bookmarkStart just BEFORE the heading paragraph, so the break must go
            # in front of those tags too, or the bookmark (and every link to it) lands on the previous page.
            h1 = [m.start() for m in re.finditer(r'(?:<w:bookmarkStart\b[^>]*/>\s*)*<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Heading1"\s*/>', x, flags=re.DOTALL)]
            for pos in reversed(h1[1:]):
                x = x[:pos] + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + x[pos:]
            # Center the title and the author block under it.
            def add_jc(p):
                if '<w:pPr>' not in p: return p.replace('<w:p>', '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>', 1)
                ppr = re.search(r'<w:pPr>.*?</w:pPr>', p, re.DOTALL).group(0)
                new = ppr.replace('<w:rPr>', '<w:jc w:val="center"/><w:rPr>', 1) if '<w:rPr>' in ppr else ppr.replace('</w:pPr>', '<w:jc w:val="center"/></w:pPr>', 1)
                return p.replace(ppr, new, 1)
            tm = re.search(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Title"\s*/>(?:(?!</w:p>).)*?</w:p>', x, flags=re.DOTALL)
            nxt = re.search(r'<w:p>.*?</w:p>', x[tm.end():], flags=re.DOTALL)
            x = x[:tm.start()] + add_jc(tm.group(0)) + x[tm.end():tm.end() + nxt.start()] + add_jc(nxt.group(0)) + x[tm.end() + nxt.end():]
            data = x.encode()
        zout.writestr(item, data)
z = zipfile.ZipFile(out); doc = z.read("word/document.xml").decode(); sty = z.read("word/styles.xml").decode()
cx = [int(m) for m in re.findall(r'<wp:extent cx="(\d+)"', doc)]
n_title, n_h1 = doc.count('w:val="Title"'), doc.count('w:val="Heading1"')
arial, portrait = 'w:ascii="Arial"' in sty, 'w:h="15840"' in doc
print(f"wrote {out} — {out.stat().st_size/1e6:.1f} MB | images {len(cx)} (widest {max(cx)/914400:.2f} in) | tables {doc.count('<w:tbl>')} | Title {n_title} | H1 {n_h1} | Arial {arial} | portrait {portrait}")
