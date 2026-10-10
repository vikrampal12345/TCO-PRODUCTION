import React from 'react';
import { ClarificationRequest } from '../../types/workflow';
import { HelpCircle, ArrowRight } from 'lucide-react';

interface ClarificationBarProps {
  clarification: ClarificationRequest;
  onSelectOption: (optionId: string, customValue?: string) => void;
  disabled?: boolean;
}

export const ClarificationBar: React.FC<ClarificationBarProps> = ({
  clarification,
  onSelectOption,
  disabled = false,
}) => {
  return (
    <div className="mx-3 mb-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-4 sm:mx-4">
      {/* Header */}
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.06] text-white/80">
          <HelpCircle className="h-4 w-4" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-white/15 bg-white/[0.05] px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-white/70">
              Clarification Needed
            </span>

            <span className="text-[11px] text-white/40">
              TCO needs your input
            </span>
          </div>

          <h4 className="text-sm font-semibold leading-relaxed text-white">
            {clarification.prompt}
          </h4>

          {clarification.contextHint && (
            <p className="mt-1 text-xs leading-relaxed text-white/50">
              {clarification.contextHint}
            </p>
          )}
        </div>
      </div>

      {/* Answer Options */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-4">
        {clarification.options.map((opt) => (
          <button
            key={opt.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectOption(opt.id, opt.label)}
            className="group rounded-lg border border-white/10 bg-white/[0.02] p-3 text-left transition-colors hover:border-white/25 hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-white/90 transition-colors group-hover:text-white">
                {opt.label}
              </span>

              <ArrowRight className="h-3.5 w-3.5 shrink-0 text-white/30 opacity-0 transition-all group-hover:translate-x-0.5 group-hover:text-white/80 group-hover:opacity-100" />
            </div>

            {opt.description && (
              <p className="mt-1 truncate text-[10px] leading-relaxed text-white/45">
                {opt.description}
              </p>
            )}
          </button>
        ))}
      </div>

      {/* Footer Hint */}
      <p className="mt-3 text-right text-[10px] leading-relaxed text-white/35">
        You can also type a custom answer in the message box below.
      </p>
    </div>
  );
};