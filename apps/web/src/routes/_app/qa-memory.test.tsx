import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const useCandidates = vi.fn();
const useMemories = vi.fn();
const confirmMutate = vi.fn();
const rejectMutate = vi.fn();
const deactivateMutate = vi.fn();

vi.mock("@/hooks/use-qa-memory", () => ({
  useQAMemoryCandidates: () => useCandidates(),
  useQAMemories: () => useMemories(),
  useConfirmMemoryCandidate: () => ({ mutate: confirmMutate, isPending: false }),
  useRejectMemoryCandidate: () => ({ mutate: rejectMutate, isPending: false }),
  useDeactivateMemory: () => ({ mutate: deactivateMutate, isPending: false }),
}));

import { Route } from "./qa-memory";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderRoute(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Component = Route.options.component as () => React.ReactElement;
  render(
    <QueryClientProvider client={queryClient}>
      <Component />
    </QueryClientProvider>,
  );
}

const pending = {
  key: "candidate_12345678",
  project_source_id: "local:/shop",
  project_fingerprint: "fp",
  title: "Checkout label",
  invariant: "Final payable must show You Pay",
  kind: "assertion_regression",
  severity: "high",
  routes: ["/checkout"],
  components: ["CheckoutSummary"],
  symbols: [],
  targets: [],
  states: ["wallet"],
  source_scenario_key: "checkout_wallet",
  source_execution_run_id: "run1",
  source_defect_id: null,
  evidence: [],
  confidence: "high",
  status: "pending",
  created_at: "2026-08-29T17:00:00Z",
  reviewed_at: null,
  reviewed_by: null,
  review_note: null,
  confirmed_memory_key: null,
  occurrences: [{ execution_run_id: "run1", scenario_key: "checkout_wallet", defect_id: null }],
};

const memory = {
  key: "memory_12345678",
  project_source_id: "local:/shop",
  title: "Checkout label",
  invariant: "Final payable must show You Pay",
  severity: "high",
  routes: ["/checkout"],
  components: ["CheckoutSummary"],
  symbols: [],
  targets: [],
  states: ["wallet"],
  originating_candidate_keys: ["candidate_12345678"],
  evidence: [],
  confidence: "high",
  status: "active",
  confirmed_at: "2026-08-29T17:02:00Z",
  confirmed_by: "user-1",
  superseded_by: null,
};

describe("QA Memory screen", () => {
  it("shows candidate as untrusted and exposes explicit review actions", () => {
    useCandidates.mockReturnValue({ isLoading: false, isError: false, data: [pending] });
    useMemories.mockReturnValue({ isLoading: false, isError: false, data: [] });
    renderRoute();
    expect(screen.getByText("QA Memory")).toBeInTheDocument();
    expect(screen.getByText(/Pending findings are review candidates/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm memory" }));
    expect(confirmMutate).toHaveBeenCalledWith({ key: "candidate_12345678" });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(rejectMutate).toHaveBeenCalledWith({ key: "candidate_12345678" });
  });

  it("shows trusted confirmed memory separately", () => {
    useCandidates.mockReturnValue({ isLoading: false, isError: false, data: [] });
    useMemories.mockReturnValue({ isLoading: false, isError: false, data: [memory] });
    renderRoute();
    expect(screen.getByText(/Trusted invariant:/)).toBeInTheDocument();
    expect(screen.getByText(/Confirmed by user-1/)).toBeInTheDocument();
  });

  it("renders empty state when no QA memory exists", () => {
    useCandidates.mockReturnValue({ isLoading: false, isError: false, data: [] });
    useMemories.mockReturnValue({ isLoading: false, isError: false, data: [] });
    renderRoute();
    expect(screen.getByTestId("qa-memory-empty")).toHaveTextContent("No QA memory yet");
  });
});
