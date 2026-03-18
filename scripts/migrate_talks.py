#!/usr/bin/env python3
"""One-time migration: parse talks.tex + talks/index.md -> talks.yaml"""

import re
import yaml
from pathlib import Path
from datetime import date

CV_DIR = Path(__file__).parent.parent
WEBSITE_DIR = Path.home() / 'code' / 'renmengye.github.io'

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}


def parse_date(text, year):
    """Extract date from text like 'Oct 31, 2025' or 'Jun 2025' or '2021/02'."""
    text = text.strip().rstrip('.')

    # Try YYYY/MM/DD or YYYY/MM format
    m = re.search(r'(\d{4})/(\d{1,2})(?:/(\d{1,2}))?', text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else 1
        return f"{y}-{mo:02d}-{d:02d}"

    # Try "Month Day, Year" or "Month Year"
    m = re.search(r'([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})', text)
    if m:
        mo = MONTH_MAP.get(m.group(1).lower(), 1)
        return f"{int(m.group(3))}-{mo:02d}-{int(m.group(2)):02d}"

    m = re.search(r'([A-Za-z]+)\.?\s+(\d{4})', text)
    if m:
        mo = MONTH_MAP.get(m.group(1).lower(), 1)
        return f"{int(m.group(2))}-{mo:02d}-01"

    # Fallback
    return f"{year}-01-01"


def parse_talks_tex(path):
    """Parse talks.tex into structured entries."""
    with open(path) as f:
        text = f.read()

    entries = []
    current_year = None
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if line.startswith('%') or not line:
            continue

        ym = re.search(r'\\textbf\{(\d{4})\}', line)
        if ym:
            current_year = int(ym.group(1))
            continue

        im = re.match(r'\\item\s+(.*)', line)
        if not im:
            continue

        item_text = im.group(1).strip()
        if not item_text:
            continue

        # Format: "Title. Venue. Location. Date."
        # Split on ". " but be careful with abbreviations
        # Protect common abbreviations
        protected = item_text
        for abbr in ['Dr.', 'Prof.', 'Mr.', 'Mrs.', 'St.', 'Jr.', 'Sr.', 'vs.']:
            protected = protected.replace(abbr, abbr.replace('.', '@@'))

        parts = [p.strip() for p in protected.split('. ')]
        parts = [p.replace('@@', '.') for p in parts]

        # First part is always the title
        title = parts[0] if parts else item_text

        # Extract date from the full item text (search all parts)
        date_str = parse_date(item_text, current_year)

        # Everything between title and date is venue + location
        # Remove the date portion from parts to get venue
        venue_parts = []
        for p in parts[1:]:
            # Skip parts that look like dates
            if re.match(r'^[A-Z][a-z]+\.?\s+\d', p) and re.search(r'\d{4}', p):
                continue
            if re.match(r'^\d{4}', p):
                continue
            venue_parts.append(p)
        venue = '. '.join(venue_parts)
        location = ''

        entries.append({
            'title': title,
            'venue': venue,
            'location': location,
            'date': date_str,
            'links': {},
            'selected': False,
            'on_website': True,
        })

    return entries


def parse_talks_md(path):
    """Parse talks/index.md to extract links."""
    with open(path) as f:
        text = f.read()

    entries = []
    # Each talk starts with "* "
    blocks = re.split(r'\n\*\s+', text)

    for block in blocks[1:]:
        # Extract title — first line up to first ". "
        block = block.strip()
        # Protect abbreviations
        for abbr in ['Dr.', 'Prof.', 'Mr.', 'Mrs.', 'St.', 'Jr.']:
            block = block.replace(abbr, abbr.replace('.', '@@'))

        first_dot = block.find('. ')
        if first_dot > 0:
            title = block[:first_dot].replace('@@', '.').strip()
            rest = block[first_dot + 2:].replace('@@', '.').strip()
        else:
            title = block.replace('@@', '.').strip()
            rest = ''

        # Extract links
        links = {}
        for m in re.finditer(r'\[\[(\w+)\]\(([^)]+)\)\]', rest):
            links[m.group(1).lower()] = m.group(2)

        # Extract date — look for YYYY/MM/DD or YYYY/MM pattern
        date_match = re.search(r'(\d{4}/\d{1,2}(?:/\d{1,2})?)', rest)
        date_str = ''
        if date_match:
            parts = date_match.group(1).split('/')
            y = int(parts[0])
            mo = int(parts[1]) if len(parts) > 1 else 1
            d = int(parts[2]) if len(parts) > 2 else 1
            date_str = f"{y}-{mo:02d}-{d:02d}"

        entries.append({
            'title': title,
            'links': links,
            'date': date_str,
        })

    return entries


def normalize(t):
    return re.sub(r'[^a-z0-9\s]', '', t.lower()).strip()


def merge_links(tex_entries, md_entries):
    """Match tex entries with md entries by title and merge links."""
    matched = 0
    for te in tex_entries:
        tn = normalize(te['title'])
        for me in md_entries:
            mn = normalize(me['title'])
            if tn == mn or (len(tn) > 20 and tn[:20] == mn[:20]):
                if me['links']:
                    te['links'] = me['links']
                    matched += 1
                # Use website date if more specific
                if me['date'] and me['date'] > te['date']:
                    te['date'] = me['date']
                break
    print(f"  Matched {matched} talks with links from website")
    return tex_entries


def parse_select_talks(path):
    """Parse select_talks.tex to get selected talk titles."""
    with open(path) as f:
        text = f.read()
    titles = []
    for m in re.finditer(r'\\item\s+(.+?)\\hfill', text):
        titles.append(m.group(1).strip())
    return titles


def main():
    talks_tex = CV_DIR / 'sections' / 'talks.tex'
    talks_md = WEBSITE_DIR / 'talks' / 'index.md'
    select_tex = CV_DIR / 'sections' / 'select_talks.tex'

    print(f"Parsing {talks_tex}...")
    entries = parse_talks_tex(str(talks_tex))
    print(f"  {len(entries)} talks from CV")

    if talks_md.exists():
        print(f"Parsing {talks_md}...")
        md_entries = parse_talks_md(str(talks_md))
        print(f"  {len(md_entries)} talks from website")
        entries = merge_links(entries, md_entries)

    # Mark selected talks
    selected_titles = parse_select_talks(str(select_tex))
    for entry in entries:
        for st in selected_titles:
            if normalize(st) in normalize(entry['title']):
                entry['selected'] = True
                break

    # Sort by date descending
    entries.sort(key=lambda e: e.get('date', ''), reverse=True)

    # Write
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    def str_representer(d, s):
        if '\n' in s:
            return d.represent_scalar('tag:yaml.org,2002:str', s, style='|')
        if any(c in s for c in ':{}[],"\'&'):
            return d.represent_scalar('tag:yaml.org,2002:str', s, style='"')
        return d.represent_scalar('tag:yaml.org,2002:str', s)

    def none_representer(d, s):
        return d.represent_scalar('tag:yaml.org,2002:null', 'null')

    NoAliasDumper.add_representer(str, str_representer)
    NoAliasDumper.add_representer(type(None), none_representer)

    output = CV_DIR / 'talks.yaml'
    with open(output, 'w') as f:
        f.write('# Talks sorted by date descending (newest first).\n')
        f.write('# To add a talk: copy an existing entry, edit fields, insert by date.\n\n')
        yaml.dump({'talks': entries}, f, Dumper=NoAliasDumper,
                  default_flow_style=False, allow_unicode=True, sort_keys=False, width=200)

    print(f"\nWrote {output} ({len(entries)} talks)")
    selected_count = sum(1 for e in entries if e.get('selected'))
    print(f"  {selected_count} marked as selected")


if __name__ == '__main__':
    main()
