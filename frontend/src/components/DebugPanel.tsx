import { useState, useEffect } from "react";
import { debuggerService } from "../../services/debugger";
import styles from "./DebugPanel.module.css";

interface Breakpoint {
  id: string;
  source: string;
  line: number;
  enabled: boolean;
  condition?: string;
}

interface StackFrame {
  id: string;
  name: string;
  source: string;
  line: number;
  column: number;
}

interface Variable {
  name: string;
  value: string;
  type: string;
}

export function DebugPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [breakpoints, setBreakpoints] = useState<Breakpoint[]>([]);
  const [stack, setStack] = useState<StackFrame[]>([]);
  const [variables, setVariables] = useState<Variable[]>([]);
  const [watchExpressions, setWatchExpressions] = useState<string[]>([]);
  const [newWatch, setNewWatch] = useState("");
  const [activeTab, setActiveTab] = useState<"breakpoints" | "variables" | "watch">("breakpoints");

  useEffect(() => {
    if (isOpen) {
      loadDebugState();
    }
  }, [isOpen]);

  const loadDebugState = async () => {
    try {
      const [bpData, stackData, varData] = await Promise.all([
        debuggerService.getBreakpoints(),
        debuggerService.getStackTrace(),
        debuggerService.getVariables(),
      ]);
      setBreakpoints(bpData.breakpoints || []);
      setStack(stackData.frames || []);
      setVariables(varData.variables || []);
      setConnected(true);
    } catch (err) {
      setConnected(false);
    }
  };

  const handleConnect = async () => {
    try {
      await debuggerService.startDebugger();
      setConnected(true);
    } catch (err) {
      console.error("Failed to connect", err);
    }
  };

  const handleDisconnect = async () => {
    try {
      await debuggerService.stop();
      setConnected(false);
      setPaused(false);
    } catch (err) {
      console.error("Failed to disconnect", err);
    }
  };

  const handleResume = async () => {
    try {
      await debuggerService.resume();
      setPaused(false);
      setStack([]);
      setVariables([]);
    } catch (err) {
      console.error("Failed to resume", err);
    }
  };

  const handlePause = async () => {
    try {
      await debuggerService.pause();
      setPaused(true);
      await loadDebugState();
    } catch (err) {
      console.error("Failed to pause", err);
    }
  };

  const handleStepOver = async () => {
    try {
      await debuggerService.stepOver();
      await loadDebugState();
    } catch (err) {
      console.error("Failed to step over", err);
    }
  };

  const handleStepInto = async () => {
    try {
      await debuggerService.stepInto();
      await loadDebugState();
    } catch (err) {
      console.error("Failed to step into", err);
    }
  };

  const handleStepOut = async () => {
    try {
      await debuggerService.stepOut();
      await loadDebugState();
    } catch (err) {
      console.error("Failed to step out", err);
    }
  };

  const toggleBreakpoint = async (bp: Breakpoint) => {
    try {
      if (bp.enabled) {
        await debuggerService.removeBreakpoint(bp.id);
      } else {
        await debuggerService.setBreakpoint(bp.source, bp.line);
      }
      loadDebugState();
    } catch (err) {
      console.error("Failed to toggle breakpoint", err);
    }
  };

  const addWatchExpression = async () => {
    if (!newWatch.trim()) return;
    setWatchExpressions([...watchExpressions, newWatch]);
    setNewWatch("");
  };

  const removeWatchExpression = (expr: string) => {
    setWatchExpressions(watchExpressions.filter(e => e !== expr));
  };

  const getBreakpointIcon = (bp: Breakpoint) => {
    return bp.enabled ? "●" : "○";
  };

  if (!isOpen) {
    return (
      <button className={styles.toggleButton} onClick={() => setIsOpen(true)}>
        <span className={styles.toggleIcon}>🐛</span>
        <span>Debug</span>
        {paused && <span className={styles.pausedBadge}>PAUSED</span>}
      </button>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.title}>Debug</span>
          <span className={`${styles.status} ${connected ? styles.connected : styles.disconnected}`}>
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <button className={styles.closeButton} onClick={() => setIsOpen(false)}>×</button>
      </div>

      <div className={styles.toolbar}>
        {connected ? (
          <>
            {paused ? (
              <div className={styles.controls}>
                <button className={styles.controlButton} onClick={handleResume} title="Resume (F5)">
                  ▶
                </button>
                <button className={styles.controlButton} onClick={handleStepOver} title="Step Over (F10)">
                  →
                </button>
                <button className={styles.controlButton} onClick={handleStepInto} title="Step Into (F11)">
                  ↓|
                </button>
                <button className={styles.controlButton} onClick={handleStepOut} title="Step Out (Shift+F11)">
                  |↑
                </button>
              </div>
            ) : (
              <button className={styles.pauseButton} onClick={handlePause}>
                ⏸ Pause
              </button>
            )}
            <button className={styles.disconnectButton} onClick={handleDisconnect}>
              Disconnect
            </button>
          </>
        ) : (
          <button className={styles.connectButton} onClick={handleConnect}>
            Connect to Chrome
          </button>
        )}
      </div>

      {paused && stack.length > 0 && (
        <div className={styles.callStackSection}>
          <div className={styles.sectionTitle}>Call Stack</div>
          <div className={styles.callStack}>
            {stack.map((frame, index) => (
              <div key={frame.id} className={`${styles.frame} ${index === 0 ? styles.activeFrame : ""}`}>
                <span className={styles.frameName}>{frame.name}</span>
                <span className={styles.frameLocation}>
                  {frame.source}:{frame.line}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "breakpoints" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("breakpoints")}
        >
          Breakpoints
        </button>
        <button
          className={`${styles.tab} ${activeTab === "variables" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("variables")}
        >
          Variables
        </button>
        <button
          className={`${styles.tab} ${activeTab === "watch" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("watch")}
        >
          Watch
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === "breakpoints" && (
          <div className={styles.breakpointsList}>
            {breakpoints.length === 0 ? (
              <div className={styles.emptyMessage}>No breakpoints</div>
            ) : (
              breakpoints.map(bp => (
                <div key={bp.id} className={`${styles.breakpointItem} ${!bp.enabled ? styles.disabled : ""}`}>
                  <span
                    className={styles.breakpointIcon}
                    onClick={() => toggleBreakpoint(bp)}
                  >
                    {getBreakpointIcon(bp)}
                  </span>
                  <span className={styles.breakpointSource}>{bp.source}</span>
                  <span className={styles.breakpointLine}>Line {bp.line}</span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "variables" && (
          <div className={styles.variablesList}>
            {variables.length === 0 ? (
              <div className={styles.emptyMessage}>No variables</div>
            ) : (
              variables.map(v => (
                <div key={v.name} className={styles.variableItem}>
                  <span className={styles.variableName}>{v.name}</span>
                  <span className={styles.variableType}>{v.type}</span>
                  <span className={styles.variableValue}>{v.value}</span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "watch" && (
          <div className={styles.watchList}>
            <div className={styles.addWatch}>
              <input
                type="text"
                className={styles.watchInput}
                placeholder="Add expression..."
                value={newWatch}
                onChange={(e) => setNewWatch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addWatchExpression()}
              />
              <button className={styles.addButton} onClick={addWatchExpression}>+</button>
            </div>
            {watchExpressions.length === 0 ? (
              <div className={styles.emptyMessage}>No watch expressions</div>
            ) : (
              watchExpressions.map(expr => (
                <div key={expr} className={styles.watchItem}>
                  <span className={styles.watchExpression}>{expr}</span>
                  <button
                    className={styles.removeButton}
                    onClick={() => removeWatchExpression(expr)}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
