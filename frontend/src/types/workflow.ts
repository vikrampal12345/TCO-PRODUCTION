export type WorkflowState =
  | 'idle'
  | 'understanding'
  | 'needs_input'
  | 'running'
  | 'review_required'
  | 'approved'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type SpecializedAgent =
  | 'TCO Master Agent'
  | 'Assessment Agent'
  | 'Evaluation Agent'
  | 'Answer Sheet Checking Agent'
  | 'Attendance Agent'
  | 'Analytics Agent'
  | 'Presentation Agent'
  | 'Content Preparation Agent';

export type WorkflowType =
  | 'answer_sheet_checking'
  | 'question_paper_generation'
  | 'assessment'
  | 'attendance'
  | 'marksheet'
  | 'ppt_generation'
  | 'analytics'
  | 'student_insights';

export interface WorkflowStep {
  id: string;
  agent: SpecializedAgent;
  label: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: string;
}

export interface ClarificationOption {
  id: string;
  label: string;
  description?: string;
  icon?: string;
}

export interface ClarificationRequest {
  id: string;
  prompt: string;
  contextHint?: string;
  options: ClarificationOption[];
  allowCustomInput?: boolean;
}

export interface ApprovalRequest {
  id: string;
  title: string;
  summary: string;
  metrics?: { label: string; value: string }[];
  reviewType: WorkflowType;
  requiresReview?: boolean;
}

export interface WorkflowProgress {
  workflowId: string;
  type: WorkflowType;
  state: WorkflowState;
  activeAgent: SpecializedAgent;
  steps: WorkflowStep[];
  clarification?: ClarificationRequest;
  approval?: ApprovalRequest;
  resultSummary?: string;
}
