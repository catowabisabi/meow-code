import { useState, useEffect } from "react";
import { gitService } from "../../services/git";
import styles from "./GitPanel.module.css";

interface GitStatus {
  branch: string;
  staged: string[];
  modified: string[];
  untracked: string[];
  conflicted: string[];
}

interface GitCommit {
  hash: string;
  message: string;
  author: string;
  date: string;
}

interface DiffHunk {
  lines: string[];
  additions: number;
  deletions: number;
}

interface Diff {
  file: string;
  status: string;
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
}

export function GitPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [branches, setBranches] = useState<{ current: string; local: string[]; remote: string[] } | null>(null);
  const [commits, setCommits] = useState<GitCommit[]>([]);
  const [diff, setDiff] = useState<Diff[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"changes" | "branches" | "history">("changes");
  const [commitMessage, setCommitMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadStatus();
      loadBranches();
      loadCommits();
    }
  }, [isOpen]);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await gitService.getStatus();
      setStatus(data);
      const diffData = await gitService.getDiff();
      setDiff(diffData.diffs);
    } catch (err) {
      console.error("Failed to load git status", err);
    } finally {
      setLoading(false);
    }
  };

  const loadBranches = async () => {
    try {
      const data = await gitService.getBranches();
      setBranches(data);
    } catch (err) {
      console.error("Failed to load branches", err);
    }
  };

  const loadCommits = async () => {
    try {
      const data = await gitService.getLog();
      setCommits(data.commits);
    } catch (err) {
      console.error("Failed to load commits", err);
    }
  };

  const handleStage = async (files: string[]) => {
    try {
      await gitService.stage(files);
      await loadStatus();
    } catch (err) {
      console.error("Failed to stage files", err);
    }
  };

  const handleUnstage = async (files: string[]) => {
    try {
      await gitService.unstage(files);
      await loadStatus();
    } catch (err) {
      console.error("Failed to unstage files", err);
    }
  };

  const handleCommit = async () => {
    if (!commitMessage.trim()) return;
    try {
      await gitService.commit(commitMessage);
      setCommitMessage("");
      await loadStatus();
      await loadCommits();
    } catch (err) {
      console.error("Failed to commit", err);
    }
  };

  const handleCheckout = async (branch: string) => {
    try {
      await gitService.checkout(branch);
      await loadStatus();
      await loadBranches();
    } catch (err) {
      console.error("Failed to checkout", err);
    }
  };

  const getFileIcon = (file: string) => {
    if (file.endsWith(".ts") || file.endsWith(".tsx")) return "📘";
    if (file.endsWith(".js") || file.endsWith(".jsx")) return "📒";
    if (file.endsWith(".py")) return "🐍";
    if (file.endsWith(".css")) return "🎨";
    if (file.endsWith(".json")) return "📋";
    return "📄";
  };

  if (!isOpen) {
    return (
      <button className={styles.toggleButton} onClick={() => setIsOpen(true)}>
        <span className={styles.toggleIcon}>⎇</span>
        <span>Git</span>
        {status && (status.staged.length > 0 || status.modified.length > 0) && (
          <span className={styles.badge}>
            {status.staged.length + status.modified.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === "changes" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("changes")}
          >
            Changes
          </button>
          <button
            className={`${styles.tab} ${activeTab === "branches" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("branches")}
          >
            Branches
          </button>
          <button
            className={`${styles.tab} ${activeTab === "history" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("history")}
          >
            History
          </button>
        </div>
        <button className={styles.closeButton} onClick={() => setIsOpen(false)}>×</button>
      </div>

      <div className={styles.content}>
        {activeTab === "changes" && status && (
          <div className={styles.changesTab}>
            <div className={styles.branchInfo}>
              <span className={styles.branchIcon}>⎇</span>
              <span>{status.branch}</span>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <span>Staged Changes</span>
                {status.staged.length > 0 && (
                  <button
                    className={styles.unstageAllButton}
                    onClick={() => handleUnstage(status.staged)}
                  >
                    Unstage All
                  </button>
                )}
              </div>
              {status.staged.length === 0 ? (
                <div className={styles.emptyMessage}>No staged changes</div>
              ) : (
                <div className={styles.fileList}>
                  {status.staged.map(file => (
                    <div key={file} className={styles.fileItem}>
                      <span className={styles.fileIcon}>{getFileIcon(file)}</span>
                      <span className={styles.fileName}>{file}</span>
                      <button
                        className={styles.fileAction}
                        onClick={() => handleUnstage([file])}
                      >
                        −
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <span>Changed Files</span>
                {status.modified.length > 0 && (
                  <button
                    className={styles.stageAllButton}
                    onClick={() => handleStage(status.modified)}
                  >
                    Stage All
                  </button>
                )}
              </div>
              {status.modified.length === 0 && status.untracked.length === 0 ? (
                <div className={styles.emptyMessage}>No changed files</div>
              ) : (
                <div className={styles.fileList}>
                  {status.modified.map(file => (
                    <div key={file} className={styles.fileItem}>
                      <span className={styles.fileIcon}>{getFileIcon(file)}</span>
                      <span className={styles.fileName}>{file}</span>
                      <button
                        className={styles.fileAction}
                        onClick={() => handleStage([file])}
                      >
                        +
                      </button>
                    </div>
                  ))}
                  {status.untracked.map(file => (
                    <div key={file} className={`${styles.fileItem} ${styles.untracked}`}>
                      <span className={styles.fileIcon}>{getFileIcon(file)}</span>
                      <span className={styles.fileName}>{file}</span>
                      <button
                        className={styles.fileAction}
                        onClick={() => handleStage([file])}
                      >
                        +
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {status.staged.length > 0 && (
              <div className={styles.commitSection}>
                <textarea
                  className={styles.commitInput}
                  placeholder="Commit message..."
                  value={commitMessage}
                  onChange={(e) => setCommitMessage(e.target.value)}
                  rows={3}
                />
                <button
                  className={styles.commitButton}
                  onClick={handleCommit}
                  disabled={!commitMessage.trim()}
                >
                  Commit ({status.staged.length} file{status.staged.length > 1 ? "s" : ""})
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "branches" && branches && (
          <div className={styles.branchesTab}>
            <div className={styles.currentBranch}>
              <span className={styles.branchLabel}>Current:</span>
              <span className={styles.branchName}>{branches.current}</span>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionHeader}>Local Branches</div>
              <div className={styles.branchList}>
                {branches.local.map(branch => (
                  <div
                    key={branch}
                    className={`${styles.branchItem} ${branch === branches.current ? styles.currentBranchItem : ""}`}
                    onClick={() => handleCheckout(branch)}
                  >
                    <span className={styles.branchIcon}>⑂</span>
                    <span>{branch}</span>
                  </div>
                ))}
              </div>
            </div>

            {branches.remote.length > 0 && (
              <div className={styles.section}>
                <div className={styles.sectionHeader}>Remote Branches</div>
                <div className={styles.branchList}>
                  {branches.remote.map(branch => (
                    <div key={branch} className={styles.branchItem}>
                      <span className={styles.branchIcon}>↑</span>
                      <span>{branch}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "history" && (
          <div className={styles.historyTab}>
            {commits.length === 0 ? (
              <div className={styles.emptyMessage}>No commits yet</div>
            ) : (
              <div className={styles.commitList}>
                {commits.map(commit => (
                  <div key={commit.hash} className={styles.commitItem}>
                    <div className={styles.commitHash}>{commit.hash.substring(0, 7)}</div>
                    <div className={styles.commitMessage}>{commit.message}</div>
                    <div className={styles.commitMeta}>
                      <span>{commit.author}</span>
                      <span>·</span>
                      <span>{new Date(commit.date).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}