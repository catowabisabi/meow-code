/**
 * Web tools — fetch URLs and search the web.
 */
import type { ToolDef, ToolContext, ToolResult } from './types.js'

// ─── Web Fetch ────────────────────────────────────────────────

export const webFetchTool: ToolDef = {
  name: 'web_fetch',
  description: 'Fetch a URL and return its content as text/markdown. Useful for reading web pages, APIs, documentation.',
  inputSchema: {
    type: 'object',
    required: ['url'],
    properties: {
      url: { type: 'string', description: 'URL to fetch' },
      raw: { type: 'boolean', description: 'Return raw HTML instead of extracted text (default: false)' },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const url = input.url as string
      const raw = input.raw as boolean

      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30000)

      // Also listen to parent abort
      ctx.abortSignal?.addEventListener('abort', () => controller.abort())

      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; AICodeAssistant/1.0)',
          Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        signal: controller.signal,
        redirect: 'follow',
      })

      clearTimeout(timeout)

      if (!response.ok) {
        return {
          output: `HTTP ${response.status} ${response.statusText}`,
          isError: true,
          metadata: { status: response.status },
        }
      }

      const contentType = response.headers.get('content-type') || ''

      // JSON responses
      if (contentType.includes('application/json')) {
        const json = await response.json()
        const text = JSON.stringify(json, null, 2)
        return {
          output: text.slice(0, 50000),
          isError: false,
          metadata: { contentType, size: text.length },
        }
      }

      // Text/HTML
      let text = await response.text()

      if (!raw && contentType.includes('html')) {
        // Simple HTML → text extraction
        text = text
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<style[\s\S]*?<\/style>/gi, '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/\s+/g, ' ')
          .replace(/&nbsp;/g, ' ')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .trim()
      }

      // Truncate
      if (text.length > 50000) {
        text = text.slice(0, 50000) + '\n...(truncated)'
      }

      return {
        output: text,
        isError: false,
        metadata: { contentType, url: response.url, size: text.length },
      }
    } catch (err: unknown) {
      return { output: `Fetch error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Web Search ───────────────────────────────────────────────

export const webSearchTool: ToolDef = {
  name: 'web_search',
  description: 'Search the web and return results. Uses DuckDuckGo Lite (no API key needed).',
  inputSchema: {
    type: 'object',
    required: ['query'],
    properties: {
      query: { type: 'string', description: 'Search query' },
      max_results: { type: 'number', description: 'Max results to return (default: 8)' },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const query = input.query as string
      const maxResults = (input.max_results as number) || 8

      // Use DuckDuckGo HTML Lite
      const url = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; AICodeAssistant/1.0)',
        },
      })

      if (!response.ok) {
        return { output: `Search failed: HTTP ${response.status}`, isError: true }
      }

      const html = await response.text()

      // Extract result links and snippets from DDG Lite HTML
      const results: Array<{ title: string; url: string; snippet: string }> = []
      const linkRegex = /<a[^>]+class="result-link"[^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/gi
      const snippetRegex = /<td[^>]+class="result-snippet"[^>]*>([\s\S]*?)<\/td>/gi

      // Simpler extraction: find all links in result blocks
      const resultBlocks = html.split(/class="result-link"/i).slice(1)

      for (const block of resultBlocks.slice(0, maxResults)) {
        const hrefMatch = block.match(/href="([^"]*)"/)
        const textMatch = block.match(/>([^<]+)</)
        if (hrefMatch && textMatch) {
          results.push({
            title: textMatch[1]?.trim() || '',
            url: hrefMatch[1] || '',
            snippet: '',
          })
        }
      }

      if (results.length === 0) {
        // Fallback: extract any links
        const allLinks = html.matchAll(/<a[^>]+href="(https?:\/\/[^"]+)"[^>]*>([^<]+)<\/a>/gi)
        let count = 0
        for (const match of allLinks) {
          if (count >= maxResults) break
          const href = match[1] || ''
          if (href.includes('duckduckgo.com')) continue
          results.push({ title: match[2]?.trim() || '', url: href, snippet: '' })
          count++
        }
      }

      if (results.length === 0) {
        return { output: 'No search results found.', isError: false }
      }

      const formatted = results
        .map((r, i) => `${i + 1}. ${r.title}\n   ${r.url}${r.snippet ? '\n   ' + r.snippet : ''}`)
        .join('\n\n')

      return {
        output: formatted,
        isError: false,
        metadata: { resultCount: results.length },
      }
    } catch (err: unknown) {
      return { output: `Search error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
