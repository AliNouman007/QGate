import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { SelectorRepairDialog } from "@/components/cases/SelectorRepairDialog";
import { server } from "@/mocks/server";

describe("SelectorRepairDialog", () => {
  it("reviews and applies a selector-only proposal", async () => {
    const onApplied = vi.fn();
    server.use(
      http.post("*/api/v1/test-cases/TC-1/self-heal/propose", () =>
        HttpResponse.json({
          step_id: "step-1",
          failure_kind: "selector_changed",
          old_selector: "#submit",
          new_selector: "[data-testid=save]",
          updated_code: "{}",
          rationale: "A stable test id exists.",
          confidence: 0.92,
          code_sha256: "a".repeat(64),
        }),
      ),
      http.post("*/api/v1/test-cases/TC-1/self-heal/apply", () =>
        HttpResponse.json({
          step_id: "step-1",
          code: '{"tool":"browser_click","arguments":{"selector":"[data-testid=save]"}}',
          old_selector: "#submit",
          new_selector: "[data-testid=save]",
          applied: true,
        }),
      ),
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <SelectorRepairDialog
          open
          onOpenChange={() => undefined}
          caseId="TC-1"
          stepId="step-1"
          onApplied={onApplied}
        />
      </QueryClientProvider>,
    );

    await userEvent.type(
      screen.getByLabelText("Failure evidence"),
      "Timeout waiting for locator('#submit')",
    );
    await userEvent.click(screen.getByRole("button", { name: "Propose repair" }));
    expect(await screen.findByText("[data-testid=save]")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apply repair" }));
    await waitFor(() => {
      expect(onApplied).toHaveBeenCalledWith(
        '{"tool":"browser_click","arguments":{"selector":"[data-testid=save]"}}',
      );
    });
  });
});
