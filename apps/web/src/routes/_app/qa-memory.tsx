import { createFileRoute } from "@tanstack/react-router";
import { Brain, CheckCircle2, CircleSlash2, History, XCircle } from "lucide-react";

import {
  type ConfirmedMemory,
  type MemoryCandidate,
  useConfirmMemoryCandidate,
  useDeactivateMemory,
  useQAMemories,
  useQAMemoryCandidates,
  useRejectMemoryCandidate,
} from "@/hooks/use-qa-memory";

function CandidateCard({ item }: { item: MemoryCandidate }): React.ReactElement {
  const confirm = useConfirmMemoryCandidate();
  const reject = useRejectMemoryCandidate();
  const pending = item.status === "pending";
  return (
    <article className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid={`memory-candidate-${item.key}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            {item.status === "confirmed" ? <CheckCircle2 className="h-4 w-4 text-green" /> : item.status === "rejected" ? <XCircle className="h-4 w-4 text-red" /> : <History className="h-4 w-4 text-amber" />}
            <h3 className="text-[13px] font-semibold text-fg-1">{item.title}</h3>
          </div>
          <p className="mt-1 font-mono text-[10px] text-fg-5">{item.key}</p>
        </div>
        <span className="rounded bg-bg-elev-3 px-2 py-1 text-[10px] uppercase text-fg-3">{item.status}</span>
      </div>
      <p className="mt-3 text-[12px] text-fg-2"><span className="font-semibold">Proposed invariant:</span> {item.invariant}</p>
      <p className="mt-2 text-[10.5px] text-fg-4">
        Pending findings are review candidates, not trusted bug history. {item.occurrences.length} occurrence(s).
      </p>
      {item.routes.length > 0 ? <p className="mt-2 font-mono text-[10px] text-fg-4">routes: {item.routes.join(", ")}</p> : null}
      {item.states.length > 0 ? <p className="mt-1 font-mono text-[10px] text-fg-4">states: {item.states.join(", ")}</p> : null}
      {item.review_note ? <p className="mt-2 text-[11px] text-fg-4">Review note: {item.review_note}</p> : null}
      {pending ? (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            className="rounded bg-green/15 px-3 py-1.5 text-[11px] font-medium text-green"
            disabled={confirm.isPending || reject.isPending}
            onClick={() => confirm.mutate({ key: item.key })}
          >
            Confirm memory
          </button>
          <button
            type="button"
            className="rounded bg-red/10 px-3 py-1.5 text-[11px] font-medium text-red"
            disabled={confirm.isPending || reject.isPending}
            onClick={() => reject.mutate({ key: item.key })}
          >
            Reject
          </button>
        </div>
      ) : null}
    </article>
  );
}

function MemoryCard({ item }: { item: ConfirmedMemory }): React.ReactElement {
  const deactivate = useDeactivateMemory();
  return (
    <article className="rounded-md border border-border bg-bg-elev-1 p-4" data-testid={`confirmed-memory-${item.key}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          {item.status === "active" ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-green" /> : <CircleSlash2 className="mt-0.5 h-4 w-4 text-fg-4" />}
          <div>
            <h3 className="text-[13px] font-semibold text-fg-1">{item.title}</h3>
            <p className="mt-1 font-mono text-[10px] text-fg-5">{item.key}</p>
          </div>
        </div>
        <span className="rounded bg-bg-elev-3 px-2 py-1 text-[10px] uppercase text-fg-3">{item.status}</span>
      </div>
      <p className="mt-3 text-[12px] text-fg-2"><span className="font-semibold">Trusted invariant:</span> {item.invariant}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-fg-4">
        <span>{item.severity}</span><span>{item.confidence} confidence</span><span>{item.originating_candidate_keys.length} source candidate(s)</span>
      </div>
      {item.routes.length > 0 ? <p className="mt-2 font-mono text-[10px] text-fg-4">routes: {item.routes.join(", ")}</p> : null}
      {item.states.length > 0 ? <p className="mt-1 font-mono text-[10px] text-fg-4">states: {item.states.join(", ")}</p> : null}
      <p className="mt-2 text-[10.5px] text-fg-5">Confirmed by {item.confirmed_by}</p>
      {item.status === "active" ? (
        <button
          type="button"
          className="mt-3 rounded bg-bg-elev-3 px-3 py-1.5 text-[11px] text-fg-3"
          disabled={deactivate.isPending}
          onClick={() => deactivate.mutate({ key: item.key })}
        >
          Deactivate
        </button>
      ) : null}
    </article>
  );
}

function QAMemory(): React.ReactElement {
  const candidates = useQAMemoryCandidates();
  const memories = useQAMemories();
  if (candidates.isLoading || memories.isLoading) return <div className="text-[13px] text-fg-4">Loading QA Memory…</div>;
  if (candidates.isError || memories.isError) return <div className="rounded-md border border-red/30 bg-red/5 p-4 text-[13px] text-red">Couldn't load QA Memory.</div>;

  const candidateItems = candidates.data ?? [];
  const memoryItems = memories.data ?? [];
  if (candidateItems.length === 0 && memoryItems.length === 0) {
    return (
      <section className="flex min-h-[360px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-bg-elev-1 p-8 text-center" data-testid="qa-memory-empty">
        <Brain className="h-8 w-8 text-fg-4" aria-hidden="true" />
        <div>
          <h2 className="text-[16px] font-semibold text-fg-1">No QA memory yet</h2>
          <p className="mt-1 max-w-[560px] text-[12px] text-fg-4">Verified findings can become review candidates. Only human-confirmed candidates become trusted regression memory.</p>
        </div>
      </section>
    );
  }

  const pending = candidateItems.filter((item) => item.status === "pending");
  const rejected = candidateItems.filter((item) => item.status === "rejected");
  return (
    <section className="flex flex-col gap-5" data-testid="qa-memory-screen">
      <header>
        <h2 className="text-[20px] font-semibold tracking-[-.01em] text-fg-1">QA Memory</h2>
        <p className="mt-1 text-[12px] text-fg-4">Two-stage learning: candidates need human confirmation before they can influence future regression recall.</p>
      </header>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[['Pending', pending.length], ['Confirmed', memoryItems.filter((item) => item.status === 'active').length], ['Rejected', rejected.length], ['Inactive/Superseded', memoryItems.filter((item) => item.status !== 'active').length]].map(([label, value]) => (
          <div key={String(label)} className="rounded-md border border-border bg-bg-elev-1 p-3"><div className="font-mono text-[18px] font-semibold text-fg-1">{value}</div><div className="mt-1 text-[10.5px] text-fg-4">{label}</div></div>
        ))}
      </div>
      <section>
        <h3 className="mb-2 text-[13px] font-semibold text-fg-1">Candidate review queue</h3>
        <div className="space-y-3">{candidateItems.map((item) => <CandidateCard key={item.key} item={item} />)}</div>
      </section>
      <section>
        <h3 className="mb-2 text-[13px] font-semibold text-fg-1">Confirmed regression memory</h3>
        <div className="space-y-3">{memoryItems.map((item) => <MemoryCard key={item.key} item={item} />)}</div>
      </section>
    </section>
  );
}

export const Route = createFileRoute("/_app/qa-memory")({
  component: QAMemory,
  staticData: { title: "QA Memory" },
});
