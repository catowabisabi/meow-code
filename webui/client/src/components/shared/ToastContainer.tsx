import { useToastStore, type Toast as ToastType } from './Toast'

const icons = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
  loading: '◌',
}

const colors = {
  success: {
    bg: 'rgba(34, 197, 94, 0.15)',
    border: 'rgba(34, 197, 94, 0.4)',
    icon: '#22c55e',
  },
  error: {
    bg: 'rgba(248, 81, 73, 0.15)',
    border: 'rgba(248, 81, 73, 0.4)',
    icon: '#f85149',
  },
  info: {
    bg: 'rgba(88, 166, 255, 0.15)',
    border: 'rgba(88, 166, 255, 0.4)',
    icon: '#58a6ff',
  },
  loading: {
    bg: 'rgba(168, 85, 247, 0.15)',
    border: 'rgba(168, 85, 247, 0.4)',
    icon: '#a855f7',
  },
}

function ToastItem({ toast }: { toast: ToastType }) {
  const removeToast = useToastStore((s) => s.removeToast)
  const color = colors[toast.type]

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '14px 16px',
        background: color.bg,
        border: `1px solid ${color.border}`,
        borderRadius: '10px',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
        minWidth: '300px',
        maxWidth: '400px',
        animation: 'slideIn 0.2s ease-out',
      }}
    >
      <span
        style={{
          fontSize: '16px',
          color: color.icon,
          flexShrink: 0,
          animation: toast.type === 'loading' ? 'spin 1s linear infinite' : undefined,
        }}
      >
        {icons[toast.type]}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '14px', fontWeight: 500, color: '#e6e6e6' }}>
          {toast.message}
        </div>
        {toast.description && (
          <div style={{ fontSize: '12px', color: '#a1a1aa', marginTop: '2px' }}>
            {toast.description}
          </div>
        )}
      </div>
      {toast.type !== 'loading' && (
        <button
          onClick={() => removeToast(toast.id)}
          style={{
            background: 'none',
            border: 'none',
            color: '#71717a',
            cursor: 'pointer',
            fontSize: '14px',
            padding: '0',
            flexShrink: 0,
          }}
        >
          ✕
        </button>
      )}
    </div>
  )
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <>
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          zIndex: 9999,
        }}
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} />
        ))}
      </div>
    </>
  )
}
