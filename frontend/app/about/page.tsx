"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Brain,
  Database,
  FileSearch,
  FileText,
  Globe,
  Layers,
  MessageSquareText,
  Quote,
  Search,
  Server,
  Shield,
  ShieldOff,
  Sparkles,
  Upload,
  Zap,
} from "lucide-react";
import { Logo } from "@/components/Header";
import ThemeToggle from "@/components/ThemeToggle";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const FEATURES = [
  {
    icon: FileText,
    title: "Multi-Format Ingestion",
    description:
      "Upload PDF, DOCX, or TXT files. DocuMind parses each format intelligently — extracting page numbers from PDFs, heading styles and tables from DOCX, and detecting language (English & German) per chunk.",
  },
  {
    icon: Search,
    title: "Hybrid Search (Dense + BM25)",
    description:
      "Every question runs through two search engines simultaneously: dense vector search (semantic understanding) and BM25 keyword search (exact matches). Results are fused using Reciprocal Rank Fusion for the best of both worlds.",
  },
  {
    icon: Quote,
    title: "Source Citations",
    description:
      "Every claim in an answer carries a numbered citation chip. Click it to see the exact passage, document name, page number, and section heading the model was given.",
  },
  {
    icon: ShieldOff,
    title: "Honest Refusals",
    description:
      "If retrieval finds nothing relevant, or the model determines the context doesn't contain the answer, DocuMind says \"I don't know\" instead of guessing. Wrong answers with a confident tone are dangerous in industrial settings.",
  },
  {
    icon: Globe,
    title: "Bilingual (EN / DE)",
    description:
      "Ask in English or German — the answer comes back in the same language. Cross-language retrieval lets you ask an English question about a German contract and vice versa.",
  },
  {
    icon: Brain,
    title: "Conversation Memory",
    description:
      "Follow-up questions like \"and the warranty?\" are automatically rewritten into standalone questions using conversation history, so the context flows naturally.",
  },
  {
    icon: Layers,
    title: "Multi-Provider LLM Support",
    description:
      "Switch between OpenAI, Anthropic, Google Gemini, Groq, or fully local Ollama with just two environment variables. Only one file in the codebase imports vendor SDKs.",
  },
  {
    icon: Zap,
    title: "Real-Time Streaming",
    description:
      "Answers stream to the browser token by token via Server-Sent Events. No waiting for the full response — you see the answer forming in real time.",
  },
];

const HOW_IT_WORKS = [
  {
    step: 1,
    title: "Upload Documents",
    icon: Upload,
    description:
      "Drop your PDF, DOCX or TXT files into the sidebar. Each file is parsed, split into chunks along heading boundaries, and indexed twice — as dense vectors in Qdrant and as keywords in BM25.",
    detail:
      "Chunks never cross a section heading or PDF page, so citations stay precise. The nearest heading is prepended to every chunk for context.",
  },
  {
    step: 2,
    title: "Ask a Question",
    icon: MessageSquareText,
    description:
      "Type your question in English or German. If you have prior messages in the session, the system first rewrites follow-ups into standalone questions.",
    detail:
      "Example: if you asked about hydraulic pumps earlier, a follow-up like \"and the warranty?\" becomes \"What is the warranty period for hydraulic pumps?\"",
  },
  {
    step: 3,
    title: "Hybrid Retrieval",
    icon: FileSearch,
    description:
      "Your question is searched against both indexes simultaneously. Dense search finds semantic matches (paraphrases, cross-language). BM25 finds exact identifiers like part numbers, ISO codes, or legal paragraphs.",
    detail:
      "Reciprocal Rank Fusion merges both lists: each contributes 1/(60+rank) per chunk. The fused scores are normalised to [0, 1].",
  },
  {
    step: 4,
    title: "Relevance Check",
    icon: Shield,
    description:
      "Before calling the LLM, the system checks whether the top retrieval score meets a minimum threshold. If nothing relevant was found, it refuses immediately — saving cost and preventing hallucination.",
    detail:
      "This cheap, explainable gate catches most out-of-scope questions before spending any LLM tokens.",
  },
  {
    step: 5,
    title: "LLM Answer Generation",
    icon: Sparkles,
    description:
      "The model receives numbered passages and must cite each claim with [n], answer in the user's language, or reply NO_ANSWER. It ends with a confidence score.",
    detail:
      "Tokens stream to the browser as they arrive. At the end, markers are mapped back to chunks to build Citation objects with document name, page, section, and verbatim quote.",
  },
];

