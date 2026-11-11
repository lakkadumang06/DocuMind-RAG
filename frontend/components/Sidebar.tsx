"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, Loader2, Trash2, Upload } from "lucide-react";
import type { DocumentInfo } from "@/lib/types";
import { formatBytes, uploadDocuments } from "@/lib/api";

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  onChanged: () => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

const typeColors: Record<DocumentInfo["file_type"], string> = {
  pdf: "bg-rose-100 text-rose-700",
  docx: "bg-sky-100 text-sky-700",
  txt: "bg-slate-200 text-slate-700",
};

export default function Sidebar({ documents, loading, onChanged, onDelete }: Props) {
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

  return (
    <aside className="flex h-full w-full flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            D
          </span>
          DocuMind
        </h1>
        <p className="mt-1 text-xs text-slate-500">Answers from your documents, with sources.</p>
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
          className={`cursor-pointer rounded-lg border-2 border-dashed p-4 text-center transition ${
            dragging
              ? "border-indigo-500 bg-indigo-50"
              : "border-slate-300 hover:border-indigo-400 hover:bg-slate-50"
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
              <div className="flex items-center justify-center gap-2 text-sm text-slate-700">
                <Loader2 className="h-4 w-4 animate-spin" />
                {phase === "upload" ? `Uploading ${progress}%` : "Parsing, chunking, embedding…"}
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded bg-slate-200">
                <div
                  className={`h-full bg-indigo-600 transition-all ${phase === "ingest" ? "animate-pulse" : ""}`}
                  style={{ width: `${progress ?? 100}%` }}
                />
              </div>
            </div>
          ) : (
            <>
              <Upload className="mx-auto h-5 w-5 text-slate-400" />
              <p className="mt-1 text-sm font-medium text-slate-700">Drop files or click to upload</p>
              <p className="text-xs text-slate-500">PDF, DOCX, TXT · English or German</p>
            </>
          )}
        </div>
        {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
      </div>

      <div className="mt-4 flex items-center justify-between px-4 text-xs font-medium uppercase tracking-wide text-slate-500">
        <span>Documents</span>
        <span>{documents.length}</span>
      </div>
      <ul className="scroll-thin mt-2 flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        {loading && documents.length === 0 && (
          <li className="px-2 py-4 text-center text-sm text-slate-400">Loading…</li>
        )}
        {!loading && documents.length === 0 && (
          <li className="px-2 py-4 text-center text-sm text-slate-400">
            No documents yet. Upload the sample docs from <code>data/sample_docs</code>.
          </li>
        )}
        {documents.map((d) => (
          <li
            key={d.id}
            className="group flex items-start gap-2 rounded-md px-2 py-2 hover:bg-slate-50"
          >
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-slate-800" title={d.filename}>
                {d.filename}
              </p>
              <p className="mt-0.5 flex flex-wrap items-center gap-1 text-[11px] text-slate-500">
                <span className={`rounded px-1 font-medium uppercase ${typeColors[d.file_type]}`}>
                  {d.file_type}
                </span>
                <span className="rounded bg-slate-100 px-1 uppercase">{d.language}</span>
                {d.num_pages > 0 && <span>{d.num_pages} p.</span>}
                <span>{d.num_chunks} chunks</span>
                <span>{formatBytes(d.size_bytes)}</span>
              </p>
            </div>
            <button
              aria-label={`Delete ${d.filename}`}
              onClick={() => void handleDelete(d.id)}
              disabled={deleting === d.id}
              className="rounded p-1 text-slate-400 opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100 disabled:opacity-100"
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
