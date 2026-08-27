import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StepTable } from "@/components/runs/StepTable";
import type { components } from "@/lib/api-types";

type RunStepPublic = components["schemas"]["RunStepPublic"];

function step(overrides: Partial<RunStepPublic> = {}): RunStepPublic {
  return {
    id: "rs_01",
    run_id: "run_1",
    case_id: "tc_1",
    case_public_id: "TC-1004",
    step_order: 0,
    outcome: "PASS",
    ...overrides,
  } as RunStepPublic;
}

describe("<StepTable>", () => {
  it("shows what a step's tool returned", () => {
    // A diagnostic step — an event recording, a tree dump — carries its whole
    // answer in stdout, so a table that only renders errors makes a passing
    // step look like it did nothing.
    render(<StepTable steps={[step({ stdout: '{"events": [{"result": "Ignored"}]}' })]} />);

    expect(screen.getByTestId("step-output")).toBeInTheDocument();
    expect(screen.getByText(/"result": "Ignored"/)).toBeInTheDocument();
  });

  it("renders no output block when the step returned nothing", () => {
    render(<StepTable steps={[step()]} />);
    expect(screen.queryByTestId("step-output")).not.toBeInTheDocument();
  });
});
