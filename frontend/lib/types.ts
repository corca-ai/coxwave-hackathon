export type RunStepName =
  | "clarify"
  | "plan"
  | "search"
  | "extract"
  | "verify"
  | "write"
  | "visualize";

export interface RunStep {
  name: RunStepName;
  input: unknown;
  output: unknown;
  status?: "ok" | "error" | "skipped";
  started_at?: string;
  ended_at?: string;
  trace_id?: string;
}

export interface RunBundle {
  run_id: string;
  created_at: string;
  query: string;
  meta?: Record<string, unknown>;
  steps: RunStep[];
}

export interface StreamEvent {
  id: string;
  timestamp: string;
  type: string;
  agent?: string;
  stage?: string;
  sequence?: number;
  payload: unknown;
}

export interface Source {
  source_id: string;
  title: string;
  url: string;
  snippet: string;
  why_relevant: string;
}

export interface Claim {
  claim: string;
  evidence: string;
  source_id: string;
  confidence: number;
}

export interface Verification {
  claim: string;
  verdict: string;
  rationale: string;
  confidence: number;
  source_id?: string;
  required_evidence?: string[];
}

export interface ReportOutput {
  title: string;
  executive_summary: string;
  key_findings: string[];
  limitations: string[];
  citations: string[];
  suggested_visuals?: string[];
}

export interface VisualComponent {
  type: string;
  props: Record<string, unknown>;
}

export interface VisualOutput {
  components: VisualComponent[];
  rationale: string;
}
