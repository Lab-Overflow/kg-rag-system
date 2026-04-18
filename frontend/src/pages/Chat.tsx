import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamSSE, apiJSON } from "../lib/api";

type Msg = { role: "user" | "assistant"; text: string; citations?: any[] };

const MODES = ["agentic", "hybrid", "local_graph", "global_graph", "hippo"] as const;

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<(typeof MODES)[number]>("agentic");
  const [streaming, setStreaming] = useState(false);

  const send = async () => {
    if (!q.trim()) return;
    const userMsg: Msg = { role: "user", text: q };
    setMessages((m) => [...m, userMsg, { role: "assistant", text: "" }]);
    setStreaming(true);

    if (mode === "agentic") {
      streamSSE(
        "/api/query/stream",
        { q, mode, top_k: 20 },
        (ev) => {
          if (ev.type === "token") {
            setMessages((m) => {
              const last = m[m.length - 1];
              return [...m.slice(0, -1), { ...last, text: last.text + ev.data }];
            });
          }
        },
        () => setStreaming(false),
      );
    } else {
      const res: any = await apiJSON("/api/query", { q, mode, top_k: 20 });
      setMessages((m) => [...m.slice(0, -1), { role: "assistant", text: res.answer, citations: res.citations }]);
      setStreaming(false);
    }
    setQ("");
  };

  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 border-b border-neutral-800 flex items-center gap-3">
        <span className="text-neutral-400">Mode:</span>
        <select value={mode} onChange={(e) => setMode(e.target.value as any)}
                className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1">
          {MODES.map((m) => <option key={m}>{m}</option>)}
        </select>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-sky-300" : "text-neutral-100"}>
            <div className="text-xs uppercase opacity-60 mb-1">{m.role}</div>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{m.text || "…"}</ReactMarkdown>
            </div>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-2 text-xs opacity-75 space-y-1">
                {m.citations.map((c: any, idx: number) => (
                  <div key={idx}>[{idx + 1}] <span className="opacity-60">{c.source}</span> — {c.snippet.slice(0, 120)}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <footer className="p-4 border-t border-neutral-800 flex gap-2">
        <input
          className="flex-1 bg-neutral-900 border border-neutral-700 rounded px-3 py-2"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="问一个问题…"
        />
        <button disabled={streaming}
          onClick={send}
          className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 px-4 py-2 rounded">
          {streaming ? "…" : "发送"}
        </button>
      </footer>
    </div>
  );
}
