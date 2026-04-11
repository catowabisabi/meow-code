#!/usr/bin/env bun
/**
 * Standalone startup script.
 * Run with: bun run src/webui/start.ts
 * Or:       npx tsx src/webui/start.ts
 */
import { startWebUI } from './server/index.js'

const portArg = process.argv.find((a) => a.startsWith('--port='))
const port = portArg ? parseInt(portArg.split('=')[1]!) : undefined

startWebUI(port)
