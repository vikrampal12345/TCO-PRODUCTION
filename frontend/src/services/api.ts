
import type { Conversation, ChatMessage, SourceCandidate } from '../types/chat';
import type {
  AssessmentLifecycleData,
  WorkflowProgress,
  WorkflowType,
} from '../types/workflow';
import { mockApi } from './mockApi';
import { fastApiService } from './fastApiService';

export type WorkspaceSourceMode =
  | 'general_knowledge'
  | 'teacher_file'
  | 'classroom'
  | 'web_search';

export type WorkspaceAgentMode =
  | 'assessment'
  | 'analytics'
  | 'copy_checking';

export interface MessageAttachmentInput {
  name: string;
  size: string;
  type: string;
  /** Original file bytes; absent for previously stored attachments/demo data. */
  file?: File;
}

export interface ClassroomCourse {
  id: string;
  name: string;
  section?: string;
  descriptionHeading?: string;
  courseState?: string;
}

export interface ITCOApiService {
  getConversations(): Promise<Conversation[]>;
  getConversation(id: string): Promise<Conversation | null>;
  createConversation(
    initialTitle?: string,
    initialMessage?: string,
  ): Promise<Conversation>;

  sendMessage(
    conversationId: string,
    content: string,
    attachments?: MessageAttachmentInput[],
    sourceMode?: WorkspaceSourceMode,
    agentMode?: WorkspaceAgentMode,
  ): Promise<{ userMessage: ChatMessage; tcoMessage: ChatMessage }>;

  respondToClarification(
    conversationId: string,
    optionId: string,
    customValue?: string,
  ): Promise<{ userMessage: ChatMessage; tcoMessage: ChatMessage }>;

  approveWorkflow(
    workflowId: string,
    conversationId: string,
    reviewType: WorkflowType,
    notes?: string,
  ): Promise<{
    status: string;
    updatedWorkflow: WorkflowProgress;
    lifecycle?: AssessmentLifecycleData;
  }>;

  rejectWorkflow(
    workflowId: string,
    conversationId: string,
    reason?: string,
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }>;

  requestRevision(
    workflowId: string,
    conversationId: string,
    instructions: string,
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }>;

  getAssessmentLifecycle(workflowId: string): Promise<AssessmentLifecycleData | null>;

  sendAssessmentToStudents(
    workflowId: string,
    target: { school_id: string; class_level: string; section: string },
  ): Promise<AssessmentLifecycleData>;
  previewAssessmentRecipients(
    workflowId: string,
  ): Promise<AssessmentLifecycleData>;
  evaluateAssessment(
    workflowId: string,
  ): Promise<AssessmentLifecycleData>;
  sendAssessmentResultEmails(
    workflowId: string,
  ): Promise<AssessmentLifecycleData>;
  approveWebSource(
    workflowId: string,
    conversationId: string,
    candidate: SourceCandidate,
  ): Promise<{ userMessage: ChatMessage; tcoMessage: ChatMessage }>;
  listClassroomCourses(): Promise<ClassroomCourse[]>;

  getReviewDetails<T>(
    reviewType: WorkflowType,
    reviewId: string,
  ): Promise<T | null>;

  renameConversation(
    conversationId: string,
    newTitle: string,
  ): Promise<boolean>;

  archiveConversation(conversationId: string): Promise<boolean>;
  deleteConversation(conversationId: string): Promise<boolean>;
}

/**
 * Demo remains the default so the UI can be previewed without a running backend.
 * Set VITE_USE_MOCK_API=false in .env to use FastAPI.
 */
export const isMockMode = import.meta.env.VITE_USE_MOCK_API !== 'false';

export const api: ITCOApiService = isMockMode ? mockApi : fastApiService;
