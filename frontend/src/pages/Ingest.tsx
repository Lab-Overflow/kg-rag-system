import { useState } from "react";
import { uploadFile, apiJSON } from "../lib/api";

export default function Ingest() {
  const [job, setJob] = useState<any>(null);
  const [polling, setPolling] = useState(false);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const j = await uploadFile(f);
    setJob(j);
    pollStatus(j.job_id);
  };

  const pollStatus = (jobId: string) => {
    setPolling(true);
    const int = setInterval(async () => {
      const j: any = await apiJSON(`/api/ingest/${jobId}`);
      setJob(j);
      if (j.status === "done" || j.status === "failed") {
        clearInterval(int);
        setPolling(false);
      }
    }, 1000);
  };

  return (
    <div className="p-10 max-w-xl">
      <h2 className="text-2xl font-bold mb-4">Ingest 文档</h2>
      <p className="opacity-70 mb-4">支持 PDF / DOCX / HTML / Markdown / JSONL / TXT。
        上传后后台自动切块 → 嵌入 → LLM 抽取实体关系 → 图谱增量更新 → 社区摘要。</p>
      <input type="file" onChange={onFile} className="mb-6" />
      {job && (
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4 text-sm">
          <div>job_id: {job.job_id}</div>
          <div>status: <span className="text-sky-400">{job.status}</span> {polling && "…"}</div>
          <div>progress: {(job.progress * 100).toFixed(0)}%</div>
          {job.error && <div className="text-red-400">err: {job.error}</div>}
        </div>
      )}
    </div>
  );
}
