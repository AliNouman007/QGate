import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";

type SelectorRepairProposal = components["schemas"]["SelectorRepairPublic"];
type SelectorRepairApplied = components["schemas"]["SelectorRepairApplied"];

export function SelectorRepairDialog({
  open,
  onOpenChange,
  caseId,
  stepId,
  onApplied,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
  stepId: string;
  onApplied: (code: string) => void;
}): React.ReactElement {
  const [errorEvidence, setErrorEvidence] = useState("");
  const [domSnapshot, setDomSnapshot] = useState("");
  const [proposal, setProposal] = useState<SelectorRepairProposal | null>(null);

  useEffect(() => {
    if (!open) {
      setErrorEvidence("");
      setDomSnapshot("");
      setProposal(null);
    }
  }, [open]);

  const propose = useMutation({
    mutationFn: async () =>
      (
        await api.post<SelectorRepairProposal>(`/test-cases/${caseId}/self-heal/propose`, {
          step_id: stepId,
          error: errorEvidence,
          dom_snapshot: domSnapshot || null,
        })
      ).data,
    onSuccess: setProposal,
  });
  const apply = useMutation({
    mutationFn: async () => {
      if (!proposal) throw new Error("No repair proposal");
      return (
        await api.post<SelectorRepairApplied>(`/test-cases/${caseId}/self-heal/apply`, {
          step_id: proposal.step_id,
          old_selector: proposal.old_selector,
          new_selector: proposal.new_selector,
          code_sha256: proposal.code_sha256,
          rationale: proposal.rationale,
        })
      ).data;
    },
    onSuccess: (result) => {
      onApplied(result.code);
      onOpenChange(false);
    },
  });
  const actionError = propose.error ?? apply.error;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-bg-elev-1 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Repair changed selector</DialogTitle>
          <DialogDescription>
            AI proposes one selector-only patch. Review it before updating the saved step.
          </DialogDescription>
        </DialogHeader>

        {proposal ? (
          <div className="space-y-3">
            <div className="grid gap-2 rounded-md border border-border bg-bg-base p-3 font-mono text-[12px] sm:grid-cols-2">
              <div>
                <span className="mb-1 block text-fg-4">Current</span>
                <code className="break-all text-red">{proposal.old_selector}</code>
              </div>
              <div>
                <span className="mb-1 block text-fg-4">Proposed</span>
                <code className="break-all text-accent">{proposal.new_selector}</code>
              </div>
            </div>
            <p className="text-[12px] leading-relaxed text-fg-3">{proposal.rationale}</p>
            <p className="font-mono text-[10px] text-fg-4">
              Confidence {Math.round(proposal.confidence * 100)}% · selector_changed
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <label className="block text-[12px] text-fg-3">
              Failure evidence
              <textarea
                aria-label="Failure evidence"
                value={errorEvidence}
                onChange={(event) => {
                  setErrorEvidence(event.target.value);
                }}
                placeholder="Paste the locator/selector failure from the run"
                className="mt-1 min-h-24 w-full rounded-md border border-border bg-bg-base p-3 font-mono text-[11px] text-fg-2 outline-none focus:border-accent"
              />
            </label>
            <label className="block text-[12px] text-fg-3">
              DOM snapshot <span className="text-fg-4">(optional)</span>
              <textarea
                aria-label="DOM snapshot"
                value={domSnapshot}
                onChange={(event) => {
                  setDomSnapshot(event.target.value);
                }}
                placeholder="Paste the relevant DOM or accessibility snapshot"
                className="mt-1 min-h-28 w-full rounded-md border border-border bg-bg-base p-3 font-mono text-[11px] text-fg-2 outline-none focus:border-accent"
              />
            </label>
          </div>
        )}

        {actionError ? (
          <p role="alert" className="text-[12px] text-red">
            {actionError.message}
          </p>
        ) : null}
        <DialogFooter>
          {proposal ? (
            <>
              <Button
                variant="outline"
                onClick={() => {
                  setProposal(null);
                }}
              >
                Back
              </Button>
              <Button
                disabled={apply.isPending}
                onClick={() => {
                  apply.mutate();
                }}
              >
                {apply.isPending ? "Applying…" : "Apply repair"}
              </Button>
            </>
          ) : (
            <Button
              disabled={!errorEvidence.trim() || propose.isPending}
              onClick={() => {
                propose.mutate();
              }}
            >
              {propose.isPending ? "Analyzing…" : "Propose repair"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
