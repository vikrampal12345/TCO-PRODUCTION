
import type { Conversation, ChatMessage } from '../types/chat';
import type { WorkflowProgress, WorkflowType } from '../types/workflow';
import { mockApi } from './mockApi';
import { fastApiService } from './fastApiService';

export type WorkspaceSourceMode =
  | 'general_knowledge'
  | 'teacher_file'
  | 'classroom'
  | 'web_search';

export interface MessageAttachmentInput {
  name: string;
  size: string;
  type: string;
  /** Original file bytes; absent for previously stored attachments/demo data. */
  file?: File;
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
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }>;

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
