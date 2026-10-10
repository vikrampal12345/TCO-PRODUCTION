import React, { useRef, useEffect } from 'react';
import { Conversation, QuickActionItem } from '../../types/chat';
import { WorkflowType } from '../../types/workflow';
import type { MessageAttachmentInput } from '../../services/api';
import { ChatMessageItem } from './ChatMessageItem';
import { MessageComposer, type WorkspaceSourceMode } from './MessageComposer';
import { TCOAnimatedLogo } from '../marketing/TCOAnimatedLogo';
import { ClarificationBar } from './ClarificationBar';
import { ApprovalBar } from './ApprovalBar';
import {
  FileCheck2,
  FileSpreadsheet,
  Users2,
  Table,
  Presentation,
  BarChart3,
  Eye,
  PanelRightClose,
  PanelRightOpen,
  Menu,
} from 'lucide-react';

interface ChatWindowProps {
  conversation: Conversation | null;
  isProcessing: boolean;
  onSendMessage: (
    message: string,
    attachments?: MessageAttachmentInput[],
    sourceMode?: WorkspaceSourceMode
  ) => void;
  onClarification: (optionId: string, customValue?: string) => void;
  onApprove: (notes?: string) => void;
  onRequestRevision: (instructions: string) => void;
  onOpenReview: (type: WorkflowType, id?: string) => void;
  onStopProcessing: () => void;
  isReviewPanelOpen: boolean;
  onToggleReviewPanel: () => void;
  onOpenMobileSidebar?: () => void;
}

const QUICK_ACTIONS: QuickActionItem[] = [
  {
    id: 'qa-check',
    title: 'Check Answer Sheets',
    description: 'Digitize, extract & verify student handwriting against rubric',
    iconName: 'FileCheck2',
    prompt: 'Check these answer sheets for the Data Structures & DBMS Unit Test.',
    workflowType: 'answer_sheet_checking',
  },
  {
    id: 'qa-paper',
    title: 'Create Question Paper',
    description: "Generate structured exam questions balanced by Bloom's Taxonomy",
    iconName: 'FileSpreadsheet',
    prompt: 'Create a question paper for Operating Systems with 20 questions (50 Marks).',
    workflowType: 'question_paper_generation',
  },
  {
    id: 'qa-ppt',
    title: 'Generate PPT',
    description: 'Create 12-slide lecture presentation outline with speaker notes',
    iconName: 'Presentation',
    prompt: 'Make a PPT on Operating Systems & Concurrency Architecture for tomorrow.',
    workflowType: 'ppt_generation',
  },
  {
    id: 'qa-attendance',
    title: 'Take Attendance',
    description: 'Reconcile sign-in sheets and roster logs without surveillance',
    iconName: 'Users2',
    prompt: "Mark attendance for today's CS-301 lecture and flag ambiguous entries.",
    workflowType: 'attendance',
  },
  {
    id: 'qa-marksheet',
    title: 'Create Marksheet',
    description: 'Aggregate scores, calculate percentage tiers, and export records',
    iconName: 'Table',
    prompt: 'Compile and format the midterm marksheet for CSE Section B.',
    workflowType: 'marksheet',
  },
  {
    id: 'qa-analytics',
    title: 'Analyze Class',
    description: 'Pinpoint weak topics, score distributions, and mastery gaps',
    iconName: 'BarChart3',
    prompt: 'Analyze my class performance for the recent unit assessment.',
    workflowType: 'analytics',
  },
];

