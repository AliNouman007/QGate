import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const useLatest = vi.fn();

vi.mock("@/hooks/use-final-gate", () => ({
  useLatestFinalGate: () => useLatest(),
}));

import { Route } from "./gate";

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

function report(verdict: "PASS" | "BLOCK" | "MANUAL_REVIEW_REQUIRED") {
  return {
    metadata: {
      report_key: "gate_12345678",
      generated_at: "2026-08-29T18:00:00Z",
      project_source_id: "local:/shop",
      project_fingerprint: "fingerprint1234",
      change_source_id: "change:1",
      scenario_plan_key: "plan:1",
      execution_run_id: "run:1",
    },
    verdict,
    confidence: "high",
    headline: `${verdict} — example decision`,
    blocking_findings:
      verdict === "BLOCK"
        ? [
            {
              key: "finding_block",
              kind: "verified_product_failure",
              title: "Checkout wallet final payable",
              reason: "expected You Pay but saw Total",
              verdict_effect: "blocking",
              priority: "P1",
              scenario_key: "checkout_wallet",
              routes: ["/checkout"],
              states: ["wallet"],
              verified: true,
              product_facing: true,
              failure_category: "assertion_failure",
              source_memory_keys: [],
              source_rule_keys: [],
            },
          ]
        : [],
    manual_review_findings:
      verdict === "MANUAL_REVIEW_REQUIRED"
        ? [
            {
              key: "finding_manual",
              kind: "environment_or_setup_gap",
              title: "Checkout wallet final payable",
              reason: "Required scenario could not be verified because environment_failure.",
              verdict_effect: "manual_review",
              priority: "P1",
              scenario_key: "checkout_wallet",
              routes: ["/checkout"],
              states: ["wallet"],
              verified: false,
              product_facing: false,
              failure_category: "environment_failure",
              source_memory_keys: [],
              source_rule_keys: [],
            },
          ]
        : [],
    informational_findings: [],
    coverage_summary: {
      required_total: 1,
      required_verified_pass: verdict === "PASS" ? 1 : 0,
      required_verified_fail: verdict === "BLOCK" ? 1 : 0,
      required_unverified: verdict === "MANUAL_REVIEW_REQUIRED" ? 1 : 0,
      required_manual: 0,
      required_blocked: 0,
      optional_total: 0,
      optional_verified: 0,
      historical_required_total: 0,
      historical_required_verified: 0,
      truncated: false,
      has_coverage_gaps: false,
    },
    coverage_items: [
      {
        scenario_key: "checkout_wallet",
        title: "Checkout wallet final payable",
        priority: "P1",
        required: true,
        required_reason: "P1 scenario is always required",
        readiness: "ready",
        execution_status: verdict === "PASS" ? "passed" : verdict === "BLOCK" ? "failed" : "execution_error",
        verified: verdict !== "MANUAL_REVIEW_REQUIRED",
        failure_category: verdict === "BLOCK" ? "assertion_failure" : verdict === "MANUAL_REVIEW_REQUIRED" ? "environment_failure" : null,
        coverage_outcome: verdict === "PASS" ? "verified_pass" : verdict === "BLOCK" ? "verified_fail" : "unverified",
        routes: ["/checkout"],
        states: ["wallet"],
        historical_memory_keys: [],
        historical_rule_keys: [],
      },
    ],
    historical_risks: [],
    input_integrity_findings: [],
    decision_trace: [{ rule_id: "FG-TEST", reason: "Deterministic example", scenario_key: null, finding_key: null }],
    ai_explanation: null,
  };
}

describe("Final Gate screen", () => {
  it("renders empty state", () => {
    useLatest.mockReturnValue({ isLoading: false, isError: false, data: null });
    renderRoute();
    expect(screen.getByTestId("gate-empty")).toHaveTextContent("No Final Gate report yet");
  });

  it("renders PASS as verified required coverage", () => {
    useLatest.mockReturnValue({ isLoading: false, isError: false, data: report("PASS") });
    renderRoute();
    expect(screen.getByTestId("gate-verdict-PASS")).toHaveTextContent("PASS");
    expect(screen.getByTestId("gate-coverage")).toHaveTextContent("1/1 verified pass");
  });

  it("renders verified product BLOCK distinctly", () => {
    useLatest.mockReturnValue({ isLoading: false, isError: false, data: report("BLOCK") });
    renderRoute();
    expect(screen.getByTestId("gate-verdict-BLOCK")).toHaveTextContent("BLOCK");
    expect(screen.getByText("Blocking product failures")).toBeInTheDocument();
    expect(screen.getByText(/expected You Pay but saw Total/)).toBeInTheDocument();
  });

  it("renders environment gap as manual review rather than product failure", () => {
    useLatest.mockReturnValue({ isLoading: false, isError: false, data: report("MANUAL_REVIEW_REQUIRED") });
    renderRoute();
    expect(screen.getByTestId("gate-verdict-MANUAL_REVIEW_REQUIRED")).toHaveTextContent("MANUAL REVIEW REQUIRED");
    expect(screen.getByText("Manual review required")).toBeInTheDocument();
    expect(screen.queryByText("Blocking product failures")).not.toBeInTheDocument();
  });
});
