"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  Check,
  CircleHelp,
  FolderDown,
  Loader2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ChatMessage, Citation, RetrievalMode } from "@/lib/types";
import { streamChat } from "@/lib/api";
import AnswerText from "./AnswerText";
import DebugPanel from "./DebugPanel";
import { Logo } from "./Header";

interface Props {
  sessionId: string;
  hasDocuments: boolean;
  onCite: (citation: Citation) => void;
  activeCitation: Citation | null;
  onReset: () => void;
  onMessagesChange: (hasMessages: boolean) => void;
  onLoadSamples: () => Promise<void>;
  loadingSamples: boolean;
  samplesError: string | null;
  onHelp: () => void;
}

const MODES: { value: RetrievalMode; label: string; hint: string }[] = [
  { value: "hybrid", label: "Hybrid", hint: "Dense + BM25 merged with Reciprocal Rank Fusion" },
  { value: "dense", label: "Dense", hint: "Embedding similarity only (Qdrant)" },
  { value: "bm25", label: "BM25", hint: "Keyword search only" },
];

const EXAMPLES: { q: string; lang: "EN" | "DE" }[] = [
  { q: "How long is the warranty for hydraulic pumps?", lang: "EN" },
  { q: "Wie lange ist die Gewährleistung im Rahmenliefervertrag?", lang: "DE" },
  { q: "What is the nitrogen pre-charge pressure of the accumulator?", lang: "EN" },
  { q: "Wie hoch ist die Hotel-Obergrenze pro Nacht in München?", lang: "DE" },
];