export const ChatWindow: React.FC<ChatWindowProps> = ({
  conversation,
  isProcessing,
  onSendMessage,
  onClarification,
  onApprove,
  onRequestRevision,
  onOpenReview,
  onStopProcessing,
  isReviewPanelOpen,
  onToggleReviewPanel,
  onOpenMobileSidebar,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as messages stream in
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation?.messages, isProcessing]);

  // Get the latest message's active clarification or approval
  const lastMsg =
    conversation?.messages[conversation.messages.length - 1];

  const activeClarification = lastMsg?.clarification;

  const activeApproval =
    lastMsg?.approval ||
    (lastMsg?.workflowProgress?.approval
      ? lastMsg.workflowProgress.approval
      : undefined);

  const getActionIcon = (iconName: string) => {
    const iconClass = 'h-5 w-5 text-white/75';

    switch (iconName) {
      case 'FileCheck2':
        return <FileCheck2 className={iconClass} />;
      case 'FileSpreadsheet':
        return <FileSpreadsheet className={iconClass} />;
      case 'Presentation':
        return <Presentation className={iconClass} />;
      case 'Users2':
        return <Users2 className={iconClass} />;
      case 'Table':
        return <Table className={iconClass} />;
      case 'BarChart3':
      default:
        return <BarChart3 className={iconClass} />;
    }
  };

  return (
    <div className="relative flex h-full flex-1 select-text flex-col overflow-hidden bg-black font-sans">
      {/* Top Header */}
      <header className="z-10 flex h-16 shrink-0 items-center justify-between border-b border-white/10 bg-black/90 px-4 backdrop-blur-md sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          {onOpenMobileSidebar && (
            <button
              onClick={onOpenMobileSidebar}
              className="rounded-lg p-2 text-white/60 transition-colors hover:bg-white/10 hover:text-white lg:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}

          <TCOAnimatedLogo
            variant="workspace"
            active={isProcessing}
            className="tco-animated-logo-header shrink-0"
          />

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="max-w-[220px] truncate text-sm font-semibold tracking-tight text-white sm:max-w-md">
                {conversation?.title || 'Teacher Workspace'}
              </h1>

              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors ${
                isProcessing
                  ? 'border-white/35 bg-white/10 text-white'
                  : 'border-white/15 bg-white/5 text-white/60'
              }`}>
                {isProcessing ? 'TCO Working' : 'TCO Ready'}
              </span>
            </div>

            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-white/45">
              <span className="h-1.5 w-1.5 rounded-full bg-white/70" />
              <span>{isProcessing ? 'TCO is working on your task…' : 'Ready · Teacher Co-Worker'}</span>
            </div>
          </div>
        </div>

        {/* Header Actions */}
        <div className="ml-2 flex shrink-0 items-center gap-2">
          {conversation?.activeWorkflowType && (
            <button
              onClick={() =>
                onOpenReview(conversation.activeWorkflowType!)
              }
              className="hidden items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white sm:flex"
            >
              <Eye className="h-3.5 w-3.5" />
              <span>View Review</span>
            </button>
          )}

          <button
            onClick={onToggleReviewPanel}
            className={`rounded-lg border p-2 transition-colors ${
              isReviewPanelOpen
                ? 'border-white/25 bg-white text-black'
                : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
            }`}
            title={
              isReviewPanelOpen
                ? 'Hide Review Panel'
                : 'Show Review Panel'
            }
            aria-label={
              isReviewPanelOpen
                ? 'Hide Review Panel'
                : 'Show Review Panel'
            }
          >
            {isReviewPanelOpen ? (
              <PanelRightClose className="h-4 w-4" />
            ) : (
              <PanelRightOpen className="h-4 w-4" />
            )}
          </button>
        </div>
      </header>

      {/* Chat Scroll Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 sm:p-6"
      >
        {!conversation || conversation.messages.length === 0 ? (
          /* Fresh Workspace */
          <div className="mx-auto flex max-w-3xl flex-col space-y-8 px-2 py-10 text-center sm:px-4 sm:py-12">
            <div className="mx-auto -mb-3 flex items-center justify-center" aria-label={isProcessing ? 'TCO is processing your task' : 'TCO is ready'}>
              <TCOAnimatedLogo variant="workspace" active={isProcessing} />
            </div>

            <div className="space-y-3">
              <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                Good morning, Teacher.
              </h2>

              <p className="mx-auto max-w-lg text-sm leading-relaxed text-white/55 sm:text-base">
                What would you like TCO to handle today? Start a conversation
                or choose a workflow below.
              </p>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 gap-3 text-left sm:grid-cols-2 md:grid-cols-3">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.id}
                  onClick={() => onSendMessage(action.prompt)}
                  className="group flex flex-col justify-between rounded-xl border border-white/10 bg-[#0b0b0b] p-4 text-left transition-colors hover:border-white/25 hover:bg-[#141414]"
                >
                  <div>
                    <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] transition-colors group-hover:bg-white/10">
                      {getActionIcon(action.iconName)}
                    </div>

                    <h3 className="text-sm font-medium text-white">
                      {action.title}
                    </h3>

                    <p className="mt-1.5 text-xs leading-relaxed text-white/45">
                      {action.description}
                    </p>
                  </div>

                  <div className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-3 text-[11px]">
                    <span className="text-white/35">
                      Quick Action
                    </span>

                    <span className="text-white/70 transition-colors group-hover:text-white">
                      Start →
                    </span>
                  </div>
                </button>
              ))}
            </div>

            <p className="pt-1 text-xs text-white/35">
              Teacher Co-Worker · Every grade requires teacher approval.
            </p>
          </div>
        ) : (
          /* Active Chat */
          <div className="mx-auto max-w-4xl space-y-4">
            {conversation.messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onOpenReview={onOpenReview}
              />
            ))}
          </div>
        )}
      </div>

      {/* Clarification */}
      {activeClarification && (
        <ClarificationBar
          clarification={activeClarification}
          onSelectOption={onClarification}
          disabled={isProcessing}
        />
      )}

      {/* Approval */}
      {activeApproval && (
        <ApprovalBar
          approval={activeApproval}
          onOpenReview={onOpenReview}
          onApprove={onApprove}
          onRequestRevision={onRequestRevision}
          disabled={isProcessing}
        />
      )}

      {/* Message Composer */}
      <MessageComposer
        onSend={onSendMessage}
        isProcessing={isProcessing}
        onStop={onStopProcessing}
      />
    </div>
  );
};
