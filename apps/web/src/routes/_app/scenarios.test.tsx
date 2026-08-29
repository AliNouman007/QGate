import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ScenarioPlan } from "@/hooks/use-scenario-intelligence";

const useLatestScenarioPlan = vi.fn();
vi.mock("@/hooks/use-scenario-intelligence", () => ({
  useLatestScenarioPlan: () => useLatestScenarioPlan(),
}));

import { Route } from "./scenarios";

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

function plan(): ScenarioPlan {
  return {
    metadata: {
      generated_at: "2026-08-29T12:00:00Z",
      project_source_id: "local:/demo",
      project_fingerprint: "abcdef1234567890",
      impact_change_source_id: "git:main...feature",
    },
    summary: {
      total: 2,
      ready: 1,
      runtime_discovery: 1,
      manual_only: 0,
      blocked: 0,
      p0: 0,
      p1: 1,
      p2: 0,
      p3: 1,
    },
    scenarios: [
      {
        key: "scn_1",
        title: "Compare Rating present vs Rating absent on /search",
        kind: "cross_state_comparison",
        priority: "P1",
        confidence: "high",
        routes: ["/search"],
        targets: ["/search"],
        states: ["rating:present", "rating:absent"],
        preconditions: ["State A: Rating present", "State B: Rating absent"],
        steps: [
          {
            action: "Exercise /search in both states.",
            expected: "Layout relationship remains intentional.",
            target_kind: "FE_WEB",
            route: "/search",
            data_hint: null,
          },
        ],
        reason: "UI state-sensitive change",
        source_impact_keys: ["state:rating"],
        evidence: [{ path: "src/Card.tsx", line: 5, excerpt: "rating", kind: "state" }],
        readiness: "ready",
        needs_runtime_discovery: false,
        manual_reason: null,
        cross_state_group: "cross:/search:data_state",
        explanation: null,
        priority_hint: null,
      },
      {
        key: "scn_2",
        title: "Discover runtime coverage for Dynamic state",
        kind: "runtime_discovery",
        priority: "P3",
        confidence: "low",
        routes: [],
        targets: ["Dynamic state"],
        states: ["Dynamic state"],
        preconditions: [],
        steps: [
          {
            action: "Discover a reachable runtime setup.",
            expected: "A concrete setup can be established.",
            target_kind: "FE_WEB",
            route: null,
            data_hint: null,
          },
        ],
        reason: "Unknown impact",
        source_impact_keys: ["unknown:dynamic"],
        evidence: [{ path: "src/Card.tsx", line: 9, excerpt: "dynamic", kind: "state" }],
        readiness: "runtime_discovery_required",
        needs_runtime_discovery: true,
        manual_reason: "Static evidence is insufficient.",
        cross_state_group: null,
        explanation: null,
        priority_hint: null,
      },
    ],
    cross_state_groups: [
      {
        key: "cross:/search:data_state",
        route: "/search",
        state_labels: ["Rating present", "Rating absent"],
        scenario_keys: ["scn_1"],
        comparison_goal: "Compare both states",
      },
    ],
    coverage_gaps: [{ reason: "dynamic_state", detail: "Needs browser discovery", source_impact_key: null }],
  };
}

describe("Scenario Intelligence screen", () => {
  it("renders prioritized scenarios, readiness and cross-state groups", () => {
    useLatestScenarioPlan.mockReturnValue({ isLoading: false, isError: false, data: plan() });
    renderRoute();
    expect(screen.getByText("Scenario Intelligence")).toBeInTheDocument();
    expect(screen.getByText(/Compare Rating present/)).toBeInTheDocument();
    expect(screen.getByText(/Runtime discovery required/)).toBeInTheDocument();
    expect(screen.getByTestId("cross-state-groups")).toBeInTheDocument();
    expect(screen.getByTestId("scenario-gaps")).toBeInTheDocument();
  });

  it("renders empty state when no plan exists", () => {
    useLatestScenarioPlan.mockReturnValue({ isLoading: false, isError: false, data: null });
    renderRoute();
    expect(screen.getByTestId("scenarios-empty")).toHaveTextContent("No Scenario Plan yet");
  });
});
