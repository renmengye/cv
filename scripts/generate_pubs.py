#!/usr/bin/env python3
"""Generate sections/pubs.tex and sections/select_pubs.tex from publications.yaml.

The YAML is a flat list of publications with a 'type' field.
This script groups by type and year to produce the LaTeX output.
Numbering: C1 = oldest, CN = newest (reverse chronological etaremune).
"""

import yaml
from pathlib import Path
from collections import OrderedDict

ME = "Mengye Ren"
CV_DIR = Path(__file__).parent.parent


def load_data():
    with open(CV_DIR / 'publications.yaml') as f:
        data = yaml.safe_load(f)
    return data.get('publications', data)


def by_type(entries, t):
    """Filter entries by type, preserving order."""
    return [e for e in entries if e.get('type') == t]


def bold_me(name):
    if name == ME:
        return r'\textbf{' + name + '}'
    return name


def abbreviate_name(name):
    """Convert 'First Middle Last' to 'F. M. Last'."""
    if name == ME:
        return r'\textbf{M. Ren}'
    parts = name.split()
    if len(parts) <= 1:
        return name
    inits = [p[0] + '.' if len(p) > 1 and not p.endswith('.') else p for p in parts[:-1]]
    return ' '.join(inits) + ' ' + parts[-1]


def format_authors(entry, abbreviate=False):
    authors = entry.get('authors', [])
    if not authors:
        return ''
    equal = set(entry.get('equal_contribution', []))
    parts = []
    for i, name in enumerate(authors):
        formatted = abbreviate_name(name) if abbreviate else bold_me(name)
        if i in equal:
            formatted += '*'
        parts.append(formatted)
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f'{parts[0]} and {parts[1]}'
    return ', '.join(parts[:-1]) + ', and ' + parts[-1]


def format_venue(entry, short=False):
    v = entry.get('venue_short' if short else 'venue_full', '')
    if not v:
        return ''
    return r'\textit{' + v + '}'


def format_note(entry):
    note = entry.get('note')
    return f'\n(\\textbf{{{note}}})' if note else ''


def format_location_year(entry):
    parts = []
    loc = entry.get('venue_location', '')
    if loc and loc not in ('.', ''):
        parts.append(loc)
    year = entry.get('year')
    if year is not None:
        parts.append(str(year))
    return ', ' + ', '.join(parts) if parts else ''


def format_item(entry):
    authors = format_authors(entry)
    title = entry.get('title', '')
    venue = format_venue(entry)
    loc_year = format_location_year(entry)
    note = format_note(entry)
    return f'\\item {authors}. {title}. {venue}{loc_year}.{note}\n'


def format_patent_item(entry, short=False):
    if short:
        raw = entry.get('authors_short', [])
        parts = []
        for a in raw:
            if a in ('M Ren', 'M. Ren'):
                parts.append(r'\textbf{' + a + '}')
            else:
                parts.append(a)
    else:
        parts = [bold_me(a) for a in entry.get('authors', [])]

    if not parts:
        author_str = ''
    elif len(parts) == 1:
        author_str = parts[0]
    else:
        author_str = ', '.join(parts[:-1]) + ', and ' + parts[-1]

    title = entry.get('title', '')
    patent_number = entry.get('patent_number', '')
    year = entry.get('year', '')
    return f'\\item {author_str}. {title}. {patent_number}, \\textit{{U.S. Patent}}, {year}.\n'


def year_grouped_blocks(entries, prefix):
    """Generate etaremune blocks grouped by year with correct reverse counters."""
    lines = []
    total = len(entries)
    by_year = OrderedDict()
    for e in entries:
        by_year.setdefault(e.get('year', 0), []).append(e)

    counter = total
    for year, year_entries in by_year.items():
        lines.append(f'\\textbf{{{year}}}')
        lines.append(f'\\begin{{etaremune}}[start={counter}]')
        lines.append(f'\\renewcommand\\labelenumi{{{prefix}\\theenumi}}')
        for entry in year_entries:
            lines.append(format_item(entry))
        counter -= len(year_entries)
        lines.append(r'\end{etaremune}')
        lines.append('')
    return lines


