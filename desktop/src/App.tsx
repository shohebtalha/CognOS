import React, { useEffect, useState } from "react";
import { Activity, Brain, Check, Layers, Lock, MessageSquare, Radar, Settings as SettingsIcon, ShieldAlert, Sparkles, X } from "lucide-react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Suggestion = { id: number; ts: string; app_name: string; window_title: string; suggestion: string };
type Permission = { key: string; label: string; state: string; detail: string };
type AssistantAction = { id: string; label: string; kind: string; payload: Record<string, unknown> };
type AssistantCard = { id: number; ts: string; kind: string; severity: string; title: string; summary: string; source: string; confidence: number; actions: AssistantAction[]; status: string };
type MonitorStatus = { running: boolean; registered_plugins: string[]; last_error: string | null; events_seen: number; cards_emitted: number; connectors: Record<string, string> };
type BackendStatus = { running: boolean; pid: number | null; lastError: string | null; mode: string };
type TimelineItem = { id: number; ts: string; source: string; event_type: string; summary: string; confidence: number | null };
type UserSettings = {
  desktop_monitor_enabled: boolean;
  ocr_monitor_enabled: boolean;
  clipboard_monitor_enabled: boolean;
  native_notifications_enabled: boolean;
  native_notification_min_severity: string;
  llm_model: string;
  terminal_monitor_enabled: boolean;
  terminal_transcript_path: string | null;
  watched_paths: string[] | null;
};
type ModelStatus = { reachable: boolean; configured_model: string; installed_models: string[]; error?: string };

const apiBase = window.cognos?.apiBase ?? "http://127.0.0.1:8420";

