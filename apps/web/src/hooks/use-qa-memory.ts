import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { api } from "@/lib/api-client";

export interface EvidenceRef {
  path: string;
  line: number;
  excerpt: string;
  kind: string;
}

export interface MemoryCandidate {
  key: string;
  project_source_id: string;
  project_fingerprint: string | null;
  title: string;
  invariant: string;
  kind: string;
  severity: string;
  routes: string[];
  components: string[];
  symbols: string[];
  targets: string[];
  states: string[];
  source_scenario_key: string | null;
  source_execution_run_id: string | null;
  source_defect_id: string | null;
  evidence: EvidenceRef[];
  confidence: string;
  status: "pending" | "confirmed" | "rejected";
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_note: string | null;
  confirmed_memory_key: string | null;
  occurrences: Array<{
    execution_run_id: string | null;
    scenario_key: string | null;
    defect_id: string | null;
  }>;
}

export interface ConfirmedMemory {
  key: string;
  project_source_id: string;
  title: string;
  invariant: string;
  severity: string;
  routes: string[];
  components: string[];
  symbols: string[];
  targets: string[];
  states: string[];
  originating_candidate_keys: string[];
  evidence: EvidenceRef[];
  confidence: string;
  status: "active" | "superseded" | "inactive";
  confirmed_at: string;
  confirmed_by: string;
  superseded_by: string | null;
}

export interface CandidateReviewResult {
  candidate: MemoryCandidate;
  memory: ConfirmedMemory | null;
}

export function useQAMemoryCandidates(): UseQueryResult<MemoryCandidate[]> {
  return useQuery({
    queryKey: ["qa-memory", "candidates"] as const,
    queryFn: async () => (await api.get<MemoryCandidate[]>("/qa-memory/candidates")).data,
    retry: false,
  });
}

export function useQAMemories(): UseQueryResult<ConfirmedMemory[]> {
  return useQuery({
    queryKey: ["qa-memory", "memories"] as const,
    queryFn: async () => (await api.get<ConfirmedMemory[]>("/qa-memory/memories")).data,
    retry: false,
  });
}

export function useConfirmMemoryCandidate(): UseMutationResult<
  CandidateReviewResult,
  Error,
  { key: string; note?: string }
> {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, note }) =>
      (await api.post<CandidateReviewResult>(`/qa-memory/candidates/${key}/confirm`, { note })).data,
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ["qa-memory", "candidates"] }),
        client.invalidateQueries({ queryKey: ["qa-memory", "memories"] }),
      ]);
    },
  });
}

export function useRejectMemoryCandidate(): UseMutationResult<
  CandidateReviewResult,
  Error,
  { key: string; note?: string }
> {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, note }) =>
      (await api.post<CandidateReviewResult>(`/qa-memory/candidates/${key}/reject`, { note })).data,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["qa-memory", "candidates"] });
    },
  });
}

export function useDeactivateMemory(): UseMutationResult<
  ConfirmedMemory,
  Error,
  { key: string; note?: string }
> {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, note }) =>
      (await api.post<ConfirmedMemory>(`/qa-memory/memories/${key}/deactivate`, { note })).data,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["qa-memory", "memories"] });
    },
  });
}
