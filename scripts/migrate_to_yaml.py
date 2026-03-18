#!/usr/bin/env python3
"""One-time migration script: parse pubs.tex + research/index.md -> publications.yaml"""

import re
import yaml
import sys
from difflib import SequenceMatcher
from pathlib import Path


def normalize_title(t):
    """Normalize title for fuzzy matching."""
    t = t.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def similar(a, b):
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


# ============================================================
# Parse pubs.tex
# ============================================================

def parse_pubs_tex(path):
    with open(path, 'r') as f:
        text = f.read()

    categories = {}

    # --- Conference ---
    m = re.search(
        r'\\section\{\\sc Peer-Reviewed Conference Publications\}(.*?)\\section\{\\sc Peer-Reviewed Workshop Papers\}',
        text, re.DOTALL)
    if m:
        categories['conference'] = extract_items(m.group(1), 'C')

    # --- Workshop ---
    m = re.search(
        r'\\section\{\\sc Peer-Reviewed Workshop Papers\}(.*?)\\fi\s*\n\s*\\section\{\\sc Preprints',
        text, re.DOTALL)
    if m:
        categories['workshop'] = extract_items(m.group(1), 'W')

    # --- Preprints ---
    m = re.search(
        r'\\section\{\\sc Preprints.*?\}\s*\\begin\{enumerate\}(.*?)\\end\{enumerate\}',
        text, re.DOTALL)
    if m:
        categories['preprint'] = extract_items_flat(m.group(1), 'R')

    # --- Patents (full version, after \else) ---
    m = re.search(
        r'\\else\s*\\section\{\\sc Patents\}.*?\\begin\{enumerate\}(.*?)\\end\{enumerate\}',
        text, re.DOTALL)
    if m:
        categories['patent'] = extract_patent_items(m.group(1))

    # --- Patents (short version) for authors_short ---
    m = re.search(
        r'\\if\\shortcv1\s*\\section\{\\sc Patents\}.*?\\begin\{list2\}(.*?)\\end\{list2\}',
        text, re.DOTALL)
    if m:
        short_patents = extract_patent_items_short(m.group(1))
        if 'patent' in categories:
            for i, pat in enumerate(categories['patent']):
                if i < len(short_patents):
                    pat['authors_short'] = short_patents[i]

    return categories


def extract_items(section_text, prefix):
    """Extract items from a section that has year-grouped enumerates."""
    entries = []
    current_year = None

    # Find all year headers and items
    # Process line by line to track year context
    lines = section_text.split('\n')
    item_buffer = []
    in_item = False

    for line in lines:
        # Check for year header
        ym = re.search(r'\\textbf\{(\d{4})\}', line)
        if ym:
            # Flush previous item
            if item_buffer:
                entry = parse_item('\n'.join(item_buffer), current_year)
                if entry:
                    entries.append(entry)
                item_buffer = []
            current_year = int(ym.group(1))
            continue

        # Check for \item
        im = re.match(r'\s*\\item\s*(.*)', line)
        if im:
            # Flush previous item
            if item_buffer:
                entry = parse_item('\n'.join(item_buffer), current_year)
                if entry:
                    entries.append(entry)
            item_buffer = [im.group(1)]
            continue

        # Skip enumerate boilerplate
        if re.match(r'\s*\\begin\{enumerate\}', line):
            continue
        if re.match(r'\s*\\end\{enumerate\}', line):
            continue
        if re.match(r'\s*\[resume\]', line):
            continue
        if re.match(r'\s*\\renewcommand', line):
            continue
        if re.match(r'\s*\\vspace', line):
            continue
        if re.match(r'\s*\\fi\s*$', line):
            continue
        if re.match(r'\s*%', line):
            continue
        if re.match(r'\s*\(\*=', line):
            continue

        # Continuation of current item
        if item_buffer:
            item_buffer.append(line)

    # Flush last item
    if item_buffer:
        entry = parse_item('\n'.join(item_buffer), current_year)
        if entry:
            entries.append(entry)

    return entries


