import { useEffect, useRef, useState, useCallback } from 'react'
import { toast } from '../components/shared/Toast'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

interface UseWebSocketOptions {
  /** Handler for incoming messages */
  onMessage: (msg: Record<string, unknown>) => void
  /** Max reconnection attempts (default: Infinity) */
  maxRetries?: number
  /** Heartbeat interval in ms (default: 30000) */
  heartbeatInterval?: number
}

interface UseWebSocketReturn {
  ws: WebSocket | null
  status: ConnectionStatus
  /** Manually reconnect */
  reconnect: () => void
}

const INITIAL_RETRY_DELAY = 1000
const MAX_RETRY_DELAY = 15000

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { onMessage, maxRetries = Infinity, heartbeatInterval = 30000 } = options

  const [wsInstance, setWsInstance] = useState<WebSocket | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')

  // All mutable state in refs to avoid re-creating connect()
  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const onMessageRef = useRef(onMessage)
  const unmountedRef = useRef(false)
  const maxRetriesRef = useRef(maxRetries)
  const heartbeatIntervalRef = useRef(heartbeatInterval)

  // Keep refs fresh
  onMessageRef.current = onMessage
  maxRetriesRef.current = maxRetries
  heartbeatIntervalRef.current = heartbeatInterval

  const clearTimers = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current)
      heartbeatTimerRef.current = null
    }
  }, [])

  // connect is stable — never changes identity
  const connectRef = useRef<() => void>(() => {})
  connectRef.current = () => {
    if (unmountedRef.current) return

    // Close existing connection if any
    if (wsRef.current) {
      try { wsRef.current.close() } catch { /* ignore */ }
      wsRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/chat`

    setStatus(retryCountRef.current > 0 ? 'reconnecting' : 'connecting')

    const socket = new WebSocket(wsUrl)
    wsRef.current = socket

    socket.onopen = () => {
      if (unmountedRef.current) { socket.close(); return }
      console.log('[WebSocket] Connected')
      setStatus('connected')
      setWsInstance(socket)
      retryCountRef.current = 0

      // Start heartbeat
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current)
      heartbeatTimerRef.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          try { socket.send(JSON.stringify({ type: 'ping' })) } catch { /* */ }
        }
      }, heartbeatIntervalRef.current)
    }

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'pong') return
        onMessageRef.current(msg)
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
        toast.error('Invalid message received', 'WebSocket parse error')
      }
    }

    socket.onclose = (event) => {
      if (unmountedRef.current) return
      console.log('[WebSocket] Disconnected', event.code, event.reason)
      wsRef.current = null
      setWsInstance(null)
      clearTimers()
      setStatus('disconnected')

      // Auto-reconnect unless intentionally closed (code 1000)
      if (event.code !== 1000 && retryCountRef.current < maxRetriesRef.current) {
        const delay = Math.min(
          INITIAL_RETRY_DELAY * Math.pow(2, retryCountRef.current),
          MAX_RETRY_DELAY
        )
        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${retryCountRef.current + 1})...`)
        setStatus('reconnecting')
        retryCountRef.current++
        retryTimerRef.current = setTimeout(() => connectRef.current(), delay)
      }
    }

    socket.onerror = () => {
      // Error is followed by close event, so reconnection is handled there
    }
  }

  const reconnect = useCallback(() => {
    retryCountRef.current = 0
    clearTimers()
    setTimeout(() => connectRef.current(), 150)
  }, [clearTimers])

  // Connect on mount, cleanup on unmount — runs exactly once
  useEffect(() => {
    unmountedRef.current = false
    connectRef.current()

    return () => {
      unmountedRef.current = true
      clearTimers()
      if (wsRef.current) {
        try { wsRef.current.close(1000, 'Component unmounted') } catch { /* ignore */ }
        wsRef.current = null
      }
    }
  }, [clearTimers])

  return { ws: wsInstance, status, reconnect }
}
