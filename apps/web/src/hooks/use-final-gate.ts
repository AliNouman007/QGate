import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api-client";

export interface GateFinding {
  key: string;
  kind: string;
  title: string;
  reason: string;
  verdict_effect: string;
  priority: string | null;
  scenario_key: string | null;
  routes: string[];
  states: string[];
  verified: boolean;
  product_facing: boolean;
  failure_category: string | null;
  source_memory_keys: string[];
  source_rule_keys: string[];
}

export interface CoverageItem {
  scenario_key: string;
  title: string;
  priority: string;
  required: boolean;
  required_reason: string | null;
  readiness: string;
  execution_status: string | null;
  verified: boolean;
  failure_category: string | null;
  coverage_outcome: string;
  routes: string[];
  states: string[];
  historical_memory_keys: string[];
  historical_rule_keys: string[];
}

export interface HistoricalRisk {
  memory_key: string;
  rule_key: string | null;
  score: number;
  reasons: string[];
  strong_match: boolean;
  objective: string | null;
  expected_invariant: string | null;
  routes: string[];
  states: string[];
  related_scenario_keys: string[];
  covered: boolean;
}

export interface GateReport {
  metadata: {
    report_key: string;
    generated_at: string;
    project_source_id: string;
    project_fingerprint: string;
    change_source_id: string;
    scenario_plan_key: string;
    execution_run_id: string;
  };
  verdict: "PASS" | "BLOCK" | "MANUAL_REVIEW_REQUIRED";
  confidence: "high" | "medium" | "low";
  headline: string;
  blocking_findings: GateFinding[];
  manual_review_findings: GateFinding[];
  informational_findings: GateFinding[];
  coverage_summary: {
    required_total: number;
    required_verified_pass: number;
    required_verified_fail: number;
    required_unverified: number;
    required_manual: number;
    required_blocked: number;
    optional_total: number;
    optional_verified: number;
    historical_required_total: number;
    historical_required_verified: number;
    truncated: boolean;
    has_coverage_gaps: boolean;
  };
  coverage_items: CoverageItem[];
  historical_risks: HistoricalRisk[];
  input_integrity_findings: Array<{ kind: string; reason: string; verdict_effect: string }>;
  decision_trace: Array<{
    rule_id: string;
    reason: string;
    scenario_key: string | null;
    finding_key: string | null;
  }>;
  ai_explanation: {
    summary: string;
    grouped_reasons: string[];
    manual_review_checklist: string[];
  } | null;
}

export function useLatestFinalGate(): UseQueryResult<GateReport | null> {
  return useQuery({
    queryKey: ["final-gate", "latest"] as const,
    queryFn: async () => {
      try {
        return (await api.get<GateReport>("/final-gate/latest")).data;
      } catch (error: any) {
        if (error?.status === 404 || (error instanceof ApiError && error.status === 404)) return null;
        throw error;
      }
    },
    retry: false,
  });
}
