import type { QueryRequest, QueryResponse } from "./types";

export async function runQuery(
  payload: QueryRequest,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return (await res.json()) as QueryResponse;
}
