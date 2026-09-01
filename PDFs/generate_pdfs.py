"""
generate_pdfs.py
Converts Complete_Project_Report.md and Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.md
to beautifully styled PDFs with rendered Mermaid flowcharts, proper headings, tables, and diagrams.

Uses: markdown2, playwright (headless Chromium)
"""

import asyncio
import os
import re
import markdown2
from playwright.async_api import async_playwright

BASE = r"c:\Users\nikhi\Videos\Healthcare Intelligence & Patient Adherence Platform"

# ──────────────────────────────────────────────────────────────────────────────
# HTML shell template
# ──────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  /* ── Page setup ── */
  @page {{ size: A4; margin: 22mm 20mm 22mm 20mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a2e;
    background: #fff;
  }}

  /* ── Cover page ── */
  .cover {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    text-align: center;
    padding: 40px;
    background: linear-gradient(135deg, #0f3460 0%, #16213e 60%, #0f3460 100%);
    color: #fff;
    page-break-after: always;
  }}
  .cover-badge {{
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 30px;
    padding: 6px 20px;
    font-size: 9pt;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 24px;
    color: #e0e0ff;
  }}
  .cover h1 {{
    font-size: 26pt;
    font-weight: 800;
    line-height: 1.2;
    max-width: 700px;
    margin-bottom: 20px;
    color: #fff;
    border: none;
  }}
  .cover h2 {{
    font-size: 14pt;
    font-weight: 400;
    color: #a8c5ff;
    margin-bottom: 40px;
    border: none;
  }}
  .cover-divider {{
    width: 80px;
    height: 3px;
    background: #4fc3f7;
    border-radius: 2px;
    margin: 24px auto;
  }}
  .cover-meta {{
    font-size: 10pt;
    color: #b0c4ff;
    line-height: 2;
  }}

  /* ── TOC ── */
  .toc {{
    page-break-after: always;
    padding: 20px 0;
  }}
  .toc h2 {{
    font-size: 16pt;
    color: #0f3460;
    border-bottom: 3px solid #4fc3f7;
    padding-bottom: 8px;
    margin-bottom: 18px;
  }}
  .toc-item {{ margin: 6px 0; font-size: 10pt; }}
  .toc-item a {{ color: #0f3460; text-decoration: none; }}
  .toc-sub {{ margin-left: 20px; color: #555; font-size: 9.5pt; }}

  /* ── Section headings ── */
  h1 {{
    font-size: 18pt; font-weight: 800; color: #0f3460;
    border-bottom: 3px solid #4fc3f7;
    padding-bottom: 6px; margin: 32px 0 16px;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 14pt; font-weight: 700; color: #16213e;
    border-left: 4px solid #4fc3f7;
    padding-left: 10px; margin: 24px 0 12px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 11.5pt; font-weight: 600; color: #0f3460;
    margin: 18px 0 8px;
    page-break-after: avoid;
  }}
  h4 {{
    font-size: 10.5pt; font-weight: 600; color: #333;
    margin: 14px 0 6px;
  }}

  /* ── Body text ── */
  p {{ margin-bottom: 10px; text-align: justify; }}
  ul, ol {{ margin: 8px 0 12px 24px; }}
  li {{ margin-bottom: 4px; }}
  strong {{ color: #0f3460; }}

  /* ── Inline code & blocks ── */
  code {{
    background: #f0f4ff; color: #0f3460;
    padding: 2px 5px; border-radius: 3px;
    font-family: 'Courier New', monospace; font-size: 9.5pt;
  }}
  pre {{
    background: #f4f6fb;
    border: 1px solid #dde3f0;
    border-left: 4px solid #4fc3f7;
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 9pt;
    overflow-x: auto;
    margin: 14px 0;
    page-break-inside: avoid;
  }}
  pre code {{ background: none; padding: 0; color: #1a1a2e; }}

  /* ── Tables ── */
  table {{
    width: 100%; border-collapse: collapse;
    margin: 16px 0; font-size: 9.5pt;
    page-break-inside: avoid;
  }}
  thead tr {{ background: #0f3460; color: #fff; }}
  thead th {{
    padding: 9px 12px; text-align: left;
    font-weight: 600; border: 1px solid #0f3460;
  }}
  tbody tr:nth-child(even) {{ background: #f0f4ff; }}
  tbody tr:hover {{ background: #dde9ff; }}
  td {{
    padding: 8px 12px;
    border: 1px solid #c8d4e8;
    vertical-align: top;
  }}
  caption {{
    font-size: 9pt; font-weight: 600; color: #555;
    caption-side: bottom; padding-top: 6px; text-align: center;
  }}

  /* ── Mermaid diagrams ── */
  .mermaid {{
    background: #f8f9ff;
    border: 1px solid #c8d4e8;
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
    text-align: center;
    page-break-inside: avoid;
  }}
  .diagram-caption {{
    text-align: center; font-size: 9pt;
    color: #555; font-style: italic; margin-top: -10px; margin-bottom: 20px;
  }}

  /* ── Blockquotes / alerts ── */
  blockquote {{
    border-left: 4px solid #4fc3f7;
    background: #f0f8ff;
    padding: 12px 16px;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
    font-size: 9.5pt;
    color: #1a1a2e;
    page-break-inside: avoid;
  }}
  blockquote strong {{ color: #0f3460; }}

  /* ── Horizontal rule ── */
  hr {{
    border: none; border-top: 2px solid #dde3f0;
    margin: 28px 0;
  }}

  /* ── Abstract / keywords box ── */
  .abstract-box {{
    border: 1px solid #c8d4e8;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 20px 0;
    background: #fafbff;
    page-break-inside: avoid;
  }}
  .abstract-box strong {{ font-size: 10pt; text-transform: uppercase; letter-spacing: 1px; }}

  /* ── Footer ── */
  @media print {{
    @page {{ @bottom-right {{ content: counter(page); font-size: 9pt; color: #888; }} }}
  }}
</style>
</head>
<body>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      primaryColor: '#0f3460',
      primaryTextColor: '#fff',
      primaryBorderColor: '#4fc3f7',
      lineColor: '#4fc3f7',
      secondaryColor: '#f0f4ff',
      tertiaryColor: '#fff'
    }},
    flowchart: {{ useMaxWidth: true, htmlLabels: true }},
    securityLevel: 'loose'
  }});
</script>
{body}
</body>
</html>"""


def md_to_html_body(md_content: str) -> str:
    """Convert Markdown to HTML, preserving mermaid blocks as <div class='mermaid'>."""

    # 1) Extract mermaid blocks before markdown processing
    mermaid_placeholder = "MERMAID_BLOCK_{}"
    mermaid_blocks = {}
    
    def save_mermaid(m):
        key = mermaid_placeholder.format(len(mermaid_blocks))
        mermaid_blocks[key] = m.group(1).strip()
        return f"\n\n{key}\n\n"

    md_content = re.sub(r'```mermaid\n(.*?)\n```', save_mermaid, md_content, flags=re.DOTALL)

    # 2) Convert markdown to HTML
    html = markdown2.markdown(
        md_content,
        extras=["tables", "fenced-code-blocks", "header-ids", "strike",
                "task_list", "break-on-newline", "cuddled-lists"]
    )

    # 3) Restore mermaid blocks as proper divs
    for key, diagram in mermaid_blocks.items():
        escaped = diagram.replace('"', '&quot;')
        html = html.replace(
            f"<p>{key}</p>",
            f'<div class="mermaid">{diagram}</div>'
        )
        # fallback if wrapped differently
        html = html.replace(key, f'<div class="mermaid">{diagram}</div>')

    # 4) Wrap italic caption lines (*Fig. X...* or *Note:...*) in diagram-caption
    html = re.sub(
        r'<p><em>(Fig\..*?|Note:.*?)</em></p>',
        r'<p class="diagram-caption"><em>\1</em></p>',
        html
    )

    # 5) Detect abstract/keyword paragraphs and wrap
    html = re.sub(
        r'<p>(<strong>Abstract—.*?</strong>.*?)</p>',
        r'<div class="abstract-box"><p>\1</p></div>',
        html, flags=re.DOTALL
    )
    html = re.sub(
        r'<p>(<strong>Keywords—.*?</strong>.*?)</p>',
        r'<div class="abstract-box"><p>\1</p></div>',
        html, flags=re.DOTALL
    )

    return html


def build_cover(title: str, subtitle: str, meta_lines: list[str]) -> str:
    meta_html = "".join(f"<div>{l}</div>" for l in meta_lines)
    return f"""
<div class="cover">
  <div class="cover-badge">Technical Project Report · 2026</div>
  <h1>{title}</h1>
  <h2>{subtitle}</h2>
  <div class="cover-divider"></div>
  <div class="cover-meta">{meta_html}</div>
</div>"""


async def generate_pdf(html_content: str, output_path: str):
    """Render HTML with Mermaid to PDF via Playwright headless Chromium."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        # Wait for Mermaid to finish rendering
        await page.wait_for_timeout(4000)
        await page.pdf(
            path=output_path,
            format="A4",
            margin={"top": "22mm", "bottom": "22mm", "left": "20mm", "right": "20mm"},
            print_background=True,
            display_header_footer=True,
            footer_template='<div style="font-size:8pt;color:#888;width:100%;text-align:right;padding-right:20mm;"><span class="pageNumber"></span></div>',
            header_template='<div></div>'
        )
        await browser.close()
        print(f"[OK] PDF saved: {output_path}")


# ──────────────────────────────────────────────────────────────────────────────
# REPORT 1 – Complete Beginner Project Report
# ──────────────────────────────────────────────────────────────────────────────
async def build_project_report():
    md_path = os.path.join(BASE, "Complete_Project_Report.md")
    out_path = os.path.join(BASE, "Complete_Project_Report.pdf")

    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    body = md_to_html_body(raw)

    cover = build_cover(
        "Healthcare Medication Adherence Analytics,<br>Knowledge Base (RAG) &amp; Agentic AI Orchestrator",
        "Complete Project Documentation Report",
        [
            "Beginner-Friendly Edition",
            "Healthcare Intelligence &amp; Patient Adherence Platform",
            "September 2026",
            "⚠️  Synthetic / Portfolio Data — Not a Clinical System",
        ]
    )

    html = HTML_TEMPLATE.format(title="Complete Project Report", body=cover + body)
    await generate_pdf(html, out_path)


# ──────────────────────────────────────────────────────────────────────────────
# REPORT 2 – IEEE Academic Paper
# ──────────────────────────────────────────────────────────────────────────────
async def build_ieee_paper():
    md_path = os.path.join(BASE, "Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.md")
    out_path = os.path.join(BASE, "Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.pdf")

    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    body = md_to_html_body(raw)

    cover = build_cover(
        "An AI-Driven Healthcare Medication Adherence Analytics and Knowledge Retrieval System Using RAG and Agentic AI",
        "IEEE-Style Academic Technical Paper (Single-Column)",
        [
            "[Author Name] · [Department] · [College/University]",
            "[City, Country] · [Email]",
            "September 2026",
            "⚠️  Prototype using Synthetic Data — Not for Clinical Use",
        ]
    )

    html = HTML_TEMPLATE.format(title="IEEE Paper", body=cover + body)
    await generate_pdf(html, out_path)


# ──────────────────────────────────────────────────────────────────────────────
async def main():
    print("Building Complete Project Report PDF...")
    await build_project_report()

    print("Building IEEE Academic Paper PDF...")
    await build_ieee_paper()

    print("\n[DONE] Both PDFs generated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
