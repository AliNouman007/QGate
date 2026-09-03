import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRouter,
} from "@tanstack/react-router";
import { render, screen, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "@/mocks/server";
import { routeTree } from "@/routeTree.gen";
import { ZERO_CAPS, resetCaps, setCaps } from "@/test/capabilities";

vi.mock("recharts", () => {
  const Pass = (props: { children?: React.ReactNode }) => <>{props.children}</>;
  return {
    ResponsiveContainer: Pass,
    LineChart: Pass,
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
  };
});

const ME = {
  id: "u_demo",
  email: "demo@suitest.dev",
  name: "Maya Demo",
  avatar_url: null,
  memberships: [],
};

function meHandler() {
  return http.get("*/api/v1/auth/me", () => HttpResponse.json(ME));
}

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: ["/dashboard"] }),
    context: { queryClient },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("Dashboard screen", () => {
  beforeEach(() => {
    setCaps(ZERO_CAPS);
    server.use(meHandler());
    vi.stubGlobal("location", {
      pathname: "/dashboard",
      assign: vi.fn(),
      origin: "http://localhost",
    });
  });
  afterEach(() => {
    resetCaps();
    vi.unstubAllGlobals();
  });

  it("renders welcome header, prominent Start QA Check button, 5-step process card, latest verdict, and recent checks", async () => {
    renderDashboard();
    expect(await screen.findByTestId("dashboard-header", undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByTestId("start-qa-check-button", undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByTestId("dashboard-qa-pipeline-card", undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByTestId("dashboard-latest-result", undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByTestId("dashboard-recent-runs", undefined, { timeout: 3000 })).toBeInTheDocument();

    // Verify uncluttered layout: legacy heavy KPI grid & readiness cards are removed
    expect(screen.queryByTestId("dashboard-kpis")).toBeNull();
    expect(screen.queryByTestId("dashboard-pass-rate")).toBeNull();
    expect(screen.queryByTestId("dashboard-readiness")).toBeNull();
  });

  it("opens Start QA Check dialog when button is clicked", async () => {
    renderDashboard();
    const btn = await screen.findByTestId("start-qa-check-button");
    act(() => {
      btn.click();
    });
    expect(await screen.findByTestId("start-qa-check-dialog")).toBeInTheDocument();
  });

  it("shows empty state when no recent checks exist", async () => {
    server.use(
      http.get("*/api/v1/runs", () => HttpResponse.json({ items: [] })),
    );
    renderDashboard();
    expect(await screen.findByTestId("dashboard-latest-result")).toHaveTextContent("No QA check has run yet");
  });
});
