export type Intent = "SCREENING" | "RESEARCH" | "COMPARISON";

export interface FeatureBreakdown {
  growth: number;
  valuation: number;
  momentum: number;
  sentiment: number;
}

export interface StockResult {
  ticker: string;
  name?: string | null;
  score: number;
  features: FeatureBreakdown;
  rationale?: string | null;
}

export interface ContextChunk {
  source: string;
  ticker?: string | null;
  text: string;
  similarity?: number | null;
}

export interface QueryResponse {
  intent: Intent;
  tickers: string[];
  results: StockResult[];
  context: ContextChunk[];
  explanation: string;
  confidence: number;
  meta: Record<string, unknown>;
}

export interface QueryRequest {
  query: string;
  top_k?: number;
}
