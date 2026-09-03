import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Topbar } from "@/components/shell/Topbar";

async function renderTopbar(initialPath = "/dashboard") {
  const rootRoute = createRootRoute({
    component: () => (
      <div data-testid="app-shell">
        <Topbar />
        <Outlet />
      </div>
    ),
  });

  const routes = [
    createRoute({
      getParentRoute: () => rootRoute,
      path: "/dashboard",
      staticData: { title: "Dashboard" },
      component: () => <div data-testid="page-/dashboard">Dashboard</div>,
    }),
    createRoute({
      getParentRoute: () => rootRoute,
      path: "/runs",
      staticData: { title: "Test Runs" },
      component: () => <div data-testid="page-/runs">Test Runs</div>,
    }),
    createRoute({
      getParentRoute: () => rootRoute,
      path: "/analytics",
      staticData: { title: "Analytics" },
      component: () => <div data-testid="page-/analytics">Analytics</div>,
    }),
  ];

  rootRoute.addChildren(routes);

  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  });

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  await waitFor(() => {
    expect(result.container.querySelector("[data-testid='topbar']")).not.toBeNull();
  });

  return result;
}

describe("<Topbar>", () => {
  it("renders search trigger, theme toggle, and tier badge", async () => {
    await renderTopbar("/dashboard");
    expect(screen.getByTestId("topbar-search-trigger")).toBeInTheDocument();
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("tier-badge")).toBeInTheDocument();
  });

  it("renders the tier badge slot from useCapabilities", async () => {
    await renderTopbar("/dashboard");
    expect(screen.getByTestId("tier-badge")).toHaveTextContent("ZERO");
  });

  it("does NOT render sponsor, support, or documentation help links in clean header", async () => {
    await renderTopbar("/dashboard");
    expect(screen.queryByTestId("topbar-sponsor-link")).toBeNull();
    expect(screen.queryByTestId("topbar-saweria-link")).toBeNull();
    expect(screen.queryByTestId("topbar-help-link")).toBeNull();
    expect(screen.queryByTestId("topbar-new-button")).toBeNull();
  });

  it("renders visible Start QA Check button in header", async () => {
    await renderTopbar("/dashboard");
    const btn = screen.getByTestId("topbar-start-qa-check-button");
    expect(btn).toBeInTheDocument();
    expect(btn.textContent).toContain("Start QA Check");
  });

  it("opens the command palette on ⌘K keydown", async () => {
    await renderTopbar("/dashboard");
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();

    const user = userEvent.setup();
    await user.keyboard("{Meta>}k{/Meta}");

    expect(await screen.findByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("opens the command palette on Ctrl+K keydown", async () => {
    await renderTopbar("/dashboard");
    const user = userEvent.setup();
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("opens the command palette when the search trigger is clicked", async () => {
    await renderTopbar("/dashboard");
    const trigger = screen.getByTestId("topbar-search-trigger");
    await userEvent.click(trigger);
    expect(await screen.findByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("lists navigation commands inside the palette", async () => {
    await renderTopbar("/dashboard");
    await userEvent.click(screen.getByTestId("topbar-search-trigger"));
    await screen.findByPlaceholderText(/Type a command/i);
    expect(screen.getByTestId("topbar-command-list")).toHaveTextContent("Go to Dashboard");
  });
});
