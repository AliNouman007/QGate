import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestStrategyDialog } from "@/components/cases/TestStrategyDialog";
import { server } from "@/mocks/server";

const strategy = {
  id: "strategy_1",
  workspace_id: "ws_1",
  project_id: "project_1",
  version: 1,
  status: "DRAFT",
  document: {
    schema_version: "1",
    summary: "Prioritize authorization and state integrity.",
    recommended_approach: "GRAY_BOX",
    approach_reason: "Repository and runtime evidence are available.",
    access_signals: ["repository"],
    risks: [
      {
        id: "RISK-AUTH",
        title: "Authorization boundaries",
        impact: "HIGH",
        likelihood: "MEDIUM",
        failure_modes: ["Tenant leak"],
        recommended_approach: "GRAY_BOX",
        test_levels: ["INTEGRATION"],
      },
    ],
    assumptions: [],
    oracles: [],
    coverage_dimensions: [],
    qa_checks: [],
    exclusions: [],
    enrichment: "DETERMINISTIC",
  },
  agent_session_id: null,
  created_by: null,
  approved_by: null,
  approved_at: null,
  created_at: "2026-07-27T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
} as const;

describe("TestStrategyDialog", () => {
  it("reviews and approves the current draft", async () => {
    let approved = false;
    server.use(
      http.get("*/api/v1/projects/project_1/test-strategies", () => HttpResponse.json([strategy])),
      http.post("*/api/v1/test-strategies/strategy_1/approve", () => {
        approved = true;
        return HttpResponse.json({ ...strategy, status: "APPROVED" });
      }),
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <TestStrategyDialog open onOpenChange={() => undefined} projectId="project_1" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Authorization boundaries")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve strategy" }));
    await waitFor(() => {
      expect(approved).toBe(true);
    });
  });
});
