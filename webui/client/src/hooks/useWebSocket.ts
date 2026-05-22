import { useEffect, useRef, useState, useCallback } from 'react'
import { toast } from '../components/shared/Toast'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'failed'

export interface BackoffState {
  attempt: number
  nextRetryMs: number
  state: 'connecting' | 'reconnecting' | 'failed'
}

interface UseWebSocketOptions {
  onMessage: (msg: Record<string, unknown>) => void
  maxRetries?: number
  heartbeatInterval?: number
  onReconnected?: () => void
}

interface UseWebSocketReturn {
  ws: WebSocket | null
  status: ConnectionStatus
  backoff: BackoffState
  reconnect: () => void
  queueMessage: (msg: Record<string, unknown>) => void
}

const INITIAL_RETRY_DELAY = 1000
const MAX_RETRY_DELAY = 30000
const MAX_RETRIES = 10
const JITTER_MAX = 500

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { onMessage, maxRetries = MAX_RETRIES, heartbeatInterval = 30000, onReconnected } = options

  const [wsInstance, setWsInstance] = useState<WebSocket | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [backoff, setBackoff] = useState<BackoffState>({ attempt: 0, nextRetryMs: 0, state: 'connecting' })

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const onMessageRef = useRef(onMessage)
  const unmountedRef = useRef(false)
  const maxRetriesRef = useRef(maxRetries)
  const heartbeatIntervalRef = useRef(heartbeatInterval)
  const onReconnectedRef = useRef(onReconnected)
  const messageQueueRef = useRef<Record<string, unknown>[]>([])
  const wasConnectedRef = useRef(false)

  onMessageRef.current = onMessage
  maxRetriesRef.current = maxRetries
  heartbeatIntervalRef.current = heartbeatInterval
  onReconnectedRef.current = onReconnected

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

  const flushQueue = useCallback((socket: WebSocket) => {
    while (messageQueueRef.current.length > 0) {
      const msg = messageQueueRef.current.shift()
      if (msg) {
        try {
          socket.send(JSON.stringify(msg))
        } catch (e) {
          console.error('[WebSocket] Failed to send queued message:', e)
          messageQueueRef.current.unshift(msg)
          break
        }
      }
    }
  }, [])

  const connectRef = useRef<() => void>(() => {})
  connectRef.current = () => {
    if (unmountedRef.current) return

    if (wsRef.current) {
      try { wsRef.current.close() } catch { /* ignore */ }
      wsRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/chat`

    const isRetry = retryCountRef.current > 0
    setStatus(isRetry ? 'reconnecting' : 'connecting')
    setBackoff((b) => ({ ...b, state: isRetry ? 'reconnecting' : 'connecting' }))

    const socket = new WebSocket(wsUrl)
    wsRef.current = socket

    socket.onopen = () => {
      if (unmountedRef.current) { socket.close(); return }
      console.log('[WebSocket] Connected')

      const hadPreviousConnection = wasConnectedRef.current
      wasConnectedRef.current = true

      setStatus('connected')
      setWsInstance(socket)
      retryCountRef.current = 0
      setBackoff({ attempt: 0, nextRetryMs: 0, state: 'connecting' })

      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current)
      heartbeatTimerRef.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          try { socket.send(JSON.stringify({ type: 'ping' })) } catch { /* */ }
        }
      }, heartbeatIntervalRef.current)

      flushQueue(socket)

      if (hadPreviousConnection && onReconnectedRef.current) {
        onReconnectedRef.current()
      }
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

      if (event.code !== 1000 && retryCountRef.current < maxRetriesRef.current) {
        const attempt = retryCountRef.current
        const baseDelay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, attempt), MAX_RETRY_DELAY)
        const jitter = Math.random() * JITTER_MAX
        const delay = Math.floor(baseDelay + jitter)

        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${attempt + 1})...`)
        setStatus('reconnecting')
        setBackoff({ attempt: attempt + 1, nextRetryMs: delay, state: 'reconnecting' })
        retryCountRef.current++
        retryTimerRef.current = setTimeout(() => connectRef.current(), delay)
      } else {
        setStatus('failed')
        setBackoff((b) => ({ ...b, state: 'failed' }))
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

  const queueMessage = useCallback((msg: Record<string, unknown>) => {
    messageQueueRef.current.push(msg)
  }, [])

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

  return { ws: wsInstance, status, backoff, reconnect, queueMessage }
}