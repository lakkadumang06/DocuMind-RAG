/** Types mirroring backend/app/schemas.py. Keep them in sync by hand; they are small. */

export type RetrievalMode = "dense" | "bm25" | "hybrid";

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: "pdf" | "docx" | "txt";
  language: string;
  num_pages: number;
  num_chunks: number;
  size_bytes: number;
  ingested_at: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  document_name: string;
  chunk_index: number;
  text: string;
  page: number | null;
  section: string | null;
  language: string;
}

export interface RetrievedChunk {
  chunk: Chunk;
  score: number;
  dense_rank: number | null;
  bm25_rank: number | null;
  dense_score: number | null;
  bm25_score: number | null;
}

export interface Citation {
  marker: number;
  chunk_id: string;
  document_id: string;
  document_name: string;
  page: number | null;
  section: string | null;
  quote: string;
}

export interface ChatAnswer {
  answer: string;
  citations: Citation[];
  confidence: number;
  answer_found: boolean;
  language: string;
  retrieved: RetrievedChunk[];
  session_id: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  llm_provider: string;
  embedding_provider: string;
  qdrant_reachable: boolean;
  documents: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  /** Filled once the final SSE event arrives. */
  answer?: ChatAnswer;
  streaming?: boolean;
  error?: string;
}
