"use client";

import { useState } from "react";
import { Bug, ChevronDown, ChevronRight } from "lucide-react";
import type { RetrievedChunk } from "@/lib/types";

interface Props {
  retrieved: RetrievedChunk[];
}

/** Collapsible view of what retrieval returned, with fused and raw scores. */
export default function DebugPanel({ retrieved }: Props) {
  const [open, setOpen] = useState(false);
  if (!retrieved.length) return null;
  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left font-medium text-slate-600 hover:text-slate-900"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Bug className="h-3.5 w-3.5" />
        Retrieval debug · {retrieved.length} chunks
      </button>
      {open && (
        <div className="scroll-thin overflow-x-auto border-t border-slate-200">
          <table className="w-full min-w-[640px] text-left">
            <thead className="text-slate-500">
              <tr>
                <th className="px-3 py-1.5 font-medium">#</th>
                <th className="px-3 py-1.5 font-medium">Score</th>
                <th className="px-3 py-1.5 font-medium">Dense</th>
                <th className="px-3 py-1.5 font-medium">BM25</th>
                <th className="px-3 py-1.5 font-medium">Document</th>
                <th className="px-3 py-1.5 font-medium">Where</th>
                <th className="px-3 py-1.5 font-medium">Text</th>
              </tr>
            </thead>
            <tbody>
              {retrieved.map((r, i) => (
                <tr key={r.chunk.id} className="border-t border-slate-200 align-top">
                  <td className="px-3 py-1.5 text-slate-500">{i + 1}</td>
                  <td className="px-3 py-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-12 overflow-hidden rounded bg-slate-200">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${Math.round(r.score * 100)}%` }}
                        />
                      </div>
                      <span className="font-mono">{r.score.toFixed(3)}</span>
                    </div>
                  </td>
                  <td className="px-3 py-1.5 font-mono text-slate-600">
                    {r.dense_rank ? `#${r.dense_rank} (${r.dense_score?.toFixed(3)})` : "–"}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-slate-600">
                    {r.bm25_rank ? `#${r.bm25_rank} (${r.bm25_score?.toFixed(1)})` : "–"}
                  </td>
                  <td className="max-w-[160px] truncate px-3 py-1.5" title={r.chunk.document_name}>
                    {r.chunk.document_name}
                  </td>
                  <td className="px-3 py-1.5 text-slate-600">
                    {r.chunk.page ? `p. ${r.chunk.page}` : ""}
                    {r.chunk.section ? ` ${r.chunk.section}` : ""}
                  </td>
                  <td className="max-w-[320px] px-3 py-1.5 text-slate-600">
                    <span className="line-clamp-2">{r.chunk.text}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
