#!/usr/bin/env python3
"""Restructure publications.yaml from category-grouped to flat time-ordered list.
Also add missing entries (2 preprints + PhD thesis)."""

import yaml
from pathlib import Path

CV_DIR = Path(__file__).parent.parent

with open(CV_DIR / 'publications.yaml') as f:
    data = yaml.safe_load(f)

# Flatten: add 'type' field to each entry
flat = []
for cat in ['conference', 'workshop', 'preprint', 'patent']:
    for entry in data.get(cat, []):
        entry['type'] = cat
        flat.append(entry)

# Add missing entries
flat.append({
    'key': 'wang2026maego',
    'type': 'preprint',
    'title': 'MA-EgoQA: Question answering over egocentric videos from multiple embodied agents',
    'authors': ['Kangsan Kim', 'Yanlai Yang', 'Suji Kim', 'Woongyeong Yeo', 'Youngwan Lee', 'Mengye Ren', 'Sung Ju Hwang'],
    'equal_contribution': [],
    'venue_full': 'arXiv preprint arXiv:2603.09827',
    'venue_short': 'arXiv preprint',
    'venue_location': '',
    'year': 2026,
    'note': None,
    'selected': False,
    'on_website': True,
    'webpage_path': None,
    'links': {'arxiv': 'https://arxiv.org/abs/2603.09827'},
})

flat.append({
    'key': 'wang2026temporal_preprint',
    'type': 'preprint',
    'title': 'Temporal straightening for latent planning',
    'authors': ['Ying Wang', 'Oumayma Bounou', 'Gaoyue Zhou', 'Randall Balestriero', 'Tim G. J. Rudner', 'Yann LeCun', 'Mengye Ren'],
    'equal_contribution': [],
    'venue_full': 'arXiv preprint arXiv:2603.12231',
    'venue_short': 'arXiv preprint',
    'venue_location': '',
    'year': 2026,
    'note': None,
    'selected': False,
    'on_website': True,
    'webpage_path': None,
    'links': {
        'webpage': 'https://agenticlearning.ai/temporal-straightening/',
        'arxiv': 'https://arxiv.org/abs/2603.12231',
    },
})

flat.append({
    'key': 'ren2022thesis',
    'type': 'thesis',
    'title': 'Open-world machine learning with limited labeled data',
    'authors': ['Mengye Ren'],
    'equal_contribution': [],
    'venue_full': 'Ph.D. Thesis, University of Toronto',
    'venue_short': 'Ph.D. Thesis, University of Toronto',
    'venue_location': '',
    'year': 2022,
    'note': None,
    'selected': False,
    'on_website': True,
    'webpage_path': None,
    'links': {
        'pdf': '2022/phd-thesis/Ren_Mengye_202206_PhD_thesis.pdf',
    },
})

# Sort by year descending, then by type priority within same year
type_order = {'conference': 0, 'workshop': 1, 'preprint': 2, 'thesis': 3, 'patent': 4}
flat.sort(key=lambda e: (-e.get('year', 0), type_order.get(e.get('type', ''), 99)))

# Write
output = {'publications': flat}

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

yaml_str = yaml.dump(output, Dumper=CleanDumper, default_flow_style=False,
                     allow_unicode=True, sort_keys=False, width=200)

with open(CV_DIR / 'publications.yaml', 'w') as f:
    f.write(yaml_str)

# Stats
from collections import Counter
counts = Counter(e['type'] for e in flat)
print(f"Restructured to flat list: {len(flat)} entries")
for t, c in sorted(counts.items()):
    print(f"  {t}: {c}")
