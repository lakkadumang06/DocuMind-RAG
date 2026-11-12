"use client";

import { BookOpen, FileText, Hash, X } from "lucide-react";
import type { Citation } from "@/lib/types";

interface Props {
  citation: Citation | null;
  onClose: () => void;
}

export default function CitationPanel({ citation, onClose }: Props) {
  if (!citation) return null;
  return (
    <aside className="flex h-full w-full flex-col border-l border-line bg-surface">
      {/* drag handle, only meaningful on the phone bottom sheet */}
      <div className="flex justify-center pt-2 xl:hidden">
        <span className="h-1 w-10 rounded-full bg-line-strong" />
      </div>

      <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent">
            <BookOpen className="h-3.5 w-3.5" /> Source [{citation.marker}]
          </p>
          <p className="mt-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink">
            <FileText className="h-4 w-4 shrink-0 text-ink-3" />
            <span className="truncate" title={citation.document_name}>
              {citation.document_name}
            </span>
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-ink-2">
            <span className="rounded bg-surface-2 px-1.5 py-px">
              {citation.page ? `Page ${citation.page}` : "No page (DOCX/TXT)"}
            </span>
            {citation.section && (
              <span className="inline-flex items-center gap-1 rounded bg-surface-2 px-1.5 py-px">
                <Hash className="h-3 w-3" /> {citation.section}
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close source panel"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink-2 transition hover:bg-surface-2 hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="scroll-thin flex-1 overflow-y-auto px-4 py-4 sm:px-5">
        <blockquote className="font-display whitespace-pre-wrap rounded-xl border-l-[3px] border-accent bg-accent-soft/60 px-4 py-3 text-[15px] leading-[1.7] text-ink">
          {citation.quote}
        </blockquote>
        <p className="mt-3 text-xs text-ink-3">
          This is the exact chunk the model was given. Verify the answer against it.
        </p>
      </div>
    </aside>
  );
}
