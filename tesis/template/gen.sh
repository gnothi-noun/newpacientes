md2latex -bibfile "iaa.bib" -citations -inlinemath -nopreamble  -o iaa.tex -tablecaptions 2026-paper-draft.md
sed -i 's/\\begin{table}\[h!\]/\\begin{table*}[t!]/g; s/\\end{table}/\\end{table*}/g' iaa.tex
