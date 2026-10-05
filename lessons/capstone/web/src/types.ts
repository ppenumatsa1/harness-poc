// Events streamed from the agent (harness.py) through the api. One SSE "data:" line = one event.

export type Fix = {
  id: number;
  order_id: string;
  action: string;
  status: "pending" | "approved" | "rejected" | "applied";
  decision_note: string | null;
  created_at: string;
  decided_at: string | null;
};

export type Finding = {
  order_id: string;
  failure_class: string;
  first_failure_log: string;
  root_cause: string;
  evidence: string[];
  proposed_fix: string;
  fix_id: number | null;
  confidence: number;
};

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  model_calls: number;
  model: string | null;
  duration_s: number;
};

export type AgentEvent =
  | { type: "conversation"; conversation_id: string; order_id: string }
  | { type: "turn_start"; kind: string; conversation_id: string; order_id: string; model: string }
  | { type: "hook"; hook: string; text: string }
  | { type: "tool_start"; tool: string; call_id: string; args: unknown; agent: string }
  | { type: "tool_done"; call_id: string; success: boolean; error: string | null }
  | { type: "subagent"; agent: string; state: string }
  | { type: "skill"; name: string }
  | { type: "intent"; text: string }
  | { type: "compaction"; success: boolean }
  | { type: "decision"; fix_id: number; status: string }
  | { type: "finding"; finding: Finding }
  | { type: "message"; text: string }
  | { type: "error"; message: string }
  | { type: "done"; usage: Usage; fixes: Fix[] };

export type Order = { order_id: string; status: string; total_cents: number; currency: string };

export type TimedEvent = { at: number; event: AgentEvent };

export type Health = {
  status: string;
  db: boolean;
  agent: { status: string; db?: boolean; runtime?: boolean };
};
