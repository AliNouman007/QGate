import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Boxes, Braces, GitBranch, Loader2, Map, ShieldAlert } from "lucide-react";

import { useLatestProjectIntelligence } from "@/hooks/use-project-intelligence";

function Counts({ values }: { values: Record<string, number> }): React.ReactElement {
  const entries = Object.entries(values).sort(([left], [right]) => left.localeCompare(right));
  if (entries.length === 0) return <span className="text-fg-4">None detected</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([name, count]) => (
        <span
          key={name}
          className="rounded-full border border-border bg-bg-elev-2 px-2 py-1 font-mono text-[11px] text-fg-3"
        >
          {name} · {count}
        </span>
      ))}
    </div>
  );
}

function ProjectMapScreen(): React.ReactElement {
  const query = useLatestProjectIntelligence();

  if (query.isLoading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center" data-testid="project-map-loading">
        <Loader2 className="h-5 w-5 animate-spin text-fg-3" aria-hidden="true" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <section className="rounded-md border border-red/30 bg-red/5 p-5" data-testid="project-map-error">
        <div className="flex items-center gap-2 text-red">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          <h2 className="text-sm font-semibold">Project Map could not be loaded</h2>
        </div>
        <button
          type="button"
          className="mt-3 rounded-md border border-border px-3 py-1.5 text-xs text-fg-2 hover:bg-bg-elev-2"
          onClick={() => void query.refetch()}
        >
          Retry
        </button>
      </section>
    );
  }

  const knowledge = query.data;
  if (knowledge === null || knowledge === undefined) {
    return (
      <section className="rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="project-map-empty">
        <Map className="mx-auto h-6 w-6 text-fg-4" aria-hidden="true" />
        <h2 className="mt-3 text-sm font-semibold text-fg-1">No project analyzed yet</h2>
        <p className="mx-auto mt-1 max-w-xl text-xs leading-5 text-fg-4">
          Run Project Intelligence locally. The latest persisted analysis will appear here automatically.
        </p>
        <code className="mt-3 inline-block rounded bg-bg-elev-2 px-2 py-1 font-mono text-[11px] text-fg-3">
          qgate-project-intelligence analyze &lt;project-path&gt;
        </code>
      </section>
    );
  }

  const routes = knowledge.files.flatMap((file) => file.routes).slice(0, 20);
  const components = knowledge.files
    .flatMap((file) => file.symbols.map((symbol) => ({ ...symbol, path: file.record.path })))
    .filter((symbol) => symbol.kind === "component")
    .slice(0, 20);
  const reused = Object.entries(knowledge.summary.reused_modules).slice(0, 12);

  return (
    <section className="flex flex-col gap-4" data-testid="project-map-screen">
      <header>
        <div className="flex items-center gap-2">
          <Map className="h-5 w-5 text-violet" aria-hidden="true" />
          <h2 className="text-[20px] font-semibold tracking-[-.01em] text-fg-1">Project Map</h2>
        </div>
        <p className="mt-1 max-w-3xl text-xs leading-5 text-fg-4">
          Evidence-backed structure and behavioral knowledge discovered by QGate Project Intelligence.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["Files", knowledge.summary.total_files, Braces],
          ["Routes", knowledge.summary.route_count, GitBranch],
          ["Components", knowledge.summary.component_count, Boxes],
          ["Runtime checks", knowledge.semantic_states.filter((state) => state.needs_runtime_verification).length, ShieldAlert],
        ].map(([label, value, Icon]) => {
          const MetricIcon = Icon as typeof Braces;
          return (
            <div key={String(label)} className="rounded-md border border-border bg-bg-elev-1 p-4">
              <MetricIcon className="h-4 w-4 text-fg-4" aria-hidden="true" />
              <div className="mt-3 font-mono text-xl font-semibold text-fg-1">{String(value)}</div>
              <div className="mt-0.5 text-[11px] uppercase tracking-wide text-fg-4">{String(label)}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Languages & frameworks</h3>
          <div className="mt-3 space-y-3">
            <Counts values={knowledge.summary.languages} />
            <Counts values={knowledge.summary.frameworks} />
          </div>
        </section>
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Behavioral states</h3>
          <div className="mt-3"><Counts values={knowledge.summary.behavioral_categories} /></div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Routes</h3>
          <ul className="mt-3 space-y-2">
            {routes.length === 0 ? <li className="text-xs text-fg-4">No framework routes detected.</li> : routes.map((route) => (
              <li key={`${route.evidence.path}:${route.route}`} className="rounded bg-bg-elev-2 px-3 py-2">
                <div className="font-mono text-xs text-fg-1">{route.route}</div>
                <div className="mt-1 text-[11px] text-fg-4">{route.router} · {route.kind} · {route.evidence.path}</div>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Components</h3>
          <ul className="mt-3 space-y-2">
            {components.length === 0 ? <li className="text-xs text-fg-4">No React components detected.</li> : components.map((component) => (
              <li key={`${component.path}:${component.name}`} className="rounded bg-bg-elev-2 px-3 py-2">
                <div className="font-mono text-xs text-fg-1">{component.name}</div>
                <div className="mt-1 text-[11px] text-fg-4">{component.path}:{component.evidence.line}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-md border border-border bg-bg-elev-1 p-4">
        <h3 className="text-sm font-semibold text-fg-1">Semantic states</h3>
        <div className="mt-3 grid grid-cols-1 gap-2 lg:grid-cols-2">
          {knowledge.semantic_states.length === 0 ? <p className="text-xs text-fg-4">No semantic states detected.</p> : knowledge.semantic_states.slice(0, 20).map((state) => (
            <div key={state.key} className="rounded bg-bg-elev-2 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-fg-1">{state.label}</span>
                <span className="font-mono text-[10px] uppercase text-fg-4">{state.confidence}</span>
              </div>
              <p className="mt-1 text-[11px] leading-4 text-fg-4">{state.explanation}</p>
              {state.needs_runtime_verification ? <div className="mt-2 text-[10px] font-medium uppercase tracking-wide text-amber">Needs runtime verification</div> : null}
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Shared / reused modules</h3>
          <ul className="mt-3 space-y-1.5">
            {reused.length === 0 ? <li className="text-xs text-fg-4">No reused internal modules detected.</li> : reused.map(([path, count]) => (
              <li key={path} className="flex items-center justify-between gap-3 text-xs">
                <span className="truncate font-mono text-fg-3">{path}</span>
                <span className="font-mono text-fg-1">{count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-md border border-border bg-bg-elev-1 p-4">
          <h3 className="text-sm font-semibold text-fg-1">Coverage gaps</h3>
          <ul className="mt-3 space-y-2">
            {knowledge.coverage_gaps.length === 0 ? <li className="text-xs text-accent">No recorded coverage gaps.</li> : knowledge.coverage_gaps.slice(0, 12).map((gap, index) => (
              <li key={`${gap.path ?? "project"}:${gap.reason}:${index}`} className="text-xs text-fg-3">
                <span className="font-medium text-amber">{gap.reason}</span>{gap.path ? ` · ${gap.path}` : ""}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <footer className="font-mono text-[10px] text-fg-5">
        {knowledge.metadata.source_id} · {knowledge.metadata.source_fingerprint.slice(0, 12)} · {new Date(knowledge.metadata.analyzed_at).toLocaleString()}
      </footer>
    </section>
  );
}

export const Route = createFileRoute("/_app/project-map")({
  component: ProjectMapScreen,
  staticData: { title: "Project Map" },
});