def generate_pubs_tex(all_entries):
    lines = []
    lines.append('% AUTO-GENERATED from publications.yaml -- do not edit manually.')
    lines.append('% !TEX root = ../cv_mengye_ren.tex')

    conf = by_type(all_entries, 'conference')
    work = by_type(all_entries, 'workshop')
    prep = by_type(all_entries, 'preprint')
    pats = by_type(all_entries, 'patent')

    # Conference + Workshop (full CV only)
    lines.append(r'\if\shortcv0')
    lines.append(r'\section{\sc Peer-Reviewed Conference Publications}')
    lines.append('(*=equal contribution)')
    lines.append('')
    lines.extend(year_grouped_blocks(conf, 'C'))

    lines.append(r'\section{\sc Peer-Reviewed Workshop Papers}')
    lines.append('')
    lines.extend(year_grouped_blocks(work, 'W'))
    lines.append(r'\vspace{0.1in}')
    lines.append(r'\fi')
    lines.append('')

    # Preprints (both CV versions)
    lines.append(r'\section{\sc Preprints \& Tech Reports}')
    lines.append(f'\\begin{{etaremune}}[start={len(prep)}]')
    lines.append(r'\renewcommand\labelenumi{R\theenumi}')
    for e in prep:
        lines.append(format_item(e))
    lines.append(r'\end{etaremune}')
    lines.append('')

    # Patents - short CV version
    lines.append(r'\if\shortcv1')
    lines.append(r'\section{\sc Patents}')
    lines.append(r'\begin{list2}')
    for e in pats:
        lines.append(format_patent_item(e, short=True))
    lines.append(r'\end{list2}')

    # Patents - full CV version
    lines.append(r'\else')
    lines.append(r'\section{\sc Patents}')
    lines.append(f'\\begin{{etaremune}}[start={len(pats)}]')
    lines.append(r'\renewcommand\labelenumi{P\theenumi}')
    for e in pats:
        lines.append(format_patent_item(e, short=False))
    lines.append(r'\end{etaremune}')
    lines.append(r'\vspace{0.1in}')
    lines.append(r'\fi')

    return '\n'.join(lines) + '\n'


def generate_select_pubs_tex(all_entries):
    selected = sorted(
        [e for e in all_entries if e.get('selected')],
        key=lambda e: -e.get('year', 0)
    )
    lines = []
    lines.append('% AUTO-GENERATED from publications.yaml -- do not edit manually.')
    lines.append('% !TEX root = ../cv_mengye_ren_short.tex')
    lines.append(r'\if\shortcv1')
    lines.append(r'\section{\sc Selected Publications}')
    lines.append(r'\begin{list2}')
    for e in selected:
        authors = format_authors(e, abbreviate=True)
        title = e.get('title', '')
        venue = format_venue(e, short=True)
        year = e.get('year', '')
        lines.append(f'\\item\n{authors}.\n{title}.\n{venue}, {year}.\n')
    lines.append(r'\end{list2}')
    lines.append(r'\fi')
    return '\n'.join(lines) + '\n'


def main():
    entries = load_data()
    if isinstance(entries, dict):
        # Old format with categories as keys
        flat = []
        for cat in ['conference', 'workshop', 'preprint', 'patent']:
            for e in entries.get(cat, []):
                e['type'] = cat
                flat.append(e)
        entries = flat

    pubs_path = CV_DIR / 'sections' / 'pubs.tex'
    with open(pubs_path, 'w') as f:
        f.write(generate_pubs_tex(entries))
    print(f'Wrote {pubs_path}')

    select_path = CV_DIR / 'sections' / 'select_pubs.tex'
    with open(select_path, 'w') as f:
        f.write(generate_select_pubs_tex(entries))
    print(f'Wrote {select_path}')

    from collections import Counter
    counts = Counter(e.get('type') for e in entries)
    for t in ['conference', 'workshop', 'preprint', 'patent']:
        n = counts.get(t, 0)
        print(f'  {t}: {n}')


if __name__ == '__main__':
    main()
