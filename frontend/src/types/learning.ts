export type LearningGraphNode = {
  term: string;
  count: number;
};

export type LearningGraphEdge = {
  source: string;
  relation: string;
  target: string;
  weight: number;
  frequency?: number;
};

export type LearningGraphResponse = {
  user_id: string;
  nodes: LearningGraphNode[];
  edges: LearningGraphEdge[];
};

export type LearningClusterItem = {
  id: string;
  label: string;
  terms: string[];
  score?: number;
};

export type LearningTopMemoryItem = {
  id: string;
  kind: string;
  text: string;
  score: number;
  source?: string;
  created_at?: string;
};

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

export type LearningReflectionItem = {
  id: string;
  user_id: string;
  kind: string;
  text: string;
  source: string;
  created_at: string;
  metadata: Record<string, string>;
};
