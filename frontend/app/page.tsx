"use client";

import { useCallback, useEffect, useState } from "react";
import { PanelLeft } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import CitationPanel from "@/components/CitationPanel";
import { API_URL, deleteDocument, getHealth, listDocuments } from "@/lib/api";
import type { Citation, DocumentInfo, HealthResponse } from "@/lib/types";

export default function Page() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessionId, setSessionId] = useState("");

  useEffect(() => setSessionId(crypto.randomUUID()), []);

  const refresh = useCallback(async () => {
    try {
      const [docs, h] = await Promise.all([listDocuments(), getHealth()]);
      setDocuments(docs);
      setHealth(h);
      setApiError(null);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleDelete = async (id: string) => {
    await deleteDocument(id);
    await refresh();
  };

  const resetSession = () => {
    setCitation(null);
    setSessionId(crypto.randomUUID());
  };

  return (
    <main className="flex h-screen flex-col">
      {/* status bar */}
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <button
            className="rounded p-1 hover:bg-slate-100 md:hidden"
            aria-label="Toggle documents"
            onClick={() => setSidebarOpen((o) => !o)}
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          <span className="hidden sm:inline">API {API_URL}</span>
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <>
              <span>
                LLM <b className="font-medium text-slate-700">{health.llm_provider}</b>
              </span>
              <span>
                Embeddings <b className="font-medium text-slate-700">{health.embedding_provider}</b>
              </span>
            </>
          )}
          <span className="inline-flex items-center gap-1">
            <span
              className={`h-2 w-2 rounded-full ${
                apiError ? "bg-rose-500" : health?.status === "ok" ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            {apiError ? "API unreachable" : health?.status === "ok" ? "Healthy" : "Degraded"}
          </span>
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        {/* sidebar: drawer on mobile, column on md+ */}
        <div
          className={`absolute inset-y-0 left-0 z-20 w-72 transform transition-transform md:static md:translate-x-0 ${
            sidebarOpen ? "translate-x-0 shadow-xl" : "-translate-x-full"
          }`}
        >
          <Sidebar documents={documents} loading={loadingDocs} onChanged={refresh} onDelete={handleDelete} />
        </div>
        {sidebarOpen && (
          <div className="absolute inset-0 z-10 bg-slate-900/30 md:hidden" onClick={() => setSidebarOpen(false)} />
        )}

        <Chat
          sessionId={sessionId}
          hasDocuments={documents.length > 0}
          onCite={setCitation}
          activeCitation={citation}
          onReset={resetSession}
        />

        {citation && (
          <div className="absolute inset-y-0 right-0 z-20 w-full max-w-md shadow-xl lg:static lg:w-96 lg:shadow-none">
            <CitationPanel citation={citation} onClose={() => setCitation(null)} />
          </div>
        )}
      </div>
    </main>
  );
}
