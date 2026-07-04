#!/usr/bin/env python3
"""Generate publications.bib from publications.yaml.

BibTeX export for tools like Interfolio FAR, ORCID, Google Scholar import, etc.
Conference + workshop -> @inproceedings, preprint -> @misc with arXiv fields,
patent -> @misc, thesis -> @phdthesis.
"""

import argparse
import re
import yaml
from pathlib import Path

CV_DIR = Path(__file__).parent.parent
YAML_PATH = CV_DIR / 'publications.yaml'
BIB_PATH = CV_DIR / 'publications.bib'

MONTH_NAMES = {
    1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
    7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec',
}


def format_authors(authors):
    """Convert ['First Last', ...] -> 'First Last and First Last and ...'."""
    return ' and '.join(authors)


def field(name, value):
    """Format one BibTeX field line, or empty string if value is falsy."""
    if value in (None, '', [], {}):
        return ''
    return f'  {name} = {{{value}}},\n'


def extract_arxiv_id(entry):
    """Pull '2605.16477' (or similar) from venue_full or links.arxiv."""
    sources = [
        entry.get('venue_full') or '',
        (entry.get('links') or {}).get('arxiv', ''),
    ]
    for s in sources:
        m = re.search(r'(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})', s)
        if m:
            return m.group(1)
    return None


def equal_contribution_note(entry):
    """Generate a brief equal-contribution note if applicable."""
    eq = entry.get('equal_contribution') or []
    if not eq:
        return ''
    authors = entry.get('authors', [])
    names = [authors[i] for i in eq if i < len(authors)]
    if not names:
        return ''
    return f"Equal contribution: {', '.join(names)}."


def format_entry(entry):
    """Return a BibTeX block for one publication."""
    key = entry['key']
    t = entry.get('type', 'misc')
    title = entry.get('title', '')
    authors = format_authors(entry.get('authors', []))
    year = entry.get('year', '')
    month = entry.get('month')
    location = entry.get('venue_location') or ''
    venue_full = entry.get('venue_full') or ''
    note = entry.get('note') or ''
    eq_note = equal_contribution_note(entry)
    arxiv_url = (entry.get('links') or {}).get('arxiv', '')

    # Combine note + equal-contribution note.
    full_note = '; '.join(filter(None, [note, eq_note])) if (note or eq_note) else ''

    if t == 'patent':
        kind = '@misc'
        body = [
            field('title', title),
            field('author', authors),
            field('howpublished', f"U.S. Patent {entry.get('patent_number', '')}"),
            field('year', year),
            field('note', full_note or 'U.S. Patent'),
        ]
    elif t == 'preprint':
        kind = '@misc'
        arxiv_id = extract_arxiv_id(entry)
        body = [
            field('title', title),
            field('author', authors),
            field('year', year),
            field('month', MONTH_NAMES.get(month, '')) if month else '',
            field('eprint', arxiv_id) if arxiv_id else '',
            field('archivePrefix', 'arXiv') if arxiv_id else '',
            field('url', arxiv_url),
            field('note', full_note),
        ]
    elif t == 'thesis':
        kind = '@phdthesis'
        body = [
            field('title', title),
            field('author', authors),
            # venue_full is the school for theses (e.g., "Ph.D. Thesis, University of Toronto").
            field('school', venue_full),
            field('year', year),
            field('month', MONTH_NAMES.get(month, '')) if month else '',
            field('address', location),
            field('note', full_note),
        ]
    else:  # conference or workshop
        kind = '@inproceedings'
        body = [
            field('title', title),
            field('author', authors),
            field('booktitle', venue_full),
            field('year', year),
            field('month', MONTH_NAMES.get(month, '')) if month else '',
            field('address', location),
            field('url', arxiv_url),
            field('note', full_note),
        ]

    body_str = ''.join(b for b in body if b)
    # Trim trailing comma+newline -> just newline.
    body_str = re.sub(r',\n$', '\n', body_str)
    return f'{kind}{{{key},\n{body_str}}}\n'


def parse_yyyymm(s):
    """Parse 'YYYY-MM' to (year, month) tuple."""
    m = re.match(r'^(\d{4})-(\d{1,2})$', s)
    if not m:
        raise ValueError(f"Expected YYYY-MM, got {s!r}")
    return int(m.group(1)), int(m.group(2))


def in_window(entry, since, until):
    """True if entry's (year, month) is within [since, until]. Missing month treated as 12 (year-end)."""
    y = entry.get('year') or 0
    mo = entry.get('month') or 12
    if since and (y, mo) < since:
        return False
    if until and (y, mo) > until:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', help='Filter to entries on or after YYYY-MM (e.g., 2025-09)')
    ap.add_argument('--until', help='Filter to entries on or before YYYY-MM')
    ap.add_argument('-o', '--output', help='Output path (default publications.bib, or publications_<since>_<until>.bib if filtered)')
    args = ap.parse_args()

    since = parse_yyyymm(args.since) if args.since else None
    until = parse_yyyymm(args.until) if args.until else None

    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    entries = data.get('publications', data)

    if since or until:
        entries = [e for e in entries if in_window(e, since, until)]

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = CV_DIR / out_path
    elif since or until:
        tag = f"{args.since or 'start'}_{args.until or 'now'}".replace('-', '')
        out_path = CV_DIR / f'publications_{tag}.bib'
    else:
        out_path = BIB_PATH

    header_filter = ''
    if since or until:
        header_filter = f"% Filtered: since={args.since or '-'}, until={args.until or '-'}\n"
    out = [
        '% Auto-generated from publications.yaml by scripts/generate_bib.py.\n',
        '% Do not edit manually; regenerate with `make bib`.\n',
        header_filter,
        '\n',
    ]
    counts = {}
    for e in entries:
        out.append(format_entry(e))
        out.append('\n')
        counts[e.get('type', 'unknown')] = counts.get(e.get('type', 'unknown'), 0) + 1

    out_path.write_text(''.join(out))
    print(f'Wrote {out_path}')
    for t, c in sorted(counts.items()):
        print(f'  {t}: {c}')
    print(f'  TOTAL: {sum(counts.values())}')


if __name__ == '__main__':
    main()
