export type AnalysisStatus =
  | "preparing" | "running" | "clarifying" | "partial" | "done"
  | "failed" | "cancelled" | "insufficient";

export type PhaseStatus = "waiting" | "running" | "done";

export interface AnalysisPhase {
  id: string;
  label: string;
  status: PhaseStatus;
}

export interface FindingBlock {
  type: "text" | "chart-trend" | "chart-contrib" | "chart-breakdown" | "table";
  id: string;
  title?: string;
  content?: string;
  data?: unknown[];
  columns?: string[];
  rows?: string[][];
  source?: string;
  sourceDetail?: string;
}

export interface FollowUpEntry {
  question: string;
  findings: FindingBlock[];
  timestamp: string;
}

export interface Analysis {
  id: string;
  question: string;
  status: AnalysisStatus;
  createdAt: string;
  updatedAt: string;
  phases: AnalysisPhase[];
  currentPhaseIndex: number;
  findings: FindingBlock[];
  insights: string[];
  followUps: FollowUpEntry[];
  failureReason?: string;
  clarificationQuestion?: string;
  reportGenerated?: boolean;
  summary?: string;
}
