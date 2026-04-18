import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Link, Navigate } from "react-router-dom";

import Chat from "./pages/Chat";
import GraphExplorer from "./pages/GraphExplorer";
import Ingest from "./pages/Ingest";
import EvalPanel from "./pages/EvalPanel";
import "./styles.css";

const qc = new QueryClient();

function Shell() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-neutral-900 border-r border-neutral-800 p-4 space-y-2">
        <h1 className="text-xl font-bold mb-4">KG-RAG</h1>
        <Link className="block hover:text-sky-400" to="/chat">🗨  Chat</Link>
        <Link className="block hover:text-sky-400" to="/graph">🕸  Graph</Link>
        <Link className="block hover:text-sky-400" to="/ingest">📥  Ingest</Link>
        <Link className="block hover:text-sky-400" to="/eval">📊  Eval</Link>
      </aside>
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/graph" element={<GraphExplorer />} />
          <Route path="/ingest" element={<Ingest />} />
          <Route path="/eval" element={<EvalPanel />} />
        </Routes>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  </QueryClientProvider>
);