function App() {
  const [health, setHealth] = useState("connecting");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [cards, setCards] = useState<AssistantCard[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [monitor, setMonitor] = useState<MonitorStatus | null>(null);
  const [backend, setBackend] = useState<BackendStatus | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  useEffect(() => {
    refresh();
    const events = new EventSource(`${apiBase}/events`);
    events.onmessage = refresh;
    events.addEventListener("assistant_card", refresh);
    return () => events.close();
  }, []);

  async function refresh() {
    try {
      if (window.cognos?.backendStatus) {
        setBackend(await window.cognos.backendStatus());
      }
      const [h, s, c, p, m, t] = await Promise.all([
        fetch(`${apiBase}/health`).then(r => r.json()),
        fetch(`${apiBase}/suggestions`).then(r => r.json()),
        fetch(`${apiBase}/cards`).then(r => r.json()),
        fetch(`${apiBase}/permissions`).then(r => r.json()),
        fetch(`${apiBase}/monitor/status`).then(r => r.json()),
        fetch(`${apiBase}/timeline?limit=30`).then(r => r.json())
      ]);
      setHealth(h.status);
      setSuggestions(s);
      setCards(c);
      setPermissions(p);
      setMonitor(m);
      setTimeline(t);
      const [settingsResponse, modelResponse] = await Promise.all([
        fetch(`${apiBase}/settings`).then(r => r.json()),
        fetch(`${apiBase}/model/status`).then(r => r.json())
      ]);
      setSettings(settingsResponse);
      setModelStatus(modelResponse);
    } catch {
      setHealth("offline");
    }
  }

  async function askWithPrompt(prompt: string) {
    if (!prompt.trim()) return;
    setAnswer("Thinking locally...");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 130000);
    try {
      const res = await fetch(`${apiBase}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt }),
        signal: controller.signal
      });
      const data = await res.json();
      setAnswer(data.answer);
    } catch {
      setAnswer("The local AI is taking too long to answer. Try a shorter prompt, or use a smaller Ollama model like llama3.2:latest.");
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function ask() {
    await askWithPrompt(question);
  }

  async function runAction(action: AssistantAction) {
    const exec = await fetch(`${apiBase}/actions/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: action.kind, payload: action.payload })
    }).then(r => r.json());
    if (exec.requires_confirmation && !window.confirm(exec.message)) return;
    if (exec.requires_confirmation) {
      await fetch(`${apiBase}/actions/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: action.kind, payload: action.payload, confirmed: true })
      });
    }
    if (action.kind === "ask") {
      const prompt = String(exec.result?.prompt ?? action.payload.prompt ?? "");
      setQuestion(prompt);
      await askWithPrompt(prompt);
    }
  }

  async function dismiss(cardId: number) {
    await fetch(`${apiBase}/cards/${cardId}/dismiss`, { method: "POST" });
    setCards(cards.filter(card => card.id !== cardId));
  }

  async function updateSettings(patch: Partial<UserSettings>) {
    const res = await fetch(`${apiBase}/settings`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch)
    });
    const updated = await res.json();
    setSettings(updated);
    await refresh();
  }

  return (
    location.hash === "#overlay" ? <Overlay cards={cards} refresh={refresh} runAction={runAction} dismiss={dismiss} /> :
    <main>
      <aside>
        <div className="brand"><Brain size={28}/><span>CognOS</span></div>
        <nav>
          <button className="active"><Radar size={18}/> Live</button>
          <button><MessageSquare size={18}/> Ask</button>
          <button><Lock size={18}/> Permissions</button>
          <button><SettingsIcon size={18}/> Settings</button>
        </nav>
        <div className={`status ${health}`}>{health}</div>
      </aside>
      <section className="workspace">
        <header>
          <div>
            <h1>Desktop Intelligence Layer</h1>
            <p>Local-first context, proactive action cards, explicit permissions.</p>
          </div>
          <div className="headerActions">
            <button className="pill" onClick={() => window.cognos?.toggleOverlay()}><Layers size={16}/> Overlay</button>
            <div className="pill"><Activity size={16}/> Always-on monitor</div>
          </div>
        </header>
        <div className="grid">
          <section className="panel feed">
            <h2><Sparkles size={17}/> Assistant Cards</h2>
            {cards.length === 0 && <p className="muted">No live cards yet. Start capture or send a browser, IDE, file, clipboard, or OCR event.</p>}
            {cards.map(card => (
              <article className={`card ${card.severity}`} key={card.id}>
                <div className="cardTop">
                  <div className="meta">{card.kind} · {card.source} · {new Date(card.ts).toLocaleTimeString()}</div>
                  <button className="icon" onClick={() => dismiss(card.id)} title="Dismiss"><X size={15}/></button>
                </div>
                <strong>{card.title}</strong>
                <p>{card.summary}</p>
                <div className="actions">
                  {card.actions.map(action => (
                    <button key={action.id} onClick={() => runAction(action)}><Check size={15}/>{action.label}</button>
                  ))}
                </div>
              </article>
            ))}
          </section>
          <section className="panel ask">
            <h2>Ask About Now</h2>
            {monitor && (
              <div className="monitor">
                <strong>{monitor.running ? "Automatic monitor running" : "Automatic monitor stopped"}</strong>
                <p>{monitor.registered_plugins.join(", ") || "No observers registered"} · {monitor.events_seen} events · {monitor.cards_emitted} cards</p>
                <p>{Object.entries(monitor.connectors || {}).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>
                {monitor.last_error && <p className="warn">{monitor.last_error}</p>}
              </div>
            )}
            {backend && (
              <div className="monitor">
                <strong>{backend.running ? "Backend online" : "Backend offline"}</strong>
                <p>{backend.mode}{backend.pid ? ` · pid ${backend.pid}` : ""}</p>
                {backend.lastError && <p className="warn">{backend.lastError}</p>}
              </div>
            )}
            <textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about visible errors, a workflow, a document, or recent activity."/>
            <button className="primary" onClick={ask}>Ask CognOS</button>
            {answer && <p className="answer">{answer}</p>}
          </section>
          <section className="panel permissions">
            <h2>Permissions</h2>
            {permissions.map(p => (
              <div className="permission" key={p.key}>
                <ShieldAlert size={16}/>
                <div><strong>{p.label}</strong><p>{p.state}: {p.detail}</p></div>
              </div>
            ))}
          </section>
          <section className="panel settings">
            <h2><SettingsIcon size={17}/> Settings</h2>
            {settings && (
              <>
                <Toggle label="Desktop monitor" checked={settings.desktop_monitor_enabled} onChange={v => updateSettings({ desktop_monitor_enabled: v })} />
                <Toggle label="OCR screen understanding" checked={settings.ocr_monitor_enabled} onChange={v => updateSettings({ ocr_monitor_enabled: v })} />
                <Toggle label="Clipboard monitor" checked={settings.clipboard_monitor_enabled} onChange={v => updateSettings({ clipboard_monitor_enabled: v })} />
                <Toggle label="Terminal transcript monitor" checked={settings.terminal_monitor_enabled} onChange={v => updateSettings({ terminal_monitor_enabled: v })} />
                <Toggle label="Windows notifications" checked={settings.native_notifications_enabled} onChange={v => updateSettings({ native_notifications_enabled: v })} />
                <label className="field">
                  <span>Model</span>
                  <input value={settings.llm_model} onChange={e => setSettings({ ...settings, llm_model: e.target.value })} onBlur={e => updateSettings({ llm_model: e.target.value })} />
                </label>
                {modelStatus && (
                  <div className="monitor">
                    <strong>{modelStatus.reachable ? "Ollama reachable" : "Ollama offline"}</strong>
                    <p>Configured: {modelStatus.configured_model}</p>
                    <p>Installed: {modelStatus.installed_models.join(", ") || "none detected"}</p>
                    {modelStatus.error && <p className="warn">{modelStatus.error}</p>}
                  </div>
                )}
              </>
            )}
          </section>
          <section className="panel history">
            <h2>Suggestion History</h2>
            {suggestions.length === 0 && <p className="muted">No saved LLM suggestions yet.</p>}
            {suggestions.slice(0, 5).map(item => (
              <article className="suggestion" key={item.id}>
                <div className="meta">{item.app_name} · {new Date(item.ts).toLocaleTimeString()}</div>
                <strong>{item.window_title || "Current activity"}</strong>
                <p>{item.suggestion}</p>
              </article>
            ))}
          </section>
          <section className="panel timeline">
            <h2>Context Timeline</h2>
            {timeline.length === 0 && <p className="muted">No observed context yet.</p>}
            {timeline.slice(0, 12).map(item => (
              <article className="timelineItem" key={item.id}>
                <div className="meta">{item.source} · {item.event_type} · {new Date(item.ts).toLocaleTimeString()}</div>
                <p>{item.summary}</p>
              </article>
            ))}
          </section>
        </div>
      </section>
    </main>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="toggle">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
    </label>
  );
}

function Overlay({ cards, refresh, runAction, dismiss }: {
  cards: AssistantCard[];
  refresh: () => Promise<void>;
  runAction: (action: AssistantAction) => Promise<void>;
  dismiss: (cardId: number) => Promise<void>;
}) {
  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 4000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="overlay">
      <div className="overlayHeader">
        <strong>CognOS</strong>
        <span>{cards.length} live</span>
      </div>
      {cards.length === 0 && <p className="muted">Watching quietly. Important moments will appear here.</p>}
      {cards.slice(0, 4).map(card => (
        <article className={`card ${card.severity}`} key={card.id}>
          <div className="cardTop">
            <div className="meta">{card.kind} · {card.source}</div>
            <button className="icon" onClick={() => dismiss(card.id)} title="Dismiss"><X size={15}/></button>
          </div>
          <strong>{card.title}</strong>
          <p>{card.summary}</p>
          <div className="actions">
            {card.actions.slice(0, 2).map(action => (
              <button key={action.id} onClick={() => runAction(action)}><Check size={15}/>{action.label}</button>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
