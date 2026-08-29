import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api-client";

export interface ScenarioEvidence {
  path: string;
  line: number;
  excerpt: string;
  kind: string;
}

export interface ScenarioPlanItem {
  key: string;
  title: string;
  kind: string;
  priority: "P0" | "P1" | "P2" | "P3";
  confidence: "high" | "medium" | "low";
  routes: string[];
  targets: string[];
  states: string[];
  preconditions: string[];
  steps: Array<{
    action: string;
    expected: string;
    target_kind: string;
    route: string | null;
    data_hint: string | null;
  }>;
  reason: string;
  source_impact_keys: string[];
  evidence: ScenarioEvidence[];
  readiness: "ready" | "runtime_discovery_required" | "manual_only" | "blocked_by_gap";
  needs_runtime_discovery: boolean;
  manual_reason: string | null;
  cross_state_group: string | null;
  explanation: string | null;
  priority_hint: string | null;
}

export interface ScenarioPlan {
  metadata: {
    generated_at: string;
    project_source_id: string;
    project_fingerprint: string;
    impact_change_source_id: string;
  };
  summary: {
    total: number;
    ready: number;
    runtime_discovery: number;
    manual_only: number;
    blocked: number;
    p0: number;
    p1: number;
    p2: number;
    p3: number;
  };
  scenarios: ScenarioPlanItem[];
  cross_state_groups: Array<{
    key: string;
    route: string | null;
    state_labels: string[];
    scenario_keys: string[];
    comparison_goal: string;
  }>;
  coverage_gaps: Array<{
    reason: string;
    detail: string | null;
    source_impact_key: string | null;
  }>;
}

export function useLatestScenarioPlan(): UseQueryResult<ScenarioPlan | null> {
  return useQuery({
    queryKey: ["scenario-intelligence", "latest"] as const,
    queryFn: async () => {
      try {
        return (await api.get<ScenarioPlan>("/scenario-intelligence/latest")).data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
  });
}
