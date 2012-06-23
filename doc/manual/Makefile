#
# Makefile for fits viewer manual
#
# Eric Jeschke  2012.01.25   (eric@naoj.org)
#

DOC	= manual

all:	pdf

pdf:	$(DOC).pdf
ps:	$(DOC).ps
dvi:	$(DOC).dvi

# $(DOC).pdf:	$(DOC).ps
# 	ps2pdf $(DOC).ps $(DOC).pdf 
$(DOC).pdf:	$(DOC).tex
	#pdflatex $(DOC).tex
	xelatex $(DOC).tex

$(DOC).ps:	$(DOC).dvi
	dvi2ps -c $(DOC).ps $(DOC).dvi 

$(DOC).dvi:	$(DOC).tex
	latex $(DOC)
	bibtex $(DOC)
	latex $(DOC)
	latex $(DOC)

