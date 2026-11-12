"use client";

import { useEffect } from "react";
import { FileUp, MessageSquareText, Quote, ShieldOff, X } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
}

const STEPS = [
  {
    icon: FileUp,
    title: "1. Add documents",
    text: "Upload PDF, DOCX or TXT files, or load the 8 bundled sample documents of a fictional German machine builder. Each file is split into chunks and indexed twice: as vectors and as keywords.",
  },
  {
    icon: MessageSquareText,
    title: "2. Ask in English or German",
    text: "Your question is matched against the chunks (hybrid search). The model only sees the best passages and must answer from them, in the language you asked in.",
  },
  {
    icon: Quote,
    title: "3. Check the source",
    text: "Every claim carries a numbered chip. Tap it to see the exact passage, document, page and section the answer came from.",
  },
  {
    icon: ShieldOff,
    title: "4. Trust the refusals",
    text: "If nothing relevant is found, or the passages do not contain the answer, DocuMind says so instead of guessing.",
  },
];

const TRY = [
  "Ask “How long is the warranty for hydraulic pumps?” and open citation [1].",
  "Ask the same in German: “Wie lange ist die Gewährleistung?” – the answer switches language.",
  "Ask something the documents cannot know, e.g. “What is the CEO’s salary?” – you get a refusal.",
  "Ask a follow-up like “and for power supplies?” – the conversation context is kept.",
  "Switch between Hybrid, Dense and BM25 and open “Retrieval debug” to compare the scores.",
];

/** Short onboarding dialog for first-time users. */
export default function HowItWorks({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <button
        type="button"
        aria-label="Close help"
        onClick={onClose}
        className="absolute inset-0 bg-ink/40 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="how-title"
        className="sheet-up scroll-thin relative max-h-[88vh] w-full overflow-y-auto rounded-t-2xl border border-line bg-surface shadow-card sm:rise sm:max-w-2xl sm:rounded-2xl"
      >
        <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-line bg-surface px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-accent">Guide</p>
            <h2 id="how-title" className="font-display mt-1 text-2xl font-semibold text-ink">
              How DocuMind works
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink-2 hover:bg-surface-2"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <ol className="grid gap-3 px-5 py-4 sm:grid-cols-2">
          {STEPS.map((s) => (
            <li key={s.title} className="rounded-xl border border-line bg-bg p-4">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                <s.icon className="h-4 w-4" />
              </span>
              <p className="mt-2 text-sm font-semibold text-ink">{s.title}</p>
              <p className="mt-1 text-[13px] leading-relaxed text-ink-2">{s.text}</p>
            </li>
          ))}
        </ol>

        <div className="border-t border-line px-5 py-4">
          <p className="text-sm font-semibold text-ink">Things to try</p>
          <ul className="mt-2 space-y-1.5 text-[13px] leading-relaxed text-ink-2">
            {TRY.map((t) => (
              <li key={t} className="flex gap-2">
                <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {t}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-ink-3">
            The sample documents belong to the fictional Rheintal Antriebstechnik GmbH: two product
            manuals, a supplier contract, a warranty policy, an IT guideline, a travel policy, an
            onboarding guide and a maintenance procedure.
          </p>
        </div>
      </div>
    </div>
  );
}
