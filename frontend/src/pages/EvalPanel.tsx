import { useQuery } from "@tanstack/react-query";
import { apiJSON } from "../lib/api";

export default function EvalPanel() {
  const { data } = useQuery<any>({
    queryKey: ["stats"],
    queryFn: () => apiJSON("/api/graph/stats"),
  });
  return (
    <div className="p-10 max-w-3xl">
      <h2 className="text-2xl font-bold mb-4">Eval & Stats</h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
          <div className="opacity-60 text-sm">Entities</div>
          <div className="text-3xl font-bold">{data?.ents ?? "…"}</div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
          <div className="opacity-60 text-sm">Relations</div>
          <div className="text-3xl font-bold">{data?.rels ?? "…"}</div>
        </div>
      </div>
      <p className="mt-6 opacity-70 text-sm">
        详细 RAGAS / HotpotQA 指标请见 <code>make bench</code>，以及 Phoenix UI
        ({import.meta.env.VITE_PHOENIX_URL ?? "http://localhost:6006"})。
      </p>
    </div>
  );
}
