import type { components } from "@/lib/api-types";
import { cn } from "@/lib/utils";

type TestingApproach = components["schemas"]["TestingApproach"];

const LABELS: Record<TestingApproach, string> = {
  BLACK_BOX: "Black-box",
  GRAY_BOX: "Gray-box",
  WHITE_BOX: "White-box",
};

export function TestingApproachBadge({
  approach,
  className,
}: {
  approach: TestingApproach;
  className?: string;
}): React.ReactElement {
  return (
    <span
      data-testid="testing-approach-badge"
      className={cn(
        "rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide",
        approach === "BLACK_BOX" && "border-border bg-bg-elev-2 text-fg-3",
        approach === "GRAY_BOX" && "border-amber/30 bg-amber/10 text-amber",
        approach === "WHITE_BOX" && "border-violet/30 bg-violet/10 text-violet",
        className,
      )}
    >
      {LABELS[approach]}
    </span>
  );
}
