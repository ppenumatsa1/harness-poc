import type { Guard } from "../derive";

/** Hooks and the permission handler: what the harness allowed, blocked or changed. */
export default function Guardrails({ guards, start }: { guards: Guard[]; start: number }) {
  if (guards.length === 0) return <p className="muted small">No guardrail events yet.</p>;
  return (
    <ul className="guards">
      {guards.map((g, i) => (
        <li key={i} className={g.tone}>
          <span className="guard-label">{g.label}</span>
          <span className="guard-text">{g.text}</span>
          <span className="dur">+{((g.at - start) / 1000).toFixed(1)}s</span>
        </li>
      ))}
    </ul>
  );
}
