"use client";

import { FileText, X } from "lucide-react";
import type { Citation } from "@/lib/types";

interface Props {
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationPanel({ citation, onClose }: Props) {
  if (!citation) return null;
  return (
    <aside className="flex h-full w-full flex-col border-l border-slate-200 bg-white">
      <div className="flex items-start justify-between gap-2 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Source [{citation.marker}]
          </p>
          <p className="mt-1 flex items-center gap-1.5 truncate text-sm font-semibold text-slate-800">
            <FileText className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="truncate" title={citation.document_name}>
              {citation.document_name}
            </span>
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {citation.page ? `Page ${citation.page}` : "No page (DOCX/TXT)"}
            {citation.section ? ` · ${citation.section}` : ""}
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close source panel"
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="scroll-thin flex-1 overflow-y-auto px-4 py-4">
        <blockquote className="whitespace-pre-wrap rounded-md border-l-4 border-indigo-400 bg-indigo-50/60 px-3 py-2 text-sm leading-relaxed text-slate-800">
          {citation.quote}
        </blockquote>
        <p className="mt-3 text-xs text-slate-400">
          This is the exact chunk the model was given. Verify the answer against it.
        </p>
      </div>
    </aside>
  );
}
