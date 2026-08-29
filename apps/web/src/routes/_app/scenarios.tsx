import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, ListChecks, Search } from "lucide-react";

import { type ScenarioPlanItem, useLatestScenarioPlan } from "@/hooks/use-scenario-intelligence";

function ScenarioCard({ scenario }: { scenario: ScenarioPlanItem }): React.ReactElement {
  return (
    <article className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid="scenario-card">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-bg-elev-3 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-fg-2">{scenario.priority}</span>
        <span className="rounded bg-bg-elev-3 px-1.5 py-0.5 text-[10px] uppercase text-fg-3">{scenario.kind}</span>
        <span className="rounded bg-bg-elev-3 px-1.5 py-0.5 text-[10px] uppercase text-fg-3">{scenario.readiness}</span>
        <span className="text-[10px] uppercase text-fg-5">{scenario.confidence}</span>
      </div>
      <h3 className="mt-2 text-[14px] font-semibold text-fg-1">{scenario.title}</h3>
      <p className="mt-1 text-[11.5px] leading-relaxed text-fg-3">{scenario.explanation ?? scenario.reason}</p>
      {scenario.routes.length > 0 ? (
        <div className="mt-2 font-mono text-[10.5px] text-fg-4">Routes: {scenario.routes.join(", ")}</div>
      ) : null}
      {scenario.states.length > 0 ? (
        <div className="mt-1 font-mono text-[10.5px] text-fg-4">States: {scenario.states.join(", ")}</div>
      ) : null}
      {scenario.preconditions.length > 0 ? (
        <div className="mt-3 rounded bg-bg-elev-2 p-2 text-[11px] text-fg-3">
          <span className="font-medium text-fg-2">Preconditions:</span> {scenario.preconditions.join(" · ")}
        </div>
      ) : null}
      <ol className="mt-3 space-y-2">
        {scenario.steps.map((step, index) => (
          <li key={`${scenario.key}:${index.toString()}`} className="rounded-md border border-border-subtle bg-bg-elev-2 p-3 text-[11px]">
            <div className="text-fg-2">{index + 1}. {step.action}</div>
            <div className="mt-1 text-fg-4">Expect: {step.expected}</div>
          </li>
        ))}
      </ol>
      {scenario.needs_runtime_discovery ? (
        <div className="mt-3 flex items-center gap-1.5 text-[10.5px] text-amber">
          <Search className="h-3.5 w-3.5" aria-hidden="true" /> Runtime discovery required
          {scenario.manual_reason ? ` — ${scenario.manual_reason}` : ""}
        </div>
      ) : null}
      <div className="mt-3 text-[10px] text-fg-5">Evidence: {scenario.evidence.length} · Impact links: {scenario.source_impact_keys.length}</div>
    </article>
  );
}

function Scenarios(): React.ReactElement {
  const query = useLatestScenarioPlan();
  if (query.isLoading) return <div className="text-[13px] text-fg-4">Loading Scenario Plan…</div>;
  if (query.isError) {
    return <div className="rounded-md border border-red/30 bg-red/5 p-4 text-[13px] text-red">Couldn't load Scenario Intelligence.</div>;
  }
  const plan = query.data;
  if (!plan) {
    return (
      <section className="flex min-h-[360px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="scenarios-empty">
        <ListChecks className="h-8 w-8 text-fg-4" aria-hidden="true" />
        <div>
          <h2 className="text-[16px] font-semibold text-fg-1">No Scenario Plan yet</h2>
          <p className="mt-1 max-w-[520px] text-[12px] text-fg-4">Generate Scenario Intelligence locally from matching ProjectKnowledge and ImpactReport. This dashboard only reads persisted plans.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4" data-testid="scenarios-screen">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[20px] font-semibold tracking-[-.01em] text-fg-1">Scenario Intelligence</h2>
          <p className="mt-1 font-mono text-[11px] text-fg-4">{plan.metadata.impact_change_source_id}</p>
        </div>
        <div className="text-right font-mono text-[10px] text-fg-5">
          <div>project {plan.metadata.project_fingerprint.slice(0, 12)}</div>
          <div>{new Date(plan.metadata.generated_at).toLocaleString()}</div>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        {[
          ["Total", plan.summary.total],
          ["READY", plan.summary.ready],
          ["Runtime discovery", plan.summary.runtime_discovery],
          ["Manual", plan.summary.manual_only],
          ["P0", plan.summary.p0],
          ["P1", plan.summary.p1],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-border bg-bg-elev-1 p-3">
            <div className="font-mono text-[18px] font-semibold text-fg-1">{value}</div>
            <div className="mt-1 text-[10.5px] text-fg-4">{label}</div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {plan.scenarios.map((scenario) => <ScenarioCard key={scenario.key} scenario={scenario} />)}
      </div>

      {plan.cross_state_groups.length > 0 ? (
        <section className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid="cross-state-groups">
          <h3 className="mb-2 text-[13px] font-semibold text-fg-1">Cross-state comparisons</h3>
          <ul className="space-y-2 text-[11.5px] text-fg-3">
            {plan.cross_state_groups.map((group) => (
              <li key={group.key}><span className="font-mono text-fg-1">{group.route ?? "surface"}</span> — {group.state_labels.join(" vs ")}: {group.comparison_goal}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {plan.coverage_gaps.length > 0 ? (
        <section className="rounded-md border border-amber/30 bg-amber/5 p-4" data-testid="scenario-gaps">
          <h3 className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-fg-1"><AlertTriangle className="h-4 w-4 text-amber" aria-hidden="true" /> Coverage gaps / manual attention</h3>
          <ul className="space-y-1 text-[11.5px] text-fg-3">
            {plan.coverage_gaps.map((gap, index) => <li key={`${gap.reason}:${index.toString()}`}>{gap.reason}{gap.detail ? ` — ${gap.detail}` : ""}</li>)}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export const Route = createFileRoute("/_app/scenarios")({
  component: Scenarios,
  staticData: { title: "Scenario Intelligence" },
});
