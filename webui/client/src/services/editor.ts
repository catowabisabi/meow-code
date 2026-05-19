import * as monaco from "monaco-editor";

export const editorService = {
  async initLSP(editor: any): Promise<void> {
    editor.onDidChangeModelContent(() => {
    });
  },

  getLanguageFromExt(ext: string): string {
    const langMap: Record<string, string> = {
      ts: "typescript",
      tsx: "typescript",
      js: "javascript",
      jsx: "javascript",
      py: "python",
      rs: "rust",
      go: "go",
      java: "java",
      cpp: "cpp",
      c: "c",
      cs: "csharp",
      rb: "ruby",
      php: "php",
      html: "html",
      css: "css",
      json: "json",
      md: "markdown",
      yaml: "yaml",
      yml: "yaml",
      sh: "shell",
      bash: "shell",
    };
    return langMap[ext.toLowerCase()] || "plaintext";
  },

  async runCode(code: string, language: string): Promise<{ output: string }> {
    return { output: `[Simulated] Would run ${language} code:\n${code.substring(0, 100)}...` };
  },

  formatCode(code: string): string {
    return code;
  },
};