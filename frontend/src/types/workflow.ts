export type WorkflowState =
  | 'idle'
  | 'understanding'
  | 'needs_input'
  | 'waiting_for_source_selection'
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

export interface AssessmentLifecycleData {
  workflow_id: string;
  status?: string;
  form_id?: string;
  responder_url?: string;
  edit_url?: string;
  assessment_id?: number | string;
  title?: string;
  topic?: string;
  question_count?: number;
  marks?: number;
  form_is_published?: boolean;
  form_accepting_responses?: boolean;
  student_email_skipped?: number;
  student_email_attempted?: number;
  eligible_student_count?: number;
  valid_email_count?: number;
  invalid_email_count?: number;
  already_invited_count?: number;
  recipient_preview?: unknown[];
  evaluation_summary?: {
    total_responses?: number;
    evaluated?: number;
    pending?: number;
    failed?: number;
  };
  approval_status?: string;
  student_email_total?: number;
  student_email_sent?: number;
  student_email_failed?: number;
  evaluation_status?: string;
  evaluation_results?: unknown[];
  result_email_status?: string;
  result_email_summary?: {
    status?: string;
    total?: number;
    sent?: number;
    failed?: number;
    skipped?: number;
    results?: unknown[];
  };
  error_message?: string;
  [key: string]: unknown;
}
