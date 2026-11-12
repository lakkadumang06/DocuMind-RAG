"use client";

import { useCallback, useEffect, useState } from "react";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import CitationPanel from "@/components/CitationPanel";
import HowItWorks from "@/components/HowItWorks";
import { deleteDocument, getHealth, listDocuments, loadSampleDocuments } from "@/lib/api";
import type { Citation, DocumentInfo, HealthResponse } from "@/lib/types";

export default function Page() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [hasMessages, setHasMessages] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [samplesError, setSamplesError] = useState<string | null>(null);

  useEffect(() => setSessionId(crypto.randomUUID()), []);

  // Escape closes whichever overlay is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setSidebarOpen(false);
      setCitation(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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

  const loadSamples = async () => {
    setLoadingSamples(true);
    setSamplesError(null);
    try {
      await loadSampleDocuments();
      await refresh();
    } catch (e) {
      setSamplesError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingSamples(false);
    }
  };

  const resetSession = () => {
    setCitation(null);
    setSessionId(crypto.randomUUID());
  };

  return (
    <main className="flex h-dvh flex-col">
      <Header
        health={health}
        apiError={apiError}
        canReset={hasMessages}
        onReset={resetSession}
        onOpenSidebar={() => setSidebarOpen(true)}
        onHelp={() => setHelpOpen(true)}
      />
      <HowItWorks open={helpOpen} onClose={() => setHelpOpen(false)} />

      <div className="relative flex min-h-0 flex-1">
        {/* Documents: fixed column on desktop, slide-in drawer below lg */}
        <div className="hidden w-[300px] shrink-0 lg:block xl:w-[320px]">
          <Sidebar
            documents={documents}
            loading={loadingDocs}
            onChanged={refresh}
            onDelete={handleDelete}
            onLoadSamples={loadSamples}
            loadingSamples={loadingSamples}
          />
        </div>
        {sidebarOpen && (
          <div className="absolute inset-0 z-30 lg:hidden">
            <button
              type="button"
              aria-label="Dismiss documents"
              onClick={() => setSidebarOpen(false)}
              className="absolute inset-0 bg-ink/40 backdrop-blur-[1px]"
            />
            <div className="drawer-left absolute inset-y-0 left-0 w-[min(88vw,340px)] shadow-card">
              <Sidebar
                documents={documents}
                loading={loadingDocs}
                onChanged={refresh}
                onDelete={handleDelete}
                onLoadSamples={loadSamples}
                loadingSamples={loadingSamples}
                onClose={() => setSidebarOpen(false)}
              />
            </div>
          </div>
        )}

        <Chat
          sessionId={sessionId}
          hasDocuments={documents.length > 0}
          onCite={setCitation}
          activeCitation={citation}
          onReset={resetSession}
          onMessagesChange={setHasMessages}
          onLoadSamples={loadSamples}
          loadingSamples={loadingSamples}
          samplesError={samplesError}
          onHelp={() => setHelpOpen(true)}
        />

        {/* Source: inline column on xl, right drawer on tablet, bottom sheet on phones */}
        {citation && (
          <div className="absolute inset-0 z-30 xl:static xl:z-auto xl:w-[380px] xl:shrink-0">
            <button
              type="button"
              aria-label="Dismiss source"
              onClick={() => setCitation(null)}
              className="absolute inset-0 bg-ink/40 backdrop-blur-[1px] xl:hidden"
            />
            <div className="sheet-up absolute inset-x-0 bottom-0 h-[78vh] overflow-hidden rounded-t-2xl shadow-card sm:drawer-right sm:inset-y-0 sm:left-auto sm:right-0 sm:h-auto sm:w-[min(90vw,420px)] sm:rounded-none xl:static xl:h-full xl:w-full xl:animate-none xl:shadow-none">
              <CitationPanel citation={citation} onClose={() => setCitation(null)} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
