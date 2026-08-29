import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api-client";

export interface ExecutionArtifact {
  kind: string;
  path: string;
  sha256: string | null;
}

export interface StepExecution {
  index: number;
  operation: string;
  source_action: string;
  source_expected: string;
  status: string;
  failure_category: string | null;
  actual: string | null;
  expected: string | null;
  duration_ms: number | null;
  detail: string | null;
  evidence: {
    requested_route: string | null;
    final_url: string | null;
    title: string | null;
    console: Array<{ level: string; message: string; source: string | null }>;
    network: Array<{
      method: string;
      url: string;
      resource_type: string | null;
      status: number | null;
      failure: string | null;
    }>;
    artifacts: ExecutionArtifact[];
  };
}

export interface ScenarioExecution {
  scenario_key: string;
  title: string;
  kind: string;
  priority: string;
  status: string;
  failure_category: string | null;
  verified: boolean;
  target_route: string | null;
  duration_ms: number | null;
  steps: StepExecution[];
  artifacts: ExecutionArtifact[];
  attempts: Array<{
    attempt: number;
    status: string;
    failure_category: string | null;
    reason: string | null;
  }>;
  detail: string | null;
}

export interface ExecutionReport {
  metadata: {
    run_id: string;
    scenario_plan_key: string;
    project_source_id: string;
    project_fingerprint: string;
    impact_change_source_id: string;
    config_fingerprint: string;
    started_at: string;
    completed_at: string | null;
  };
  summary: {
    selected: number;
    executed: number;
    passed: number;
    failed: number;
    execution_error: number;
    unverified: number;
    skipped_manual: number;
    blocked: number;
  };
  scenarios: ScenarioExecution[];
  coverage_gaps: Array<{
    scenario_key: string | null;
    reason: string;
    detail: string | null;
  }>;
  run_artifacts: ExecutionArtifact[];
}

export function useLatestBrowserExecution(): UseQueryResult<ExecutionReport | null> {
  return useQuery({
    queryKey: ["browser-execution", "latest"] as const,
    queryFn: async () => {
      try {
        return (await api.get<ExecutionReport>("/browser-execution/latest")).data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
  });
}
