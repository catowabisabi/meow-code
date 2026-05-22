import { useEffect } from 'react'
import { toast } from './shared/Toast'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'failed'

interface ConnectionStatusProps {
  status: ConnectionStatus
  onReconnect: () => void
}

export function ConnectionStatusBadge({ status, onReconnect }: ConnectionStatusProps) {
  useEffect(() => {
    if (status === 'connected') {
      toast.success('Reconnected', 'Connection restored')
    }
  }, [status])

  if (status === 'connected') {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '3px 8px', borderRadius: 5,
        background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.2)',
        fontSize: 11, color: '#4ade80',
      }}>
        <span style={{ fontSize: 6, fontWeight: 700 }}>●</span>
        Connected
      </div>
    )
  }

  if (status === 'reconnecting' || status === 'connecting') {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '3px 8px', borderRadius: 5,
        background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)',
        fontSize: 11, color: '#fbbf24',
      }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: '#fbbf24', animation: 'pulse-dot 1s infinite',
        }} />
        Reconnecting...
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 5,
      padding: '3px 8px', borderRadius: 5,
      background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)',
      fontSize: 11, color: '#f87171',
    }}>
      <span style={{ fontSize: 6, fontWeight: 700 }}>●</span>
      Disconnected
      <button
        onClick={onReconnect}
        style={{
          padding: '1px 6px', borderRadius: 3,
          border: '1px solid #f87171', background: 'transparent',
          color: '#f87171', fontSize: 10, cursor: 'pointer',
          fontFamily: 'inherit', marginLeft: 2,
        }}
      >
        Retry
      </button>
    </div>
  )
}

interface ConnectionBannerProps {
  status: ConnectionStatus
}

export function ConnectionBanner({ status }: ConnectionBannerProps) {
  if (status === 'connected') return null

  const isReconnecting = status === 'reconnecting' || status === 'connecting'
  const color = isReconnecting ? '#fbbf24' : '#f87171'
  const bg = isReconnecting ? 'rgba(251,191,36,0.08)' : 'rgba(248,113,113,0.08)'
  const border = isReconnecting ? 'rgba(251,191,36,0.25)' : 'rgba(248,113,113,0.25)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      padding: '7px 16px', margin: '0 0 8px',
      background: bg, border: `1px solid ${border}`,
      borderRadius: 8, fontSize: 12, color,
    }}>
      {isReconnecting && (
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: color, animation: 'pulse-dot 1.2s infinite',
        }} />
      )}
      <span>{isReconnecting ? 'Connection lost — reconnecting...' : 'Connection failed'}</span>
    </div>
  )
}