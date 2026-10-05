// Turn the raw event stream into view state: steps, agent lanes, guardrails and the active role.
import type { AgentEvent, Finding, Fix, TimedEvent } from "./types";

export type StepState = "todo" | "active" | "waiting" | "done" | "skipped" | "failed";
export type Step = { id: string; label: string; hint: string; state: StepState };

export type ToolCall = {
  callId: string; tool: string; agent: string; args: unknown;
  startedAt: number; endedAt?: number; success?: boolean; error?: string | null;
};
export type LaneState = "running" | "completed" | "failed" | "idle";
export type Lane = { agent: string; label: string; state: LaneState; calls: ToolCall[] };
export type Guard = { at: number; label: string; text: string; tone: "ok" | "warn" | "bad" | "info" };
export type Role = "human" | "app" | "harness" | "model" | "biz";

export const DATA_TOOLS = new Set(["get_order", "get_payment", "get_inventory", "logs-get_logs"]);
const FIX_TOOLS = new Set(["propose_fix", "apply_fix"]);
const RATE_LIMIT = /rate_limit|too_many_requests|\b429\b/;

export const AGENT_LABELS: Record<string, string> = {
  main: "Orchestrator",
  "payment-analyst": "Payment analyst",
  "inventory-analyst": "Inventory analyst",
};

export const TOOL_LABELS: Record<string, string> = {
  get_order: "get_order", get_payment: "get_payment", get_inventory: "get_inventory",
  "logs-get_logs": "get_logs · MCP", task: "delegate", skill: "load skill",
  propose_fix: "propose_fix", apply_fix: "apply_fix",
};

const GUARD_LABELS: Record<string, string> = {
  pre_tool: "Scope guard", post_tool: "Redaction", agent_stop: "Stop gate", permission: "Permission",
  tool_failure: "Tool failure", error: "Runtime error", session_start: "Session", session_end: "Session",
};

export function argSummary(tool: string, args: unknown): string {
  if (!args || typeof args !== "object") return "";
  const a = args as Record<string, unknown>;
  if (tool === "task") return String(a.agent_type ?? a.description ?? "");
  if (tool === "skill") return String(a.skill ?? a.name ?? "");
  if (typeof a.order_id === "string" || typeof a.order_id === "number") return `order ${a.order_id}`;
  if (a.fix_id != null) return `fix #${a.fix_id}`;
  const text = JSON.stringify(a);
  return text.length > 60 ? `${text.slice(0, 60)}…` : text;
}

export type View = {
  steps: Step[]; lanes: Lane[]; guards: Guard[]; toolCalls: number; retries: number;
  errors: string[]; activeRole: Role | null; live: Partial<Record<Role, string>>;
};

