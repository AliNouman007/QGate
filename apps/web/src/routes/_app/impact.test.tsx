import { render, screen } from "@testing-library/react";
import type { UseQueryResult } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ImpactReport } from "@/hooks/use-impact-analysis";
import { useLatestImpactAnalysis } from "@/hooks/use-impact-analysis";

import { Route } from "./impact";

vi.mock("@/hooks/use-impact-analysis", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/use-impact-analysis")>(
    "@/hooks/use-impact-analysis",
  );
  return { ...actual, useLatestImpactAnalysis: vi.fn() };
});

const mockedUseLatest = vi.mocked(useLatestImpactAnalysis);
const Impact = Route.options.component as () => React.ReactElement;

function queryResult(data: ImpactReport | null): UseQueryResult<ImpactReport | null> {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as UseQueryResult<ImpactReport | null>;
}

const evidence = { path: "src/components/Card.tsx", line: 5, excerpt: "Card", kind: "diff_hunk" };
const report: ImpactReport = {
  metadata: {
    analyzed_at: "2026-08-29T12:00:00Z",
    project_source_id: "local:/demo",
    project_fingerprint: "1234567890abcdef",
    change_source_id: "git:/demo:main...HEAD",
  },
  summary: {
    changed_files: 1,
    changed_symbols: 1,
    direct_impacts: 2,
    indirect_impacts: 2,
    possible_impacts: 1,
    unknown_impacts: 0,
    affected_routes: 2,
    affected_states: 1,
    runtime_verification_items: 1,
  },
  change_set: {
    source_kind: "local_git",
    source_id: "git:/demo:main...HEAD",
    base_ref: "main",
    head_ref: "HEAD",
    title: null,
    files: [
      {
        path: "src/components/Card.tsx",
        old_path: "src/components/Card.tsx",
        status: "modified",
        additions: 1,
        deletions: 1,
        categories: ["ui", "state", "shared"],
      },
    ],
  },
  changed_symbols: [
    { file_path: "src/components/Card.tsx", symbol_name: "Card", symbol_kind: "component", confidence: "high" },
  ],
  direct_impacts: [
    {
      key: "file:card",
      target_type: "file",
      target: "src/components/Card.tsx",
      level: "direct",
      reason: "Changed file",
      confidence: "high",
      evidence: [evidence],
      dependency_path: [],
      categories: ["ui"],
      needs_runtime_verification: false,
      explanation: null,
      priority_hint: null,
    },
  ],
  indirect_impacts: [
    {
      key: "dependent:search",
      target_type: "module",
      target: "src/app/search/page.tsx",
      level: "indirect",
      reason: "Imports changed component",
      confidence: "high",
      evidence: [evidence],
      dependency_path: [{ source: "src/app/search/page.tsx", target: "src/components/Card.tsx", module: "Card" }],
      categories: ["ui"],
      needs_runtime_verification: false,
      explanation: null,
      priority_hint: null,
    },
  ],
  possible_impacts: [],
  unknown_impacts: [],
  affected_routes: [
    {
      key: "route:search",
      target_type: "route",
      target: "/search",
      level: "indirect",
      reason: "Route depends on changed component",
      confidence: "high",
      evidence: [evidence],
      dependency_path: [{ source: "src/app/search/page.tsx", target: "src/components/Card.tsx", module: "Card" }],
      categories: ["ui"],
      needs_runtime_verification: false,
      explanation: null,
      priority_hint: null,
    },
  ],
  affected_states: [
    {
      key: "state:no-rating",
      target_type: "state",
      target: "No rating state",
      level: "possible",
      reason: "Runtime reachability not proven",
      confidence: "medium",
      evidence: [evidence],
      dependency_path: [],
      categories: ["state"],
      needs_runtime_verification: true,
      explanation: "Card may render without rating data.",
      priority_hint: null,
    },
  ],
  shared_groups: [
    {
      changed_target: "src/components/Card.tsx",
      reuse_count: 3,
      affected_files: ["src/app/search/page.tsx"],
      affected_routes: ["/search"],
    },
  ],
  coverage_gaps: [],
};

describe("Impact Analysis", () => {
  beforeEach(() => mockedUseLatest.mockReset());

  it("shows an empty state when no report exists", () => {
    mockedUseLatest.mockReturnValue(queryResult(null));
    render(<Impact />);
    expect(screen.getByTestId("impact-empty")).toBeInTheDocument();
    expect(screen.getByText("No impact report yet")).toBeInTheDocument();
  });

  it("renders changed code, indirect blast radius, routes and runtime state warnings", () => {
    mockedUseLatest.mockReturnValue(queryResult(report));
    render(<Impact />);
    expect(screen.getByTestId("impact-screen")).toBeInTheDocument();
    expect(screen.getAllByText("src/components/Card.tsx").length).toBeGreaterThan(0);
    expect(screen.getByText("src/app/search/page.tsx")).toBeInTheDocument();
    expect(screen.getByText("/search")).toBeInTheDocument();
    expect(screen.getByText("No rating state")).toBeInTheDocument();
    expect(screen.getByText("runtime verify")).toBeInTheDocument();
  });
});
