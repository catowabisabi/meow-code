import { useState } from 'react'
import { useLayoutStore } from '../../stores/layoutStore.ts'

function Section({ title, defaultOpen = true, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ borderBottom: '1px solid var(--border-muted)' }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 16px', cursor: 'pointer', userSelect: 'none',
        }}
        onClick={() => setOpen(!open)}
      >
        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.2px' }}>{title}</span>
        <span style={{
          fontSize: '11px', color: 'var(--text-muted)',
          display: 'inline-block', transition: 'transform 0.15s',
          transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>›</span>
      </div>
      {open && <div style={{ padding: '0 16px 14px' }}>{children}</div>}
    </div>
  )
}

export default function RightPanel() {
  const { rightPanelOpen, mode, currentFolder } = useLayoutStore()
  const [scratchpad, setScratchpad] = useState('')

  if (!rightPanelOpen || mode === 'chat') return null

  const currentStep = 2
  const totalSteps = 2
  const progressPct = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0
  const folderName = currentFolder
    ? currentFolder.split(/[\\/]/).filter(Boolean).pop() ?? 'Project'
    : 'Project'

  return (
    <div style={{
      width: 280, minWidth: 280, height: '100%',
      background: 'var(--bg-sidebar)',
      borderLeft: '1px solid var(--border-muted)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid var(--border-muted)',
        fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.6px',
      }}>
        Context
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 0 16px' }}>
        {/* Progress */}
        <Section title="Progress">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {currentStep} of {totalSteps}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {[['‹', 'Previous'], ['›', 'Next']].map(([label, title]) => (
                <button key={title} title={title} style={{
                  background: 'none', border: '1px solid var(--border-default)',
                  borderRadius: '4px', color: 'var(--text-muted)', fontSize: '14px',
                  width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', padding: 0, lineHeight: 1, fontFamily: 'inherit',
                }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.borderColor = 'var(--border-focus)' }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--border-default)' }}
                >{label}</button>
              ))}
            </div>
          </div>
          <div style={{ width: '100%', height: 3, background: 'var(--bg-hover)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${progressPct}%`, background: 'var(--accent-purple)', borderRadius: 2, transition: 'width 0.25s ease' }} />
          </div>
        </Section>

        {/* Project */}
        <Section title="Project">
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>{folderName}</div>
          {[
            { icon: '📄', label: 'Instructions · CLAUDE.md' },
            { icon: '📝', label: 'Scratchpad' },
          ].map(item => (
            <div key={item.label} style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '6px 0', fontSize: '13px', color: 'var(--text-secondary)',
              cursor: 'pointer', transition: 'color 0.12s',
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.color = 'var(--text-primary)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.color = 'var(--text-secondary)' }}
            >
              <span style={{ width: 18, textAlign: 'center', flexShrink: 0, fontSize: '14px' }}>{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
          <textarea
            style={{
              width: '100%', minHeight: 72, marginTop: 8,
              background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)',
              borderRadius: 6, color: 'var(--text-secondary)', fontSize: 12,
              padding: '8px 10px', resize: 'vertical', outline: 'none', fontFamily: 'inherit',
              transition: 'border-color 0.12s',
            }}
            placeholder="Jot down notes..."
            value={scratchpad}
            onChange={e => setScratchpad(e.target.value)}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--border-focus)' }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-default)' }}
          />
        </Section>

        {/* Context */}
        <Section title="Context">
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            {['⌨', '✏️', '🔍'].map((icon, i) => (
              <div key={i} style={{
                width: 30, height: 30, background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)', borderRadius: 7,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, color: 'var(--text-muted)', cursor: 'pointer',
                transition: 'all 0.12s',
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-focus)'; (e.currentTarget as HTMLDivElement).style.color = 'var(--text-primary)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-default)'; (e.currentTarget as HTMLDivElement).style.color = 'var(--text-muted)' }}
              >{icon}</div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Track tools and referenced files used in this task.
          </div>
        </Section>
      </div>
    </div>
  )
}
