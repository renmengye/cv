#!/usr/bin/env python3
"""
Output publications.yaml as a RIS file for import into PubMed / NIH My
Bibliography (SciENcv).

RIS type tags used:
    JOUR   - Journal article
    CONF   - Conference proceedings
    CPAPER - Conference paper (peer-reviewed)
    GEN    - Generic (used for arXiv preprints / workshops)
    THES   - Thesis

Usage:
    python3 generate_ris.py --publications ~/code/cv/publications.yaml \\
        --output ~/publications.ris \\
        [--exclude-listed ~/pubmed_current.txt]   # optional: skip papers
                                                  # already in your MyBib
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Type mapping (publications.yaml `type` → RIS TY tag)
# ---------------------------------------------------------------------------
TYPE_MAP = {
    "journal":     "JOUR",
    "conference":  "CPAPER",     # Conference Paper (individual paper in proceedings)
    "workshop":    "CPAPER",
    "preprint":    "GEN",
    "thesis":      "THES",
    "book":        "BOOK",
    "chapter":     "CHAP",
    "poster":      "CPAPER",
    "arxiv":       "GEN",
}


# ---------------------------------------------------------------------------
# Name handling
# ---------------------------------------------------------------------------
def format_author_ris(raw: str) -> str:
    """RIS wants 'Last, First Middle' or 'Last, F. M.'"""
    raw = raw.strip().rstrip(",")
    if "," in raw:
        return raw
    parts = raw.rsplit(" ", 1)
    if len(parts) == 1:
        return raw
    first, last = parts[0].strip(), parts[1].strip()
    return f"{last}, {first}"


def title_key(title: str) -> str:
    """Lowercased first ~40 non-alphanumeric-stripped chars for dedup."""
    t = re.sub(r"[^a-z0-9]", "", title.lower())
    return t[:40]


# ---------------------------------------------------------------------------
# Exclusion list parsing
# ---------------------------------------------------------------------------
def load_exclusion_keys(path: Path) -> set:
    """Read a plaintext file where each line contains a paper title (or the
    citation string as PubMed prints it). Match to publications.yaml via
    normalized-title-prefix keys."""
    keys = set()
    if not path or not path.exists():
        return keys
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Try to extract the title portion between the first ". " and the
        # next terminator (venue). Best-effort.
        m = re.search(r"\.\s*([^\.]{10,})\.", line)
        if m:
            keys.add(title_key(m.group(1).strip()))
        else:
            keys.add(title_key(line))
    return keys


# ---------------------------------------------------------------------------
# RIS writer
# ---------------------------------------------------------------------------
def format_ris(pub: dict) -> str:
    ty = TYPE_MAP.get(pub.get("type", "").lower(), "GEN")
    lines = [f"TY  - {ty}"]
    lines.append(f"TI  - {pub.get('title', '').strip()}")
    for a in pub.get("authors") or []:
        lines.append(f"AU  - {format_author_ris(a)}")
    year = pub.get("year")
    month = pub.get("month")
    if year:
        if month:
            lines.append(f"PY  - {year}")
            lines.append(f"DA  - {year}/{int(month):02d}")
        else:
            lines.append(f"PY  - {year}")
    venue_full = pub.get("venue_full") or ""
    venue_short = pub.get("venue_short") or ""
    # PubMed My Bibliography reads different RIS tags for different display
    # slots depending on record type (e.g., T2 works for JOUR but not for
    # meeting abstracts / CONF). Write the venue to multiple tags so
    # PubMed picks up whichever it prefers.
    short = venue_short or venue_full
    long_ = venue_full or venue_short
    if short:
        lines.append(f"T2  - {short}")           # Secondary title (journals)
        lines.append(f"JF  - {short}")           # Journal / venue full name (broadly-read)
        lines.append(f"JA  - {short}")           # Journal abbreviation
        lines.append(f"SO  - {short}")           # Source (used by some PubMed importers)
    if long_ and long_ != short:
        lines.append(f"BT  - {long_}")           # Book/proceedings title (used by CPAPER)
        lines.append(f"CN  - {long_}")           # Conference name (secondary — some parsers)
    loc = pub.get("venue_location") or ""
    if loc:
        lines.append(f"CY  - {loc}")
    # arXiv or DOI
    links = pub.get("links") or {}
    url = None
    if isinstance(links, dict):
        for k in ("arxiv", "pdf", "code", "openreview", "doi"):
            v = links.get(k)
            if v:
                url = v
                break
    if url:
        lines.append(f"UR  - {url}")
    key = pub.get("key")
    if key:
        lines.append(f"ID  - {key}")
    lines.append("ER  - ")
    lines.append("")  # blank separator between records
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--publications", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--exclude-listed", type=Path,
                   help="Plain text file of paper titles already in MyBib "
                        "(one citation per line)")
    p.add_argument("--min-year", type=int, default=None,
                   help="Only export papers with year >= min-year")
    args = p.parse_args()

    data = yaml.safe_load(args.publications.read_text())
    pubs = data.get("publications", data if isinstance(data, list) else [])

    exclusion_keys = load_exclusion_keys(args.exclude_listed) if args.exclude_listed else set()
    if exclusion_keys:
        print(f"[exclude] {len(exclusion_keys)} title keys loaded from {args.exclude_listed.name}")

    kept, skipped = [], []
    for pub in pubs:
        year = pub.get("year")
        if args.min_year and year and int(year) < args.min_year:
            skipped.append((pub, "before min_year"))
            continue
        tk = title_key(pub.get("title", ""))
        # Exact prefix match on either side (yaml key is 40 chars; user key
        # can be shorter, so check both directions).
        matched = any(tk.startswith(k) or k.startswith(tk[:20])
                      for k in exclusion_keys) if exclusion_keys else False
        if matched:
            skipped.append((pub, "already in MyBib"))
            continue
        kept.append(pub)

    # PubMed's RIS parser rejects the whole file unless the very first line
    # is a `TY  -` tag — no comment header, no BOM, no leading whitespace.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for pub in kept:
            f.write(format_ris(pub))

    print(f"[output] wrote {len(kept)} RIS records to {args.output}")
    if skipped:
        print(f"[skipped] {len(skipped)}:")
        for pub, reason in skipped[:15]:
            title = pub.get("title", "")[:60]
            print(f"  ({reason:22s}) {pub.get('year','?')}  {title}")
        if len(skipped) > 15:
            print(f"  ... {len(skipped) - 15} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
