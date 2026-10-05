import type { Role } from "../derive";

type Box = { role: Role; title: string; sub: string };

const BOXES: Box[] = [
  { role: "human", title: "You", sub: "Approve or reject" },
  { role: "app", title: "App", sub: "React · FastAPI" },
  { role: "harness", title: "Harness", sub: "Copilot SDK · hooks" },
  { role: "model", title: "Model", sub: "Foundry · BYOK" },
  { role: "biz", title: "Business data", sub: "Postgres · logs MCP" },
];

/** "Who is working right now": the same role colours as docs/explainer-checkout-flow.html. */
export default function Stage({ active, live }: { active: Role | null; live: Partial<Record<Role, string>> }) {
  return (
    <div className="stage">
      {BOXES.map((b, i) => (
        <div key={b.role} className="stage-cell">
          {i > 0 && <span className={`link ${active === b.role || active === BOXES[i - 1].role ? "on" : ""}`} />}
          <div className={`role ${b.role} ${active === b.role ? "active" : ""}`}>
            <div className="role-head">
              <span className="dot" />
              <strong>{b.title}</strong>
            </div>
            <small>{b.sub}</small>
            <div className="role-live" title={live[b.role]}>{live[b.role] ?? "—"}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
