# CV — Mengye Ren

LaTeX CV with publications managed via a single YAML file.

## Quick start

```bash
make cv      # build full CV (auto-generates pubs.tex from YAML first)
make short   # build short CV
make all     # build both
```

Requires: Python 3 with `pyyaml`, LaTeX with `latexmk`.

## Adding a paper

1. Edit `publications.yaml` — copy an existing entry and insert by arxiv date (newest first)
2. Run `make cv` to verify the PDF
3. Commit and push

### Entry format

```yaml
- key: lastname2026firstword       # unique key
  type: conference                  # conference | workshop | preprint | thesis | patent
  title: Your paper title
  authors:
  - First Author
  - Mengye Ren
  equal_contribution: []            # 0-based indices of authors with *
  venue_full: Proceedings of the Nth International Conference on X (CONF)
  venue_short: CONF
  venue_location: "City, Country"
  year: 2026
  note: null                        # oral | spotlight | null
  selected: false                   # true to include in short CV selected pubs
  on_website: true                  # true to show on mengyeren.com
  webpage_path: null                # relative path to paper page on website (if any)
  links:
    arxiv: "https://arxiv.org/abs/XXXX.XXXXX"
    code: null
    webpage: null
  type: conference
```

## How it works

- `publications.yaml` — single source of truth (flat list, sorted by arxiv date)
- `scripts/generate_pubs.py` — reads YAML, writes `sections/pubs.tex` and `sections/select_pubs.tex`
- Numbering is reverse chronological: C1 = oldest paper, CN = newest (etaremune)
- The website repo ([renmengye.github.io](https://github.com/renmengye/renmengye.github.io)) includes this repo as a submodule and generates its publications page from the same YAML

## Files

| File | Description |
|------|-------------|
| `publications.yaml` | All publications (single source of truth) |
| `cv_mengye_ren.tex` | Full CV entry point |
| `cv_mengye_ren_short.tex` | Short CV entry point |
| `sections/` | Modular LaTeX sections (pubs.tex is auto-generated) |
| `scripts/generate_pubs.py` | YAML → LaTeX generator |
| `res.cls` | Custom document class |
| `macro.sty` | Custom macros |
