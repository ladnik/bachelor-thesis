# should only be the tex root file
TEXS := presentation.tex

LATEXMKFLAGS+=-pdf -halt-on-error -interaction=nonstopmode

.PHONY: $(TEXS) clean distclean

$(TEXS:.tex=.pdf): $(TEXS)
	TEXINPUTS=./tumlatex//: latexmk $(LATEXMKFLAGS) $<
	
clean::
	rm -f *.nav
	rm -f *.snm
	rm -f *.vrb
	rm -f *.fls
	latexmk -c

distclean:: clean
	rm -f $(TEXS:.tex=.pdf)

live:
	TEXINPUTS=./tumlatex//: latexmk $(LATEXMKFLAGS) ./$(TEXS) -pvc