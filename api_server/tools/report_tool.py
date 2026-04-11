"""Report generation tool — Generates HTML reports with tables, charts, text."""
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .types import ToolDef, ToolContext, ToolResult


def _get_report_dir() -> Path:
    """Get the reports directory, creating it if needed."""
    home = Path.home()
    report_dir = home / ".claude" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def _sanitize_filename(title: str) -> str:
    """Convert title to a safe filename."""
    return re.sub(r"[^a-zA-Z0-9]", "_", title).lower()


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


async def _generate_report(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute report generation."""
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""

    try:
        title = args.get("title", "Untitled Report")
        sections: List[Dict[str, Any]] = args.get("sections", [])
        subtitle = args.get("subtitle")
        author = args.get("author")
        date = args.get("date") or ""
        theme = args.get("theme", "light")
        filename = args.get("filename") or _sanitize_filename(title)

        # Ensure we have a date
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")

        is_dark = theme == "dark"
        bg = "#1a1a2e" if is_dark else "#ffffff"
        text_color = "#e6e6e6" if is_dark else "#333333"
        card_bg = "#16213e" if is_dark else "#f8f9fa"
        border_color = "#2a2a4a" if is_dark else "#e0e0e0"
        header_bg = "#0f3460" if is_dark else "#2c3e50"

        chart_counter = 0
        chart_scripts: List[str] = []

        # Build HTML
        html_parts: List[str] = []

        html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {bg}; color: {text_color}; line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 32px; }}
  .header {{ text-align: center; margin-bottom: 40px; padding-bottom: 24px; border-bottom: 3px solid {header_bg}; }}
  .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
  .header .subtitle {{ font-size: 16px; color: {'#a0a0c0' if is_dark else '#666'}; }}
  .header .meta {{ font-size: 13px; color: {'#808090' if is_dark else '#999'}; margin-top: 8px; }}
  .section {{ margin-bottom: 32px; }}
  h2 {{ font-size: 22px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid {border_color}; }}
  h3 {{ font-size: 18px; font-weight: 600; margin-bottom: 12px; }}
  h4 {{ font-size: 16px; font-weight: 600; margin-bottom: 8px; }}
  p {{ margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 14px; }}
  th {{ background: {header_bg}; color: white; padding: 12px 16px; text-align: left; font-weight: 600; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid {border_color}; }}
  tr:nth-child(even) {{ background: {'#1e1e3a' if is_dark else '#f8f9fa'}; }}
  tr:hover {{ background: {'#252550' if is_dark else '#e8f4f8'}; }}
  .caption {{ font-size: 13px; color: {'#808090' if is_dark else '#999'}; margin-top: 8px; text-align: center; font-style: italic; }}
  .chart-container {{ position: relative; max-width: 600px; margin: 0 auto 24px; }}
  .summary-cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .summary-card {{ flex: 1; min-width: 180px; padding: 20px; border-radius: 12px; background: {card_bg}; border: 1px solid {border_color}; text-align: center; }}
  .summary-card .value {{ font-size: 32px; font-weight: 700; margin-bottom: 4px; }}
  .summary-card .card-title {{ font-size: 14px; color: {'#a0a0c0' if is_dark else '#666'}; }}
  .summary-card .card-subtitle {{ font-size: 12px; color: {'#808090' if is_dark else '#999'}; margin-top: 4px; }}
  .divider {{ height: 1px; background: {border_color}; margin: 32px 0; }}
  @media print {{ body {{ background: white; color: #333; }} .container {{ padding: 20px; }} }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>{_escape_html(title)}</h1>
  {f'<div class="subtitle">{_escape_html(subtitle)}</div>' if subtitle else ''}
  <div class="meta">{f'{_escape_html(author)} · ' if author else ''}{_escape_html(date)}</div>
</div>
""")

        # Process sections
        for section in sections:
            section_type = section.get("type", "")

            if section_type == "heading":
                level = section.get("level", 2)
                content = section.get("content", "")
                html_parts.append(f"<h{level}>{_escape_html(content)}</h{level}>\n")

            elif section_type == "text":
                content = section.get("content", "")
                html_parts.append(f'<div class="section"><p>{_escape_html(content)}</p></div>\n')

            elif section_type == "table":
                headers = section.get("headers", [])
                rows = section.get("rows", [])
                caption = section.get("caption")
                html_parts.append(
                    '<div class="section"><table><thead><tr>'
                    + "".join(f"<th>{_escape_html(h)}</th>" for h in headers)
                    + "</tr></thead><tbody>"
                )
                for row in rows:
                    html_parts.append(
                        "<tr>" + "".join(f"<td>{_escape_html(str(c))}</td>" for c in row) + "</tr>"
                    )
                html_parts.append("</tbody></table>")
                if caption:
                    html_parts.append(f'<div class="caption">{_escape_html(caption)}</div>')
                html_parts.append("</div>\n")

            elif section_type == "chart":
                chart_id = f"chart_{chart_counter}"
                chart_counter += 1
                chart_type = section.get("chartType", "bar")
                labels = section.get("labels", [])
                datasets = section.get("datasets", [])
                chart_title = section.get("title")

                default_colors = [
                    "#3498db",
                    "#e74c3c",
                    "#2ecc71",
                    "#f39c12",
                    "#9b59b6",
                    "#1abc9c",
                    "#e67e22",
                    "#34495e",
                ]

                html_parts.append('<div class="section">')
                if chart_title:
                    html_parts.append(f"<h3>{_escape_html(chart_title)}</h3>")
                html_parts.append(f'<div class="chart-container"><canvas id="{chart_id}"></canvas></div></div>\n')

                ds_config = []
                for i, ds in enumerate(datasets):
                    color = ds.get("color") or default_colors[i % len(default_colors)]
                    if chart_type in ("pie", "doughnut"):
                        # For pie/doughnut, use backgroundColor array with distinct colors
                        colors = default_colors[: len(ds.get("data", []))]
                        ds_config.append(
                            f"{{ label: {json.dumps(ds.get('label', ''))}, "
                            f"data: {json.dumps(ds.get('data', []))}, "
                            f"backgroundColor: {json.dumps(colors)} }}"
                        )
                    else:
                        ds_config.append(
                            f"{{ label: {json.dumps(ds.get('label', ''))}, "
                            f"data: {json.dumps(ds.get('data', []))}, "
                            f"backgroundColor: {json.dumps(color)}, "
                            f"borderColor: {json.dumps(color)}, "
                            f"borderWidth: 2, tension: 0.3 }}"
                        )

                chart_scripts.append(
                    f"new Chart(document.getElementById('{chart_id}'), {{ "
                    f"type: '{chart_type}', "
                    f"data: {{ labels: {json.dumps(labels)}, datasets: [{','.join(ds_config)}] }}, "
                    f"options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }} "
                    f"}});"
                )

            elif section_type == "summary_cards":
                cards = section.get("cards", [])
                html_parts.append('<div class="summary-cards">')
                for card in cards:
                    card_color = card.get("color") or header_bg
                    card_value = card.get("value", "")
                    card_title = card.get("title", "")
                    card_subtitle = card.get("subtitle", "")
                    html_parts.append(
                        f'<div class="summary-card">'
                        f'<div class="value" style="color: {card_color}">{_escape_html(str(card_value))}</div>'
                        f'<div class="card-title">{_escape_html(card_title)}</div>'
                        + (f'<div class="card-subtitle">{_escape_html(card_subtitle)}</div>' if card_subtitle else "")
                        + "</div>"
                    )
                html_parts.append("</div>\n")

            elif section_type == "divider":
                html_parts.append('<div class="divider"></div>\n')

        # Close HTML
        html_parts.append("</div>\n")
        if chart_scripts:
            html_parts.append("<script>\n" + "\n".join(chart_scripts) + "\n</script>\n")
        html_parts.append("</body>\n</html>")

        html_content = "".join(html_parts)

        # Write file
        report_dir = _get_report_dir()
        file_path = report_dir / f"{filename}.html"
        file_path.write_text(html_content, encoding="utf-8")

        # Calculate size
        size_kb = len(html_content) / 1024

        result_data = {
            "message": f'Report "{title}" generated successfully.',
            "path": str(file_path),
            "size": f"{size_kb:.1f} KB",
            "sections": len(sections),
            "charts": chart_counter,
        }

        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps(result_data, indent=2, ensure_ascii=False),
            is_error=False,
        )

    except Exception as err:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error generating report: {err}",
            is_error=True,
        )


