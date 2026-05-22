import { useState, useEffect } from "react";
import { hooksApi, Hook, HookExecution } from "../services/hooks";
import styles from "./HooksPage.module.css";

export function HooksPage() {
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedHook, setSelectedHook] = useState<Hook | null>(null);
  const [executions, setExecutions] = useState<HookExecution[]>([]);

  useEffect(() => {
    loadHooks();
  }, []);

  const loadHooks = async () => {
    try {
      setLoading(true);
      const data = await hooksApi.getHooks();
      setHooks(data);
    } catch (err: any) {
      setError(err.message || "Failed to load hooks");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateHook = async (data: Partial<Hook>) => {
    try {
      await hooksApi.createHook(data);
      setShowCreateModal(false);
      loadHooks();
    } catch (err: any) {
      setError(err.message || "Failed to create hook");
    }
  };

  const handleUpdateHook = async (hookId: string, data: Partial<Hook>) => {
    try {
      await hooksApi.updateHook(hookId, data);
      setSelectedHook(null);
      loadHooks();
    } catch (err: any) {
      setError(err.message || "Failed to update hook");
    }
  };

  const handleDeleteHook = async (hookId: string) => {
    if (!confirm("Are you sure you want to delete this hook?")) return;
    try {
      await hooksApi.deleteHook(hookId);
      loadHooks();
    } catch (err: any) {
      setError(err.message || "Failed to delete hook");
    }
  };

  const handleExecuteHook = async (hookId: string) => {
    try {
      await hooksApi.executeHook(hookId);
      loadHooks();
    } catch (err: any) {
      setError(err.message || "Failed to execute hook");
    }
  };

  const loadExecutions = async (hookId: string) => {
    try {
      const data = await hooksApi.getHookExecutions(hookId);
      setExecutions(data);
    } catch (err: any) {
      console.error("Failed to load executions", err);
    }
  };

  const getTriggerIcon = (triggerType: string) => {
    switch (triggerType) {
      case "on_commit": return "✓";
      case "on_pr": return "⬡";
      case "on_deploy": return "🚀";
      case "on_timer": return "⏰";
      default: return "⚡";
    }
  };

  if (loading) return <div className={styles.loading}>Loading hooks...</div>;
  if (error) return <div className={styles.error}>{error}</div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Hooks</h1>
        <button className={styles.buttonPrimary} onClick={() => setShowCreateModal(true)}>
          Create Hook
        </button>
      </div>

      <div className={styles.hooksList}>
        {hooks.length === 0 ? (
          <div className={styles.empty}>No hooks configured</div>
        ) : (
          hooks.map(hook => (
            <div key={hook.id} className={`${styles.hookCard} ${!hook.is_active ? styles.inactive : ""}`}>
              <div className={styles.hookHeader}>
                <span className={styles.triggerIcon}>{getTriggerIcon(hook.trigger_type)}</span>
                <div className={styles.hookInfo}>
                  <h3 className={styles.hookName}>{hook.name}</h3>
                  <span className={styles.hookType}>{hook.hook_type}</span>
                </div>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    checked={hook.is_active}
                    onChange={() => handleUpdateHook(hook.id, { is_active: !hook.is_active })}
                  />
                  <span className={styles.slider}></span>
                </label>
              </div>
              <div className={styles.hookMeta}>
                <span>Trigger: {hook.trigger_type}</span>
                <span>Created: {new Date(hook.created_at).toLocaleDateString()}</span>
              </div>
              <div className={styles.hookActions}>
                <button className={styles.buttonSmall} onClick={() => { setSelectedHook(hook); loadExecutions(hook.id); }}>
                  View Executions
                </button>
                <button className={styles.buttonSmall} onClick={() => handleExecuteHook(hook.id)}>
                  Execute
                </button>
                <button className={styles.buttonSmall} onClick={() => setSelectedHook(hook)}>
                  Edit
                </button>
                <button className={styles.buttonDanger} onClick={() => handleDeleteHook(hook.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <HookModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateHook}
        />
      )}

      {selectedHook && (
        <HookModal
          hook={selectedHook}
          onClose={() => setSelectedHook(null)}
          onSubmit={(data) => handleUpdateHook(selectedHook.id, data)}
        />
      )}
    </div>
  );
}

function HookModal({ hook, onClose, onSubmit }: { hook?: Hook; onClose: () => void; onSubmit: (data: Partial<Hook>) => void }) {
  const [name, setName] = useState(hook?.name || "");
  const [triggerType, setTriggerType] = useState(hook?.trigger_type || "on_commit");
  const [hookType, setHookType] = useState(hook?.hook_type || "webhook");
  const [code, setCode] = useState(hook?.code || "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      trigger_type: triggerType,
      hook_type: hookType,
      code,
      config: {},
    });
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <h2 className={styles.modalTitle}>{hook ? "Edit Hook" : "Create Hook"}</h2>
        <form onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label>Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className={styles.field}>
            <label>Trigger Type</label>
            <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              <option value="on_commit">On Commit</option>
              <option value="on_pr">On Pull Request</option>
              <option value="on_deploy">On Deploy</option>
              <option value="on_timer">On Timer</option>
            </select>
          </div>
          <div className={styles.field}>
            <label>Hook Type</label>
            <select value={hookType} onChange={(e) => setHookType(e.target.value)}>
              <option value="webhook">Webhook</option>
              <option value="script">Script</option>
              <option value="pipeline">Pipeline</option>
            </select>
          </div>
          <div className={styles.field}>
            <label>Code (optional)</label>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={6} />
          </div>
          <div className={styles.modalActions}>
            <button type="button" className={styles.buttonSecondary} onClick={onClose}>Cancel</button>
            <button type="submit" className={styles.buttonPrimary}>{hook ? "Update" : "Create"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}