"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import type { RetrievedChunk } from "@/lib/types";

interface Props {
  retrieved: RetrievedChunk[];
}

const fmtDense = (r: RetrievedChunk) =>
  r.dense_rank ? `#${r.dense_rank} (${r.dense_score?.toFixed(3)})` : "–";
const fmtBm25 = (r: RetrievedChunk) =>
  r.bm25_rank ? `#${r.bm25_rank} (${r.bm25_score?.toFixed(1)})` : "–";
const where = (r: RetrievedChunk) =>
  [r.chunk.page ? `p. ${r.chunk.page}` : "", r.chunk.section ?? ""].filter(Boolean).join(" · ");

/** Collapsible view of what retrieval returned: a table on wide screens, cards on phones. */
export default function DebugPanel({ retrieved }: Props) {
  const [open, setOpen] = useState(false);
  if (!retrieved.length) return null;
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-line bg-surface-2/60 text-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left font-medium text-ink-2 transition hover:text-ink"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Search className="h-3.5 w-3.5" />
        Retrieval debug
        <span className="ml-auto rounded-full bg-surface px-2 py-px font-mono text-[10px] text-ink-3">
          {retrieved.length} chunks
        </span>
      </button>

      {open && (
        <>
          {/* phones: stacked cards */}
          <ul className="space-y-2 border-t border-line p-2 sm:hidden">
            {retrieved.map((r, i) => (
              <li key={r.chunk.id} className="rounded-lg border border-line bg-surface p-2.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-ink-3">#{i + 1}</span>
                  <ScoreBar score={r.score} />
                  <span className="ml-auto truncate text-ink-2" title={r.chunk.document_name}>
                    {r.chunk.document_name}
                  </span>
                </div>
                <p className="mt-1 font-mono text-[10px] text-ink-3">
                  dense {fmtDense(r)} · bm25 {fmtBm25(r)}
                  {where(r) ? ` · ${where(r)}` : ""}
                </p>
                <p className="mt-1.5 line-clamp-3 text-ink-2">{r.chunk.text}</p>
              </li>
            ))}
          </ul>

          {/* tablet and up: table */}
          <div className="scroll-thin hidden overflow-x-auto border-t border-line sm:block">
            <table className="w-full min-w-[640px] text-left">
              <thead className="text-ink-3">
                <tr>
                  {["#", "Score", "Dense", "BM25", "Document", "Where", "Text"].map((h) => (
                    <th key={h} className="px-3 py-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {retrieved.map((r, i) => (
                  <tr key={r.chunk.id} className="border-t border-line bg-surface align-top">
                    <td className="px-3 py-2 font-mono text-ink-3">{i + 1}</td>
                    <td className="px-3 py-2">
                      <ScoreBar score={r.score} />
                    </td>
                    <td className="px-3 py-2 font-mono text-ink-2">{fmtDense(r)}</td>
                    <td className="px-3 py-2 font-mono text-ink-2">{fmtBm25(r)}</td>
                    <td className="max-w-[160px] truncate px-3 py-2" title={r.chunk.document_name}>
                      {r.chunk.document_name}
                    </td>
                    <td className="px-3 py-2 text-ink-2">{where(r)}</td>
                    <td className="max-w-[320px] px-3 py-2 text-ink-2">
                      <span className="line-clamp-2">{r.chunk.text}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-line">
        <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.round(score * 100)}%` }} />
      </span>
      <span className="font-mono">{score.toFixed(3)}</span>
    </span>
  );
}