export function derive(events: TimedEvent[], finding: Finding | null, fixes: Fix[], busy: boolean): View {
  const calls = new Map<string, ToolCall>();
  const lanes = new Map<string, Lane>([["main", { agent: "main", label: AGENT_LABELS.main, state: "idle", calls: [] }]]);
  const guards: Guard[] = [];
  const errors: string[] = [];
  const live: Partial<Record<Role, string>> = {};
  let retries = 0, skill = "", started = false;

  const lane = (agent: string) => {
    let l = lanes.get(agent);
    if (!l) lanes.set(agent, (l = { agent, label: AGENT_LABELS[agent] ?? agent, state: "idle", calls: [] }));
    return l;
  };

  for (const { at, event: e } of events) {
    switch (e.type) {
      case "turn_start":
        started = true;
        lane("main").state = "running";
        live.model = `${e.model} · ${e.kind} turn`;
        break;
      case "skill":
        skill = e.name;
        live.harness = `skill ${e.name} loaded`;
        break;
      case "subagent":
        lane(e.agent).state = e.state === "started" ? "running" : e.state === "failed" ? "failed" : "completed";
        live.harness = `${AGENT_LABELS[e.agent] ?? e.agent} ${e.state}`;
        break;
      case "tool_start": {
        const call: ToolCall = { callId: e.call_id, tool: e.tool, agent: e.agent, args: e.args, startedAt: at };
        calls.set(e.call_id, call);
        lane(e.agent).calls.push(call);
        const line = `${TOOL_LABELS[e.tool] ?? e.tool} ${argSummary(e.tool, e.args)}`.trim();
        if (DATA_TOOLS.has(e.tool) || FIX_TOOLS.has(e.tool)) live.biz = line;
        else live.harness = line;
        break;
      }
      case "tool_done": {
        const call = calls.get(e.call_id);
        if (call) Object.assign(call, { endedAt: at, success: e.success, error: e.error });
        break;
      }
      case "hook":
        if (e.hook === "error" && RATE_LIMIT.test(e.text)) {
          retries += 1;
          live.model = `rate limited · runtime retrying (${retries})`;
          break;
        }
        if (e.hook === "session_start" || e.hook === "session_end") break;
        guards.push({
          at, label: GUARD_LABELS[e.hook] ?? e.hook, text: e.text,
          tone: e.hook === "post_tool" ? "ok" : e.hook === "error" || e.hook === "tool_failure" ? "bad" : /DENY|REJECT|blocked/.test(e.text) ? "warn" : "info",
        });
        live.harness = `${GUARD_LABELS[e.hook] ?? e.hook}: ${e.text}`;
        break;
      case "intent":
        live.model = e.text;
        break;
      case "decision":
        live.app = `fix #${e.fix_id} ${e.status}`;
        break;
      case "error":
        errors.push(e.message);
        break;
      case "done":
        lane("main").state = "completed";
        live.model = `${e.usage.model_calls} model calls · ${(e.usage.input_tokens / 1000).toFixed(1)}K tokens in`;
        break;
    }
  }

  const subs = [...lanes.values()].filter((l) => l.agent !== "main");
  const allCalls = [...calls.values()];
  const facts = allCalls.filter((c) => DATA_TOOLS.has(c.tool)).length;
  const fix = (finding?.fix_id != null ? fixes.find((f) => f.id === finding.fix_id) : undefined) ?? fixes[0];
  const healthy = finding?.failure_class === "NO_FAILURE";
  const subsDone = subs.length > 0 && subs.every((s) => s.state !== "running");

  const steps: Step[] = [
    { id: "plan", label: "Plan", hint: skill || "load runbook skill", state: skill ? "done" : "todo" },
    {
      id: "delegate", label: "Delegate", hint: subs.length ? `${subs.length} specialists` : "specialist sub-agents",
      state: subs.some((s) => s.state === "failed") ? "failed" : subsDone ? "done" : subs.length ? "active" : "todo",
    },
    {
      id: "facts", label: "Gather facts", hint: facts ? `${facts} tool calls` : "orders · payments · stock · logs",
      state: facts && (finding || subsDone) ? "done" : facts ? "active" : "todo",
    },
    { id: "diagnose", label: "Diagnose", hint: finding?.failure_class.replace(/_/g, " ").toLowerCase() ?? "structured finding", state: finding ? "done" : "todo" },
    { id: "propose", label: "Propose fix", hint: fix ? `fix #${fix.id}` : healthy ? "nothing to fix" : "pending row in DB", state: fix ? "done" : healthy ? "skipped" : "todo" },
    {
      id: "decide", label: "Human decision", hint: fix && fix.status !== "pending" ? fix.status : fix ? "waiting for you" : "approve or reject",
      state: fix && fix.status !== "pending" ? "done" : fix ? "waiting" : healthy ? "skipped" : "todo",
    },
    {
      id: "apply", label: "Apply", hint: fix?.status === "applied" ? "applied" : fix?.status === "rejected" ? "rejected" : "only after approval",
      state: fix?.status === "applied" ? "done" : fix?.status === "rejected" || healthy ? "skipped" : "todo",
    },
  ];
  if (busy && !steps.some((s) => s.state === "active")) {
    const next = steps.find((s) => s.state === "todo" || s.state === "waiting");
    if (next) next.state = "active";
  } else if (!busy && started && !finding && errors.length) {
    const next = steps.find((s) => s.state === "todo" || s.state === "active");
    if (next) next.state = "failed";
  }

  if (fix?.status === "pending") live.human = `review fix #${fix.id}`;
  if (fix) live.biz = `fixes #${fix.id} · ${fix.status}`;

  return {
    steps, lanes: [...lanes.values()], guards, toolCalls: allCalls.length, retries, errors,
    activeRole: activeRole(events, busy, fix), live,
  };
}

function activeRole(events: TimedEvent[], busy: boolean, fix: Fix | undefined): Role | null {
  if (!busy) return fix?.status === "pending" ? "human" : null;
  const last: AgentEvent | undefined = events[events.length - 1]?.event;
  if (!last) return "app";
  switch (last.type) {
    case "conversation":
    case "decision":
      return "app";
    case "tool_start":
      return DATA_TOOLS.has(last.tool) || FIX_TOOLS.has(last.tool) ? "biz" : "harness";
    case "hook":
      return last.hook === "error" ? "model" : "harness";
    case "subagent":
    case "skill":
      return "harness";
    default:
      return "model";
  }
}
