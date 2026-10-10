import React, { useState } from 'react';
import { ApprovalRequest, WorkflowType } from '../../types/workflow';
import {
  ShieldCheck,
  Eye,
  ThumbsUp,
  RotateCcw,
  Check,
  Sparkles,
  X,
} from 'lucide-react';

interface ApprovalBarProps {
  approval: ApprovalRequest;
  onOpenReview: (type: WorkflowType) => void;
  onApprove: (notes?: string) => void;
  onRequestRevision: (instructions: string) => void;
  disabled?: boolean;
}

export const ApprovalBar: React.FC<ApprovalBarProps> = ({
  approval,
  onOpenReview,
  onApprove,
  onRequestRevision,
  disabled = false,
}) => {
  const [showRevisionInput, setShowRevisionInput] = useState(false);
  const [revisionNote, setRevisionNote] = useState('');

  const handleRevisionSubmit = () => {
    const instruction = revisionNote.trim();

    if (!instruction || disabled) return;

    onRequestRevision(instruction);
    setRevisionNote('');
    setShowRevisionInput(false);
  };

  const handleRevisionCancel = () => {
    setShowRevisionInput(false);
    setRevisionNote('');
  };

  return (
    <div className="mx-4 mb-3 space-y-4 rounded-2xl border border-white/10 bg-[#0b0b0b] p-4">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.05] text-white/75">
            <ShieldCheck className="h-5 w-5" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded-md border border-white/15 bg-white/[0.05] px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-white/70">
                Action Required
              </span>

              <span className="text-[11px] font-medium text-white/45">
                Teacher Decision Checkpoint
              </span>
            </div>

            <h4 className="text-sm font-semibold leading-relaxed text-white">
              {approval.title}
            </h4>

            <p className="mt-1 text-xs leading-relaxed text-white/50">
              {approval.summary}
            </p>
          </div>
        </div>

        {/* Quick Metrics */}
        {approval.metrics && approval.metrics.length > 0 && (
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.02] p-2">
            {approval.metrics.map((metric, index) => (
              <div
                key={`${metric.label}-${index}`}
                className={`min-w-[60px] px-2 text-center ${
                  index !== approval.metrics!.length - 1
                    ? 'border-r border-white/10'
                    : ''
                }`}
              >
                <span className="block text-[9px] uppercase tracking-wider text-white/40">
                  {metric.label}
                </span>

                <span className="mt-1 block font-mono text-xs font-semibold text-white/85">
                  {metric.value}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Revision Input */}
      {showRevisionInput && (
        <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05]">
              <Sparkles className="h-3.5 w-3.5 text-white/70" />
            </div>

            <div>
              <h5 className="text-xs font-semibold text-white/85">
                Request Changes
              </h5>

              <p className="mt-0.5 text-[10px] text-white/40">
                Describe what TCO should improve or modify.
              </p>
            </div>
          </div>

          <textarea
            value={revisionNote}
            onChange={(event) => setRevisionNote(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                handleRevisionSubmit();
              }
            }}
            placeholder="e.g. Make questions 5 and 7 harder, or adjust the rubric to award partial credit..."
            rows={3}
            disabled={disabled}
            className="w-full resize-y rounded-lg border border-white/10 bg-black px-3 py-2.5 text-xs leading-relaxed text-white outline-none transition-colors placeholder:text-white/25 focus:border-white/30 disabled:cursor-not-allowed disabled:opacity-50"
          />

          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[10px] text-white/35">
              Enter to submit · Shift + Enter for a new line
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRevisionCancel}
                disabled={disabled}
                className="rounded-lg border border-white/10 px-3 py-2 text-[11px] font-medium text-white/55 transition-colors hover:bg-white/[0.05] hover:text-white disabled:opacity-40"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleRevisionSubmit}
                disabled={disabled || !revisionNote.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-[11px] font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Send Instructions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decision Buttons */}
      <div className="flex flex-col gap-2 border-t border-white/[0.08] pt-3 sm:flex-row sm:flex-wrap sm:items-center">
        {/* Open Review */}
        <button
          type="button"
          disabled={disabled}
          onClick={() => onOpenReview(approval.reviewType)}
          className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-xs font-medium text-white/75 transition-colors hover:bg-white/[0.08] hover:text-white disabled:cursor-not-allowed disabled:opacity-40 sm:justify-start"
        >
          <Eye className="h-3.5 w-3.5" />
          <span>Open Review Panel</span>
        </button>

        {/* Approve */}
        <button
          type="button"
          disabled={disabled}
          onClick={() => onApprove()}
          className="flex min-w-[140px] flex-1 items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ThumbsUp className="h-3.5 w-3.5" />
          <span>Approve Outcome</span>
        </button>

        {/* Request Revision */}
        <button
          type="button"
          disabled={disabled}
          onClick={() => setShowRevisionInput((previous) => !previous)}
          className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 sm:justify-start ${
            showRevisionInput
              ? 'border-white/20 bg-white/[0.08] text-white'
              : 'border-white/10 bg-transparent text-white/55 hover:bg-white/[0.05] hover:text-white'
          }`}
        >
          {showRevisionInput ? (
            <X className="h-3.5 w-3.5" />
          ) : (
            <RotateCcw className="h-3.5 w-3.5" />
          )}

          <span>{showRevisionInput ? 'Close Editor' : 'Ask for Changes'}</span>
        </button>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 text-[10px] text-white/35">
        <Check className="h-3 w-3 shrink-0" />
        <span>AI assists. Teachers decide.</span>
      </div>
    </div>
  );
};