TEXS := $(wildcard *.tex)
BIBS := $(wildcard *.bib)

.PHONY: all clean distclean

thesis.pdf: thesis.tex settings.tex literature.bib
	latexmk -pdf -halt-on-error -interaction=nonstopmode -synctex=1 $<
	
# compile thesis
all: thesis.pdf

# clean auxiliary files
clean:
	rm -f *.aux *.log *.out *.toc *.nav *.snm *.vrb *.synctex.gz *.fls *.fdb_latexmk *.bak* *.tmp

# clean all output files
distclean: clean
	rm -f $(TEXS:.tex=.pdf)