REPORT_GENERATE_TOOL = ToolDef(
    name="report_generate",
    description="""Generate professional HTML reports with tables, charts, and formatted text.
Reports are saved to ~/.claude/reports/ and can be opened in a browser.

The report uses Chart.js for charts and professional CSS styling.

Params:
- title: Report title
- sections: Array of sections, each section has:
  - type: "text" | "table" | "chart" | "heading" | "summary_cards" | "divider"
  - For "text": content (string)
  - For "heading": content (string), level (1-4)
  - For "table": headers (string[]), rows (any[][]), caption? (string)
  - For "chart": chartType ("bar"|"line"|"pie"|"doughnut"), labels (string[]), datasets ({label, data, color?}[]), title? (string)
  - For "summary_cards": cards ({title, value, subtitle?, color?}[])
  - For "divider": (no params needed)
- filename?: Custom filename (default: auto-generated from title)
- subtitle?: Report subtitle
- author?: Author name
- date?: Report date (default: today)
- theme?: "light" | "dark" (default: "light")

Example: Generate an accounting report with income/expense tables and pie chart.""",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Report title"},
            "sections": {
                "type": "array",
                "description": "Report sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["text", "table", "chart", "heading", "summary_cards", "divider"],
                        },
                        "content": {"type": "string"},
                        "level": {"type": "number"},
                        "headers": {"type": "array", "items": {"type": "string"}},
                        "rows": {"type": "array", "items": {"type": "array"}},
                        "caption": {"type": "string"},
                        "chartType": {"type": "string", "enum": ["bar", "line", "pie", "doughnut"]},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "datasets": {"type": "array"},
                        "title": {"type": "string"},
                        "cards": {"type": "array"},
                    },
                    "required": ["type"],
                },
            },
            "filename": {"type": "string"},
            "subtitle": {"type": "string"},
            "author": {"type": "string"},
            "date": {"type": "string"},
            "theme": {"type": "string", "enum": ["light", "dark"]},
        },
        "required": ["title", "sections"],
    },
    is_read_only=False,
    risk_level="low",
    execute=_generate_report,
)


def register_report_tools() -> None:
    """Register report tools."""
    from .executor import register_tool

    register_tool(REPORT_GENERATE_TOOL)


__all__ = ["REPORT_GENERATE_TOOL", "register_report_tools"]
