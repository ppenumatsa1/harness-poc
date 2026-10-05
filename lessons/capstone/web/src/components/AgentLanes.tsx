import { argSummary, TOOL_LABELS, type Lane, type ToolCall } from "../derive";

function status(c: ToolCall) {
  if (c.success === undefined) return <span className="spin" aria-label="running" />;
  return c.success ? <span className="ok-mark">✓</span> : <span className="bad-mark">✕</span>;
}

function duration(c: ToolCall) {
  return c.endedAt ? `${((c.endedAt - c.startedAt) / 1000).toFixed(1)}s` : "";
}

/** One lane per agent: the orchestrator and each specialist sub-agent, with its tool calls. */
export default function AgentLanes({ lanes }: { lanes: Lane[] }) {
  return (
    <div className="lanes">
      {lanes.map((l) => (
        <div key={l.agent} className={`lane ${l.agent === "main" ? "main" : "sub"}`}>
          <div className="lane-head">
            <strong>{l.label}</strong>
            <span className={`state ${l.state}`}>{l.state}</span>
          </div>
          {l.calls.length === 0 ? (
            <div className="muted small">No tool calls yet</div>
          ) : (
            <ul className="calls">
              {l.calls.map((c) => (
                <li key={c.callId} className={c.success === false ? "failed" : ""} title={c.error ?? JSON.stringify(c.args)}>
                  {status(c)}
                  <code>{TOOL_LABELS[c.tool] ?? c.tool}</code>
                  <span className="arg">{argSummary(c.tool, c.args)}</span>
                  <span className="dur">{duration(c)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
