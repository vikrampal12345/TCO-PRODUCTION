import React from 'react';
import { motion } from 'framer-motion';
import { ChatMessage, SourceCandidate } from '../../types/chat';
import { WorkflowType } from '../../types/workflow';
import { ProcessTimeline } from './ProcessTimeline';
import {
  FileText,
  Eye,
  Sparkles,
  User,
} from 'lucide-react';

interface ChatMessageItemProps {
  message: ChatMessage;
  onOpenReview?: (type: WorkflowType, id?: string) => void;
  onApproveWebSource?: (workflowId: string, candidate: SourceCandidate) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onOpenReview,
  onApproveWebSource,
}) => {
  const isTeacher = message.sender === 'teacher';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex gap-3 px-3 py-3 sm:px-4 ${
        isTeacher ? 'justify-end' : 'justify-start'
      }`}
    >
      {/* TCO Avatar */}
      {!isTeacher && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-white text-[10px] font-bold text-black">
          TCO
        </div>
      )}

      {/* Message Container */}
      <div
        className={`flex max-w-[88%] flex-col gap-2 sm:max-w-[80%] md:max-w-[72%] ${
          isTeacher ? 'items-end' : 'items-start'
        }`}
      >
        {/* Author and Timestamp */}
        <div
          className={`flex flex-wrap items-center gap-2 text-[11px] ${
            isTeacher ? 'justify-end' : 'justify-start'
          }`}
        >
          <span className="font-medium text-white/80">
            {isTeacher ? 'You' : 'TCO Master Agent'}
          </span>

          <span className="text-white/40">
            {message.timestamp}
          </span>
        </div>

        {/* Message Bubble */}
        <div
          className={`rounded-2xl p-4 text-sm leading-relaxed ${
            isTeacher
              ? 'rounded-tr-sm bg-white text-black'
              : 'rounded-tl-sm border border-white/10 bg-[#111111] text-white/90'
          }`}
        >
          {/* Message Text */}
          <div className="whitespace-pre-line break-words">
            {message.content}
          </div>

          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-white/50">
                Attached Exam Material
              </div>

              <div className="flex flex-wrap gap-2">
                {message.attachments.map((att, i) => (
                  <div
                    key={i}
                    className={`flex max-w-full items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                      isTeacher
                        ? 'border-black/10 bg-black/5 text-black/80'
                        : 'border-white/10 bg-white/[0.04] text-white/80'
                    }`}
                  >
                    <FileText
                      className={`h-4 w-4 shrink-0 ${
                        isTeacher ? 'text-black' : 'text-white/70'
                      }`}
                    />

                    <span className="max-w-[180px] truncate">
                      {att.name}
                    </span>

                    <span
                      className={`shrink-0 text-[10px] ${
                        isTeacher ? 'text-black/50' : 'text-white/40'
                      }`}
                    >
                      ({att.size})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Workflow Timeline */}
          {message.workflowProgress && (
            <ProcessTimeline progress={message.workflowProgress} />
          )}

          {message.sourceCandidates && message.sourceCandidates.length > 0 && (
            <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
              <div className="text-xs font-semibold text-white/75">
                Web sources requiring teacher approval
              </div>
              {message.sourceCandidates.map((candidate) => (
                <div key={candidate.url} className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
                  <div className="text-xs font-medium text-white">{candidate.title}</div>
                  <div className="mt-1 line-clamp-2 text-[10px] text-white/50">{candidate.snippet}</div>
                  {onApproveWebSource && message.workflowProgress?.workflowId && (
                    <button
                      type="button"
                      onClick={() => onApproveWebSource(message.workflowProgress!.workflowId, candidate)}
                      className="mt-2 rounded-md border border-white/20 px-2 py-1 text-[10px] text-white hover:bg-white/10"
                    >
                      Approve and continue
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Review Panel Action */}
          {message.reviewType && onOpenReview && (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
              <div className="flex items-center gap-2 text-xs text-white/60">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Ready for teacher review</span>
              </div>

              <button
                onClick={() =>
                  onOpenReview(message.reviewType!, message.reviewDataId)
                }
                className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-white/10"
              >
                <Eye className="h-3.5 w-3.5" />
                <span>Open Review Panel</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Teacher Avatar */}
      {isTeacher && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-[#171717] text-white">
          <User className="h-4 w-4" />
        </div>
      )}
    </motion.div>
  );
};