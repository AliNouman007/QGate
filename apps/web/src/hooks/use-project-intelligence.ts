import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api-client";

export interface ProjectEvidence {
  path: string;
  line: number;
  excerpt: string;
  kind: string;
}

export interface FrameworkFact {
  framework: "react" | "nextjs" | "typescript";
  feature: string;
  value: string | null;
  confidence: "high" | "medium" | "low";
  evidence: ProjectEvidence;
}

export interface RouteFact {
  route: string;
  router: string;
  kind: string;
  dynamic: boolean;
  evidence: ProjectEvidence;
}

export interface SymbolFact {
  name: string;
  kind: string;
  exported: boolean;
  evidence: ProjectEvidence;
}

export interface FileAnalysis {
  record: {
    path: string;
    role: string;
    language: string | null;
  };
  frameworks: FrameworkFact[];
  routes: RouteFact[];
  symbols: SymbolFact[];
}

export interface SemanticState {
  key: string;
  label: string;
  kind: string;
  explanation: string;
  confidence: "high" | "medium" | "low";
  evidence: ProjectEvidence[];
  needs_runtime_verification: boolean;
}

export interface ProjectKnowledge {
  metadata: {
    source_id: string;
    source_fingerprint: string;
    analyzed_at: string;
    reused_files: number;
    analyzed_files: number;
  };
  summary: {
    total_files: number;
    total_source_bytes: number;
    languages: Record<string, number>;
    frameworks: Record<string, number>;
    declared_frameworks: string[];
    roles: Record<string, number>;
    reused_modules: Record<string, number>;
    behavioral_categories: Record<string, number>;
    route_count: number;
    component_count: number;
    hook_count: number;
  };
  files: FileAnalysis[];
  semantic_states: SemanticState[];
  coverage_gaps: Array<{ path: string | null; reason: string; detail: string | null }>;
}

export function useLatestProjectIntelligence(): UseQueryResult<ProjectKnowledge | null> {
  return useQuery({
    queryKey: ["project-intelligence", "latest"] as const,
    queryFn: async () => {
      try {
        return (await api.get<ProjectKnowledge>("/project-intelligence/latest")).data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
  });
}
