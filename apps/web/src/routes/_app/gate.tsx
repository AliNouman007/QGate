import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, CircleHelp, ShieldAlert } from "lucide-react";

import { type GateFinding, useLatestFinalGate } from "@/hooks/use-final-gate";

function VerdictIcon({ verdict }: { verdict: string }): React.ReactElement {
  if (verdict === "PASS") return <CheckCircle2 className="h-6 w-6 text-green" aria-hidden="true" />;
  if (verdict === "BLOCK") return <ShieldAlert className="h-6 w-6 text-red" aria-hidden="true" />;
  return <AlertTriangle className="h-6 w-6 text-amber" aria-hidden="true" />;
}

function FindingList({ title, items }: { title: string; items: GateFinding[] }): React.ReactElement | null {
  if (items.length === 0) return null;
  return (
    <section className="rounded-md border border-border bg-bg-elev-1 p-4">
      <h3 className="text-[13px] font-semibold text-fg-1">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <article key={item.key} className="rounded bg-bg-elev-2 p-3" data-testid={`gate-finding-${item.key}`}>
            <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase text-fg-4">
              {item.priority ? <span>{item.priority}</span> : null}
              {item.scenario_key ? <span>{item.scenario_key}</span> : null}
              {item.failure_category ? <span>{item.failure_category}</span> : null}
              {item.verified ? <span>verified</span> : <span>unverified</span>}
            </div>
            <h4 className="mt-1 text-[12.5px] font-medium text-fg-1">{item.title}</h4>
            <p className="mt-1 text-[11.5px] leading-relaxed text-fg-3">{item.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Gate(): React.ReactElement {
  const query = useLatestFinalGate();
  if (query.isLoading) return <div className="text-[13px] text-fg-4">Loading Final Gate…</div>;
  if (query.isError) {
    return <div className="rounded-md border border-red/30 bg-red/5 p-4 text-[13px] text-red">Couldn't load Final Gate.</div>;
  }
  const report = query.data;
  if (!report) {
    return (
      <section className="flex min-h-[360px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="gate-empty">
        <CircleHelp className="h-8 w-8 text-fg-4" aria-hidden="true" />
        <div>
          <h2 className="text-[16px] font-semibold text-fg-1">No Final Gate report yet</h2>
          <p className="mt-1 max-w-[560px] text-[12px] text-fg-4">
            Run the local Final Gate evaluator after Project Intelligence, Impact Analysis, Scenario Intelligence, Browser Execution, and QA Memory are ready.
          </p>
        </div>
      </section>
    );
  }

  const required = report.coverage_items.filter((item) => item.required);
  const strongRisks = report.historical_risks.filter((item) => item.strong_match);

  return (
    <section className="flex flex-col gap-4" data-testid="gate-screen">
      <header className="rounded-md border border-border bg-bg-elev-1 p-5" data-testid={`gate-verdict-${report.verdict}`}>
        <div className="flex items-start gap-3">
          <VerdictIcon verdict={report.verdict} />
          <div>
            <div className="text-[10px] uppercase tracking-[0.12em] text-fg-4">Final Gate</div>
            <h2 className="mt-1 text-[22px] font-semibold tracking-[-.02em] text-fg-1">{report.verdict.replaceAll("_", " ")}</h2>
            <p className="mt-2 text-[12.5px] leading-relaxed text-fg-3">{report.headline}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 font-mono text-[10px] text-fg-5">
          <span>confidence {report.confidence}</span>
          <span>run {report.metadata.execution_run_id}</span>
          <span>project {report.metadata.project_fingerprint.slice(0, 12)}</span>
        </div>
      </header>

      <FindingList title="Blocking product failures" items={report.blocking_findings} />
      <FindingList title="Manual review required" items={report.manual_review_findings} />

      <section className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid="gate-coverage">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-[13px] font-semibold text-fg-1">Required scenario coverage</h3>
          <span className="font-mono text-[11px] text-fg-4">
            {report.coverage_summary.required_verified_pass}/{report.coverage_summary.required_total} verified pass
          </span>
        </div>
        <div className="mt-3 space-y-2">
          {required.map((item) => (
            <article key={item.scenario_key} className="rounded bg-bg-elev-2 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[12px] font-medium text-fg-1">{item.title}</span>
                <span className="font-mono text-[10px] uppercase text-fg-4">{item.coverage_outcome}</span>
              </div>
              <p className="mt-1 text-[10.5px] text-fg-4">{item.required_reason ?? "Required by gate policy"}</p>
              {item.failure_category ? <p className="mt-1 text-[10.5px] text-amber">{item.failure_category}</p> : null}
            </article>
          ))}
        </div>
      </section>

      {strongRisks.length > 0 ? (
        <section className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid="gate-history">
          <h3 className="text-[13px] font-semibold text-fg-1">Relevant confirmed QA memory</h3>
          <p className="mt-1 text-[10.5px] text-fg-4">Historical risk requires regression coverage; it is not proof the current code is broken.</p>
          <div className="mt-3 space-y-2">
            {strongRisks.map((risk) => (
              <article key={risk.rule_key ?? risk.memory_key} className="rounded bg-bg-elev-2 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11.5px] text-fg-1">{risk.objective ?? risk.rule_key ?? risk.memory_key}</span>
                  <span className="font-mono text-[10px] text-fg-4">{risk.covered ? "covered" : "unverified"}</span>
                </div>
                {risk.expected_invariant ? <p className="mt-1 text-[10.5px] text-fg-4">{risk.expected_invariant}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid="gate-trace">
        <h3 className="text-[13px] font-semibold text-fg-1">Decision trace</h3>
        <ol className="mt-3 space-y-2 text-[11px] text-fg-3">
          {report.decision_trace.map((entry, index) => (
            <li key={`${entry.rule_id}:${index.toString()}`}>
              <span className="font-mono text-fg-4">{entry.rule_id}</span> — {entry.reason}
            </li>
          ))}
        </ol>
      </section>
    </section>
  );
}

export const Route = createFileRoute("/_app/gate")({
  component: Gate,
  staticData: { title: "Final Gate" },
});
