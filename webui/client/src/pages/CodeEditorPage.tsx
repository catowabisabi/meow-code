import { useState, useEffect, useRef, useCallback } from "react";
import MonacoEditor, { OnMount, OnChange } from "@monaco-editor/react";
import { editorService } from "../services/editor";
import styles from "./CodeEditor.module.css";

interface File {
  id: string;
  name: string;
  content: string;
  language: string;
  saved: boolean;
}

const DEFAULT_CODE = `// Welcome to Cato Claude IDE
// Start coding by opening a file or creating a new one

function greet(name: string): string {
    return \`Hello, \${name}!\`;
}

console.log(greet("World"));
`;

export function CodeEditorPage() {
  const [files, setFiles] = useState<File[]>([
    { id: "1", name: "main.ts", content: DEFAULT_CODE, language: "typescript", saved: true },
  ]);
  const [activeFileId, setActiveFileId] = useState("1");
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [theme, setTheme] = useState<"vs-dark" | "vs-light">("vs-dark");
  const editorRef = useRef<any>(null);

  const activeFile = files.find(f => f.id === activeFileId);

  const handleEditorMount: OnMount = (editor) => {
    editorRef.current = editor;
    editorService.initLSP(editor);
  };

  const handleEditorChange: OnChange = (value) => {
    if (!value || !activeFile) return;
    setFiles(files.map(f =>
      f.id === activeFileId ? { ...f, content: value, saved: false } : f
    ));
  };

  const handleNewFile = () => {
    const name = prompt("Enter file name:");
    if (!name) return;
    const ext = name.split(".").pop() || "txt";
    const lang = editorService.getLanguageFromExt(ext);
    const newFile: File = {
      id: Date.now().toString(),
      name,
      content: "",
      language: lang,
      saved: true,
    };
    setFiles([...files, newFile]);
    setActiveFileId(newFile.id);
  };

  const handleSave = () => {
    setFiles(files.map(f =>
      f.id === activeFileId ? { ...f, saved: true } : f
    ));
  };

  const handleCloseFile = (fileId: string) => {
    const newFiles = files.filter(f => f.id !== fileId);
    setFiles(newFiles);
    if (activeFileId === fileId && newFiles.length > 0) {
      setActiveFileId(newFiles[0].id);
    }
  };

  const handleRun = async () => {
    if (!activeFile) return;
    setTerminalOutput(prev => [...prev, `> Running ${activeFile.name}...`]);
    try {
      const result = await editorService.runCode(activeFile.content, activeFile.language);
      setTerminalOutput(prev => [...prev, result.output, "> Done"]);
    } catch (err: any) {
      setTerminalOutput(prev => [...prev, `Error: ${err.message}`]);
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === "vs-dark" ? "vs-light" : "vs-dark");
  };

  return (
    <div className={styles.container}>
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span>Files</span>
          <button onClick={handleNewFile} className={styles.iconButton}>+</button>
        </div>
        <div className={styles.fileList}>
          {files.map(file => (
            <div
              key={file.id}
              className={`${styles.fileItem} ${file.id === activeFileId ? styles.active : ""}`}
              onClick={() => setActiveFileId(file.id)}
            >
              <span className={styles.fileName}>{file.name}</span>
              {!file.saved && <span className={styles.unsavedDot} />}
              <button
                className={styles.closeButton}
                onClick={(e) => { e.stopPropagation(); handleCloseFile(file.id); }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.editorContainer}>
        <div className={styles.editorHeader}>
          <div className={styles.tabs}>
            {files.map(file => (
              <div
                key={file.id}
                className={`${styles.tab} ${file.id === activeFileId ? styles.activeTab : ""}`}
                onClick={() => setActiveFileId(file.id)}
              >
                <span>{file.name}</span>
                {!file.saved && <span className={styles.unsavedDot} />}
              </div>
            ))}
          </div>
          <div className={styles.editorActions}>
            <button onClick={handleSave} className={styles.actionButton} title="Save (Ctrl+S)">
              💾
            </button>
            <button onClick={toggleTheme} className={styles.actionButton} title="Toggle Theme">
              {theme === "vs-dark" ? "☀️" : "🌙"}
            </button>
            <button onClick={handleRun} className={styles.runButton} title="Run (Ctrl+Enter)">
              ▶ Run
            </button>
          </div>
        </div>

        <div className={styles.editorWrapper}>
          <MonacoEditor
            height="100%"
            language={activeFile?.language || "typescript"}
            value={activeFile?.content || ""}
            theme={theme}
            onMount={handleEditorMount}
            onChange={handleEditorChange}
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
              fontLigatures: true,
              lineNumbers: "on",
              renderWhitespace: "selection",
              bracketPairColorization: { enabled: true },
              automaticLayout: true,
              scrollBeyondLastLine: false,
              padding: { top: 16 },
            }}
          />
        </div>

        <div className={styles.terminal}>
          <div className={styles.terminalHeader}>
            <span>Terminal</span>
            <button onClick={() => setTerminalOutput([])} className={styles.clearButton}>Clear</button>
          </div>
          <div className={styles.terminalOutput}>
            {terminalOutput.map((line, i) => (
              <div key={i} className={styles.terminalLine}>{line}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}