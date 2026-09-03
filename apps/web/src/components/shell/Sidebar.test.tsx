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

import { Sidebar, type SidebarProps } from "@/components/shell/Sidebar";

async function renderSidebar(
  initialPath = "/dashboard",
  props: SidebarProps = {},
) {
  const rootRoute = createRootRoute({
    component: () => (
      <div data-testid="app-shell">
        <Sidebar {...props} />
        <Outlet />
      </div>
    ),
  });

  const routes = [
    "/dashboard",
    "/gate",
    "/project-map",
    "/impact",
    "/qa-memory",
    "/settings",
    "/cases",
    "/runs",
    "/defects",
    "/execution",
    "/analytics",
    "/inbox",
    "/integrations",
    "/docs",
    "/admin",
  ].map((path) =>
    createRoute({
      getParentRoute: () => rootRoute,
      path,
      component: () => <div data-testid={`page-${path}`}>{path}</div>,
    }),
  );

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
    expect(result.container.querySelector("[data-testid='sidebar']")).not.toBeNull();
  });

  return result;
}

describe("<Sidebar>", () => {
  it("renders only the 6 primary QGate navigation items by default", async () => {
    await renderSidebar("/dashboard");
    const expectedPrimary = [
      "Overview",
      "QA Checks",
      "Project Knowledge",
      "Impact & Test Plan",
      "QA Memory",
      "Settings",
    ];
    for (const label of expectedPrimary) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    // Uncluttered: old broad section headers are not rendered
    expect(screen.queryByText("Workspace")).toBeNull();
    expect(screen.queryByText("Testing")).toBeNull();
    expect(screen.queryByText("Insights")).toBeNull();
    expect(screen.queryByText("Config")).toBeNull();

    // Secondary items hidden by default
    expect(screen.queryByText("Inbox")).toBeNull();
    expect(screen.queryByText("Test Runs")).toBeNull();
    expect(screen.queryByText("Browser Execution")).toBeNull();
    expect(screen.queryByText("Analytics")).toBeNull();
    expect(screen.queryByText("Docs")).toBeNull();
    expect(screen.queryByText("Integrations")).toBeNull();
  });

  it("keeps More tools collapsed by default and expands on click", async () => {
    await renderSidebar("/dashboard");
    expect(screen.queryByTestId("more-tools-list")).toBeNull();

    const toggle = screen.getByTestId("nav-more-tools-toggle");
    expect(toggle).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(toggle);

    expect(screen.getByTestId("more-tools-list")).toBeInTheDocument();
    expect(screen.getByText("Test Cases & Suites")).toBeInTheDocument();
    expect(screen.getByText("Docs")).toBeInTheDocument();
  });

  it("renders active project picker", async () => {
    await renderSidebar("/dashboard");
    expect(screen.getByTestId("project-picker")).toBeInTheDocument();
  });

  it("highlights the active route via Link activeProps", async () => {
    await renderSidebar("/gate");
    const gateNav = screen.getByTestId("nav-qa-checks");
    await waitFor(() => {
      expect(gateNav.getAttribute("data-status")).toBe("active");
    });
    const dashboardNav = screen.getByTestId("nav-overview");
    expect(dashboardNav.getAttribute("data-status")).not.toBe("active");
  });

  it("shows a live dot next to QA Checks when activeRunsCount > 0", async () => {
    await renderSidebar("/dashboard", { activeRunsCount: 2 });
    expect(screen.getByTestId("nav-qa-checks-live-dot")).toBeInTheDocument();
  });

  it("hides the live dot when activeRunsCount is 0", async () => {
    await renderSidebar("/dashboard", { activeRunsCount: 0 });
    expect(screen.queryByTestId("nav-qa-checks-live-dot")).toBeNull();
  });

  it("renders the notification bell with a red dot when unreadCount > 0", async () => {
    await renderSidebar("/dashboard", { unreadCount: 5 });
    expect(screen.getByTestId("sidebar-bell")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar-bell-unread")).toBeInTheDocument();
  });

  it("omits the bell red dot when unreadCount is 0", async () => {
    await renderSidebar("/dashboard", { unreadCount: 0 });
    expect(screen.queryByTestId("sidebar-bell-unread")).toBeNull();
  });

  it("Settings nav item links to /settings", async () => {
    await renderSidebar("/dashboard");
    const settings = screen.getByTestId("nav-settings");
    expect(settings.getAttribute("aria-disabled")).toBeNull();
    expect(settings.getAttribute("href")).toBe("/settings");
  });

  it("hides the Admin nav item for non-superusers", async () => {
    await renderSidebar("/dashboard");
    expect(screen.queryByText("Admin")).toBeNull();
  });

  it("shows the Admin nav item for superusers under More tools", async () => {
    await renderSidebar("/dashboard", { isSuperuser: true });
    const user = userEvent.setup();
    await user.click(screen.getByTestId("nav-more-tools-toggle"));
    const adminNav = screen.getByTestId("nav-admin");
    expect(adminNav.getAttribute("href")).toBe("/admin");
  });
});
