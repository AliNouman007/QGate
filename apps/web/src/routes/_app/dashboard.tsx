import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import {
  CheckCircle2,
  FolderKanban,
  Loader2,
  Play,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";

import { DashboardSkeleton } from "@/components/dashboard/skeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { StatusBadge, type StatusBadgeStatus } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { useRecentRuns } from "@/hooks/use-dashboard";
import { useLatestFinalGate } from "@/hooks/use-final-gate";
import { useProject } from "@/hooks/use-projects";
import { useActiveRun } from "@/hooks/use-runs";
import { useActiveProject } from "@/stores/use-active-project";

export const Route = createFileRoute("/_app/dashboard")({
  component: DashboardPage,
  staticData: { title: "Overview" },
});

type StepStageStatus = "Pending" | "Running" | "Completed" | "Failed" | "Skipped";

interface JourneyStepState {
  num: number;
  title: string;
  desc: string;
  status: StepStageStatus;
}

function mapRunStatus(status?: string | null): StatusBadgeStatus {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (s === "pass" || s === "passed") return "pass";
  if (s === "fail" || s === "failed" || s === "error") return "fail";
  if (s === "running" || s === "queued") return "running";
  return "neutral";
}

function deriveJourneySteps(activeRun: any): { steps: JourneyStepState[]; completedCount: number; activeStage: string | null } {
  if (!activeRun) {
    return {
      steps: [
        { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Pending" },
        { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Pending" },
        { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Pending" },
        { num: 4, title: "Execute Checks", desc: "Parallel Playwright execution", status: "Pending" },
        { num: 5, title: "Get Verdict", desc: "PASS / BLOCK decision", status: "Pending" },
      ],
      completedCount: 0,
      activeStage: null,
    };
  }

  const s = (activeRun.status ?? "QUEUED").toUpperCase();

  if (s === "QUEUED") {
    return {
      steps: [
        { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Running" },
        { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Pending" },
        { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Pending" },
        { num: 4, title: "Execute Checks", desc: "Parallel Playwright execution", status: "Pending" },
        { num: 5, title: "Get Verdict", desc: "PASS / BLOCK decision", status: "Pending" },
      ],
      completedCount: 0,
      activeStage: "Analyzing Project",
    };
  }

  if (s === "RUNNING") {
    const total = activeRun.total_steps ?? activeRun.totalSteps ?? 0;
    const passed = activeRun.passed_steps ?? activeRun.passedSteps ?? 0;
    const failed = activeRun.failed_steps ?? activeRun.failedSteps ?? 0;
    const countStr = total > 0 ? ` (${passed + failed}/${total})` : "";

    return {
      steps: [
        { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Completed" },
        { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Completed" },
        { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Completed" },
        { num: 4, title: "Execute Checks", desc: `Executing checks${countStr}`, status: "Running" },
        { num: 5, title: "Get Verdict", desc: "PASS / BLOCK decision", status: "Pending" },
      ],
      completedCount: 3,
      activeStage: "Executing Browser Checks",
    };
  }

  if (s === "PASS" || s === "PASSED") {
    return {
      steps: [
        { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Completed" },
        { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Completed" },
        { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Completed" },
        { num: 4, title: "Execute Checks", desc: "Parallel Playwright execution", status: "Completed" },
        { num: 5, title: "Get Verdict", desc: "Gate verdict issued", status: "Completed" },
      ],
      completedCount: 5,
      activeStage: null,
    };
  }

  if (s === "FAIL" || s === "FAILED" || s === "ERROR") {
    return {
      steps: [
        { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Completed" },
        { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Completed" },
        { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Completed" },
        { num: 4, title: "Execute Checks", desc: "Execution failed", status: "Failed" },
        { num: 5, title: "Get Verdict", desc: "Gate verdict blocked", status: "Skipped" },
      ],
      completedCount: 3,
      activeStage: null,
    };
  }

  return {
    steps: [
      { num: 1, title: "Analyze Project", desc: "Static code index & route graph", status: "Pending" },
      { num: 2, title: "Assess Impact", desc: "Git diff risk scoring", status: "Pending" },
      { num: 3, title: "Build Test Plan", desc: "Scenario & assertion synthesis", status: "Pending" },
      { num: 4, title: "Execute Checks", desc: "Parallel Playwright execution", status: "Pending" },
      { num: 5, title: "Get Verdict", desc: "PASS / BLOCK decision", status: "Pending" },
    ],
    completedCount: 0,
    activeStage: null,
  };
}

function WelcomeHeader({ onStartQaCheck }: { onStartQaCheck: () => void }): React.ReactElement {
  const projectId = useActiveProject((s) => s.projectId);
  const { data: project } = useProject(projectId);
  const { data: activeRun } = useActiveRun();

  const isActive = activeRun?.status === "QUEUED" || activeRun?.status === "RUNNING";
  const activeLabel = activeRun?.status === "QUEUED" ? "QA Check Queued" : "QA Check Running";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-bg-elev-1 p-5" data-testid="dashboard-header">
      <div>
        <div className="flex items-center gap-2 text-[11.5px] font-medium text-fg-4">
          <FolderKanban className="h-4 w-4 text-accent" aria-hidden="true" />
          <span>Active Project: <strong className="font-mono text-fg-1">{project?.name ?? "D:\\QGate\\qgate-test-shop"}</strong></span>
        </div>
        <h1 className="mt-2 text-[22px] font-bold tracking-tight text-fg-1">
          QGate Command Center
        </h1>
        <p className="mt-1 max-w-[640px] text-[13px] text-fg-3">
          QGate validates software changes against baseline behavior with empirical evidence before deployment.
        </p>
      </div>
      <div>
        <Button
          size="lg"
          disabled={isActive}
          onClick={onStartQaCheck}
          className="h-10 gap-2 bg-accent text-[13.5px] font-semibold text-accent-fg hover:bg-accent/90 shadow-sm disabled:opacity-75"
          data-testid="start-qa-check-button"
        >
          {isActive ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          )}
          <span>{isActive ? activeLabel : "Start QA Check"}</span>
        </Button>
      </div>
    </header>
  );
}

function ActiveRunProgressCard({ run, journey }: { run: any; journey: any }): React.ReactElement {
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    const rawTime = run.created_at || run.createdAt;
    const startTime = rawTime ? new Date(rawTime).getTime() : Date.now();
    const timer = setInterval(() => {
      setElapsedSec(Math.max(0, Math.floor((Date.now() - startTime) / 1000)));
    }, 1000);
    return () => clearInterval(timer);
  }, [run.created_at, run.createdAt]);

  const mins = Math.floor(elapsedSec / 60);
  const secs = elapsedSec % 60;
  const elapsedStr = `${mins}m ${secs.toString().padStart(2, "0")}s`;

  const percent = Math.round((journey.completedCount / 5) * 100);
  const isQueuedStalled = run.status === "QUEUED" && elapsedSec > 30;
  const pubId = (run as any)?.public_id || (run as any)?.publicId || run.id;

  return (
    <section className="rounded-lg border border-accent/40 bg-bg-elev-1 p-5 shadow-sm" data-testid="active-run-progress-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2.5">
          <Loader2 className="h-5 w-5 animate-spin text-accent" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[15px] font-bold text-fg-1">QA Check in Progress</h2>
              <span className="font-mono text-[12px] font-semibold text-accent">{pubId}</span>
            </div>
            <p className="text-[12px] text-fg-3">{run.name ?? "Automated Validation Run"}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[12px]">
          <span className="font-mono text-fg-3">Elapsed: <strong className="text-fg-1">{elapsedStr}</strong></span>
          <StatusBadge status="running" label={run.status === "QUEUED" ? "QUEUED" : "RUNNING"} />
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-[12.5px]">
          <span className="font-medium text-fg-2">Stage: <strong className="text-fg-1">{journey.activeStage ?? "Processing"}</strong></span>
          <span className="font-mono text-[12px] text-fg-3">{journey.completedCount} of 5 steps complete ({percent}%)</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-bg-elev-2">
          <div
            className="h-full bg-accent transition-all duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {isQueuedStalled ? (
        <div className="mt-3 rounded-md border border-amber/30 bg-amber/10 p-2.5 text-[12px] text-amber flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Waiting for local QA worker supervisor to process queued run...</span>
        </div>
      ) : null}
    </section>
  );
}

function QaPipelineProcessCard({ steps }: { steps: JourneyStepState[] }): React.ReactElement {
  return (
    <section className="rounded-lg border border-border bg-bg-elev-1 p-5" data-testid="dashboard-qa-pipeline-card">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[15px] font-semibold text-fg-1">5-Step QGate QA Journey</h2>
          <p className="text-[12px] text-fg-4">Automated code change validation workflow from commit to verdict</p>
        </div>
        <ShieldCheck className="h-5 w-5 text-accent opacity-80" aria-hidden="true" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {steps.map((step) => {
          let badgeClass = "text-fg-4 bg-bg-elev-3";
          let icon = null;

          if (step.status === "Completed") {
            badgeClass = "text-green bg-green/10 border-green/30";
            icon = <CheckCircle2 className="h-3.5 w-3.5 text-green shrink-0" aria-hidden="true" />;
          } else if (step.status === "Running") {
            badgeClass = "text-accent bg-accent/10 border-accent/30";
            icon = <Loader2 className="h-3.5 w-3.5 animate-spin text-accent shrink-0" aria-hidden="true" />;
          } else if (step.status === "Failed") {
            badgeClass = "text-red bg-red/10 border-red/30";
            icon = <XCircle className="h-3.5 w-3.5 text-red shrink-0" aria-hidden="true" />;
          }

          return (
            <div key={step.num} className="flex flex-col justify-between rounded-md border border-border-subtle bg-bg-elev-2 p-3">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-fg-4">
                    Step {step.num}
                  </span>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badgeClass}`}>
                    {icon}
                    <span>{step.status}</span>
                  </span>
                </div>
                <div className="mt-2 text-[13px] font-semibold text-fg-1">{step.title}</div>
                <div className="mt-1 text-[11px] leading-snug text-fg-4">{step.desc}</div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function LatestResultCard(): React.ReactElement {
  const { data: page } = useRecentRuns(1);
  const { data: latestFinalGate } = useLatestFinalGate();
  const runs = page?.items ?? [];
  const latestRun = runs.length > 0 ? runs[0] : null;

  const isActive = latestRun?.status === "QUEUED" || latestRun?.status === "RUNNING";
  const pubId = (latestRun as any)?.public_id || (latestRun as any)?.publicId || latestRun?.id;

  return (
    <section className="flex flex-col rounded-lg border border-border bg-bg-elev-1 p-5" data-testid="dashboard-latest-result">
      <h2 className="text-[15px] font-semibold text-fg-1">
        {isActive ? "Current QA Check" : "Latest QA Verdict"}
      </h2>
      {latestRun ? (
        <div className="mt-4 flex flex-1 flex-col justify-between rounded-md border border-border-subtle bg-bg-elev-2 p-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-mono text-[12px] font-bold text-fg-1">RUN #{pubId}</div>
              <div className="mt-0.5 text-[12px] text-fg-3">{latestRun.name ?? "Automated Validation Run"}</div>
            </div>
            <StatusBadge status={mapRunStatus(latestRun.status)} label={latestRun.status} />
          </div>

          {latestFinalGate && !isActive ? (
            <div className="mt-3 rounded-md border border-border-subtle bg-bg-elev-1 p-3 text-[12px]">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-fg-1">Final Gate Verdict:</span>
                <span className={`font-mono font-bold ${latestFinalGate.verdict === "PASS" ? "text-green" : "text-red"}`}>
                  {latestFinalGate.verdict}
                </span>
              </div>
              <p className="mt-1 text-[11.5px] text-fg-3">{latestFinalGate.headline}</p>
            </div>
          ) : null}

          <div className="mt-4 flex items-center justify-between border-t border-border-subtle pt-3 text-[11px] text-fg-4">
            <span>
              {latestRun.completed_at
                ? formatDistanceToNow(new Date(latestRun.completed_at), { addSuffix: true })
                : isActive
                ? "In progress..."
                : "Completed"}
            </span>
            <span className="font-mono text-fg-2">{latestRun.status}</span>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex flex-1 flex-col items-center justify-center rounded-md border border-dashed border-border-subtle bg-bg-elev-2/50 p-6 text-center">
          <ShieldAlert className="h-8 w-8 text-fg-4 opacity-50" aria-hidden="true" />
          <div className="mt-2 text-[13px] font-medium text-fg-2">No QA check has run yet</div>
          <p className="mt-1 max-w-[280px] text-[11.5px] text-fg-4">
            Click "Start QA Check" above to trigger automated validation for your current project branch.
          </p>
        </div>
      )}
    </section>
  );
}

function RecentChecksCard(): React.ReactElement {
  const navigate = useNavigate();
  const { data: page } = useRecentRuns(5);
  const runs = page?.items ?? [];

  return (
    <section className="flex flex-col rounded-lg border border-border bg-bg-elev-1 p-5" data-testid="dashboard-recent-runs">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-fg-1">Recent QA Checks</h2>
        <span className="text-[11px] text-fg-4 font-mono">{runs.length} checks</span>
      </div>

      {runs.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {runs.map((run) => {
            const pubId = (run as any)?.public_id || (run as any)?.publicId || run.id;
            const isRunActive = run.status === "QUEUED" || run.status === "RUNNING";

            return (
              <li
                key={run.id}
                onClick={() => {
                  void navigate({ to: "/runs" });
                }}
                className="flex cursor-pointer items-center justify-between rounded-md border border-border-subtle bg-bg-elev-2 p-3 text-[12px] transition-colors hover:bg-bg-elev-3"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <StatusBadge status={mapRunStatus(run.status)} label={run.status} />
                  <div className="truncate">
                    <span className="font-mono font-bold text-fg-1">{pubId}</span>
                    <span className="ml-2 text-fg-3">{run.name ?? "QA Check"}</span>
                  </div>
                </div>
                <span className="shrink-0 font-mono text-[11px] text-fg-4">
                  {run.completed_at
                    ? formatDistanceToNow(new Date(run.completed_at), { addSuffix: true })
                    : isRunActive
                    ? "In progress..."
                    : "Created"}
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="mt-4 flex flex-1 flex-col items-center justify-center rounded-md border border-dashed border-border-subtle bg-bg-elev-2/50 p-6 text-center">
          <Play className="h-8 w-8 text-fg-4 opacity-50" aria-hidden="true" />
          <div className="mt-2 text-[13px] font-medium text-fg-2">No recent QA checks</div>
          <p className="mt-1 text-[11.5px] text-fg-4">
            Trigger a QA Check to evaluate changes and populate recent verdicts.
          </p>
        </div>
      )}
    </section>
  );
}

function DashboardBody(): React.ReactElement {
  const { data: activeRun } = useActiveRun();
  const journey = deriveJourneySteps(activeRun);
  const isRunActive = activeRun?.status === "QUEUED" || activeRun?.status === "RUNNING";

  const handleTriggerQaCheck = () => {
    if (!isRunActive) {
      window.dispatchEvent(new CustomEvent("open-start-qa-check"));
    }
  };

  return (
    <main className="flex flex-col gap-5 p-6" data-testid="dashboard-screen">
      <WelcomeHeader onStartQaCheck={handleTriggerQaCheck} />

      {isRunActive && activeRun ? (
        <ActiveRunProgressCard run={activeRun} journey={journey} />
      ) : null}

      <QaPipelineProcessCard steps={journey.steps} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <LatestResultCard />
        <RecentChecksCard />
      </div>
    </main>
  );
}

function DashboardError({ reset }: { reset: () => void }): React.ReactElement {
  return (
    <div className="rounded-lg border border-red/30 bg-red/5 p-6 text-center text-fg-1">
      <h3 className="text-[15px] font-semibold text-red">Couldn't load dashboard</h3>
      <p className="mt-1 text-[12px] text-fg-4">The backend may be unavailable. Retry or check API status.</p>

      <Button onClick={reset} size="sm" variant="outline" className="mt-3">
        Retry
      </Button>
    </div>
  );
}

function DashboardPage(): React.ReactElement {
  return (
    <ErrorBoundary fallback={({ reset }) => <DashboardError reset={reset} />}>
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardBody />
      </Suspense>
    </ErrorBoundary>
  );
}
