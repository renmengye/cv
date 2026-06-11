LATEXMK=latexmk
PYTHON=python3

pubs:
	$(PYTHON) scripts/generate_pubs.py

cv: pubs
	$(LATEXMK) cv_mengye_ren.tex -pdf

short: pubs
	$(LATEXMK) cv_mengye_ren_short.tex -pdf

ami: pubs
	$(LATEXMK) cv_mengye_ren_ami_2025_2026.tex -pdf

all: cv short
