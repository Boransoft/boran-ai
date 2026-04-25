import type {
  LearningClusterItem,
  LearningGraphResponse,
  LearningReflectionItem,
  LearningSummary,
  LearningTopMemoryItem,
} from "../types/learning";

import { apiRequest } from "./api";

export function getLearningGraph(params: {
  token: string;
  userId: string;
}): Promise<LearningGraphResponse> {
  return apiRequest<LearningGraphResponse>(`/learning/graph/${params.userId}`, {
    token: params.token,
  });
}

export function getRelatedTerms(params: {
  token: string;
  userId: string;
  term: string;
}): Promise<LearningGraphResponse> {
  const query = encodeURIComponent(params.term);
  return apiRequest<LearningGraphResponse>(`/learning/graph/${params.userId}/related?term=${query}`, {
    token: params.token,
  });
}

export function getSemanticTerms(params: {
  token: string;
  userId: string;
  term: string;
}): Promise<LearningGraphResponse> {
  const query = encodeURIComponent(params.term);
  return apiRequest<LearningGraphResponse>(`/learning/graph/${params.userId}/semantic?term=${query}`, {
    token: params.token,
  });
}

export function getClusters(params: {
  token: string;
  userId: string;
}): Promise<LearningClusterItem[]> {
  return apiRequest<LearningClusterItem[]>(`/learning/clusters/${params.userId}`, {
    token: params.token,
  });
}

export function getTopMemory(params: {
  token: string;
  userId: string;
  query: string;
  limit?: number;
}): Promise<LearningTopMemoryItem[]> {
  const query = encodeURIComponent(params.query);
  const limit = params.limit ?? 8;
  return apiRequest<LearningTopMemoryItem[]>(
    `/learning/memory/top/${params.userId}?query=${query}&limit=${limit}`,
    { token: params.token },
  );
}

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
}): Promise<LearningReflectionItem[]> {
  const limit = params.limit ?? 20;
  return apiRequest<LearningReflectionItem[]>(`/learning/reflections/${params.userId}?limit=${limit}`, {
    token: params.token,
  });
}
