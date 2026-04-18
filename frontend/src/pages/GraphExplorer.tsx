import { useEffect, useRef, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import { apiJSON } from "../lib/api";

type GraphData = { nodes: any[]; links: any[] };

export default function GraphExplorer() {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [seed, setSeed] = useState("");
  const [hops, setHops] = useState(2);
  const fgRef = useRef<any>();

  const load = async () => {
    const res: any = await apiJSON("/api/graph/subgraph", {
      seed: seed || null, hops, limit: 500, min_confidence: 0.0,
    });
    const nodes = res.nodes.map((n: any) => ({ id: n.id, name: n.name, type: n.type }));
    const links = res.edges.map((e: any) => ({ source: e.source, target: e.target, label: e.type }));
    setData({ nodes, links });
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 border-b border-neutral-800 flex gap-2 items-center">
        <input className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1"
          value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="种子实体名 (空=全图采样)" />
        <input type="number" min={1} max={4} value={hops}
          onChange={(e) => setHops(Number(e.target.value))}
          className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 w-16" />
        <button onClick={load}
          className="bg-sky-600 hover:bg-sky-500 rounded px-3 py-1">加载</button>
        <span className="text-sm opacity-60">节点 {data.nodes.length} · 边 {data.links.length}</span>
      </header>
      <div className="flex-1">
        <ForceGraph3D
          ref={fgRef}
          graphData={data}
          nodeAutoColorBy="type"
          linkDirectionalParticles={2}
          linkDirectionalArrowLength={3}
          nodeLabel={(n: any) => `${n.name} (${n.type})`}
          backgroundColor="#0a0a0a"
        />
      </div>
    </div>
  );
}
