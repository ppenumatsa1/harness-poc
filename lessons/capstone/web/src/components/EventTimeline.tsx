import type { AgentEvent, TimedEvent } from "../types";

type Row = { key: string; icon: string; text: string; detail?: string; tone?: "ok" | "bad" | "warn" };

function short(value: unknown, max = 140): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

/** Turn raw events into readable rows. tool_done is merged into its tool_start row. */
function toRows(events: TimedEvent[], start: number): Row[] {
  const done = new Map<string, Extract<AgentEvent, { type: "tool_done" }>>();
  for (const { event } of events) if (event.type === "tool_done") done.set(event.call_id, event);

  const rows: Row[] = [];
  events.forEach(({ at, event: e }, i) => {
    const t = `+${((at - start) / 1000).toFixed(1)}s`;
    const key = `${i}`;
    switch (e.type) {
      case "turn_start":
        rows.push({ key, icon: "▶", text: `${t} ${e.kind} turn · ${e.model}` });
        break;
      case "skill":
        rows.push({ key, icon: "📘", text: `${t} skill loaded: ${e.name}` });
        break;
      case "subagent":
        rows.push({ key, icon: "🤖", text: `${t} sub-agent ${e.agent} ${e.state}`, tone: e.state === "failed" ? "bad" : undefined });
        break;
      case "tool_start": {
        const d = done.get(e.call_id);
        const status = !d ? "…" : d.success ? "✓" : `✗ ${d.error ?? ""}`;
        const who = e.agent === "main" ? "" : ` (${e.agent})`;
        rows.push({
          key, icon: "🔧", text: `${t} ${e.tool}${who} ${status}`, detail: short(e.args),
          tone: d && !d.success ? "bad" : undefined,
        });
        break;
      }
      case "hook": {
        const tone = /DENY|REJECT|blocked/.test(e.text) ? "warn" : e.hook === "error" ? "bad" : undefined;
        rows.push({ key, icon: "🪝", text: `${t} hook ${e.hook}`, detail: short(e.text, 200), tone });
        break;
      }
      case "intent":
        rows.push({ key, icon: "💭", text: `${t} ${e.text}` });
        break;
      case "compaction":
        rows.push({ key, icon: "🗜", text: `${t} context compacted` });
        break;
      case "decision":
        rows.push({ key, icon: "🧑", text: `${t} human ${e.status} fix #${e.fix_id}`, tone: "ok" });
        break;
      case "finding":
        rows.push({ key, icon: "📋", text: `${t} finding: ${e.finding.failure_class}`, tone: "ok" });
        break;
      case "message":
        rows.push({ key, icon: "💬", text: `${t} ${short(e.text)}` });
        break;
      case "error":
        rows.push({ key, icon: "⚠", text: `${t} error`, detail: e.message, tone: "bad" });
        break;
      case "done":
        rows.push({ key, icon: "■", text: `${t} turn done` });
        break;
    }
  });
  return rows;
}

export default function EventTimeline({ events, busy }: { events: TimedEvent[]; busy: boolean }) {
  if (events.length === 0) return <p className="muted">{busy ? "Starting…" : "Pick an order and investigate."}</p>;
  return (
    <ol className="timeline">
      {toRows(events, events[0].at).map((r) => (
        <li key={r.key} className={r.tone}>
          <span className="icon">{r.icon}</span>
          <span>{r.text}</span>
          {r.detail && <div className="detail">{r.detail}</div>}
        </li>
      ))}
      {busy && <li className="muted">…</li>}
    </ol>
  );
}