def extract_items_flat(text, prefix):
    """Extract items from a flat enumerate (no year groups, like preprints)."""
    entries = []
    lines = text.split('\n')
    item_buffer = []

    for line in lines:
        if re.match(r'\s*\\renewcommand', line):
            continue
        im = re.match(r'\s*\\item\s*(.*)', line)
        if im:
            if item_buffer:
                entry = parse_item('\n'.join(item_buffer), None)
                if entry:
                    entries.append(entry)
            item_buffer = [im.group(1)]
        elif item_buffer:
            item_buffer.append(line)

    if item_buffer:
        entry = parse_item('\n'.join(item_buffer), None)
        if entry:
            entries.append(entry)

    return entries


def parse_item(text, year):
    """Parse a single bibliography item into structured data."""
    text = ' '.join(text.split())  # normalize whitespace
    text = text.strip()
    if not text:
        return None

    # Remove comments
    text = re.sub(r'%.*', '', text)
    text = text.strip()
    if not text:
        return None

    # Extract note (oral/spotlight)
    note = None
    note_match = re.search(r'\(\\textbf\{(oral|spotlight)\}\)', text)
    if note_match:
        note = note_match.group(1)
        text = text[:note_match.start()] + text[note_match.end():]

    text = text.strip().rstrip('.')

    # Strategy: split on \textit{...} which contains the venue
    # Everything before is "authors. title. [In]"
    # The \textit{...} is the venue
    # Everything after is "location, year"

    venue_match = re.search(r'\\textit\{([^}]+)\}', text)
    if not venue_match:
        return None

    before_venue = text[:venue_match.start()].strip()
    venue_full = venue_match.group(1)
    after_venue = text[venue_match.end():].strip()

    # Clean "In " or ". In " from before_venue end
    before_venue = re.sub(r'\.?\s*In\s*$', '', before_venue).strip()
    # Also clean leading "In " from before venue if right before \textit
    before_venue = re.sub(r'\.\s*$', '', before_venue).strip()

    # Extract location and year from after_venue
    after_venue = after_venue.strip().lstrip(',').strip().rstrip('.')
    venue_location = ''
    detected_year = year

    # Pattern: "Location, Year" or just "Year"
    year_match = re.search(r',?\s*(\d{4})\s*$', after_venue)
    if year_match:
        detected_year = int(year_match.group(1))
        venue_location = after_venue[:year_match.start()].strip().rstrip(',').strip()
    elif year is None:
        # Try to find year in venue text
        ym2 = re.search(r'(\d{4})', venue_full)
        if ym2:
            detected_year = int(ym2.group(1))

    if detected_year is None:
        detected_year = year

    # Now split before_venue into authors and title
    # Key insight: author names end with a period, then title follows
    # Authors contain \textbf{Mengye Ren} and possibly *
    # Strategy: find the split point by looking for ". " followed by title text

    authors, title = split_authors_title(before_venue)

    # Parse author list
    author_list, equal_indices = parse_authors(authors)

    # Extract venue_short
    venue_short = extract_venue_short(venue_full)

    # Generate key
    if author_list:
        first_last = re.sub(r'[^a-z]', '', author_list[0].split()[-1].lower())
    else:
        first_last = 'unknown'
    title_words = re.sub(r'[^a-z\s]', '', title.lower()).split()
    title_word = title_words[0] if title_words else 'untitled'
    key = f"{first_last}{detected_year}{title_word}"

    return {
        'key': key,
        'title': title,
        'authors': author_list,
        'equal_contribution': equal_indices,
        'venue_full': venue_full,
        'venue_short': venue_short,
        'venue_location': venue_location,
        'year': detected_year,
        'note': note,
        'selected': False,
        'on_website': True,
        'webpage_path': None,
        'links': {},
    }


