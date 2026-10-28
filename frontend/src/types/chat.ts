
import {
  WorkflowProgress,
  ClarificationRequest,
  ApprovalRequest,
  WorkflowType,
} from './workflow';

export type SenderRole = 'teacher' | 'tco';

export type ConversationStatus =
  | 'Completed'
  | 'In Review'
  | 'Needs Input'
  | 'Running'
  | 'Draft'
  | 'Archived';

export type ConversationTimeGroup =
  | 'Today'
  | 'Yesterday'
  | 'Previous 7 Days'
  | 'Older';

export interface ChatAttachment {
  id: string;
  name: string;
  size: string;
  type: string;
}

export interface SourceCandidate {
  title: string;
  url: string;
  snippet?: string;
  source_type?: string;
  domain?: string;
  approved?: boolean;
}

export interface ChatMessage {
  id: string;
  sender: SenderRole;
  timestamp: string;
  content: string;
  workflowProgress?: WorkflowProgress;
  clarification?: ClarificationRequest;
  approval?: ApprovalRequest;
  attachments?: ChatAttachment[];
  reviewType?: WorkflowType;
  reviewDataId?: string;
  sourceCandidates?: SourceCandidate[];
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  status: ConversationStatus;
  group: ConversationTimeGroup;
  lastUpdated: string;
  preview: string;
  messages: ChatMessage[];
  activeWorkflowType?: WorkflowType;
}

export interface QuickActionItem {
  id: string;
  title: string;
  description: string;
  iconName: string;
  prompt: string;
  workflowType: WorkflowType;
}