export default function Chat({
  sessionId,
  hasDocuments,
  onCite,
  activeCitation,
  onReset,
  onMessagesChange,
  onLoadSamples,
  loadingSamples,
  samplesError,
  onHelp,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<RetrievalMode>("hybrid");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastSession = useRef(sessionId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => onMessagesChange(messages.length > 0), [messages.length, onMessagesChange]);

  // A new session id from the header's "New chat" button clears the thread.
  useEffect(() => {
    if (lastSession.current !== sessionId) {
      lastSession.current = sessionId;
      abortRef.current?.abort();
      setMessages([]);
    }
  }, [sessionId]);

  // Grow the textarea with its content, up to a few lines.
  const autosize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const update = (id: string, patch: Partial<ChatMessage> | ((m: ChatMessage) => ChatMessage)) =>
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? (typeof patch === "function" ? patch(m) : { ...m, ...patch }) : m)),
    );

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    requestAnimationFrame(autosize);
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
    <section className="paper flex h-full min-w-0 flex-1 flex-col">
      {/* thread */}
      <div className="scroll-thin flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && (
            <EmptyState
              hasDocuments={hasDocuments}
              busy={busy}
              onAsk={ask}
              onLoadSamples={onLoadSamples}
              loadingSamples={loadingSamples}
              samplesError={samplesError}
              onHelp={onHelp}
            />
          )}

          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="rise flex justify-end">
                <div className="max-w-[88%] rounded-2xl rounded-br-md bg-user-bubble px-4 py-2.5 text-[15px] leading-relaxed text-user-ink shadow-card sm:max-w-[75%]">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={m.id} className="rise flex items-start gap-3">
                <span className="mt-1 hidden shrink-0 sm:block">
                  <Logo className="h-7 w-7" />
                </span>
                <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3.5 text-[15px] text-ink shadow-card sm:px-5">
                  {m.error ? (
                    <p className="flex items-start gap-2 text-sm text-danger">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {m.error}
                    </p>
                  ) : (
                    <>
                      {m.streaming && !m.text && <Thinking />}
                      <AnswerText
                        text={m.text}
                        citations={m.answer?.citations ?? []}
                        onCite={onCite}
                        active={activeCitation?.marker ?? null}
                      />
                      {m.streaming && m.text && (
                        <span className="cursor-blink ml-0.5 inline-block h-4 w-[3px] rounded bg-accent align-middle" />
                      )}
                    </>
                  )}
                  {m.answer && <AnswerMeta message={m} />}
                  {m.answer && <DebugPanel retrieved={m.answer.retrieved} />}
                </div>
              </div>
            ),
          )}
          <div ref={bottomRef} className="h-px" />
        </div>
      </div>

      {/* composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
        className="safe-bottom border-t border-line bg-surface/90 px-3 pt-3 backdrop-blur sm:px-6"
      >
        <div className="mx-auto max-w-3xl">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div
              className="inline-flex rounded-full border border-line bg-surface p-0.5"
              role="radiogroup"
              aria-label="Retrieval mode"
            >
              {MODES.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  role="radio"
                  aria-checked={mode === m.value}
                  title={m.hint}
                  onClick={() => setMode(m.value)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    mode === m.value
                      ? "bg-ink text-bg shadow-sm"
                      : "text-ink-2 hover:text-ink"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={reset}
                className="text-xs text-ink-3 underline-offset-2 hover:text-ink hover:underline"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-1.5 shadow-card transition focus-within:border-accent">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                autosize();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void ask(input);
                }
              }}
              rows={1}
              placeholder={hasDocuments ? "Ask in English or German…" : "Upload a document first"}
              disabled={!hasDocuments || busy}
              className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-3 py-2 text-[15px] text-ink outline-none placeholder:text-ink-3 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!input.trim() || busy || !hasDocuments}
              aria-label="Send"
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-ink transition hover:bg-accent-strong disabled:opacity-40"
            >
              <ArrowUp className="h-4.5 w-4.5" />
            </button>
          </div>
          <p className="mt-1.5 hidden text-[11px] text-ink-3 sm:block">
            Enter to send · Shift+Enter for a new line · follow-ups keep the conversation context
          </p>
        </div>
      </form>
    </section>
  );
}

function EmptyState({
  hasDocuments,
  busy,
  onAsk,
  onLoadSamples,
  loadingSamples,
  samplesError,
  onHelp,
}: {
  hasDocuments: boolean;
  busy: boolean;
  onAsk: (q: string) => Promise<void>;
  onLoadSamples: () => Promise<void>;
  loadingSamples: boolean;
  samplesError: string | null;
  onHelp: () => void;
}) {
  return (
    <div className="rise pt-4 sm:pt-10">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-ink-2">
        <Sparkles className="h-3.5 w-3.5 text-accent" /> Grounded answers only
      </span>
      <h2 className="font-display mt-4 text-[32px] font-semibold leading-[1.05] tracking-tight text-ink sm:text-[44px]">
        Ask your documents.
        <br />
        <span className="text-accent">Every claim has a source.</span>
      </h2>
      <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-2">
        DocuMind answers only from the uploaded files, cites the exact passage behind each statement
        and says <em>I don&apos;t know</em> when the answer is not there. Ask in English or German.
      </p>

      <ul className="mt-6 grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map((ex) => (
          <li key={ex.q}>
            <button
              type="button"
              onClick={() => void onAsk(ex.q)}
              disabled={!hasDocuments || busy}
              className="group flex w-full items-start gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-left text-sm text-ink transition hover:border-accent hover:shadow-card disabled:opacity-50 disabled:hover:border-line disabled:hover:shadow-none"
            >
              <span className="mt-0.5 rounded bg-surface-2 px-1.5 py-px font-mono text-[10px] font-medium text-ink-3">
                {ex.lang}
              </span>
              <span className="flex-1 leading-snug">{ex.q}</span>
              <ArrowUp className="mt-0.5 h-4 w-4 shrink-0 rotate-45 text-ink-3 transition group-hover:text-accent" />
            </button>
          </li>
        ))}
      </ul>

      {!hasDocuments && (
        <div className="mt-6 rounded-2xl border border-accent/30 bg-accent-soft/50 p-4 sm:p-5">
          <p className="text-sm font-semibold text-ink">New here? Start with the sample documents.</p>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-2">
            Eight fictional company files (manuals, a contract, policies) in English and German.
            Indexing takes about half a minute, then the questions above work right away.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void onLoadSamples()}
              disabled={loadingSamples}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-ink transition hover:bg-accent-strong disabled:opacity-60"
            >
              {loadingSamples ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FolderDown className="h-4 w-4" />
              )}
              {loadingSamples ? "Indexing 8 documents…" : "Load sample documents"}
            </button>
            <span className="text-xs text-ink-3">or upload your own files in the sidebar</span>
          </div>
          {samplesError && (
            <p className="mt-3 inline-flex items-center gap-2 rounded-lg bg-danger-soft px-3 py-2 text-xs text-danger">
              <AlertTriangle className="h-3.5 w-3.5" /> {samplesError}
            </p>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={onHelp}
        className="mt-5 inline-flex items-center gap-1.5 text-sm text-ink-2 underline-offset-4 hover:text-accent hover:underline"
      >
        <CircleHelp className="h-4 w-4" /> How it works and what to try
      </button>
    </div>
  );
}

function Thinking() {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-ink-3" aria-live="polite">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
      <span className="ml-1">Searching documents…</span>
    </span>
  );
}

function AnswerMeta({ message }: { message: ChatMessage }) {
  const a = message.answer!;
  const n = a.citations.length;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-line pt-3 text-xs text-ink-2">
      {a.answer_found ? (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-ok-soft px-2.5 py-1 font-medium text-ok">
          <ShieldCheck className="h-3.5 w-3.5" /> Grounded · {n} source{n === 1 ? "" : "s"}
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-warn-soft px-2.5 py-1 font-medium text-warn">
          <AlertTriangle className="h-3.5 w-3.5" /> Refused · not in documents
        </span>
      )}
      <ConfidenceRing value={a.confidence} />
      <span className="rounded bg-surface-2 px-1.5 py-px font-mono text-[10px] uppercase text-ink-3">
        {a.language}
      </span>
      {n > 0 && (
        <span className="ml-auto hidden items-center gap-1 text-ink-3 sm:inline-flex">
          <Check className="h-3.5 w-3.5" /> tap a number to see the passage
        </span>
      )}
    </div>
  );
}

/** Small ring showing the blended confidence score, coloured by band. */
function ConfidenceRing({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const r = 7;
  const c = 2 * Math.PI * r;
  const tone = value >= 0.7 ? "stroke-ok" : value >= 0.4 ? "stroke-warn" : "stroke-danger";
  return (
    <span className="inline-flex items-center gap-1.5" title={`Confidence ${value.toFixed(2)}`}>
      <svg viewBox="0 0 20 20" className="h-4 w-4 -rotate-90">
        <circle cx="10" cy="10" r={r} className="stroke-line" strokeWidth="3" fill="none" />
        <circle
          cx="10"
          cy="10"
          r={r}
          className={tone}
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct / 100)}
        />
      </svg>
      <span className="font-mono">{pct}%</span>
      <span className="text-ink-3">confidence</span>
    </span>
  );
}
