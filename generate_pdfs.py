"""
generate_pdfs.py  –  Playwright-based PDF generator with live Mermaid.js rendering
Generates:
  1. Complete_Project_Report.pdf            (Beginner project report)
  2. Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.pdf  (IEEE paper)
  3. Interview_QA_Guide.pdf                (Interview Q&A guide)
"""

import asyncio
import os
import re
import markdown2
from playwright.async_api import async_playwright

BASE = r"c:\Users\nikhi\Videos\Healthcare Intelligence & Patient Adherence Platform"

# ──────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  @page {{ size: A4; margin: 22mm 20mm 22mm 20mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1a1a2e;
    background: #fff;
  }}

  /* ── Cover ── */
  .cover {{
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    min-height: 100vh; text-align: center; padding: 40px;
    background: {cover_bg};
    color: #fff; page-break-after: always;
  }}
  .cover-badge {{
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 30px; padding: 6px 20px;
    font-size: 9pt; letter-spacing: 2px;
    text-transform: uppercase; margin-bottom: 24px; color: #e0e0ff;
  }}
  .cover h1 {{
    font-size: 24pt; font-weight: 800; line-height: 1.25;
    max-width: 700px; margin-bottom: 18px; color: #fff; border: none;
  }}
  .cover h2 {{ font-size: 13pt; font-weight: 400; color: #a8c5ff; margin-bottom: 36px; border: none; }}
  .cover-divider {{ width: 80px; height: 3px; background: {accent}; border-radius: 2px; margin: 20px auto; }}
  .cover-meta {{ font-size: 10pt; color: #b0c4ff; line-height: 2.2; }}

  /* ── Headings ── */
  h1 {{
    font-size: 17pt; font-weight: 800; color: {h1_color};
    border-bottom: 3px solid {accent};
    padding-bottom: 6px; margin: 30px 0 14px;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 13pt; font-weight: 700; color: {h2_color};
    border-left: 4px solid {accent}; padding-left: 10px;
    margin: 22px 0 10px; page-break-after: avoid;
  }}
  h3 {{
    font-size: 11pt; font-weight: 600; color: {h3_color};
    margin: 16px 0 7px; page-break-after: avoid;
  }}
  h4 {{ font-size: 10.5pt; font-weight: 600; color: #444; margin: 12px 0 5px; }}

  /* ── Q&A specific ── */
  .qa-question {{
    background: {qa_bg};
    border-left: 5px solid {accent};
    border-radius: 0 8px 8px 0;
    padding: 12px 16px; margin: 22px 0 6px;
    font-weight: 700; font-size: 11pt; color: {h1_color};
    page-break-after: avoid;
  }}
  .qa-crossq {{
    background: #fff8f0;
    border-left: 5px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px; margin: 18px 0 5px;
    font-weight: 600; font-size: 10.5pt; color: #92400e;
    page-break-after: avoid;
  }}
  .qa-answer {{
    padding: 0 0 0 6px; margin-bottom: 14px;
    border-left: 2px solid #e5e7eb;
    color: #374151;
  }}

  /* ── Body ── */
  p {{ margin-bottom: 9px; text-align: justify; }}
  ul, ol {{ margin: 7px 0 11px 24px; }}
  li {{ margin-bottom: 3px; }}
  strong {{ color: {h1_color}; }}

  /* ── Code ── */
  code {{
    background: #f0f4ff; color: #1e3a8a;
    padding: 2px 5px; border-radius: 3px;
    font-family: 'Courier New', monospace; font-size: 9pt;
  }}
  pre {{
    background: #f4f6fb; border: 1px solid #dde3f0;
    border-left: 4px solid {accent}; border-radius: 6px;
    padding: 13px 15px; font-size: 9pt; margin: 12px 0;
    page-break-inside: avoid;
  }}
  pre code {{ background: none; padding: 0; color: #1a1a2e; }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 9.5pt; page-break-inside: avoid; }}
  thead tr {{ background: {h1_color}; color: #fff; }}
  thead th {{ padding: 9px 11px; text-align: left; font-weight: 600; border: 1px solid {h1_color}; }}
  tbody tr:nth-child(even) {{ background: #f0f4ff; }}
  td {{ padding: 7px 11px; border: 1px solid #c8d4e8; vertical-align: top; }}

  /* ── Mermaid ── */
  .mermaid {{
    background: #f8f9ff; border: 1px solid #c8d4e8;
    border-radius: 10px; padding: 18px; margin: 18px 0;
    text-align: center; page-break-inside: avoid;
  }}
  .diagram-caption {{
    text-align: center; font-size: 9pt; color: #555;
    font-style: italic; margin-top: -8px; margin-bottom: 18px;
  }}

  /* ── Blockquote ── */
  blockquote {{
    border-left: 4px solid {accent}; background: #f0f8ff;
    padding: 11px 15px; margin: 12px 0;
    border-radius: 0 6px 6px 0; font-size: 9.5pt; color: #1a1a2e;
    page-break-inside: avoid;
  }}

  hr {{ border: none; border-top: 2px solid #e5e7eb; margin: 26px 0; }}

  .abstract-box {{
    border: 1px solid #c8d4e8; border-radius: 8px;
    padding: 14px 18px; margin: 18px 0; background: #fafbff;
    page-break-inside: avoid;
  }}
</style>
</head>
<body>
<script>
  mermaid.initialize({{
    startOnLoad: true, theme: 'base',
    themeVariables: {{
      primaryColor: '{h1_color}', primaryTextColor: '#fff',
      primaryBorderColor: '{accent}', lineColor: '{accent}',
      secondaryColor: '#f0f4ff', tertiaryColor: '#fff'
    }},
    flowchart: {{ useMaxWidth: true, htmlLabels: true }},
    securityLevel: 'loose'
  }});
</script>
{body}
</body>
</html>"""


THEMES = {
    "blue": {
        "cover_bg": "linear-gradient(135deg,#0f3460 0%,#16213e 60%,#0f3460 100%)",
        "accent": "#4fc3f7", "h1_color": "#0f3460", "h2_color": "#16213e",
        "h3_color": "#0f3460", "qa_bg": "#eff6ff",
    },
    "green": {
        "cover_bg": "linear-gradient(135deg,#064e3b 0%,#065f46 60%,#047857 100%)",
        "accent": "#34d399", "h1_color": "#064e3b", "h2_color": "#065f46",
        "h3_color": "#047857", "qa_bg": "#f0fdf4",
    },
}


def md_to_html_body(md_content: str, qa_mode: bool = False) -> str:
    mermaid_placeholder = "MERMAID_BLOCK_{}"
    mermaid_blocks = {}

    def save_mermaid(m):
        key = mermaid_placeholder.format(len(mermaid_blocks))
        mermaid_blocks[key] = m.group(1).strip()
        return f"\n\n{key}\n\n"

    md_content = re.sub(r'```mermaid\n(.*?)\n```', save_mermaid, md_content, flags=re.DOTALL)

    html = markdown2.markdown(
        md_content,
        extras=["tables", "fenced-code-blocks", "header-ids", "strike",
                "task_list", "break-on-newline", "cuddled-lists"]
    )

    for key, diagram in mermaid_blocks.items():
        html = html.replace(f"<p>{key}</p>", f'<div class="mermaid">{diagram}</div>')
        html = html.replace(key, f'<div class="mermaid">{diagram}</div>')

    html = re.sub(
        r'<p><em>(Fig\..*?|Note:.*?)</em></p>',
        r'<p class="diagram-caption"><em>\1</em></p>', html
    )
    html = re.sub(
        r'<p>(<strong>Abstract—.*?</strong>.*?)</p>',
        r'<div class="abstract-box"><p>\1</p></div>', html, flags=re.DOTALL
    )
    html = re.sub(
        r'<p>(<strong>Keywords—.*?</strong>.*?)</p>',
        r'<div class="abstract-box"><p>\1</p></div>', html, flags=re.DOTALL
    )

    if qa_mode:
        # Wrap Q/Cross-Q headings and their answer paragraphs
        html = re.sub(
            r'<h3>(Q\d+.*?)</h3>',
            r'<div class="qa-question">\1</div>', html
        )
        html = re.sub(
            r'<h3>(Cross-Q.*?)</h3>',
            r'<div class="qa-crossq">\1</div>', html
        )
        # Wrap <p><strong>Answer:</strong>... blocks
        html = re.sub(
            r'<p><strong>Answer:</strong>(.*?)</p>',
            r'<div class="qa-answer"><strong>Answer:</strong>\1</div>', html,
            flags=re.DOTALL
        )

    return html


def build_cover(title: str, subtitle: str, meta_lines: list, badge: str = "Technical Project Report · 2026") -> str:
    meta_html = "".join(f"<div>{l}</div>" for l in meta_lines)
    return f"""
<div class="cover">
  <div class="cover-badge">{badge}</div>
  <h1>{title}</h1>
  <h2>{subtitle}</h2>
  <div class="cover-divider"></div>
  <div class="cover-meta">{meta_html}</div>
</div>"""


async def generate_pdf(html_content: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        await page.wait_for_timeout(4000)
        await page.pdf(
            path=output_path, format="A4",
            margin={"top": "22mm", "bottom": "22mm", "left": "20mm", "right": "20mm"},
            print_background=True,
            display_header_footer=True,
            footer_template='<div style="font-size:8pt;color:#aaa;width:100%;text-align:right;padding-right:20mm;"><span class="pageNumber"></span></div>',
            header_template='<div></div>'
        )
        await browser.close()
        print(f"[OK] PDF saved: {output_path}")


def apply_theme(template: str, theme: dict) -> str:
    return template.format(**theme, body="{body}", title="{title}")


async def build_project_report():
    md_path = os.path.join(BASE, "Complete_Project_Report.md")
    out_path = os.path.join(BASE, "Complete_Project_Report.pdf")
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    body = md_to_html_body(raw)
    cover = build_cover(
        "Healthcare Medication Adherence Analytics,<br>Knowledge Base (RAG) &amp; Agentic AI Orchestrator",
        "Complete Project Documentation Report — Beginner-Friendly Edition",
        ["Healthcare Intelligence &amp; Patient Adherence Platform",
         "September 2026",
         "Synthetic / Portfolio Data — Not a Clinical System"]
    )
    t = THEMES["blue"]
    html = HTML_TEMPLATE.format(title="Complete Project Report", body=cover + body, **t)
    await generate_pdf(html, out_path)


async def build_ieee_paper():
    md_path = os.path.join(BASE, "Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.md")
    out_path = os.path.join(BASE, "Healthcare_AI_Medication_Adherence_IEEE_One_Column_Paper.pdf")
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    body = md_to_html_body(raw)
    cover = build_cover(
        "An AI-Driven Healthcare Medication Adherence Analytics and Knowledge Retrieval System Using RAG and Agentic AI",
        "IEEE-Style Academic Technical Paper (Single-Column)",
        ["[Author Name] · [Department] · [College/University]",
         "[City, Country] · [Email]",
         "September 2026 · Prototype using Synthetic Data"],
        badge="IEEE-Style Academic Paper · 2026"
    )
    t = THEMES["blue"]
    html = HTML_TEMPLATE.format(title="IEEE Paper", body=cover + body, **t)
    await generate_pdf(html, out_path)


async def build_interview_guide():
    md_path = os.path.join(BASE, "Interview_QA_Guide.md")
    out_path = os.path.join(BASE, "Interview_QA_Guide.pdf")
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    body = md_to_html_body(raw, qa_mode=True)
    cover = build_cover(
        "Interview Preparation Guide",
        "Healthcare Medication Adherence Analytics, RAG &amp; Agentic AI Platform",
        ["Complete Q&amp;A with Cross-Questions &amp; Humanized Answers",
         "ZS Associates / Data Analytics / Technology Interviews",
         "September 2026"],
        badge="Interview Prep · 2026"
    )
    t = THEMES["green"]
    html = HTML_TEMPLATE.format(title="Interview Q&A Guide", body=cover + body, **t)
    await generate_pdf(html, out_path)


async def main():
    print("Building Complete Project Report PDF...")
    await build_project_report()

    print("Building IEEE Academic Paper PDF...")
    await build_ieee_paper()

    print("Building Interview Q&A Guide PDF...")
    await build_interview_guide()

    print("\n[DONE] All 3 PDFs generated successfully!")


if __name__ == "__main__":
    asyncio.run(main())
