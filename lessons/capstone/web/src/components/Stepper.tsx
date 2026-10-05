import type { Step } from "../derive";

const MARK: Record<Step["state"], string> = {
  todo: "", active: "", waiting: "!", done: "✓", skipped: "–", failed: "✕",
};

export default function Stepper({ steps }: { steps: Step[] }) {
  const done = steps.filter((s) => s.state === "done" || s.state === "skipped").length;
  return (
    <div className="stepper-wrap">
      <ol className="stepper">
        {steps.map((s, i) => (
          <li key={s.id} className={s.state}>
            <span className="mark">{MARK[s.state] || i + 1}</span>
            <div>
              <div className="step-label">{s.label}</div>
              <div className="step-hint">{s.hint}</div>
            </div>
          </li>
        ))}
      </ol>
      <div className="progress">
        <div style={{ width: `${(done / steps.length) * 100}%` }} />
      </div>
    </div>
  );
}