const TECH_STACK = [
  { category: "Backend", items: ["Python 3.12", "FastAPI", "LangChain", "Pydantic v2"] },
  { category: "Frontend", items: ["Next.js 16", "TypeScript", "Tailwind CSS 4", "App Router"] },
  { category: "Vector DB", items: ["Qdrant", "Cosine similarity", "Dense embeddings"] },
  { category: "Search", items: ["BM25Plus", "Reciprocal Rank Fusion", "Hybrid retrieval"] },
  {
    category: "LLM Providers",
    items: ["Google Gemini (default)", "OpenAI", "Anthropic", "Groq", "Ollama (local)"],
  },
  { category: "DevOps", items: ["Docker Compose", "pytest (61 tests)", "Ruff", "GitHub Actions CI"] },
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function AboutPage() {
  return (
    <main className="flex min-h-dvh flex-col bg-bg">
      {/* -------- Top bar -------- */}
      <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line bg-surface/90 px-3 backdrop-blur sm:px-6">
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-2 transition hover:bg-surface-2 hover:text-ink"
            aria-label="Back to chat"
          >
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <Logo />
          <span className="font-display text-[19px] font-semibold leading-none tracking-tight text-ink">
            DocuMind
          </span>
          <span className="ml-1 hidden rounded-full border border-line px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider whitespace-nowrap text-ink-3 sm:inline">
            About
          </span>
        </div>
        <ThemeToggle />
      </header>

      {/* -------- Content -------- */}
      <div className="scroll-thin mx-auto w-full max-w-4xl flex-1 overflow-y-auto px-4 py-8 sm:px-6 md:py-12">
        {/* Hero */}
        <section className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent-soft">
            <Logo className="h-12 w-12" />
          </div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl md:text-5xl">
            DocuMind
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-lg leading-relaxed text-ink-2">
            A <strong className="text-ink">RAG Knowledge Assistant</strong> for industrial company
            documents. Ask questions about your PDFs, contracts and manuals — get answers with{" "}
            <strong className="text-ink">exact source citations</strong>, or an honest{" "}
            <em>&quot;I don&apos;t know&quot;</em>.
          </p>
        </section>

        {/* Divider */}
        <hr className="my-10 border-line md:my-14" />

        {/* What is DocuMind? */}
        <section>
          <SectionLabel>Overview</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            What is DocuMind?
          </h2>
          <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-ink-2">
            <p>
              Industrial companies drown in PDFs — product manuals, supplier contracts, security
              guidelines, travel policies. Employees ask the same questions every day{" "}
              <em>(&quot;How long is the warranty?&quot;, &quot;Wie hoch ist die Hotel-Obergrenze?&quot;)</em>{" "}
              and either spend twenty minutes searching or ask a colleague.
            </p>
            <p>
              A plain chatbot is not the answer either, because an LLM that confidently invents a
              warranty period or a torque value has real consequences in an industrial setting.
            </p>
            <p>
              <strong className="text-ink">DocuMind solves this with Retrieval-Augmented Generation (RAG):</strong>{" "}
              it indexes your documents, retrieves the most relevant passages for each question,
              and makes the LLM answer <em>only</em> from those passages — citing each claim so
              you can verify it, and refusing when it doesn&apos;t know.
            </p>
          </div>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* Key Features */}
        <section>
          <SectionLabel>Capabilities</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            Key Features
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-xl border border-line bg-surface p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <f.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-3 text-sm font-semibold text-ink">{f.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">{f.description}</p>
              </div>
            ))}
          </div>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* How It Works (pipeline) */}
        <section>
          <SectionLabel>Pipeline</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            How It Works
          </h2>
          <p className="mt-3 text-[15px] text-ink-2">
            Every question flows through five stages. Here is what happens under the hood:
          </p>
          <ol className="mt-6 space-y-5">
            {HOW_IT_WORKS.map((s) => (
              <li key={s.step} className="flex gap-4">
                {/* Step indicator */}
                <div className="flex shrink-0 flex-col items-center">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-sm font-bold text-accent-ink">
                    {s.step}
                  </span>
                  {s.step < HOW_IT_WORKS.length && (
                    <span className="mt-1 h-full w-px bg-line" />
                  )}
                </div>
                {/* Content */}
                <div className="pb-2">
                  <div className="flex items-center gap-2">
                    <s.icon className="h-4 w-4 text-accent" />
                    <h3 className="text-sm font-semibold text-ink">{s.title}</h3>
                  </div>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">{s.description}</p>
                  <p className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-[12px] leading-relaxed text-ink-3 italic">
                    {s.detail}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* Architecture Overview */}
        <section>
          <SectionLabel>Architecture</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            System Architecture
          </h2>
          <div className="mt-6 rounded-xl border border-line bg-surface p-5 sm:p-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <ArchBox
                icon={Globe}
                title="Frontend"
                subtitle="Next.js 16 + TypeScript"
                items={[
                  "Responsive three-column layout",
                  "Light & dark mode",
                  "Drag-and-drop file upload",
                  "Streamed chat with SSE",
                  "Clickable citation chips",
                  "Retrieval debug panel",
                ]}
              />
              <ArchBox
                icon={Server}
                title="Backend API"
                subtitle="FastAPI + Python 3.12"
                items={[
                  "Document upload & ingestion",
                  "Heading-aware chunking",
                  "Hybrid retrieval (RRF)",
                  "RAG answer pipeline",
                  "SSE streaming responses",
                  "Conversation memory",
                ]}
              />
              <ArchBox
                icon={Database}
                title="Data Stores"
                subtitle="Qdrant + BM25 Index"
                items={[
                  "Dense vectors in Qdrant",
                  "BM25Plus keyword index",
                  "Content-hash manifest",
                  "Idempotent re-ingestion",
                  "Configurable collection",
                  "On-disk persistence",
                ]}
              />
            </div>
          </div>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* Tech Stack */}
        <section>
          <SectionLabel>Technology</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            Tech Stack
          </h2>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TECH_STACK.map((group) => (
              <div key={group.category} className="rounded-xl border border-line bg-bg p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-accent">
                  {group.category}
                </p>
                <ul className="mt-2.5 space-y-1.5">
                  {group.items.map((item) => (
                    <li key={item} className="flex items-center gap-2 text-[13px] text-ink-2">
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* Why These Choices */}
        <section>
          <SectionLabel>Design Decisions</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink sm:text-3xl">
            Why These Choices?
          </h2>
          <div className="mt-6 space-y-4">
            <DecisionCard
              question="Why hybrid search instead of just embeddings?"
              answer="Embeddings handle paraphrases and cross-language questions beautifully, but they're weak on exact identifiers like part numbers (RA-HP 450), ISO codes, or legal paragraphs (§ 7). BM25 is the opposite. Reciprocal Rank Fusion merges both lists without needing to calibrate scores from two different systems."
            />
            <DecisionCard
              question="Why citations and refusal instead of plain answers?"
              answer="In an industrial setting, a wrong torque value or warranty period has real consequences. The model only sees numbered passages and must cite them; the backend maps markers back to chunks, so a citation can never point to text the model didn't see. A relevance threshold catches most out-of-scope questions before the LLM is even called."
            />
            <DecisionCard
              question="Why heading-aware chunking?"
              answer="Chunks never cross a section heading or PDF page, so citations stay precise. The nearest heading is prepended to every chunk so a table row like '14 Tage | 3 % Skonto' still carries '§ 4 Preise und Zahlungsbedingungen' as context."
            />
            <DecisionCard
              question="Why support both local and hosted models?"
              answer="Ollama keeps every document on the machine, which matters for contracts and technical drawings. Hosted models are faster and better at structured output. DocuMind makes the switch a two-variable change so the decision can be made per deployment."
            />
          </div>
        </section>

        <hr className="my-10 border-line md:my-14" />

        {/* Author */}
        <section className="text-center pb-8">
          <SectionLabel>Author</SectionLabel>
          <h2 className="font-display mt-1 text-2xl font-semibold text-ink">Built by</h2>
          <p className="mt-3 text-lg font-semibold text-ink">Umang Lakkad</p>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-3 text-sm text-ink-2">
            <a
              href="https://github.com/lakkadumang06"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 transition hover:bg-surface-2 hover:text-ink"
            >
              GitHub
            </a>
            <a
              href="https://www.linkedin.com/in/umang-lakkad-923212299"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 transition hover:bg-surface-2 hover:text-ink"
            >
              LinkedIn
            </a>
          </div>
          <p className="mt-4 text-xs text-ink-3">MIT License</p>
        </section>
      </div>

      {/* -------- Back button (bottom) -------- */}
      <div className="border-t border-line bg-surface/90 px-4 py-3 text-center backdrop-blur">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-ink transition hover:opacity-90"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Chat
        </Link>
      </div>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/*  Helper components                                                  */
/* ------------------------------------------------------------------ */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-wider text-accent">{children}</p>
  );
}

function ArchBox({
  icon: Icon,
  title,
  subtitle,
  items,
}: {
  icon: typeof Server;
  title: string;
  subtitle: string;
  items: string[];
}) {
  return (
    <div className="rounded-xl border border-line bg-bg p-4">
      <Icon className="h-5 w-5 text-accent" />
      <p className="mt-2 text-sm font-semibold text-ink">{title}</p>
      <p className="text-[11px] text-ink-3">{subtitle}</p>
      <ul className="mt-3 space-y-1.5">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-[12px] leading-snug text-ink-2">
            <span className="mt-[5px] h-1 w-1 shrink-0 rounded-full bg-accent" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DecisionCard({ question, answer }: { question: string; answer: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <p className="text-sm font-semibold text-ink">{question}</p>
      <p className="mt-2 text-[13px] leading-relaxed text-ink-2">{answer}</p>
    </div>
  );
}

