import { useEffect, useMemo, useState } from "react";
import AgentLanes from "./components/AgentLanes";
import DecisionPanel from "./components/DecisionPanel";
import EventTimeline from "./components/EventTimeline";
import FindingCard from "./components/FindingCard";
import Guardrails from "./components/Guardrails";
import OrderList, { type CaseSummary } from "./components/OrderList";
import Stage from "./components/Stage";
import Stepper from "./components/Stepper";
import { derive } from "./derive";
import { streamEvents } from "./sse";
import type { AgentEvent, Finding, Fix, Health, Order, TimedEvent, Usage } from "./types";

const FACT_CHECK = "finding failed fact checks: ";

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selected, setSelected] = useState("1000");
  const [health, setHealth] = useState<Health | "down" | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [events, setEvents] = useState<TimedEvent[]>([]);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [usages, setUsages] = useState<Usage[]>([]);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    fetch("/api/orders")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then(setOrders)
      .catch((e: Error) => setError(`Could not load orders: ${e.message}`));
    const check = () =>
      fetch("/api/health")
        .then((r) => r.json())
        .then(setHealth)
        .catch(() => setHealth("down"));
    void check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!busy) return;
    const id = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(id);
  }, [busy]);

  const view = useMemo(() => derive(events, finding, fixes, busy), [events, finding, fixes, busy]);

  function onEvent(event: AgentEvent) {
    setEvents((prev) => [...prev, { at: Date.now(), event }]);
    switch (event.type) {
      case "conversation":
        setConversationId(event.conversation_id);
        break;
      case "finding":
        setFinding(event.finding);
        break;
      case "message":
        setMessage(event.text);
        break;
      case "done":
        setFixes(event.fixes);
        setUsages((prev) => [...prev, event.usage]);
        break;
    }
  }

  async function run(url: string, body: unknown) {
    setBusy(true);
    setError(null);
    setNow(Date.now());
    try {
      await streamEvents(url, body, onEvent);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function investigate() {
    setConversationId(null);
    setEvents([]);
    setFinding(null);
    setMessage(null);
    setFixes([]);
    setUsages([]);
    void run("/api/investigate", { order_id: selected });
  }

  function decide(fix: Fix, approve: boolean, note: string) {
    if (!conversationId) return;
    setMessage(null);
    void run("/api/decision", { conversation_id: conversationId, fix_id: fix.id, approve, note });
  }

  // Keep a short list of this browser session's cases.
  useEffect(() => {
    if (busy || !conversationId || events.length === 0) return;
    const fix = fixes[0];
    const summary: CaseSummary = {
      caseId: conversationId,
      orderId: finding?.order_id ?? selected,
      result: finding ? finding.failure_class.replace(/_/g, " ").toLowerCase() : "no finding",
      fix: fix ? `fix #${fix.id} ${fix.status}` : "no fix",
    };
    setCases((prev) => [summary, ...prev.filter((c) => c.caseId !== conversationId)].slice(0, 6));
  }, [busy]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = events[0]?.at ?? now;
  const end = busy ? now : events[events.length - 1]?.at ?? start;
  const totals = usages.reduce(
    (t, u) => ({ calls: t.calls + u.model_calls, tin: t.tin + u.input_tokens, tout: t.tout + u.output_tokens }),
    { calls: 0, tin: 0, tout: 0 },
  );
  const model = usages[usages.length - 1]?.model ?? null;
  const problems = view.errors.filter((e) => e.startsWith(FACT_CHECK)).map((e) => e.slice(FACT_CHECK.length));
  const otherErrors = [...view.errors.filter((e) => !e.startsWith(FACT_CHECK)), ...(error ? [error] : [])];
  const h = health === "down" ? null : health;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span>
          <div>
            <h1>Checkout Investigator</h1>
            <p>A Copilot SDK agent finds why a checkout failed and proposes a fix you approve.</p>
          </div>
        </div>
        <div className="health">
          <Pill label="API" ok={health === null ? undefined : health !== "down"} />
          <Pill label="Harness" ok={h ? h.agent.status === "ok" : health === "down" ? false : undefined} />
          <Pill label="Runtime" ok={h?.agent.runtime} />
          <Pill label="Postgres" ok={h?.db} />
          {model && <span className="pill model-pill">{model}</span>}
        </div>
      </header>

      <div className="layout">
        <OrderList
          orders={orders}
          selected={selected}
          busy={busy}
          cases={cases}
          onSelect={setSelected}
          onInvestigate={investigate}
        />

        <main className="main">
          {events.length === 0 && !busy ? (
            <Intro />
          ) : (
            <>
              <section className="card">
                <div className="case-head">
                  <div>
                    <div className="eyebrow">Case</div>
                    <div className="case-title">
                      Order #{finding?.order_id ?? selected}
                      <span className="mono muted">{conversationId ?? "starting…"}</span>
                    </div>
                  </div>
                  <div className="stats">
                    <Stat label="Elapsed" value={`${((end - start) / 1000).toFixed(1)}s`} live={busy} />
                    <Stat label="Model calls" value={String(totals.calls || "—")} />
                    <Stat label="Tool calls" value={String(view.toolCalls)} />
                    <Stat label="Tokens in / out" value={totals.tin ? `${(totals.tin / 1000).toFixed(1)}K / ${(totals.tout / 1000).toFixed(1)}K` : "—"} />
                    <Stat label="429 retries" value={String(view.retries)} warn={view.retries > 0} />
                  </div>
                </div>
                <Stepper steps={view.steps} />
              </section>

              <section className="card">
                <div className="card-title">Who is working now</div>
                <Stage active={view.activeRole} live={view.live} />
              </section>

              {otherErrors.map((e, i) => <div key={i} className="notice bad">{e}</div>)}

              <div className="grid">
                <div className="col">
                  <section className="card">
                    <div className="card-title">Agents and tool calls</div>
                    <AgentLanes lanes={view.lanes} />
                  </section>
                  <section className="card">
                    <div className="card-title">Guardrails <span className="muted">hooks · permissions</span></div>
                    <Guardrails guards={view.guards} start={start} />
                  </section>
                </div>
                <div className="col">
                  <section className="card">
                    <div className="card-title">Result</div>
                    {finding ? (
                      <FindingCard finding={finding} problems={problems} />
                    ) : (
                      <p className="muted small">{busy ? "The agent is still investigating…" : "No finding."}</p>
                    )}
                    {message && <p className="message">{message}</p>}
                  </section>
                  {fixes.length > 0 && (
                    <section className="card">
                      <div className="card-title">Your decision</div>
                      <DecisionPanel fixes={fixes} busy={busy} onDecide={decide} />
                    </section>
                  )}
                </div>
              </div>

              <details className="card raw">
                <summary>Raw event stream <span className="muted">({events.length} events)</span></summary>
                <EventTimeline events={events} busy={busy} />
              </details>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function Pill({ label, ok }: { label: string; ok?: boolean }) {
  return (
    <span className={`pill ${ok === undefined ? "unknown" : ok ? "up" : "down"}`}>
      <i />
      {label}
    </span>
  );
}

function Stat({ label, value, live, warn }: { label: string; value: string; live?: boolean; warn?: boolean }) {
  return (
    <div className={`stat ${warn ? "warn" : ""}`}>
      <div className="stat-value">
        {live && <span className="pulse" />}
        {value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function Intro() {
  const steps = [
    ["Plan", "The agent loads the checkout runbook skill."],
    ["Delegate", "Two specialist sub-agents look at payments, stock and logs in parallel."],
    ["Guard", "Hooks keep tools inside this order and hide card numbers."],
    ["Diagnose", "The model returns a structured finding with evidence."],
    ["Decide", "You approve or reject the proposed fix. Nothing changes without you."],
  ];
  return (
    <section className="card intro">
      <div className="eyebrow">How it works</div>
      <h2>Pick an order and start an investigation.</h2>
      <ol className="intro-steps">
        {steps.map(([t, d], i) => (
          <li key={t}>
            <span className="mark">{i + 1}</span>
            <div>
              <strong>{t}</strong>
              <p>{d}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
