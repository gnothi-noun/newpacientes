#!/usr/bin/env bash
# Genera el cuerpo LaTeX de la tesis a partir del fuente Markdown (tesis.md)
# usando md2latex (github.com/soypat/goldmark-latex).
#
# Requisitos:
#   - Go instalado y  go install github.com/soypat/goldmark-latex/cmd/md2latex@latest
#   - El binario queda en  $(go env GOPATH)/bin  (p. ej. C:\Users\Ro\go\bin)
#
# Uso:  bash build.sh   (desde Git Bash)
#
# Decisiones (ver claudio-querido-quiero-preparar-binary-prism.md):
#   -citations  ......  convierte [@clave] / [@a; @b]  ->  \cite{clave} / \cite{a,b}
#   -inlinemath .....   deja pasar  $...$  (SpO$_2$, $\sim$520 MB, etc.)
#   -nopreamble .....   emite solo el cuerpo; el preambulo vive en documento.tex
#   -tablecaptions ..   habilita el caption  ': texto'  bajo cada tabla
#   SIN -bibfile  ...   asi md2latex NO agrega \bibliographystyle/\bibliography;
#                       la bibliografia la maneja biblatex en documento.tex.
set -euo pipefail
cd "$(dirname "$0")"

# Asegura que el binario de Go este en el PATH (no rompe si ya estaba).
if command -v go >/dev/null 2>&1; then
  PATH="$PATH:$(go env GOPATH)/bin"
fi

if ! command -v md2latex >/dev/null 2>&1; then
  echo "ERROR: no se encontro 'md2latex'. Instalalo con:" >&2
  echo "  go install github.com/soypat/goldmark-latex/cmd/md2latex@latest" >&2
  exit 1
fi

md2latex -citations -inlinemath -nopreamble -tablecaptions -o cuerpo.tex tesis.md

echo "OK -> cuerpo.tex  (incluido por documento.tex)"
