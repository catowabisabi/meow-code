import * as monaco from "monaco-editor";

const API_BASE = "/api/lsp";

interface LSPCompletionItem {
  label: string;
  kind: number;
  detail?: string;
  documentation?: string;
  insertText: string;
  range?: {
    startLineNumber: number;
    startColumn: number;
    endLineNumber: number;
    endColumn: number;
  };
}

interface LSPHover {
  contents: string | { language: string; value: string } | Array<{ language: string; value: string }>;
  range?: {
    startLineNumber: number;
    startColumn: number;
    endLineNumber: number;
    endColumn: number;
  };
}

interface LSPLocation {
  uri: string;
  range: {
    startLineNumber: number;
    startColumn: number;
    endLineNumber: number;
    endColumn: number;
  };
}

class LSPClient {
  private editor: monaco.editor.IStandaloneCodeEditor | null = null;
  private language: string = "typescript";
  private disposables: monaco.IDisposable[] = [];
  private completionProvider: monaco.languages.registerCompletionItemProvider | null = null;
  private hoverProvider: monaco.languages.registerHoverProvider | null = null;
  private definitionProvider: monaco.languages.registerDefinitionProvider | null = null;

  init(editor: monaco.editor.IStandaloneCodeEditor, language: string): void {
    this.editor = editor;
    this.language = language;
    this.setupProviders();
  }

  private setupProviders(): void {
    if (!this.editor) return;

    this.completionProvider = monaco.languages.registerCompletionItemProvider({
      triggerCharacters: [".", "(", "[", "'", '"'],
      provideCompletionItems: async (model, position) => {
        try {
          const response = await this.fetchCompletions(model.uri.path, {
            line: position.lineNumber,
            character: position.column,
          });
          return {
            suggestions: response.items.map((item: LSPCompletionItem) => ({
              label: item.label,
              kind: item.kind,
              detail: item.detail,
              documentation: item.documentation,
              insertText: item.insertText,
              range: item.range,
            })),
          };
        } catch {
          return { suggestions: [] };
        }
      },
    });

    this.hoverProvider = monaco.languages.registerHoverProvider(this.language, {
      provideHover: async (model, position) => {
        try {
          const response = await this.fetchHover(model.uri.path, {
            line: position.lineNumber,
            character: position.column,
          });
          if (!response || !response.contents) return null;
          return {
            contents: Array.isArray(response.contents)
              ? response.contents.map(c => (typeof c === "string" ? c : c.value))
              : [response.contents],
            range: response.range,
          };
        } catch {
          return null;
        }
      },
    });

    this.definitionProvider = monaco.languages.registerDefinitionProvider(this.language, {
      provideDefinition: async (model, position) => {
        try {
          const response = await this.fetchDefinition(model.uri.path, {
            line: position.lineNumber,
            character: position.column,
          });
          if (!response || !response.locations) return [];
          return response.locations.map((loc: LSPLocation) => ({
            uri: monaco.Uri.parse(loc.uri),
            range: loc.range,
          }));
        } catch {
          return [];
        }
      },
    });
  }

  private async fetchCompletions(filePath: string, position: { line: number; character: number }): Promise<{ items: LSPCompletionItem[] }> {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`${API_BASE}/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        language: this.language,
        file_path: filePath,
        position,
        content: this.editor?.getModel()?.getValue() || "",
      }),
    });
    return response.json();
  }

  private async fetchHover(filePath: string, position: { line: number; character: number }): Promise<LSPHover> {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`${API_BASE}/hover`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        language: this.language,
        file_path: filePath,
        position,
      }),
    });
    return response.json();
  }

  private async fetchDefinition(filePath: string, position: { line: number; character: number }): Promise<{ locations: LSPLocation[] }> {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`${API_BASE}/definition`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        language: this.language,
        file_path: filePath,
        position,
      }),
    });
    return response.json();
  }

  async initialize(): Promise<void> {
    const token = localStorage.getItem("access_token");
    await fetch(`${API_BASE}/initialize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        language: this.language,
        root_uri: "/workspace",
      }),
    });
  }

  dispose(): void {
    if (this.completionProvider) {
      this.completionProvider.dispose();
    }
    if (this.hoverProvider) {
      this.hoverProvider.dispose();
    }
    if (this.definitionProvider) {
      this.definitionProvider.dispose();
    }
    this.disposables.forEach(d => d.dispose());
    this.disposables = [];
  }
}

const lspClient = new LSPClient();

export const editorService = {
  async initLSP(editor: monaco.editor.IStandaloneCodeEditor): Promise<void> {
    const model = editor.getModel();
    if (!model) return;
    
    const fileName = model.uri.path;
    const ext = fileName.split(".").pop() || "";
    const language = editorService.getLanguageFromExt(ext);
    
    lspClient.init(editor, language);
    await lspClient.initialize();
    
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK, () => {
      const position = editor.getPosition();
      if (position) {
        editor.getModel()?.getLineContent(position.lineNumber);
      }
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
    return { output: `[Simulated] Would run ${language} code` };
  },

  formatCode(code: string): string {
    return code;
  },
};