import { useState } from "react";
import type { Fix } from "../types";

type Props = { fixes: Fix[]; busy: boolean; onDecide: (fix: Fix, approve: boolean, note: string) => void };

/** Human-in-the-loop: the agent can only apply a fix after a person approves it here. */
export default function DecisionPanel({ fixes, busy, onDecide }: Props) {
  const [note, setNote] = useState("");
  return (
    <div className="fixes">
      {fixes.map((f) => {
        // "approved" but not "applied" means the follow-up turn failed: allow a retry.
        const open = f.status === "pending" || f.status === "approved";
        return (
          <div key={f.id} className={`fix ${f.status} ${open ? "open" : ""}`}>
            <div className="fix-head">
              <span className="eyebrow">Fix #{f.id}</span>
              <span className={`badge ${f.status}`}>{f.status}</span>
            </div>
            <p>{f.action}</p>
            {f.decision_note && <p className="muted small">Note: {f.decision_note}</p>}
            {open && (
              <>
                <textarea
                  placeholder="Add a note for the record (optional)"
                  maxLength={500}
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  disabled={busy}
                />
                <div className="actions">
                  <button className="btn primary" disabled={busy} onClick={() => onDecide(f, true, note)}>
                    Approve and apply
                  </button>
                  <button className="btn" disabled={busy} onClick={() => onDecide(f, false, note)}>
                    Reject
                  </button>
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
