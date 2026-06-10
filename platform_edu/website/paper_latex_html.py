"""
Rough LaTeX → HTML helpers for uploaded IB-like exam bundles (.tex + images/).

Covers common patterns seen in Digitary / IB maths exports—not a full LaTeX engine.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import quote


MARK_RE = re.compile(r'\[\s*Maximum mark:\s*(\d+)\s*\]', re.MULTILINE | re.IGNORECASE)
INCLUDE_RE = re.compile(
    r'\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}',
    re.MULTILINE,
)


def strip_latex_comments(text: str) -> str:
    out = []
    for line in text.splitlines(True):
        nl_end = ''
        core = line
        if core.endswith('\r\n'):
            nl_end = '\r\n'
            core = core[:-2]
        elif core.endswith('\n'):
            nl_end = '\n'
            core = core[:-1]
        elif core.endswith('\r'):
            nl_end = '\r'
            core = core[:-1]

        if core.lstrip().startswith('%'):
            continue

        kept = []
        for i2, ch2 in enumerate(core):
            if ch2 == '%' and (i2 == 0 or core[i2 - 1] != '\\'):
                break
            kept.append(ch2)
        out.append(''.join(kept) + nl_end)
    return ''.join(out)


def extract_document(tex: str) -> str:
    m = re.search(
        r'\\begin\{document\}(.*)\\end\{document\}',
        tex,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1) if m else tex


SECTION_STAR_RE = re.compile(r'\\section\*\{([^}]*)\}', re.DOTALL)


def extract_paper_meta(body: str) -> dict:
    titles = SECTION_STAR_RE.findall(body)
    short = []
    for t in titles[:8]:
        t = re.sub(r'\s+', ' ', t.replace('\\\\', ' — ')).strip()
        if len(t) > 420 or 'rights reserved' in t.lower():
            continue
        if 'please do not write' in t.lower():
            continue
        short.append(t)

    title = short[0] if short else 'Uploaded paper preview'
    subtitle_parts = short[1:3] if len(short) > 1 else []
    meta = {
        'title': title,
        'subtitle': ' · '.join(subtitle_parts) if subtitle_parts else '',
    }
    mtime = re.search(r'(\d+\s+[A-Za-z]+\s+\d{4})\b', body[:4500])
    if mtime and meta['subtitle'] == '':
        meta['subtitle'] = mtime.group(1)

    mh = re.search(
        r'(\d+\s*hours?\s*\d*\s*minutes?|\d+\s*hour\s*\d+\s*minutes?)',
        body[:8000],
        re.IGNORECASE,
    )
    if not mh:
        mh = re.search(
            r'\b(\d+\s*minutes?)\b',
            body[:8000],
            re.IGNORECASE,
        )
    meta['time'] = mh.group(0).strip() if mh else '—'
    meta['notes'] = (
        'Auto-converted from uploaded LaTeX. Tables and layout are approximate; '
        'check figures and notation against the PDF.'
    )
    return meta


def resolve_image(rel_name: str, roots: Iterable[Path]) -> Optional[Path]:
    rel_name = rel_name.strip()
    if not rel_name or '..' in rel_name.replace('\\', '/'):
        return None
    if Path(rel_name).is_absolute():
        return None

    rel_posix = rel_name.replace('\\', '/')
    basename = Path(rel_posix).name
    stem = Path(rel_posix).stem

    for root in roots:
        if not root.exists():
            continue
        direct = root / rel_posix
        try:
            if direct.is_file():
                direct.resolve().relative_to(root.resolve())
                return direct
        except (OSError, ValueError):
            pass
        for ext in ('', '.jpg', '.jpeg', '.png', '.webp'):
            p = (root / f'{stem}{ext}') if ext else (root / basename)
            try:
                if p.is_file():
                    p.resolve().relative_to(root.resolve())
                    return p
            except (OSError, ValueError):
                continue
        try:
            for p in root.rglob(stem + '*'):
                if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                    p.resolve().relative_to(root.resolve())
                    return p
        except (OSError, ValueError):
            continue
    return None


def _tex_inline_cell(fragment: str) -> str:
    s = fragment.replace('\\&', '&')
    return html.escape(s, quote=False)


def _convert_tabular_block(inner: str) -> str:
    inner = re.sub(
        r'\\multicolumn\{[^}]+\}\{[^}]+\}\{(.*?)\}',
        r'\1',
        inner,
        flags=re.DOTALL,
    )
    inner = re.sub(
        r'\\multirow\{[^}]+\}\{[^}]+\}\{(.*?)\}',
        r'\1',
        inner,
        flags=re.DOTALL,
    )
    blob = re.sub(r'\\hline\s*', '', inner)
    rows_raw = [r.strip() for r in re.split(r'\\\\(?![A-Za-z])', blob) if r.strip()]

    trs = []
    for raw in rows_raw:
        cols = [_tex_inline_cell(c.strip()) for c in re.split(r'(?<!\\)&', raw)]
        if not cols:
            continue
        row = ''.join(f'<td>{c}</td>' for c in cols)
        trs.append(f'<tr>{row}</tr>')

    return (
        '<table class="table table-sm table-bordered" '
        'style="max-width:46rem;font-size:.86rem;"><tbody>'
        f'{"".join(trs)}</tbody></table>'
    )


def _convert_tables(s: str) -> str:
    pat = re.compile(
        r'\\begin\{tabular\}\{[^}]*\}([\s\S]*?)\\end\{tabular\}',
        re.MULTILINE,
    )
    return pat.sub(lambda m: _convert_tabular_block(m.group(1)), s)


NOISE_FRAGMENTS = tuple(
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in (
        r'\\?\(This question continues on the following page\)\s*\\.?',
        r'\\?\(Question\s*\d+\s*continued\)\s*\\.?',
        r'diagram\s+not\s+to\s+scale\.?',
    )
)


def _section_drop_please(m: re.Match) -> str:
    if 'please do not write' in m.group(1).lower():
        return ''
    return m.group(0)


def _strip_noise(s: str) -> str:
    for pat in NOISE_FRAGMENTS:
        s = pat.sub('', s)
    s = SECTION_STAR_RE.sub(_section_drop_please, s)
    s = re.sub(r'\\begin\{enumerate\}|\\end\{enumerate\}', '', s)
    s = re.sub(r'\\begin\{center\}|\\end\{center\}', '', s)
    return s.strip()


# Roman markers used for *splitting* latin (a)-(z) vs (i)-(xii) sub-parts
_ROMAN_PART_TOKENS = frozenset(
    'i ii iii iv v vi vii viii ix x xi xii'.split(),
)
_ROMAN_SUB_SPLIT_RE = re.compile(
    r'(?:^|\n)\s*\(\s*(xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)\s*\)\s+',
    re.IGNORECASE | re.MULTILINE,
)
_ROMAN_SUB_INLINE_RE = re.compile(
    r'(?<=[\.!?])\s+\(\s*(xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)\s*\)\s+(?=[A-Za-z"“])',
    re.IGNORECASE,
)


def _is_roman_part_token(tok: str) -> bool:
    return tok.lower() in _ROMAN_PART_TOKENS


def _collect_roman_subpart_spans(tex: str) -> list[tuple[int, int, str]]:
    """Sorted non-overlapping (start, end, lowercase roman) spans for \\\\( i) ... headers."""
    raw: list[tuple[int, int, str]] = []
    for rx in (_ROMAN_SUB_SPLIT_RE, _ROMAN_SUB_INLINE_RE):
        for m in rx.finditer(tex):
            raw.append((m.start(), m.end(), m.group(1).lower()))
    raw.sort(key=lambda t: (t[0], t[1]))
    merged: list[tuple[int, int, str]] = []
    for start, end, tok in raw:
        if merged and start < merged[-1][1] + 1:
            continue
        merged.append((start, end, tok))
    return merged


def split_tex_roman_subparts(tex: str) -> list[tuple[Optional[str], str]]:
    """
    Split a latin-part body into (roman_label_or_None, latex_chunk).
    None = material before first (i)/(ii)/… roman header.
    """
    tex_st = tex.strip('\n ')
    spans = _collect_roman_subpart_spans(tex_st)
    if not spans:
        return [(None, tex_st)]
    chunks: list[tuple[Optional[str], str]] = []
    preamble = tex_st[: spans[0][0]].strip()
    chunks.append((None, preamble))
    for i, (start, end, tok) in enumerate(spans):
        body_start = end
        body_end = spans[i + 1][0] if i + 1 < len(spans) else len(tex_st)
        body = tex_st[body_start:body_end].strip()
        chunks.append((tok, body))
    return chunks


def _shield_tabulars(s: str) -> tuple[str, dict[int, str]]:
    """
    Replace \\begin{tabular}...\\end{tabular} with placeholders so part-splitting
    does not see false '(a)' matches inside table cells.
    """
    store: dict[int, str] = {}

    def repl(m: re.Match) -> str:
        idx = len(store)
        store[idx] = m.group(0)
        return f'«TAB{idx}»'

    shielded = re.sub(
        r'\\begin\{tabular\}[\s\S]*?\\end\{tabular\}',
        repl,
        s,
    )
    return shielded, store


def _restore_tabulars(s: str, store: dict[int, str]) -> str:
    def repl(m: re.Match) -> str:
        idx = int(m.group(1))
        return store.get(idx, m.group(0))

    return re.sub(r'«TAB(\d+)»', repl, s)


def _normalize_tex_linebreaks(s: str) -> str:
    """
    Remove IB/Digitary TeX line-continuation backslashes and merge broken lines.
    Does not run on tabular placeholders.
    """
    chunks = re.split(r'(«TAB\d+»)', s)
    out = []
    for ch in chunks:
        if ch.startswith('«TAB'):
            out.append(ch)
            continue
        t = ch
        # Explicit LaTeX row break "\\" (+ optional [\dimen]) → new paragraph boundary
        t = re.sub(r'\\\\(?:\[[^\]]*\])?\s*\r?\n\s*', '\n\n', t)
        # Single "\" + newline (Digitary continuation) → keep as paragraph break before next line
        t = re.sub(r'(?<!\\)\\(\s*\r?\n\s*)', '\n\n', t)
        # "... .\ \n" variants
        t = re.sub(r'(\s)\\(\s*\r?\n\s*)', '\n\n', t)
        t = re.sub(r'\n{3,}', '\n\n', t)
        # Trailing "\" at end of line
        t = re.sub(r'(?m)(?<=[\w\.\)\]])\s*\\\s*$', '', t)
        out.append(t)
    return ''.join(out)


def _part_split_indices(s: str) -> list[int]:
    """
    Indices in s where a new (a)/(b)/… sub-question begins (Latin labels only).
    """
    candidates: dict[int, str] = {}

    for m in re.finditer(
        r'(?:^|\n|;)\s*\\textbf\s*\{\s*\(([a-z]+)\)\s*\}',
        s,
        re.IGNORECASE | re.MULTILINE,
    ):
        tok = m.group(1).lower()
        if not _is_roman_part_token(tok):
            candidates[m.start()] = tok

    for m in re.finditer(
        r'(?:^|\n)\s*\(\s*([a-z]+)\)\s+(?=\S)',
        s,
        re.IGNORECASE | re.MULTILINE,
    ):
        tok = m.group(1).lower()
        if _is_roman_part_token(tok):
            continue
        pos = m.start()
        dup = False
        for px in candidates:
            if abs(pos - px) < 3:
                dup = True
                break
        if not dup:
            candidates[pos] = tok

    for m in re.finditer(
        r'(?<=[\.!?])\s+\(\s*([a-z]+)\)\s+(?=[A-Za-z"$])',
        s,
        re.IGNORECASE,
    ):
        tok = m.group(1).lower()
        if _is_roman_part_token(tok):
            continue
        pos = m.start()
        dup = False
        for px in candidates:
            if abs(pos - px) < 20:
                dup = True
                break
        if not dup:
            candidates[pos] = tok

    return sorted(candidates.keys())


def _peel_first_part_marker(raw_tex: str) -> tuple[str | None, str]:
    """
    Return (latin_label_without_parens_or_None, remainder).
    """
    m = re.match(r'^\s*\\textbf\s*\{\s*\(([a-z]+)\)\s*\}\s*', raw_tex, re.I)
    if m:
        tok = m.group(1).lower()
        if not _is_roman_part_token(tok):
            return tok, raw_tex[m.end():].lstrip()
    m2 = re.match(r'^\s*\(\s*([a-z]+)\)\s+', raw_tex, re.I)
    if m2:
        tok = m2.group(1).lower()
        if not _is_roman_part_token(tok):
            return tok, raw_tex[m2.end():].lstrip()
    return None, raw_tex


def _apply_simple_text_commands(s: str) -> str:
    while True:
        n = re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', s)
        if n == s:
            break
        s = n
    s = re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', s)
    s = re.sub(r'\\emph\{([^}]*)\}', r'<em>\1</em>', s)
    s = re.sub(
        r'\\href\{([^}]*)\}\{([^}]*)\}',
        r'<a href="\1" target="_blank" rel="noopener">\2</a>',
        s,
    )
    return s


def _latex_fragment_to_inner_html(
    s: str,
    image_url_builder: Callable[[str], Optional[str]],
) -> str:
    """Convert LaTeX fragment (one intro or one part body) to HTML body content."""

    def img_repl(m: re.Match) -> str:
        stem = m.group(1).strip()
        url = image_url_builder(stem)
        if not url:
            return (
                f'<span class="text-muted small">[missing image: {html.escape(stem)}]</span>'
            )
        return (
            f'<img class="medium_question" src="{html.escape(url, quote=True)}" '
            f'alt="{html.escape(stem)}"/>'
        )

    s = INCLUDE_RE.sub(img_repl, s)
    s = _apply_simple_text_commands(s)
    s = _convert_tables(s)

    s = re.sub(r'\\item\s+', '</li><li>', s)
    if '</li><li>' in s:
        s = '<ul><li>' + s + '</li></ul>'
        s = re.sub(r'<li>\s*</li>', '', s)

    s = re.sub(r'\\begin\{itemize\}', '<ul>', s)
    s = re.sub(r'\\end\{itemize\}', '</ul>', s)

    s = re.sub(r'\\\s*$', '', s, flags=re.MULTILINE)
    s = s.replace('\\[0pt]', '')
    s = re.sub(r'\\\\(?:\[[^\]]*\])?\s*', '<br/>', s)
    s = re.sub(r'\s+\\(?=\s|$)', '', s)

    # Flow markup only (no <p>) so we can wrap once in intro / question-bank wrappers.
    parts = [b.strip() for b in re.split(r'\n\s*\n\s*', s) if b.strip()]
    return '<br/><br/>'.join(
        re.sub(r'\s*\n\s*', '<br/>', p) for p in parts
    )


def _intro_markup(flow_html: str) -> str:
    if not flow_html.strip():
        return ''
    if re.search(r'<(?:table|ul|img)\b', flow_html, re.I):
        return f'<div class="qb-intro mb-3">{flow_html}</div>'
    return f'<p>{flow_html}</p>'


def _sub_question_markup(roman: str, inner_html: str) -> str:
    if not inner_html.strip():
        return f'<p class="sub-question"><strong>({roman})</strong></p>'
    if re.search(r'<(?:table|ul|img)\b', inner_html, re.I):
        return (
            f'<div class="sub-question mb-2"><strong>({roman})</strong> {inner_html}</div>'
        )
    return (
        f'<p class="sub-question"><strong>({roman})</strong> {inner_html}</p>'
    )


def _part_markup(letter: str, inner_html: str) -> str:
    if not inner_html.strip():
        return f'<p class="question"><strong>({letter})</strong></p>'
    if re.search(r'<(?:table|ul|img)\b', inner_html, re.I):
        return (
            f'<div class="question mb-2"><strong>({letter})</strong> {inner_html}</div>'
        )
    return (
        f'<p class="question"><strong>({letter})</strong> {inner_html}</p>'
    )


def _part_markup_with_roman_subparts(
    letter: str,
    remainder_tex: str,
    image_url_builder: Callable[[str], Optional[str]],
) -> str:
    pieces = split_tex_roman_subparts(remainder_tex)
    fragments: list[str] = []
    for rom, tex_piece in pieces:
        stripped = tex_piece.strip()
        if rom is None and not stripped:
            fragments.append(f'<p class="question"><strong>({letter})</strong></p>')
            continue
        inner = _latex_fragment_to_inner_html(tex_piece, image_url_builder)
        if rom is None:
            fragments.append(_part_markup(letter, inner))
        else:
            fragments.append(_sub_question_markup(rom, inner))
    return ''.join(fragments)


def _append_flow_to_last_block(out_fragments: list[str], flow_html: str) -> None:
    """Glue a continuation fragment onto the tail of the last rendered block."""
    if not flow_html.strip():
        return
    if not out_fragments:
        out_fragments.append(_intro_markup(flow_html))
        return
    last = out_fragments[-1]
    glue = '<br/><br/>' + flow_html
    if last.endswith('</p>'):
        out_fragments[-1] = last[:-4] + glue + '</p>'
    elif last.endswith('</div>'):
        out_fragments[-1] = last[:-6] + glue + '</div>'
    else:
        out_fragments.append(_intro_markup(flow_html))


def latex_chunk_to_html(
    chunk: str,
    image_url_builder: Callable[[str], Optional[str]],
) -> str:
    s = strip_latex_comments(chunk)
    s = _strip_noise(s)
    s_tex, tab_store = _shield_tabulars(s)
    s_tex = _normalize_tex_linebreaks(s_tex)

    cuts = sorted(_part_split_indices(s_tex))
    if not cuts:
        segments = [s_tex]
    else:
        segments: list[str] = []
        start_i = 0
        for c in cuts:
            segments.append(s_tex[start_i:c])
            start_i = c
        segments.append(s_tex[start_i:])

    out: list[str] = []
    first = True
    for raw_seg in segments:
        seg_restored = _restore_tabulars(raw_seg.strip('\n '), tab_store)
        if first:
            frag = _latex_fragment_to_inner_html(seg_restored, image_url_builder)
            if frag.strip():
                out.append(_intro_markup(frag))
            first = False
            continue

        lett, remainder = _peel_first_part_marker(seg_restored.strip())
        if lett is None:
            frag = _latex_fragment_to_inner_html(seg_restored, image_url_builder)
            _append_flow_to_last_block(out, frag)
            continue

        out.append(
            _part_markup_with_roman_subparts(lett, remainder, image_url_builder),
        )

    return ''.join(out)


def _media_abs_url(upload_rel: str, path_under_media: Path) -> str:
    rel_parts = Path(upload_rel).joinpath(*path_under_media.parts)
    rel_str = '/'.join(quote(part, safe='') for part in rel_parts.parts)
    return f'/media/{rel_str}'


def parse_tex_bundle(
    tex_text: str,
    *,
    pack_root_resolved: Path,
    upload_rel: str,
) -> tuple[dict, list[dict]]:
    body_raw = extract_document(tex_text)

    imgs_sub = pack_root_resolved / 'images'
    roots = []
    if imgs_sub.is_dir():
        roots.append(imgs_sub)
    roots.append(pack_root_resolved)

    def image_url_simple(stem: str) -> Optional[str]:
        p = resolve_image(stem, roots)
        if not p:
            return None
        rel_u = Path(p.relative_to(pack_root_resolved))
        return _media_abs_url(upload_rel, rel_u)

    marks = list(MARK_RE.finditer(body_raw))
    if not marks:
        raise ValueError(
            'No “[Maximum mark: …]” markers found — this export may use a '
            'different template.',
        )

    meta = extract_paper_meta(body_raw)
    qs: list[dict] = []

    for i, m in enumerate(marks):
        marks_int = int(m.group(1))
        next_pos = marks[i + 1].start() if i + 1 < len(marks) else len(body_raw)

        chunk = body_raw[m.end():next_pos].strip()
        chunk = SECTION_STAR_RE.sub(_section_drop_please, chunk)
        chunk = chunk.strip()

        body_html = latex_chunk_to_html(chunk, image_url_simple)
        qs.append({
            'num': i + 1,
            'marks': marks_int,
            'image': None,
            'image_url': None,
            'body_html': body_html,
        })

    return meta, qs


def write_manifest(pack_root: Path, meta: dict, questions: list[dict]) -> None:
    mf = {'paper_meta': meta, 'questions': questions}
    (pack_root / 'manifest.json').write_text(json.dumps(mf), encoding='utf-8')


def read_manifest(pack_root: Path) -> Optional[dict]:
    p = pack_root / 'manifest.json'
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding='utf-8'))
