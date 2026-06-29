#!/usr/bin/env bash
# Build completo de la tesis:
#   1) tesis.md  --(md2latex)-->  cuerpo.tex     (fragmento, -nopreamble)
#   2) documento.tex --(latexmk/biber)--> documento.pdf
#
# Requisitos:
#   - md2latex v0.1.4 (imágenes + raw LaTeX passthrough; NO @latest = v0.1.3):
#       go install github.com/soypat/goldmark-latex/cmd/md2latex@v0.1.4
#   - MiKTeX (pdflatex + biber + latexmk). Si no está, se genera el .tex igual
#     y se omite el PDF.
#
# Uso:  bash build.sh   (desde Git Bash)
set -euo pipefail
cd "$(dirname "$0")"

# ----------------------------------------------------------------------
# md2latex en el PATH
# ----------------------------------------------------------------------
if command -v go >/dev/null 2>&1; then
  PATH="$PATH:$(go env GOPATH)/bin"
fi
if ! command -v md2latex >/dev/null 2>&1; then
  echo "ERROR: no se encontró 'md2latex'. Instalalo con:" >&2
  echo "  go install github.com/soypat/goldmark-latex/cmd/md2latex@v0.1.4" >&2
  exit 1
fi

# ----------------------------------------------------------------------
# 1) Markdown -> cuerpo.tex
#    -citations  : [@clave] / [@a; @b]  ->  \cite{clave} / \cite{a,b}
#    -inlinemath : deja pasar  $...$
#    -nopreamble : solo el cuerpo (el preámbulo vive en documento.tex)
#    -tablecaptions : caption ': texto' debajo de cada tabla
#    -unsafe     : habilita links y bloques de LaTeX crudo  ```{=latex} ... ```
#                  (passthrough; sin esto se descartan). Útil p. ej. para \ref
#                  reales. Las imágenes ![cap](ruta) ya generan \begin{figure}.
# ----------------------------------------------------------------------
md2latex -citations -inlinemath -nopreamble -tablecaptions -unsafe -o cuerpo.tex tesis.md
echo "OK -> cuerpo.tex"

# ----------------------------------------------------------------------
# MiKTeX (pdflatex/biber/latexmk) en el PATH si no está ya.
# Tras instalar MiKTeX puede hacer falta reabrir la terminal para que el
# PATH se actualice; mientras tanto lo agregamos desde su ubicación típica.
# ----------------------------------------------------------------------
if ! command -v latexmk >/dev/null 2>&1 && ! command -v pdflatex >/dev/null 2>&1; then
  for d in "$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64" \
           "/c/Program Files/MiKTeX/miktex/bin/x64"; do
    if [ -d "$d" ]; then PATH="$PATH:$d"; break; fi
  done
fi

# ----------------------------------------------------------------------
# 2) documento.tex -> documento.pdf
#    latexmk detecta biblatex/biber por el .bcf y hace las pasadas solo.
# ----------------------------------------------------------------------
if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error documento.tex
  echo "OK -> documento.pdf"
elif command -v pdflatex >/dev/null 2>&1; then
  # Sin latexmk: secuencia manual para biblatex + biber.
  pdflatex -interaction=nonstopmode -halt-on-error documento.tex
  biber documento
  pdflatex -interaction=nonstopmode -halt-on-error documento.tex
  pdflatex -interaction=nonstopmode -halt-on-error documento.tex
  echo "OK -> documento.pdf"
else
  echo "AVISO: no se encontró latexmk/pdflatex (MiKTeX). Se generó cuerpo.tex" >&2
  echo "       pero NO el PDF. Reabrí la terminal o instalá MiKTeX." >&2
fi