def split_authors_title(text):
    """Split 'Author1, Author2, and Author3. Title here' into (authors, title).

    Strategy: Find ". " that separates authors from title, but NOT ". " that's
    part of an author initial (e.g., "Richard S. Zemel", "Brenden M. Lake").
    An initial is a single uppercase letter followed by ". ".
    """
    text = text.strip()

    # Protect initials: temporarily replace "X. " (single letter + period + space)
    # with a placeholder so they don't look like sentence boundaries
    protected = re.sub(r'(?<=[A-Z])\.\s+', '@@DOT@@', text)

    # Now find the real ". " that separates authors from title
    # Find "Mengye Ren" position to anchor the author section
    ren_match = re.search(r'(?:Mengye Ren|\\textbf\{Mengye Ren\})', protected)

    if ren_match:
        after_ren = protected[ren_match.end():]
        # Look for ". " followed by uppercase (the title start)
        dot_match = re.search(r'\.\s+([A-Z])', after_ren)
        if dot_match:
            split_pos = ren_match.end() + dot_match.start() + 1
            authors = protected[:split_pos].replace('@@DOT@@', '. ').strip().rstrip('.')
            title = protected[split_pos:].replace('@@DOT@@', '. ').strip().lstrip('. ')
            return (authors, title)

        # Mengye Ren is the last author — everything after ". " is title
        # If no ". " found after Ren, they might be the last entry with no separator
        # In this case the text after Ren might just be empty or end
        authors = protected.replace('@@DOT@@', '. ').strip().rstrip('.')
        return (authors, '')

    # Fallback: split on first ". " followed by uppercase
    dot_match = re.search(r'\.\s+([A-Z])', protected)
    if dot_match:
        authors = protected[:dot_match.start()].replace('@@DOT@@', '. ').strip().rstrip('.')
        title = protected[dot_match.start() + 1:].replace('@@DOT@@', '. ').strip().lstrip('. ')
        return (authors, title)

    return (text, text)


def parse_authors(text):
    """Parse author string into list of names and equal contribution indices."""
    text = text.strip().rstrip('.')
    # Remove \textbf{} but keep content
    text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)

    # Split on " and " or ", and " — handle carefully
    # First replace ", and " with just ","
    text = re.sub(r',\s+and\s+', ', ', text)
    text = re.sub(r'\s+and\s+', ', ', text)

    # Split on ", "
    parts = [p.strip() for p in text.split(',')]

    authors = []
    equal_indices = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        has_star = '*' in part
        part = part.replace('*', '').strip()
        if part:
            if has_star:
                equal_indices.append(len(authors))
            authors.append(part)

    return authors, equal_indices


def extract_venue_short(venue_full):
    """Extract short venue name."""
    # Check for parenthetical abbreviation first
    paren_match = re.search(r'\(([A-Z][A-Za-z]+)\)', venue_full)

    abbrevs = [
        ('International Conference on Learning Representations', 'ICLR'),
        ('International Conference on Machine Learning', 'ICML'),
        ('Neural Information Processing Systems', 'NeurIPS'),
        ('NIPS', 'NIPS'),
        ('Conference on Computer Vision and Pattern Recognition', 'CVPR'),
        ('European Conference (ECCV)', 'ECCV'),
        ('European Conference', 'ECCV'),
        ('International Conference on Computer Vision (ICCV)', 'ICCV'),
        ('Conference on Robot Learning', 'CoRL'),
        ('Conference on Lifelong Learning Agents', 'CoLLAs'),
        ('Conference on Language Modeling', 'COLM'),
        ('Cognitive Science Society', 'CogSci'),
        ('International Conference on Robotics and Automation', 'ICRA'),
        ('International Conference on Intelligent Robots', 'IROS'),
        ('arXiv preprint', 'arXiv preprint'),
    ]
    for pattern, short in abbrevs:
        if pattern.lower() in venue_full.lower():
            return short
    if paren_match:
        return paren_match.group(1)
    # For workshop venues, keep as-is but shortened
    if 'Workshop' in venue_full or 'workshop' in venue_full:
        return venue_full
    return venue_full


