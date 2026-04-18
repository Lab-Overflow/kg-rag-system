const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function apiJSON<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export function streamSSE(
  path: string,
  body: unknown,
  onEvent: (ev: { type: string; data: string }) => void,
  onDone?: () => void,
) {
  fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  }).then(async (res) => {
    if (!res.body) return;
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const p of parts) {
        const ev: any = { type: "message", data: "" };
        for (const line of p.split("\n")) {
          const [k, ...rest] = line.split(":");
          const v = rest.join(":").trim();
          if (k === "event") ev.type = v;
          else if (k === "data") ev.data = v;
        }
        onEvent(ev);
      }
    }
    onDone?.();
  });
}

export async function uploadFile(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/api/ingest`, { method: "POST", body: fd });
  return res.json();
}
