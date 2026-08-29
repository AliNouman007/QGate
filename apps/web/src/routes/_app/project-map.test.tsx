import { render, screen } from "@testing-library/react";
import type { UseQueryResult } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectKnowledge } from "@/hooks/use-project-intelligence";
import { useLatestProjectIntelligence } from "@/hooks/use-project-intelligence";

import { Route } from "./project-map";

vi.mock("@/hooks/use-project-intelligence", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/use-project-intelligence")>(
    "@/hooks/use-project-intelligence",
  );
  return { ...actual, useLatestProjectIntelligence: vi.fn() };
});

const mockedUseLatest = vi.mocked(useLatestProjectIntelligence);
const ProjectMap = Route.options.component as () => React.ReactElement;

function queryResult(data: ProjectKnowledge | null): UseQueryResult<ProjectKnowledge | null> {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as UseQueryResult<ProjectKnowledge | null>;
}

const knowledge: ProjectKnowledge = {
  metadata: {
    source_id: "local:/demo",
    source_fingerprint: "1234567890abcdef",
    analyzed_at: "2026-08-29T12:00:00Z",
    reused_files: 3,
    analyzed_files: 1,
  },
  summary: {
    total_files: 8,
    total_source_bytes: 2048,
    languages: { typescript: 7 },
    frameworks: { nextjs: 2, react: 4, typescript: 7 },
    declared_frameworks: ["nextjs", "react", "typescript"],
    roles: { component: 2, route: 2 },
    reused_modules: { "src/components/Card.tsx": 3 },
    behavioral_categories: { auth: 1, loading: 1 },
    route_count: 2,
    component_count: 2,
    hook_count: 3,
  },
  files: [
    {
      record: { path: "src/app/products/[id]/page.tsx", role: "route", language: "typescript" },
      frameworks: [],
      routes: [
        {
          route: "/products/:id",
          router: "next_app",
          kind: "page",
          dynamic: true,
          evidence: { path: "src/app/products/[id]/page.tsx", line: 1, excerpt: "page", kind: "next_route" },
        },
      ],
      symbols: [],
    },
    {
      record: { path: "src/components/Card.tsx", role: "component", language: "typescript" },
      frameworks: [],
      routes: [],
      symbols: [
        {
          name: "Card",
          kind: "component",
          exported: true,
          evidence: { path: "src/components/Card.tsx", line: 4, excerpt: "Card", kind: "symbol" },
        },
      ],
    },
  ],
  semantic_states: [
    {
      key: "src/app/products/[id]/page.tsx:0",
      label: "Loading state",
      kind: "data_state",
      explanation: "Evidence suggests a loading state.",
      confidence: "high",
      evidence: [{ path: "src/app/products/[id]/page.tsx", line: 8, excerpt: "if (loading)", kind: "condition" }],
      needs_runtime_verification: false,
    },
  ],
  coverage_gaps: [],
};

describe("Project Map", () => {
  beforeEach(() => mockedUseLatest.mockReset());

  it("shows an empty state when no project has been analyzed", () => {
    mockedUseLatest.mockReturnValue(queryResult(null));
    render(<ProjectMap />);
    expect(screen.getByTestId("project-map-empty")).toBeInTheDocument();
    expect(screen.getByText("No project analyzed yet")).toBeInTheDocument();
  });

  it("renders framework, route, component and semantic knowledge", () => {
    mockedUseLatest.mockReturnValue(queryResult(knowledge));
    render(<ProjectMap />);
    expect(screen.getByTestId("project-map-screen")).toBeInTheDocument();
    expect(screen.getByText("/products/:id")).toBeInTheDocument();
    expect(screen.getByText("Card")).toBeInTheDocument();
    expect(screen.getByText("Loading state")).toBeInTheDocument();
    expect(screen.getByText(/nextjs/)).toBeInTheDocument();
  });
});
