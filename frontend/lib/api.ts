/** Thin client for the DocuMind FastAPI backend, including SSE parsing for /chat. */

import type { ChatAnswer, DocumentInfo, HealthResponse, RetrievalMode } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* body was not JSON */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const getHealth = () => fetch(`${API_URL}/health`).then(handle<HealthResponse>);
export const listDocuments = () => fetch(`${API_URL}/documents`).then(handle<DocumentInfo[]>);
export const deleteDocument = (id: string) =>
  fetch(`${API_URL}/documents/${id}`, { method: "DELETE" }).then(handle<void>);
/** Index the bundled sample documents so a first-time user has something to ask about. */
export const loadSampleDocuments = () =>
  fetch(`${API_URL}/documents/samples`, { method: "POST" }).then(handle<DocumentInfo[]>);

/** Upload with progress events; XMLHttpRequest is the only browser API that reports them. */
export function uploadDocuments(
  files: File[],
  onProgress: (percent: number) => void,
): Promise<DocumentInfo[]> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/documents`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as DocumentInfo[]);
      } else {
        let detail = xhr.statusText;
        try {
          detail = JSON.parse(xhr.responseText).detail ?? detail;
        } catch {
          /* not JSON */
        }
        reject(new Error(detail || `Upload failed (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(form);
  });
}

export interface ChatHandlers {
  onToken: (text: string) => void;
  onFinal: (answer: ChatAnswer) => void;
  onError: (message: string) => void;
}

/** POST /chat and parse the Server-Sent Events stream (token*, final | error). */
export async function streamChat(
  body: { question: string; session_id: string; retrieval_mode: RetrievalMode; top_k?: number },
  handlers: ChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    handlers.onError(detail || "Request failed");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const dispatch = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    const payload = JSON.parse(data.join("\n"));
    if (event === "token") handlers.onToken(payload.text as string);
    else if (event === "final") handlers.onFinal(payload as ChatAnswer);
    else if (event === "error") handlers.onError(payload.detail as string);
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      dispatch(buffer.slice(0, idx));
      buffer = buffer.slice(idx + 2);
    }
  }
  if (buffer.trim()) dispatch(buffer);
}

export const formatBytes = (n: number) =>
  n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
