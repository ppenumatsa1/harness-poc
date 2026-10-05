import type { Order } from "../types";

export type CaseSummary = { caseId: string; orderId: string; result: string; fix: string };

type Props = {
  orders: Order[]; selected: string; busy: boolean; cases: CaseSummary[];
  onSelect: (id: string) => void; onInvestigate: () => void;
};

const money = (cents: number, currency: string) =>
  new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);

export default function OrderList({ orders, selected, busy, cases, onSelect, onInvestigate }: Props) {
  return (
    <aside className="sidebar">
      <div className="eyebrow">Orders</div>
      <div className="orders">
        {orders.map((o) => (
          <button
            key={o.order_id}
            className={`order ${o.order_id === selected ? "selected" : ""}`}
            onClick={() => onSelect(o.order_id)}
            disabled={busy}
          >
            <div className="order-top">
              <strong>#{o.order_id}</strong>
              <span className="amount">{money(o.total_cents, o.currency)}</span>
            </div>
            <span className={`status ${o.status.toLowerCase()}`}>{o.status.replace(/_/g, " ").toLowerCase()}</span>
          </button>
        ))}
      </div>
      <button className="btn primary block" disabled={busy || !selected} onClick={onInvestigate}>
        {busy ? "Agent working…" : `Investigate #${selected}`}
      </button>

      {cases.length > 0 && (
        <>
          <div className="eyebrow spaced">This session</div>
          <ul className="cases">
            {cases.map((c) => (
              <li key={c.caseId}>
                <div><strong>#{c.orderId}</strong> <span className="muted">{c.result}</span></div>
                <div className="mono muted">{c.caseId} · {c.fix}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}
