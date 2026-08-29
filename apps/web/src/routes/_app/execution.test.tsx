import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ExecutionReport } from "@/hooks/use-browser-execution";

const useLatestBrowserExecution = vi.fn();
vi.mock("@/hooks/use-browser-execution", () => ({
  useLatestBrowserExecution: () => useLatestBrowserExecution(),
}));

import { Route } from "./execution";

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

function report(): ExecutionReport {
  return {
    metadata: {
      run_id: "run-1",
      scenario_plan_key: "plan-1",
      project_source_id: "local:/demo",
      project_fingerprint: "abcdef1234567890",
      impact_change_source_id: "diff:1",
      config_fingerprint: "config",
      started_at: "2026-08-29T12:00:00Z",
      completed_at: "2026-08-29T12:00:01Z",
    },
    summary: {
      selected: 2,
      executed: 2,
      passed: 1,
      failed: 1,
      execution_error: 0,
      unverified: 0,
      skipped_manual: 0,
      blocked: 0,
    },
    scenarios: [
      {
        scenario_key: "scn-pass",
        title: "Checkout smoke",
        kind: "smoke",
        priority: "P0",
        status: "passed",
        failure_category: null,
        verified: true,
        target_route: "/checkout",
        duration_ms: 120,
        steps: [],
        artifacts: [],
        attempts: [],
        detail: null,
      },
      {
        scenario_key: "scn-fail",
        title: "Checkout label",
        kind: "state_variant",
        priority: "P0",
        status: "failed",
        failure_category: "assertion_failure",
        verified: true,
        target_route: "/checkout",
        duration_ms: 90,
        artifacts: [],
        attempts: [],
        detail: "expected You Pay, observed Total",
        steps: [
          {
            index: 1,
            operation: "assert_text",
            source_action: 'Assert text "You Pay"',
            source_expected: "You Pay",
            status: "failed",
            failure_category: "assertion_failure",
            actual: "Total",
            expected: "You Pay",
            duration_ms: 20,
            detail: "text mismatch",
            evidence: {
              requested_route: "/checkout",
              final_url: "http://localhost/checkout",
              title: "Checkout",
              console: [],
              network: [],
              artifacts: [{ kind: "screenshot", path: "/tmp/fail.png", sha256: null }],
            },
          },
        ],
      },
    ],
    coverage_gaps: [],
    run_artifacts: [],
  };
}

describe("Browser Execution screen", () => {
  it("renders execution status, failure category and evidence", () => {
    useLatestBrowserExecution.mockReturnValue({ isLoading: false, isError: false, data: report() });
    renderRoute();
    expect(screen.getByText("Browser Execution & Evidence")).toBeInTheDocument();
    expect(screen.getByText("Checkout label")).toBeInTheDocument();
    expect(screen.getByText(/Failure category: assertion_failure/)).toBeInTheDocument();
    expect(screen.getByText(/screenshot: \/tmp\/fail.png/)).toBeInTheDocument();
  });

  it("renders empty state when no report exists", () => {
    useLatestBrowserExecution.mockReturnValue({ isLoading: false, isError: false, data: null });
    renderRoute();
    expect(screen.getByTestId("execution-empty")).toHaveTextContent("No execution report yet");
  });
});
