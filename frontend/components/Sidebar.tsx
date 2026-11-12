"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, FolderDown, Loader2, Trash2, UploadCloud, X } from "lucide-react";
import type { DocumentInfo } from "@/lib/types";
import { formatBytes, uploadDocuments } from "@/lib/api";

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  onChanged: () => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onLoadSamples: () => Promise<void>;
  loadingSamples: boolean;
  /** Present only when rendered as a mobile drawer. */
  onClose?: () => void;
}

const typeStyles: Record<DocumentInfo["file_type"], string> = {
  pdf: "bg-danger-soft text-danger",
  docx: "bg-accent-soft text-accent",
  txt: "bg-surface-2 text-ink-2",
};

export default function Sidebar({
  documents,
  loading,
  onChanged,
  onDelete,
  onLoadSamples,
  loadingSamples,
  onClose,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [phase, setPhase] = useState<"upload" | "ingest" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      if (!list.length) return;
      setError(null);
      setPhase("upload");
      setProgress(0);
      try {
        await uploadDocuments(list, (p) => {
          setProgress(p);
          if (p >= 100) setPhase("ingest"); // bytes are in, backend is parsing + embedding
        });
        await onChanged();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setProgress(null);
        setPhase(null);
      }
    },
    [onChanged],
  );

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await onDelete(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(null);
    }
  };

  const totalChunks = documents.reduce((n, d) => n + d.num_chunks, 0);

  return (
    <aside className="flex h-full w-full flex-col border-r border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">Knowledge base</p>
          <p className="mt-0.5 text-sm text-ink-2">
            {documents.length} document{documents.length === 1 ? "" : "s"} · {totalChunks} chunks
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close documents"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-2 hover:bg-surface-2"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="px-4 pt-4">
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            void upload(e.dataTransfer.files);
          }}
          className={`cursor-pointer rounded-xl border border-dashed p-4 text-center transition ${
            dragging
              ? "border-accent bg-accent-soft"
              : "border-line-strong hover:border-accent hover:bg-surface-2"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={(e) => e.target.files && void upload(e.target.files)}
          />
          {phase ? (
            <div className="space-y-2">
              <div className="flex items-center justify-center gap-2 text-sm text-ink">
                <Loader2 className="h-4 w-4 animate-spin text-accent" />
                {phase === "upload" ? `Uploading ${progress}%` : "Parsing, chunking, embedding…"}
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                <div
                  className={`h-full rounded-full bg-accent transition-all ${phase === "ingest" ? "animate-pulse" : ""}`}
                  style={{ width: `${progress ?? 100}%` }}
                />
              </div>
            </div>
          ) : (
            <>
              <span className="mx-auto inline-flex h-10 w-10 items-center justify-center rounded-full bg-accent-soft text-accent">
                <UploadCloud className="h-5 w-5" />
              </span>
              <p className="mt-2 text-sm font-medium text-ink">Drop files or tap to upload</p>
              <p className="mt-0.5 text-xs text-ink-3">PDF, DOCX, TXT · English or German</p>
            </>
          )}
        </div>
        {error && (
          <p className="mt-2 rounded-lg bg-danger-soft px-3 py-2 text-xs text-danger">{error}</p>
        )}
      </div>

      <ul className="scroll-thin mt-3 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {loading && documents.length === 0 && (
          <li className="px-2 py-6 text-center text-sm text-ink-3">Loading…</li>
        )}
        {!loading && documents.length === 0 && (
          <li className="mx-2 rounded-xl border border-line px-3 py-5 text-center">
            <p className="text-sm text-ink-2">No documents yet.</p>
            <button
              type="button"
              onClick={() => void onLoadSamples()}
              disabled={loadingSamples}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-accent px-3.5 py-1.5 text-xs font-medium text-accent-ink transition hover:bg-accent-strong disabled:opacity-60"
            >
              {loadingSamples ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FolderDown className="h-3.5 w-3.5" />
              )}
              {loadingSamples ? "Indexing samples…" : "Load 8 sample documents"}
            </button>
          </li>
        )}
        {documents.map((d) => (
          <li
            key={d.id}
            className="group flex items-start gap-2.5 rounded-lg px-2 py-2 transition hover:bg-surface-2"
          >
            <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-2 text-ink-3 group-hover:bg-surface">
              <FileText className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink" title={d.filename}>
                {d.filename}
              </p>
              <p className="mt-1 flex flex-wrap items-center gap-1 text-[11px] text-ink-3">
                <span className={`rounded px-1.5 py-px font-semibold uppercase ${typeStyles[d.file_type]}`}>
                  {d.file_type}
                </span>
                <span className="rounded bg-surface-2 px-1.5 py-px uppercase">{d.language}</span>
                {d.num_pages > 0 && <span>{d.num_pages} p.</span>}
                <span>{d.num_chunks} chunks</span>
                <span>{formatBytes(d.size_bytes)}</span>
              </p>
            </div>
            <button
              type="button"
              aria-label={`Delete ${d.filename}`}
              onClick={() => void handleDelete(d.id)}
              disabled={deleting === d.id}
              className="rounded-md p-1.5 text-ink-3 transition hover:bg-danger-soft hover:text-danger sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100 sm:disabled:opacity-100"
            >
              {deleting === d.id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
