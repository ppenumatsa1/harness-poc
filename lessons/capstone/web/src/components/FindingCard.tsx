import type { Finding } from "../types";

const clean = (s: string) => s.replace(/^[`"']+|[`"']+$/g, "");

export default function FindingCard({ finding, problems }: { finding: Finding; problems: string[] }) {
  const healthy = finding.failure_class === "NO_FAILURE";
  const pct = Math.round(finding.confidence * 100);
  return (
    <div className={`finding ${healthy ? "healthy" : "failed"}`}>
      <div className="finding-head">
        <div>
          <div className="eyebrow">Finding · order {finding.order_id}</div>
          <div className="finding-class">{finding.failure_class.replace(/_/g, " ")}</div>
        </div>
        <div className="confidence" title="Model-reported confidence">
          <span>{pct}%</span>
          <div className="meter"><div style={{ width: `${pct}%` }} /></div>
        </div>
      </div>
      <p className="root-cause">{finding.root_cause}</p>
      {!healthy && (
        <>
          <div className="eyebrow">First failing log line</div>
          <pre className="log">{clean(finding.first_failure_log)}</pre>
        </>
      )}
      <div className="eyebrow">Evidence</div>
      <ul className="evidence">
        {finding.evidence.map((e, i) => <li key={i}>{e}</li>)}
      </ul>
      {problems.map((p, i) => <div key={i} className="notice warn">{p}</div>)}
    </div>
  );
}
