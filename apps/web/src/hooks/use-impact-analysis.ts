import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api-client";

export interface ImpactEvidence {
  path: string;
  line: number;
  excerpt: string;
  kind: string;
}

export interface ImpactItem {
  key: string;
  target_type: string;
  target: string;
  level: "direct" | "indirect" | "possible" | "unknown";
  reason: string;
  confidence: "high" | "medium" | "low";
  evidence: ImpactEvidence[];
  dependency_path: Array<{ source: string; target: string; module: string }>;
  categories: string[];
  needs_runtime_verification: boolean;
  explanation: string | null;
  priority_hint: string | null;
}

export interface ImpactReport {
  metadata: {
    analyzed_at: string;
    project_source_id: string;
    project_fingerprint: string;
    change_source_id: string;
  };
  summary: {
    changed_files: number;
    changed_symbols: number;
    direct_impacts: number;
    indirect_impacts: number;
    possible_impacts: number;
    unknown_impacts: number;
    affected_routes: number;
    affected_states: number;
    runtime_verification_items: number;
  };
  change_set: {
    source_kind: string;
    source_id: string;
    base_ref: string | null;
    head_ref: string | null;
    title: string | null;
    files: Array<{
      path: string;
      old_path: string | null;
      status: string;
      additions: number;
      deletions: number;
      categories: string[];
    }>;
  };
  changed_symbols: Array<{
    file_path: string;
    symbol_name: string;
    symbol_kind: string;
    confidence: string;
  }>;
  direct_impacts: ImpactItem[];
  indirect_impacts: ImpactItem[];
  possible_impacts: ImpactItem[];
  unknown_impacts: ImpactItem[];
  affected_routes: ImpactItem[];
  affected_states: ImpactItem[];
  shared_groups: Array<{
    changed_target: string;
    reuse_count: number;
    affected_files: string[];
    affected_routes: string[];
  }>;
  coverage_gaps: Array<{
    path: string | null;
    reason: string;
    detail: string | null;
    needs_runtime_verification: boolean;
  }>;
}

export function useLatestImpactAnalysis(): UseQueryResult<ImpactReport | null> {
  return useQuery({
    queryKey: ["impact-analysis", "latest"] as const,
    queryFn: async () => {
      try {
        return (await api.get<ImpactReport>("/impact-analysis/latest")).data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
  });
}
