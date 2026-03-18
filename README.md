# CV — Mengye Ren

LaTeX CV with publications and talks managed via YAML files.

## Quick start

```bash
make cv      # build full CV (auto-generates from YAML first)
make short   # build short CV
make all     # build both
```

Requires: Python 3 with `pyyaml`, LaTeX with `latexmk`.

## Adding a paper

1. Edit `publications.yaml` — copy an existing entry and insert by arxiv date (newest first)
2. Run `make cv` to verify the PDF
3. Commit and push — the website auto-rebuilds and deploys

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
```

## Adding a talk

1. Edit `talks.yaml` — copy an existing entry and insert by date (newest first)
2. Run `make cv` to verify the PDF
3. Commit and push — the website auto-rebuilds and deploys

### Entry format

```yaml
- title: Your talk title
  venue: Institution or Conference Name
  location: "City, State, Country"
  date: '2026-03-15'               # YYYY-MM-DD (use DD=01 if day unknown)
  links:
    slides: "https://drive.google.com/..."
    video: "https://youtu.be/..."
  selected: false                   # true to include in short CV selected talks
  on_website: true                  # true to show on mengyeren.com
  on_cv: true                      # set false for website-only entries (e.g., consolidated job talk)
```

## How it works

- `publications.yaml` — all publications, sorted by arxiv date descending
- `talks.yaml` — all talks, sorted by date descending
- `scripts/generate_pubs.py` — reads both YAML files, generates LaTeX for pubs, talks, and selected versions
- Numbering is reverse chronological: C1 = oldest, CN = newest (etaremune)
- Pushing YAML changes auto-triggers the website rebuild via GitHub Actions

## Files

| File | Description |
|------|-------------|
| `publications.yaml` | All publications (single source of truth) |
| `talks.yaml` | All talks (single source of truth) |
| `cv_mengye_ren.tex` | Full CV entry point |
| `cv_mengye_ren_short.tex` | Short CV entry point |
| `sections/` | Modular LaTeX sections (pubs.tex, talks.tex are auto-generated) |
| `scripts/generate_pubs.py` | YAML → LaTeX generator (pubs + talks) |
| `.github/workflows/trigger-website.yml` | Triggers website rebuild on YAML changes |
| `res.cls` | Custom document class |
| `macro.sty` | Custom macros |
