import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateSuite } from "@/hooks/use-test-cases";
import type { components } from "@/lib/api-types";

type TestingApproach = components["schemas"]["TestingApproach"];

export interface CreateSuiteDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * First-suite bootstrap (dogfood blocker #1). Test cases live under suites, so
 * an empty project needs a suite before any case can be authored or generated.
 * Posts to the active project; on success the Cases tree picks the new suite up
 * via query invalidation.
 */
export function CreateSuiteDialog({ open, onClose }: CreateSuiteDialogProps): React.ReactElement {
  const [name, setName] = useState("");
  const [approach, setApproach] = useState<TestingApproach>("BLACK_BOX");
  const createSuite = useCreateSuite();

  const reset = (): void => {
    setName("");
    setApproach("BLACK_BOX");
    createSuite.reset();
  };

  const close = (): void => {
    reset();
    onClose();
  };

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed.length === 0) return;
    createSuite.mutate(
      { name: trimmed, defaultTestingApproach: approach },
      {
        onSuccess: () => {
          close();
        },
      },
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) close();
      }}
    >
      <DialogContent data-testid="create-suite-dialog">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>New suite</DialogTitle>
            <DialogDescription>
              Suites group related test cases — e.g. a login flow or a checkout journey.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="create-suite-name">Suite name</Label>
            <Input
              id="create-suite-name"
              data-testid="create-suite-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
              }}
              placeholder="e.g. Login flow"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="create-suite-approach">Default testing approach</Label>
            <select
              id="create-suite-approach"
              value={approach}
              onChange={(event) => {
                setApproach(event.target.value as TestingApproach);
              }}
              className="h-9 rounded-md border border-border bg-bg-base px-3 text-[13px] text-fg-2 outline-none focus:border-accent"
            >
              <option value="BLACK_BOX">Black-box — public behavior only</option>
              <option value="GRAY_BOX">Gray-box — public behavior + internal context</option>
              <option value="WHITE_BOX">White-box — internal tests and coverage</option>
            </select>
          </div>
          {createSuite.isError ? (
            <p data-testid="create-suite-error" className="text-[12.5px] text-red">
              Couldn&apos;t create the suite. Please try again.
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={close}>
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              data-testid="create-suite-submit"
              disabled={name.trim().length === 0 || createSuite.isPending}
            >
              {createSuite.isPending ? "Creating…" : "Create suite"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
