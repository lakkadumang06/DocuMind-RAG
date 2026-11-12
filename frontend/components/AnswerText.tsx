"use client";

import type { Citation } from "@/lib/types";

interface Props {
  text: string;
  citations: Citation[];
  onCite: (citation: Citation) => void;
  active?: number | null;
}

const MARKER = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

/** Render answer text, turning "[2]" markers into clickable citation chips. */
export default function AnswerText({ text, citations, onCite, active }: Props) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  const parts: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(MARKER)) {
    const start = match.index ?? 0;
    if (start > last) parts.push(<span key={key++}>{text.slice(last, start)}</span>);
    const numbers = match[1].split(",").map((n) => parseInt(n.trim(), 10));
    numbers.forEach((n) => {
      const cit = byMarker.get(n);
      parts.push(
        cit ? (
          <button
            key={key++}
            type="button"
            onClick={() => onCite(cit)}
            title={`${cit.document_name}${cit.page ? `, page ${cit.page}` : ""}`}
            className={`mx-0.5 inline-flex h-[20px] min-w-[20px] items-center justify-center rounded-md border px-1.5 align-text-bottom font-mono text-[11px] font-medium transition ${
              active === n
                ? "border-accent bg-accent text-accent-ink"
                : "border-accent/30 bg-accent-soft text-accent hover:border-accent"
            }`}
          >
            {n}
          </button>
        ) : (
          <span key={key++} className="text-ink-3">
            [{n}]
          </span>
        ),
      );
    });
    last = start + match[0].length;
  }
  if (last < text.length) parts.push(<span key={key++}>{text.slice(last)}</span>);
  return <p className="whitespace-pre-wrap leading-[1.7]">{parts}</p>;
}
