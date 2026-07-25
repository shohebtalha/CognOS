import * as vscode from "vscode";

type ContextPayload = Record<string, unknown>;

export function activate(context: vscode.ExtensionContext) {
  const disposables = [
    vscode.window.onDidChangeActiveTextEditor(editor => {
      if (editor) sendActiveFile(editor);
    }),
    vscode.languages.onDidChangeDiagnostics(event => {
      for (const uri of event.uris) sendDiagnostics(uri);
    })
  ];
  if (vscode.window.activeTextEditor) sendActiveFile(vscode.window.activeTextEditor);
  context.subscriptions.push(...disposables);
}

export function deactivate() {}

function enabled(): boolean {
  return vscode.workspace.getConfiguration("cognos").get<boolean>("enabled", true);
}

function apiBase(): string {
  return vscode.workspace.getConfiguration("cognos").get<string>("apiBase", "http://127.0.0.1:8420");
}

async function ingest(event_type: string, payload: ContextPayload, confidence = 1.0) {
  if (!enabled()) return;
  try {
    await fetch(`${apiBase()}/events/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "vscode_extension", event_type, payload, confidence })
    });
  } catch {
    // CognOS may be offline; extension should never interrupt coding.
  }
}

function sendActiveFile(editor: vscode.TextEditor) {
  const doc = editor.document;
  ingest("editor_file_changed", {
    file_name: doc.fileName,
    language_id: doc.languageId,
    line_count: doc.lineCount,
    is_dirty: doc.isDirty,
    selection: {
      start_line: editor.selection.start.line,
      start_character: editor.selection.start.character,
      end_line: editor.selection.end.line,
      end_character: editor.selection.end.character
    }
  });
  sendDiagnostics(doc.uri);
}

function sendDiagnostics(uri: vscode.Uri) {
  const diagnostics = vscode.languages.getDiagnostics(uri)
    .filter(d => d.severity === vscode.DiagnosticSeverity.Error || d.severity === vscode.DiagnosticSeverity.Warning)
    .slice(0, 20)
    .map(d => ({
      message: d.message,
      severity: vscode.DiagnosticSeverity[d.severity],
      source: d.source,
      code: typeof d.code === "object" ? d.code.value : d.code,
      range: {
        start_line: d.range.start.line,
        start_character: d.range.start.character,
        end_line: d.range.end.line,
        end_character: d.range.end.character
      }
    }));
  if (diagnostics.length === 0) return;
  ingest("editor_diagnostic", {
    file_name: uri.fsPath,
    diagnostics
  }, 0.98);
}
