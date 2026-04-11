import { useState } from 'react'
import { useLayoutStore } from '../../stores/layoutStore.ts'

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = {
  panel: {
    width: '300px',
    minWidth: '300px',
    height: '100%',
    background: '#151517',
    borderLeft: '1px solid #2a2a2e',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  scrollArea: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '0 0 16px',
  },

  /* ---- section ---- */
  section: {
    borderBottom: '1px solid #2a2a2e',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e6e6e6',
  },
  collapseArrow: {
    fontSize: '12px',
    color: '#71717a',
    transition: 'transform 0.15s',
    display: 'inline-block',
  },
  sectionBody: {
    padding: '0 16px 14px',
  },

  /* ---- progress ---- */
  stepRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '10px',
  },
  stepLabel: {
    fontSize: '13px',
    color: '#a1a1aa',
  },
  stepNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  stepBtn: {
    background: 'none',
    border: '1px solid #2a2a2e',
    borderRadius: '4px',
    color: '#71717a',
    fontSize: '12px',
    width: '22px',
    height: '22px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    padding: 0,
    lineHeight: 1,
  },
  progressBarOuter: {
    width: '100%',
    height: '4px',
    background: '#2a2a2e',
    borderRadius: '2px',
    overflow: 'hidden' as const,
  },
  progressBarInner: {
    height: '100%',
    background: '#c084fc',
    borderRadius: '2px',
    transition: 'width 0.25s ease',
  },

  /* ---- project ---- */
  projectName: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e6e6e6',
    marginBottom: '10px',
  },
  linkRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 0',
    fontSize: '13px',
    color: '#a1a1aa',
    cursor: 'pointer',
    transition: 'color 0.15s',
  },
  linkIcon: {
    fontSize: '14px',
    width: '18px',
    textAlign: 'center' as const,
    flexShrink: 0,
  },
  scratchpadArea: {
    width: '100%',
    minHeight: '72px',
    background: '#1c1c1f',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#a1a1aa',
    fontSize: '12px',
    padding: '8px 10px',
    resize: 'vertical' as const,
    outline: 'none',
    fontFamily: 'inherit',
    marginTop: '8px',
  },

  /* ---- context ---- */
  contextIcons: {
    display: 'flex',
    gap: '8px',
    marginBottom: '8px',
  },
  contextIcon: {
    width: '28px',
    height: '28px',
    background: '#1c1c1f',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    color: '#71717a',
  },
  contextHint: {
    fontSize: '12px',
    color: '#52525b',
    lineHeight: 1.45,
  },
}

/* ------------------------------------------------------------------ */
/*  Collapsible section wrapper                                        */
/* ------------------------------------------------------------------ */

function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={styles.section}>
      <div style={styles.sectionHeader} onClick={() => setOpen(!open)}>
        <span style={styles.sectionTitle}>{title}</span>
        <span
          style={{
            ...styles.collapseArrow,
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
          }}
        >
          &#8250;
        </span>
      </div>
      {open && <div style={styles.sectionBody}>{children}</div>}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function RightPanel() {
  const { rightPanelOpen, mode, currentFolder } = useLayoutStore()
  const [scratchpad, setScratchpad] = useState('')

  // Only render in cowork / code modes and when open
  if (!rightPanelOpen || mode === 'chat') return null

  // Mock progress data
  const currentStep = 2
  const totalSteps = 2
  const progressPct = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0

  const folderName = currentFolder
    ? currentFolder.split(/[\\/]/).filter(Boolean).pop() ?? 'Project'
    : 'Project'

  return (
    <div style={styles.panel}>
      <div style={styles.scrollArea}>
        {/* ---- Progress ---- */}
        <Section title="Progress">
          <div style={styles.stepRow}>
            <span style={styles.stepLabel}>
              {currentStep} of {totalSteps}
            </span>
            <div style={styles.stepNav}>
              <button
                style={styles.stepBtn}
                title="Previous step"
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#e6e6e6'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#71717a'
                }}
              >
                &#8249;
              </button>
              <button
                style={styles.stepBtn}
                title="Next step"
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#e6e6e6'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#71717a'
                }}
              >
                &#8250;
              </button>
            </div>
          </div>
          <div style={styles.progressBarOuter}>
            <div
              style={{ ...styles.progressBarInner, width: `${progressPct}%` }}
            />
          </div>
        </Section>

        {/* ---- Project ---- */}
        <Section title="Project">
          <div style={styles.projectName}>{folderName}</div>
          <div
            style={styles.linkRow}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLDivElement).style.color = '#e6e6e6'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLDivElement).style.color = '#a1a1aa'
            }}
          >
            <span style={styles.linkIcon}>&#128196;</span>
            <span>Instructions &middot; CLAUDE.md</span>
          </div>
          <div
            style={styles.linkRow}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLDivElement).style.color = '#e6e6e6'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLDivElement).style.color = '#a1a1aa'
            }}
          >
            <span style={styles.linkIcon}>&#128221;</span>
            <span>Scratchpad</span>
          </div>
          <textarea
            style={styles.scratchpadArea as React.CSSProperties}
            placeholder="Jot down notes..."
            value={scratchpad}
            onChange={(e) => setScratchpad(e.target.value)}
          />
        </Section>

        {/* ---- Context ---- */}
        <Section title="Context">
          <div style={styles.contextIcons}>
            <div style={styles.contextIcon} title="Terminal">
              &#9002;
            </div>
            <div style={styles.contextIcon} title="File editor">
              &#128393;
            </div>
            <div style={styles.contextIcon} title="Search">
              &#128269;
            </div>
          </div>
          <div style={styles.contextHint}>
            Track tools and referenced files used in this task.
          </div>
        </Section>
      </div>
    </div>
  )
}