def extract_patent_items(text):
    """Parse patent items from full CV enumerate block."""
    entries = []
    items = re.split(r'\\item\s*', text)
    for item in items:
        item = item.strip()
        if not item or item.startswith('%') or item.startswith('\\renewcommand'):
            continue
        entry = parse_single_patent(item)
        if entry:
            entries.append(entry)
    return entries


def extract_patent_items_short(text):
    """Parse short CV patent items, return list of author_short lists."""
    results = []
    items = re.split(r'\\item\s*', text)
    for item in items:
        item = item.strip()
        if not item or item.startswith('%'):
            continue
        # Clean markup
        clean = re.sub(r'\\textbf\{([^}]+)\}', r'\1', item)
        clean = re.sub(r'\\textit\{([^}]+)\}', r'\1', clean)
        # Authors are before first ". "
        parts = clean.split('. ')
        if parts:
            author_str = parts[0]
            author_str = re.sub(r',\s+and\s+', ', ', author_str)
            author_str = re.sub(r'\s+and\s+', ', ', author_str)
            authors = [a.strip() for a in author_str.split(',') if a.strip()]
            results.append(authors)
    return results


def parse_single_patent(text):
    """Parse a single patent entry from full CV."""
    text = text.strip()
    if not text:
        return None

    # Clean markup for parsing
    clean = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
    clean = re.sub(r'\\textit\{([^}]+)\}', r'\1', clean)

    # Extract patent number
    patent_match = re.search(r'(US\s+[\d,]+\s+B\d)', clean)
    patent_number = patent_match.group(1) if patent_match else ''

    # Extract year
    year_match = re.search(r',\s*(\d{4})\s*\.?\s*$', clean)
    year = int(year_match.group(1)) if year_match else None

    # Split on ". " to get authors and title
    parts = clean.split('. ')
    authors_str = parts[0] if parts else ''
    # Title is between authors and patent number
    rest = '. '.join(parts[1:]) if len(parts) > 1 else ''
    # Remove patent number, "U.S. Patent", year from rest
    title = re.sub(r'\s*US\s+[\d,]+\s+B\d.*$', '', rest).strip()
    title = re.sub(r',?\s*U\.?S\.?\s*Patent.*$', '', title).strip()
    title = title.rstrip(',').rstrip('.').strip()

    # Parse authors
    authors_str = re.sub(r',\s+and\s+', ', ', authors_str)
    authors_str = re.sub(r'\s+and\s+', ', ', authors_str)
    authors = [a.strip() for a in authors_str.split(',') if a.strip()]

    safe_num = re.sub(r'[\s,]', '', patent_number)
    key = f"patent_{safe_num}" if patent_number else f"patent_{year}"

    return {
        'key': key,
        'title': title,
        'authors': authors,
        'patent_number': patent_number,
        'year': year,
        'on_website': False,
        'authors_short': [],
    }


# ============================================================
# Parse research/index.md
# ============================================================

def parse_research_md(path):
    with open(path, 'r') as f:
        text = f.read()

    entries = []
    # Each paper starts with "* <span class='paper-title'>"
    blocks = re.split(r'\n\*\s+<span', text)

    for block in blocks[1:]:
        block = '<span' + block
        entry = parse_md_paper(block)
        if entry:
            entries.append(entry)

    return entries


