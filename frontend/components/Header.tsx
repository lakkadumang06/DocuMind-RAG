"use client";

import Link from "next/link";
import { CircleHelp, FolderOpen, Info, MessageSquarePlus } from "lucide-react";
import type { HealthResponse } from "@/lib/types";
import ThemeToggle from "./ThemeToggle";

interface Props {
  health: HealthResponse | null;
  apiError: string | null;
  canReset: boolean;
  onReset: () => void;
  onOpenSidebar: () => void;
  onHelp: () => void;
}

export default function Header({
  health,
  apiError,
  canReset,
  onReset,
  onOpenSidebar,
  onHelp,
}: Props) {
  const status = apiError ? "down" : health?.status === "ok" ? "ok" : "degraded";
  const statusLabel =
    status === "down" ? "API unreachable" : status === "ok" ? "All systems healthy" : "Degraded";
  const dot =
    status === "down" ? "bg-danger" : status === "ok" ? "bg-ok" : "bg-warn";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line bg-surface/90 px-3 backdrop-blur sm:px-4">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onOpenSidebar}
          aria-label="Open documents"
          className="inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-2 transition hover:bg-surface-2 hover:text-ink lg:hidden"
        >
          <FolderOpen className="h-4.5 w-4.5" />
        </button>
        <a href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-[19px] font-semibold leading-none tracking-tight text-ink">
            DocuMind
          </span>
        </a>
        <span className="ml-1 hidden rounded-full border border-line px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider whitespace-nowrap text-ink-3 lg:inline">
          RAG assistant
        </span>
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        {health && (
          <div className="hidden items-center gap-1.5 text-xs text-ink-3 lg:flex">
            <Pill label="LLM" value={health.llm_provider} />
            <Pill label="Embeddings" value={health.embedding_provider} />
          </div>
        )}
        <span
          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-line px-2.5 py-1 text-xs text-ink-2"
          title={statusLabel}
        >
          <span className={`h-2 w-2 rounded-full ${dot}`} />
          <span className="hidden sm:inline">{statusLabel}</span>
        </span>
        <button
          type="button"
          onClick={onHelp}
          aria-label="How it works"
          title="How it works"
          className="inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-2 transition hover:bg-surface-2 hover:text-ink"
        >
          <CircleHelp className="h-4.5 w-4.5" />
        </button>
        <Link
          href="/about"
          className="inline-flex h-9 items-center gap-1.5 rounded-full border border-line px-3 text-xs font-medium text-ink-2 transition hover:bg-surface-2 hover:text-ink"
        >
          <Info className="h-3.5 w-3.5" />
          <span>About Us</span>
        </Link>
        <ThemeToggle />
        <button
          type="button"
          onClick={onReset}
          disabled={!canReset}
          className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-full bg-ink px-3 text-xs font-medium text-bg transition hover:opacity-90 disabled:opacity-40"
        >
          <MessageSquarePlus className="h-4 w-4" />
          <span className="hidden sm:inline">New chat</span>
        </button>
      </div>
    </header>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="whitespace-nowrap rounded-full bg-surface-2 px-2.5 py-1">
      {label} <b className="font-medium text-ink-2">{value}</b>
    </span>
  );
}

/** Two stacked pages with a highlight line: documents that answer back. */
export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect x="4" y="3" width="24" height="26" rx="6" className="fill-accent" />
      <path
        d="M11 11h10M11 16h10M11 21h6"
        className="stroke-accent-ink"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
