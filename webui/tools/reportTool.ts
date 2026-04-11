/**
 * Report generation tool — Generates HTML reports with tables, charts, text.
 * Reports stored in ~/.claude/reports/
 */
import * as path from 'path'
import * as fs from 'fs'
import type { ToolDef } from './types.js'

const REPORT_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '.', '.claude', 'reports')

function ensureDir() {
  if (!fs.existsSync(REPORT_DIR)) fs.mkdirSync(REPORT_DIR, { recursive: true })
}

export const reportGenerateTool: ToolDef = {
  name: 'report_generate',
  description: `Generate professional HTML reports with tables, charts, and formatted text.
Reports are saved to ~/.claude/reports/ and can be opened in a browser.

The report uses Chart.js for charts and professional CSS styling.

Params:
- title: Report title
- sections: Array of sections, each section has:
  - type: "text" | "table" | "chart" | "heading" | "summary_cards" | "divider"
  - For "text": content (string, supports basic HTML)
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

Example: Generate an accounting report with income/expense tables and pie chart.`,
  inputSchema: {
    type: 'object',
    properties: {
      title: { type: 'string', description: 'Report title' },
      sections: {
        type: 'array',
        description: 'Report sections',
        items: {
          type: 'object',
          properties: {
            type: { type: 'string', enum: ['text', 'table', 'chart', 'heading', 'summary_cards', 'divider'] },
            content: { type: 'string' },
            level: { type: 'number' },
            headers: { type: 'array', items: { type: 'string' } },
            rows: { type: 'array', items: { type: 'array' } },
            caption: { type: 'string' },
            chartType: { type: 'string', enum: ['bar', 'line', 'pie', 'doughnut'] },
            labels: { type: 'array', items: { type: 'string' } },
            datasets: { type: 'array' },
            cards: { type: 'array' },
          },
          required: ['type'],
        },
      },
      filename: { type: 'string' },
      subtitle: { type: 'string' },
      author: { type: 'string' },
      date: { type: 'string' },
      theme: { type: 'string', enum: ['light', 'dark'] },
    },
    required: ['title', 'sections'],
  },
  isReadOnly: false,
  riskLevel: 'low',
  execute: async (input: Record<string, unknown>) => {
    const title = input.title as string
    const sections = input.sections as Record<string, unknown>[]
    const subtitle = input.subtitle as string | undefined
    const author = input.author as string | undefined
    const date = input.date as string || new Date().toISOString().split('T')[0]
    const theme = (input.theme as string) || 'light'
    const filename = (input.filename as string) || title.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()

    ensureDir()

    const isDark = theme === 'dark'
    const bg = isDark ? '#1a1a2e' : '#ffffff'
    const text = isDark ? '#e6e6e6' : '#333333'
    const cardBg = isDark ? '#16213e' : '#f8f9fa'
    const borderColor = isDark ? '#2a2a4a' : '#e0e0e0'
    const headerBg = isDark ? '#0f3460' : '#2c3e50'

    let chartCounter = 0
    const chartScripts: string[] = []

    let html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: ${bg}; color: ${text}; line-height: 1.6; }
  .container { max-width: 1100px; margin: 0 auto; padding: 40px 32px; }
  .header { text-align: center; margin-bottom: 40px; padding-bottom: 24px; border-bottom: 3px solid ${headerBg}; }
  .header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
  .header .subtitle { font-size: 16px; color: ${isDark ? '#a0a0c0' : '#666'}; }
  .header .meta { font-size: 13px; color: ${isDark ? '#808090' : '#999'}; margin-top: 8px; }
  .section { margin-bottom: 32px; }
  h2 { font-size: 22px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid ${borderColor}; }
  h3 { font-size: 18px; font-weight: 600; margin-bottom: 12px; }
  h4 { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
  p { margin-bottom: 12px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 14px; }
  th { background: ${headerBg}; color: white; padding: 12px 16px; text-align: left; font-weight: 600; }
  td { padding: 10px 16px; border-bottom: 1px solid ${borderColor}; }
  tr:nth-child(even) { background: ${isDark ? '#1e1e3a' : '#f8f9fa'}; }
  tr:hover { background: ${isDark ? '#252550' : '#e8f4f8'}; }
  .caption { font-size: 13px; color: ${isDark ? '#808090' : '#999'}; margin-top: 8px; text-align: center; font-style: italic; }
  .chart-container { position: relative; max-width: 600px; margin: 0 auto 24px; }
  .summary-cards { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .summary-card { flex: 1; min-width: 180px; padding: 20px; border-radius: 12px; background: ${cardBg}; border: 1px solid ${borderColor}; text-align: center; }
  .summary-card .value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
  .summary-card .card-title { font-size: 14px; color: ${isDark ? '#a0a0c0' : '#666'}; }
  .summary-card .card-subtitle { font-size: 12px; color: ${isDark ? '#808090' : '#999'}; margin-top: 4px; }
  .divider { height: 1px; background: ${borderColor}; margin: 32px 0; }
  @media print { body { background: white; color: #333; } .container { padding: 20px; } }
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>${title}</h1>
  ${subtitle ? `<div class="subtitle">${subtitle}</div>` : ''}
  <div class="meta">${author ? `${author} · ` : ''}${date}</div>
</div>
`

    for (const section of sections) {
      const type = section.type as string
      switch (type) {
        case 'heading': {
          const level = (section.level as number) || 2
          html += `<h${level}>${section.content}</h${level}>\n`
          break
        }
        case 'text': {
          html += `<div class="section"><p>${section.content}</p></div>\n`
          break
        }
        case 'table': {
          const headers = section.headers as string[]
          const rows = section.rows as unknown[][]
          const caption = section.caption as string | undefined
          html += `<div class="section"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>`
          for (const row of rows) {
            html += `<tr>${row.map(c => `<td>${c}</td>`).join('')}</tr>`
          }
          html += `</tbody></table>${caption ? `<div class="caption">${caption}</div>` : ''}</div>\n`
          break
        }
        case 'chart': {
          const chartId = `chart_${chartCounter++}`
          const chartType = section.chartType as string || 'bar'
          const labels = section.labels as string[]
          const datasets = section.datasets as { label: string; data: number[]; color?: string }[]
          const chartTitle = (section as Record<string, unknown>).title as string | undefined

          const defaultColors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e']

          html += `<div class="section">${chartTitle ? `<h3>${chartTitle}</h3>` : ''}<div class="chart-container"><canvas id="${chartId}"></canvas></div></div>\n`

          const dsConfig = datasets.map((ds, i) => {
            const color = ds.color || defaultColors[i % defaultColors.length]
            if (chartType === 'pie' || chartType === 'doughnut') {
              return `{ label: ${JSON.stringify(ds.label)}, data: ${JSON.stringify(ds.data)}, backgroundColor: ${JSON.stringify(defaultColors.slice(0, ds.data.length))} }`
            }
            return `{ label: ${JSON.stringify(ds.label)}, data: ${JSON.stringify(ds.data)}, backgroundColor: '${color}', borderColor: '${color}', borderWidth: 2, tension: 0.3 }`
          })

          chartScripts.push(`new Chart(document.getElementById('${chartId}'), { type: '${chartType}', data: { labels: ${JSON.stringify(labels)}, datasets: [${dsConfig.join(',')}] }, options: { responsive: true, plugins: { legend: { position: 'top' } } } });`)
          break
        }
        case 'summary_cards': {
          const cards = section.cards as { title: string; value: string; subtitle?: string; color?: string }[]
          html += `<div class="summary-cards">`
          for (const card of cards) {
            html += `<div class="summary-card"><div class="value" style="color: ${card.color || headerBg}">${card.value}</div><div class="card-title">${card.title}</div>${card.subtitle ? `<div class="card-subtitle">${card.subtitle}</div>` : ''}</div>`
          }
          html += `</div>\n`
          break
        }
        case 'divider': {
          html += `<div class="divider"></div>\n`
          break
        }
      }
    }

    html += `</div>\n<script>\n${chartScripts.join('\n')}\n</script>\n</body>\n</html>`

    const filePath = path.join(REPORT_DIR, `${filename}.html`)
    fs.writeFileSync(filePath, html, 'utf-8')

    return {
      output: JSON.stringify({
        message: `Report "${title}" generated successfully.`,
        path: filePath,
        size: `${(html.length / 1024).toFixed(1)} KB`,
        sections: sections.length,
        charts: chartCounter,
      }, null, 2),
      isError: false,
    }
  },
}
