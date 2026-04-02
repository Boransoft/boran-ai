import { apiRequest } from "./api";

export type LearningSummary = {
  user_id: string;
  summary: string;
  generated_at: string;
  user_preferences: string;
  stable_rules: string;
  project_focus: string;
  recurring_topics: string;
  concept_clusters: string;
};

export type ReflectionItem = {
  id: string;
  user_id: string;
  kind: string;
  text: string;
  source: string;
  created_at: string;
  metadata: Record<string, string>;
};

export function getLearningSummary(params: {
  token: string;
  userId: string;
}): Promise<LearningSummary> {
  return apiRequest<LearningSummary>(`/learning/summary/${params.userId}`, {
    token: params.token,
  });
}

export function getReflections(params: {
  token: string;
  userId: string;
  limit?: number;
}): Promise<ReflectionItem[]> {
  return apiRequest<ReflectionItem[]>(`/learning/reflections/${params.userId}?limit=${params.limit || 20}`, {
    token: params.token,
  });
}