def parse_md_paper(block):
    # Get first few lines (paper entry ends at next blank line or next *)
    lines = block.split('\n')
    # Collect lines until we hit an empty line after the links line
    paper_text = '\n'.join(lines)

    # Extract title - could be [Title](url) or just Title
    title_match = re.search(
        r"class='paper-title'>\[([^\]]+)\]\([^)]+\)\.</span>", paper_text)
    if not title_match:
        title_match = re.search(
            r"class='paper-title'>([^<]+?)\.</span>", paper_text)
    if not title_match:
        title_match = re.search(
            r"class='paper-title'>\[([^\]]+)\]", paper_text)
    if not title_match:
        return None

    title = title_match.group(1).strip()

    # Extract webpage_path from title link
    webpage_path = None
    path_match = re.search(
        r"class='paper-title'>\[[^\]]+\]\(([^)]+)\)", paper_text)
    if path_match:
        link = path_match.group(1)
        if not link.startswith('http'):
            webpage_path = link

    # Extract all [[type](url)] links
    links = {}
    for m in re.finditer(r'\[\[(\w[\w\s]*?)\]\(([^)]+)\)\]', paper_text):
        link_type = m.group(1).strip().lower().replace(' ', '_')
        url = m.group(2)
        if link_type == 'open_review':
            link_type = 'openreview'
        if link_type == 'slide':
            link_type = 'slides'
        if link_type == 'link':
            link_type = 'webpage'
        if link_type == 'website':
            link_type = 'webpage'
        if link_type == 'question_generation':
            link_type = 'code2'
        if link_type == 'results':
            link_type = 'results'
        links[link_type] = url

    return {
        'title': title,
        'links': links,
        'webpage_path': webpage_path,
    }


# ============================================================
# Merge
# ============================================================

def merge_entries(tex_categories, md_entries):
    """Match tex entries with md entries by title and merge links/webpage_path."""
    # Build lookup by normalized title
    md_lookup = {}
    for entry in md_entries:
        key = normalize_title(entry['title'])
        md_lookup[key] = entry

    matched = 0
    unmatched = []

    for cat_name, entries in tex_categories.items():
        for entry in entries:
            norm = normalize_title(entry['title'])
            # Exact match
            if norm in md_lookup:
                md = md_lookup[norm]
                entry['links'] = md['links']
                entry['webpage_path'] = md.get('webpage_path')
                matched += 1
                continue

            # Fuzzy match
            best_score = 0
            best_md = None
            best_key = None
            for md_key, md in md_lookup.items():
                score = similar(entry['title'], md['title'])
                if score > best_score:
                    best_score = score
                    best_md = md
                    best_key = md_key

            if best_score > 0.7:
                entry['links'] = best_md['links']
                entry['webpage_path'] = best_md.get('webpage_path')
                matched += 1
            else:
                unmatched.append(f"  [{cat_name}] {entry['title'][:60]}... (best: {best_score:.2f})")

    print(f"  Matched {matched} entries")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}):")
        for u in unmatched:
            print(u)

    return tex_categories


# ============================================================
# Output
# ============================================================

def to_yaml(categories):
    class CleanDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        if any(c in data for c in ':{}[],"\'&'):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    def none_representer(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:null', 'null')

    CleanDumper.add_representer(str, str_representer)
    CleanDumper.add_representer(type(None), none_representer)

    return yaml.dump(categories, Dumper=CleanDumper, default_flow_style=False,
                     allow_unicode=True, sort_keys=False, width=200)


def main():
    cv_dir = Path(__file__).parent.parent
    pubs_tex = cv_dir / 'sections' / 'pubs.tex'
    website_dir = Path.home() / 'code' / 'renmengye.github.io'
    research_md = website_dir / 'research' / 'index.md'

    print(f"Parsing {pubs_tex}...")
    tex_categories = parse_pubs_tex(str(pubs_tex))
    for cat, entries in tex_categories.items():
        print(f"  {cat}: {len(entries)} entries")

    md_entries = []
    if research_md.exists():
        print(f"\nParsing {research_md}...")
        md_entries = parse_research_md(str(research_md))
        print(f"  Found {len(md_entries)} papers on website")

    if md_entries:
        print("\nMerging links...")
        tex_categories = merge_entries(tex_categories, md_entries)

    output = cv_dir / 'publications.yaml'
    yaml_str = to_yaml(tex_categories)
    with open(output, 'w') as f:
        f.write(yaml_str)

    print(f"\nWrote {output}")
    print(f"Total entries: {sum(len(v) for v in tex_categories.values())}")


if __name__ == '__main__':
    main()
