"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Send, ShieldCheck, Trash } from "lucide-react";
import type { ChatMessage, Citation, RetrievalMode } from "@/lib/types";
import { streamChat } from "@/lib/api";
import AnswerText from "./AnswerText";
import DebugPanel from "./DebugPanel";

interface Props {
  sessionId: string;
  hasDocuments: boolean;
  onCite: (citation: Citation) => void;
  activeCitation: Citation | null;
  onReset: () => void;
}

const MODES: { value: RetrievalMode; label: string; hint: string }[] = [
  { value: "hybrid", label: "Hybrid", hint: "Dense + BM25 merged with Reciprocal Rank Fusion" },
  { value: "dense", label: "Dense", hint: "Embedding similarity only (Qdrant)" },
  { value: "bm25", label: "BM25", hint: "Keyword search only" },
];

const EXAMPLES = [
  "How long is the warranty for hydraulic pumps?",
  "Wie lange ist die Gewährleistung im Rahmenliefervertrag?",
  "What is the nitrogen pre-charge pressure of the accumulator?",
  "Wie hoch ist die Hotel-Obergrenze pro Nacht in München?",
];

export default function Chat({ sessionId, hasDocuments, onCite, activeCitation, onReset }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<RetrievalMode>("hybrid");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const update = (id: string, patch: Partial<ChatMessage> | ((m: ChatMessage) => ChatMessage)) =>
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? (typeof patch === "function" ? patch(m) : { ...m, ...patch }) : m)),
    );

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    const userId = crypto.randomUUID();
    const botId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", text: q },
      { id: botId, role: "assistant", text: "", streaming: true },
    ]);
    abortRef.current = new AbortController();
    try {
      await streamChat(
        { question: q, session_id: sessionId, retrieval_mode: mode },
        {
          onToken: (t) => update(botId, (m) => ({ ...m, text: m.text + t })),
          onFinal: (answer) => update(botId, { text: answer.answer, answer, streaming: false }),
          onError: (err) => update(botId, { error: err, streaming: false }),
        },
        abortRef.current.signal,
      );
    } catch (e) {
      update(botId, { error: e instanceof Error ? e.message : String(e), streaming: false });
    } finally {
      update(botId, { streaming: false });
      setBusy(false);
    }
  };

  const reset = () => {
    abortRef.current?.abort();
    setMessages([]);
    onReset();
  };

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col">
      {/* toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Retrieval mode">
          {MODES.map((m) => (
            <button
              key={m.value}
              role="radio"
              aria-checked={mode === m.value}
              title={m.hint}
              onClick={() => setMode(m.value)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                mode === m.value ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <button
          onClick={reset}
          disabled={!messages.length}
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-40"
        >
          <Trash className="h-3.5 w-3.5" /> New conversation
        </button>
      </div>

      {/* messages */}
      <div className="scroll-thin flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-5">
          {messages.length === 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-base font-semibold text-slate-800">Ask your documents</h2>
              <p className="mt-1 text-sm text-slate-500">
                DocuMind answers only from the uploaded documents, cites the exact passage for every
                claim and says <em>I don&apos;t know</em> when the answer is not there. Ask in English or German.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => void ask(ex)}
                    disabled={!hasDocuments || busy}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 disabled:opacity-50"
                  >
                    {ex}
                  </button>
                ))}
              </div>
              {!hasDocuments && (
                <p className="mt-3 text-xs text-amber-700">Upload at least one document to start.</p>
              )}
            </div>
          )}

          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-sm text-white shadow-sm">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex justify-start">
                <div className="w-full max-w-[92%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-sm">
                  {m.error ? (
                    <p className="flex items-center gap-2 text-rose-600">
                      <AlertTriangle className="h-4 w-4" /> {m.error}
                    </p>
                  ) : (
                    <>
                      <AnswerText
                        text={m.text}
                        citations={m.answer?.citations ?? []}
                        onCite={onCite}
                        active={activeCitation?.marker ?? null}
                      />
                      {m.streaming && <span className="cursor-blink ml-0.5 inline-block h-4 w-1.5 bg-slate-400 align-middle" />}
                    </>
                  )}
                  {m.answer && (
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2 text-xs text-slate-500">
                      {m.answer.answer_found ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
                          <ShieldCheck className="h-3.5 w-3.5" /> Grounded · {m.answer.citations.length} source
                          {m.answer.citations.length === 1 ? "" : "s"}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700">
                          <AlertTriangle className="h-3.5 w-3.5" /> Refused · not in documents
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1.5">
                        Confidence
                        <span className="h-1.5 w-16 overflow-hidden rounded bg-slate-200">
                          <span
                            className={`block h-full ${m.answer.confidence >= 0.7 ? "bg-emerald-500" : m.answer.confidence >= 0.4 ? "bg-amber-500" : "bg-rose-500"}`}
                            style={{ width: `${Math.round(m.answer.confidence * 100)}%` }}
                          />
                        </span>
                        <span className="font-mono">{m.answer.confidence.toFixed(2)}</span>
                      </span>
                      <span className="uppercase">{m.answer.language}</span>
                    </div>
                  )}
                  {m.answer && <DebugPanel retrieved={m.answer.retrieved} />}
                </div>
              </div>
            ),
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
        className="border-t border-slate-200 bg-white px-4 py-3"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void ask(input);
              }
            }}
            rows={1}
            placeholder={hasDocuments ? "Ask a question in English or German…" : "Upload a document first"}
            disabled={!hasDocuments || busy}
            className="max-h-40 min-h-[42px] flex-1 resize-y rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || busy || !hasDocuments}
            aria-label="Send"
            className="inline-flex h-[42px] w-[42px] items-center justify-center rounded-lg bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mx-auto mt-1.5 max-w-3xl text-[11px] text-slate-400">
          Enter to send, Shift+Enter for a new line. Follow-up questions keep the conversation context.
        </p>
      </form>
    </section>
  );
}
