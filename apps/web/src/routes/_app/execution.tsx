import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, CircleSlash2, PlayCircle, XCircle } from "lucide-react";

import {
  type ScenarioExecution,
  useLatestBrowserExecution,
} from "@/hooks/use-browser-execution";

function StatusIcon({ status }: { status: string }): React.ReactElement {
  if (status === "passed") return <CheckCircle2 className="h-4 w-4 text-green" aria-hidden="true" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red" aria-hidden="true" />;
  if (status === "execution_error") return <AlertTriangle className="h-4 w-4 text-amber" aria-hidden="true" />;
  return <CircleSlash2 className="h-4 w-4 text-fg-4" aria-hidden="true" />;
}

function ScenarioCard({ item }: { item: ScenarioExecution }): React.ReactElement {
  const artifacts = item.steps.flatMap((step) => step.evidence.artifacts);
  const consoleCount = item.steps.reduce((count, step) => count + step.evidence.console.length, 0);
  const networkFailures = item.steps.reduce(
    (count, step) => count + step.evidence.network.filter((event) => event.failure || (event.status ?? 0) >= 400).length,
    0,
  );
  return (
    <article className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid={`execution-${item.scenario_key}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <StatusIcon status={item.status} />
          <div>
            <h3 className="text-[13px] font-semibold text-fg-1">{item.title}</h3>
            <p className="mt-1 font-mono text-[10px] text-fg-5">{item.scenario_key}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[10px] uppercase text-fg-3">
          <span className="rounded bg-bg-elev-3 px-1.5 py-0.5">{item.priority || "—"}</span>
          <span className="rounded bg-bg-elev-3 px-1.5 py-0.5">{item.status}</span>
          <span className="rounded bg-bg-elev-3 px-1.5 py-0.5">{item.verified ? "verified" : "unverified"}</span>
        </div>
      </div>
      {item.target_route ? <p className="mt-2 font-mono text-[11px] text-fg-3">route {item.target_route}</p> : null}
      {item.failure_category ? (
        <p className="mt-2 text-[11px] text-amber">Failure category: {item.failure_category}</p>
      ) : null}
      {item.detail ? <p className="mt-2 text-[11.5px] leading-relaxed text-fg-3">{item.detail}</p> : null}
      <div className="mt-3 flex flex-wrap gap-3 text-[10.5px] text-fg-4">
        <span>{item.steps.length} steps</span>
        <span>{consoleCount} console events</span>
        <span>{networkFailures} network failures</span>
        <span>{artifacts.length} evidence artifacts</span>
        {item.duration_ms != null ? <span>{Math.round(item.duration_ms)} ms</span> : null}
      </div>
      {item.steps.length > 0 ? (
        <ol className="mt-3 space-y-2 border-t border-border-subtle pt-3">
          {item.steps.map((step) => (
            <li key={`${item.scenario_key}:${step.index}`} className="rounded bg-bg-elev-2 p-2.5 text-[11px]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-fg-1">{step.index}. {step.operation}</span>
                <span className="uppercase text-fg-4">{step.status}</span>
                {step.failure_category ? <span className="text-amber">{step.failure_category}</span> : null}
              </div>
              <p className="mt-1 text-fg-3">{step.source_action}</p>
              {step.actual != null || step.expected != null ? (
                <p className="mt-1 font-mono text-[10px] text-fg-5">
                  expected: {step.expected ?? "—"} · actual: {step.actual ?? "—"}
                </p>
              ) : null}
              {step.evidence.artifacts.map((artifact) => (
                <p key={artifact.path} className="mt-1 truncate font-mono text-[9.5px] text-fg-5">
                  {artifact.kind}: {artifact.path}
                </p>
              ))}
            </li>
          ))}
        </ol>
      ) : null}
    </article>
  );
}

function Execution(): React.ReactElement {
  const query = useLatestBrowserExecution();
  if (query.isLoading) return <div className="text-[13px] text-fg-4">Loading execution report…</div>;
  if (query.isError) {
    return <div className="rounded-md border border-red/30 bg-red/5 p-4 text-[13px] text-red">Couldn't load Browser Execution.</div>;
  }
  const report = query.data;
  if (!report) {
    return (
      <section className="flex min-h-[360px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="execution-empty">
        <PlayCircle className="h-8 w-8 text-fg-4" aria-hidden="true" />
        <div>
          <h2 className="text-[16px] font-semibold text-fg-1">No execution report yet</h2>
          <p className="mt-1 max-w-[540px] text-[12px] text-fg-4">
            Run QGate Browser Execution locally against a persisted Scenario Plan. This dashboard only reads evidence reports.
          </p>
        </div>
      </section>
    );
  }

  const metrics: Array<[string, number]> = [
    ["Selected", report.summary.selected],
    ["Passed", report.summary.passed],
    ["Failed", report.summary.failed],
    ["Execution errors", report.summary.execution_error],
    ["Unverified", report.summary.unverified],
    ["Manual", report.summary.skipped_manual],
    ["Blocked", report.summary.blocked],
  ];

  return (
    <section className="flex flex-col gap-4" data-testid="execution-screen">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[20px] font-semibold tracking-[-.01em] text-fg-1">Browser Execution & Evidence</h2>
          <p className="mt-1 font-mono text-[11px] text-fg-4">run {report.metadata.run_id}</p>
        </div>
        <div className="text-right font-mono text-[10px] text-fg-5">
          <div>plan {report.metadata.scenario_plan_key}</div>
          <div>project {report.metadata.project_fingerprint.slice(0, 12)}</div>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
        {metrics.map(([label, value]) => (
          <div key={label} className="rounded-md border border-border bg-bg-elev-1 p-3">
            <div className="font-mono text-[18px] font-semibold text-fg-1">{value}</div>
            <div className="mt-1 text-[10.5px] text-fg-4">{label}</div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {report.scenarios.map((scenario) => <ScenarioCard key={scenario.scenario_key} item={scenario} />)}
      </div>

      {report.coverage_gaps.length > 0 ? (
        <section className="rounded-md border border-amber/30 bg-amber/5 p-4" data-testid="execution-gaps">
          <h3 className="mb-2 text-[13px] font-semibold text-fg-1">Coverage gaps / unverified execution</h3>
          <ul className="space-y-1 text-[11.5px] text-fg-3">
            {report.coverage_gaps.map((gap, index) => (
              <li key={`${gap.scenario_key ?? "run"}:${gap.reason}:${index.toString()}`}>
                {gap.scenario_key ? `${gap.scenario_key}: ` : ""}{gap.reason}{gap.detail ? ` — ${gap.detail}` : ""}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export const Route = createFileRoute("/_app/execution")({
  component: Execution,
  staticData: { title: "Browser Execution" },
});
