import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, GitPullRequest, Route as RouteIcon, ShieldAlert } from "lucide-react";

import { type ImpactItem, useLatestImpactAnalysis } from "@/hooks/use-impact-analysis";

function ImpactCard({ title, items }: { title: string; items: ImpactItem[] }): React.ReactElement | null {
  if (items.length === 0) return null;
  return (
    <section className="rounded-md border border-border bg-bg-elev-1 p-4">
      <h3 className="mb-3 text-[13px] font-semibold text-fg-1">{title}</h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.key} className="rounded-md border border-border-subtle bg-bg-elev-2 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[12px] text-fg-1">{item.target}</span>
              <span className="rounded bg-bg-elev-3 px-1.5 py-0.5 text-[10px] uppercase text-fg-3">
                {item.level}
              </span>
              <span className="rounded bg-bg-elev-3 px-1.5 py-0.5 text-[10px] uppercase text-fg-3">
                {item.confidence}
              </span>
              {item.needs_runtime_verification ? (
                <span className="inline-flex items-center gap-1 text-[10px] text-amber">
                  <ShieldAlert className="h-3 w-3" aria-hidden="true" /> runtime verify
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-[11.5px] leading-relaxed text-fg-3">
              {item.explanation ?? item.reason}
            </p>
            {item.dependency_path.length > 0 ? (
              <p className="mt-1 font-mono text-[10px] text-fg-5">
                {item.dependency_path.map((step) => step.source).join(" → ")} → changed code
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Impact(): React.ReactElement {
  const query = useLatestImpactAnalysis();

  if (query.isLoading) {
    return <div className="text-[13px] text-fg-4">Loading impact report…</div>;
  }
  if (query.isError) {
    return (
      <div className="rounded-md border border-red/30 bg-red/5 p-4 text-[13px] text-red">
        Couldn't load Impact Analysis.
      </div>
    );
  }
  const report = query.data;
  if (!report) {
    return (
      <section className="flex min-h-[360px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="impact-empty">
        <GitPullRequest className="h-8 w-8 text-fg-4" aria-hidden="true" />
        <div>
          <h2 className="text-[16px] font-semibold text-fg-1">No impact report yet</h2>
          <p className="mt-1 max-w-[520px] text-[12px] text-fg-4">
            Run QGate Impact Analysis locally against a Git comparison or patch. The dashboard only reads persisted reports.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4" data-testid="impact-screen">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[20px] font-semibold tracking-[-.01em] text-fg-1">Impact Analysis</h2>
          <p className="mt-1 font-mono text-[11px] text-fg-4">{report.metadata.change_source_id}</p>
        </div>
        <div className="text-right font-mono text-[10px] text-fg-5">
          <div>project {report.metadata.project_fingerprint.slice(0, 12)}</div>
          <div>{new Date(report.metadata.analyzed_at).toLocaleString()}</div>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        {[
          ["Changed files", report.summary.changed_files],
          ["Symbols", report.summary.changed_symbols],
          ["Direct", report.summary.direct_impacts],
          ["Indirect", report.summary.indirect_impacts],
          ["Routes", report.summary.affected_routes],
          ["States", report.summary.affected_states],
          ["Runtime verify", report.summary.runtime_verification_items],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-border bg-bg-elev-1 p-3">
            <div className="font-mono text-[18px] font-semibold text-fg-1">{value}</div>
            <div className="mt-1 text-[10.5px] text-fg-4">{label}</div>
          </div>
        ))}
      </div>

      <section className="rounded-md border border-border bg-bg-elev-1 p-4">
        <h3 className="mb-3 text-[13px] font-semibold text-fg-1">What changed</h3>
        <ul className="space-y-1.5">
          {report.change_set.files.map((file) => (
            <li key={`${file.old_path ?? ""}:${file.path}`} className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
              <span className="text-fg-1">{file.path}</span>
              <span className="text-fg-4">{file.status}</span>
              <span className="text-fg-5">+{file.additions} / -{file.deletions}</span>
              {file.categories.map((category) => (
                <span key={category} className="rounded bg-bg-elev-3 px-1.5 py-0.5 text-[9.5px] text-fg-3">{category}</span>
              ))}
            </li>
          ))}
        </ul>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ImpactCard title="Direct impact" items={report.direct_impacts} />
        <ImpactCard title="Indirect / shared blast radius" items={report.indirect_impacts} />
        <ImpactCard title="Affected routes" items={report.affected_routes} />
        <ImpactCard title="Affected states" items={report.affected_states} />
        <ImpactCard title="Possible impact" items={report.possible_impacts} />
        <ImpactCard title="Unknown impact" items={report.unknown_impacts} />
      </div>

      {report.shared_groups.length > 0 ? (
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-fg-1">
            <RouteIcon className="h-4 w-4" aria-hidden="true" /> Shared/reused blast radius
          </h3>
          <ul className="space-y-2 text-[11.5px] text-fg-3">
            {report.shared_groups.map((group) => (
              <li key={group.changed_target}>
                <span className="font-mono text-fg-1">{group.changed_target}</span> — {group.reuse_count} known importers; routes: {group.affected_routes.join(", ") || "none detected"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {report.coverage_gaps.length > 0 ? (
        <section className="rounded-md border border-amber/30 bg-amber/5 p-4" data-testid="impact-gaps">
          <h3 className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-fg-1">
            <AlertTriangle className="h-4 w-4 text-amber" aria-hidden="true" /> Unknown / manual attention
          </h3>
          <ul className="space-y-1 text-[11.5px] text-fg-3">
            {report.coverage_gaps.map((gap, index) => (
              <li key={`${gap.path ?? "project"}:${gap.reason}:${index.toString()}`}>
                {gap.path ? `${gap.path}: ` : ""}{gap.reason}{gap.detail ? ` — ${gap.detail}` : ""}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export const Route = createFileRoute("/_app/impact")({
  component: Impact,
  staticData: { title: "Impact Analysis" },
});
