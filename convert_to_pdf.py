#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para convertir INFORME_TECNICO.md a PDF
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path

def convert_markdown_to_pdf(md_file, pdf_file):
    """Convierte un archivo Markdown a PDF."""

    # Leer el archivo markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convertir Markdown a HTML
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc'
        ]
    )

    # Crear HTML completo con estilos
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>INFORME TÉCNICO - VITAICARE</title>
        <style>
            @page {{
                size: A4;
                margin: 2.5cm 2cm 2cm 2cm;
                @top-center {{
                    content: "VITAICARE - Informe Técnico";
                    font-size: 9pt;
                    color: #666;
                }}
                @bottom-right {{
                    content: "Página " counter(page) " de " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }}
            }}

            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 0;
            }}

            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 30px;
                font-size: 28pt;
                page-break-after: avoid;
            }}

            h2 {{
                color: #34495e;
                border-bottom: 2px solid #95a5a6;
                padding-bottom: 5px;
                margin-top: 25px;
                font-size: 20pt;
                page-break-after: avoid;
            }}

            h3 {{
                color: #2c3e50;
                margin-top: 20px;
                font-size: 16pt;
                page-break-after: avoid;
            }}

            h4 {{
                color: #34495e;
                margin-top: 15px;
                font-size: 14pt;
                page-break-after: avoid;
            }}

            p {{
                text-align: justify;
                margin: 10px 0;
            }}

            code {{
                background-color: #f4f4f4;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 2px 5px;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }}

            pre {{
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                overflow-x: auto;
                page-break-inside: avoid;
            }}

            pre code {{
                background-color: transparent;
                border: none;
                padding: 0;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
                page-break-inside: avoid;
                font-size: 10pt;
            }}

            th {{
                background-color: #3498db;
                color: white;
                padding: 10px;
                text-align: left;
                font-weight: bold;
            }}

            td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}

            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}

            blockquote {{
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-left: 0;
                color: #555;
                font-style: italic;
            }}

            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}

            li {{
                margin: 5px 0;
            }}

            strong {{
                color: #2c3e50;
            }}

            .page-break {{
                page-break-before: always;
            }}

            hr {{
                border: none;
                border-top: 2px solid #3498db;
                margin: 30px 0;
            }}

            /* Estilos para checkmarks */
            li:has(input[type="checkbox"]) {{
                list-style: none;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Convertir HTML a PDF
    print(f"Convirtiendo {md_file} a PDF...")
    HTML(string=full_html).write_pdf(pdf_file)
    print(f"✓ PDF generado exitosamente: {pdf_file}")

    # Obtener tamaño del archivo
    size_mb = Path(pdf_file).stat().st_size / (1024 * 1024)
    print(f"  Tamaño: {size_mb:.2f} MB")

if __name__ == "__main__":
    md_file = "INFORME_TECNICO.md"
    pdf_file = "INFORME_TECNICO.pdf"

    convert_markdown_to_pdf(md_file, pdf_file)
