import React, { useState } from 'react';
import { AnswerSheetReviewData } from '../../../types/review';
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Edit3,
  Check,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

interface AnswerSheetReviewProps {
  data: AnswerSheetReviewData;
  onApprove: (notes?: string) => void;
  onReject: (reason?: string) => void;
  onRequestRevision: (instructions: string) => void;
}

export const AnswerSheetReview: React.FC<AnswerSheetReviewProps> = ({
  data,
  onApprove,
  onReject,
  onRequestRevision,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState<number>(0);
  const [editingMarks, setEditingMarks] = useState<boolean>(false);
  const [assignedMarks, setAssignedMarks] = useState<number>(
    data.questions[0]?.suggestedMarks || 4
  );
  const [teacherNote, setTeacherNote] = useState<string>('');
  const [revisionText, setRevisionText] = useState<string>('');
  const [showRevisionInput, setShowRevisionInput] = useState<boolean>(false);

  const currentQ = data.questions[selectedQuestionIndex] || data.questions[0];

  if (!currentQ) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-white/10 bg-[#0b0b0b] p-6 text-center">
        <FileText className="mb-3 h-8 w-8 text-white/40" />
        <h3 className="text-sm font-semibold text-white">
          No question data available
        </h3>
        <p className="mt-1 text-xs text-white/45">
          Question-level evaluation details are not available for this answer sheet.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col space-y-6 text-white/80">
      {/* Student Information */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="rounded-md border border-white/15 bg-white/[0.05] px-2.5 py-1 font-mono text-xs font-semibold text-white/80">
              {data.studentId}
            </span>

            <span className="truncate text-sm font-semibold text-white">
              {data.studentName}
            </span>
          </div>

          <span className="rounded-md border border-white/15 bg-white/[0.04] px-2.5 py-1 text-xs text-white/60">
            {data.status}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 border-t border-white/[0.08] pt-3 text-xs sm:grid-cols-4">
          <div>
            <p className="mb-1 text-white/40">Roll Number</p>
            <p className="break-words text-white/80">{data.rollNumber}</p>
          </div>

          <div>
            <p className="mb-1 text-white/40">Subject</p>
            <p className="break-words text-white/80">{data.subject}</p>
          </div>

          <div>
            <p className="mb-1 text-white/40">Total Pages</p>
            <p className="text-white/80">{data.totalPages}</p>
          </div>

          <div>
            <p className="mb-1 text-white/40">Exam</p>
            <p className="text-white/80">Unit Test</p>
          </div>
        </div>

        {/* Verification Pipeline */}
        <div className="border-t border-white/[0.08] pt-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/40">
            Verification Pipeline
          </p>

          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="text-white/60">Extraction ✓</span>
            <span className="text-white/25">→</span>
            <span className="text-white/60">Verification ✓</span>
            <span className="text-white/25">→</span>
            <span className="text-white/60">Grading ✓</span>
            <span className="text-white/25">→</span>
            <span className="rounded-md border border-white/20 bg-white/[0.08] px-2 py-1 font-medium text-white">
              Teacher Review
            </span>
            <span className="text-white/25">→</span>
            <span className="text-white/40">Final Approval</span>
          </div>
        </div>
      </div>

      {/* Original Answer Sheet Preview */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-white">
            <FileText className="h-4 w-4 text-white/60" />
            <span>Student Answer Sheet</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-white/45">
              Page {currentPage} of {data.totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => p - 1)}
              className="rounded-lg border border-white/10 bg-white/[0.04] p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>

            <button
              type="button"
              disabled={currentPage >= data.totalPages}
              onClick={() => setCurrentPage((p) => p + 1)}
              className="rounded-lg border border-white/10 bg-white/[0.04] p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
              aria-label="Next page"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Preview Mockup */}
        <div className="relative space-y-4 rounded-xl border border-white/10 bg-[#f8f8f6] p-4 font-mono text-xs text-[#242424] shadow-inner sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-black/10 pb-2 font-sans text-[10px] text-black/50">
            <span>Name: {data.studentName}</span>
            <span>Roll: {data.rollNumber}</span>
            <span>Page {currentPage}</span>
          </div>

          <div className="space-y-2 rounded-lg border border-black/10 bg-white p-3 sm:p-4">
            <div className="font-sans text-xs font-semibold leading-relaxed text-black/80">
              {currentQ.questionNumber}. {currentQ.questionText}
            </div>

            <p className="whitespace-pre-line text-xs leading-relaxed text-black/75">
              {currentQ.extractedAnswer}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-black/10 pt-2 font-sans text-[10px] text-black/45">
            <span>Extracted answer preview</span>
            <span className="font-medium text-black/60">
              Confidence: {currentQ.confidence}
            </span>
          </div>
        </div>

        <p className="text-[10px] leading-relaxed text-white/35">
          This panel displays an answer preview. Connect the original uploaded
          page image or PDF renderer to inspect the actual handwritten scan.
        </p>
      </div>

      {/* Question Selector */}
      <div className="space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">
          Questions
        </p>

        <div className="flex items-center gap-2 overflow-x-auto border-b border-white/10 pb-2">
          {data.questions.map((q, idx) => (
            <button
              type="button"
              key={idx}
              onClick={() => {
                setSelectedQuestionIndex(idx);
                setAssignedMarks(q.suggestedMarks);
                setEditingMarks(false);
              }}
              className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                selectedQuestionIndex === idx
                  ? 'border-white bg-white text-black'
                  : 'border-white/10 bg-white/[0.03] text-white/55 hover:bg-white/[0.08] hover:text-white'
              }`}
            >
              {q.questionNumber} ({q.suggestedMarks}/{q.maxMarks})
            </button>
          ))}
        </div>
      </div>

      {/* Evaluation and Marks */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
          <div>
            <h3 className="text-xs font-semibold text-white">
              AI Rubric Evaluation
            </h3>
            <p className="mt-1 text-[11px] text-white/40">
              Evaluation against the instructor's answer key
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-white/40">Provisional</span>

            {editingMarks ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max={currentQ.maxMarks}
                  value={assignedMarks}
                  onChange={(e) =>
                    setAssignedMarks(
                      Math.min(
                        currentQ.maxMarks,
                        Math.max(0, parseFloat(e.target.value) || 0)
                      )
                    )
                  }
                  className="w-16 rounded-lg border border-white/20 bg-black px-2 py-1.5 text-center text-xs font-semibold text-white outline-none focus:border-white/50"
                  aria-label="Assigned marks"
                />

                <button
                  type="button"
                  onClick={() => setEditingMarks(false)}
                  className="rounded-lg bg-white p-1.5 text-black transition-colors hover:bg-white/80"
                  title="Save marks"
                  aria-label="Save marks"
                >
                  <Check className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-base font-semibold text-white">
                  {assignedMarks} / {currentQ.maxMarks}
                </span>

                <button
                  type="button"
                  onClick={() => setEditingMarks(true)}
                  className="rounded-lg p-1.5 text-white/45 transition-colors hover:bg-white/10 hover:text-white"
                  title="Edit marks"
                  aria-label="Edit marks"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Rubric Criteria */}
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-white/40">
            Rubric Criteria
          </p>

          {currentQ.rubricCriteria.map((criterion, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between gap-3 rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 text-xs text-white/70"
            >
              <span>{criterion}</span>
              <CheckCircle2 className="h-4 w-4 shrink-0 text-white/60" />
            </div>
          ))}
        </div>

        {/* AI Rationale */}
        <div className="space-y-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-white/80">
            <AlertCircle className="h-4 w-4 text-white/60" />
            AI Rationale
          </div>

          <p className="text-xs leading-relaxed text-white/60">
            {currentQ.rationale}
          </p>
        </div>

        {/* Teacher Notes */}
        <div>
          <label
            htmlFor="teacher-note"
            className="mb-2 block text-[10px] font-semibold uppercase tracking-wider text-white/45"
          >
            Teacher Notes / Student Feedback
          </label>

          <input
            id="teacher-note"
            type="text"
            value={teacherNote}
            onChange={(e) => setTeacherNote(e.target.value)}
            placeholder="Add feedback (optional)..."
            className="w-full rounded-lg border border-white/10 bg-black px-3 py-2.5 text-xs text-white outline-none placeholder:text-white/30 focus:border-white/30"
          />
        </div>
      </div>

      {/* Revision Request */}
      {showRevisionInput && (
        <div className="space-y-3 rounded-xl border border-white/15 bg-[#0b0b0b] p-4">
          <div>
            <h3 className="text-xs font-semibold text-white">
              Request Re-evaluation
            </h3>
            <p className="mt-1 text-[11px] text-white/40">
              Explain what the AI should review again.
            </p>
          </div>

          <textarea
            value={revisionText}
            onChange={(e) => setRevisionText(e.target.value)}
            placeholder="e.g., Re-check Question 1 and consider partial credit for the diagram..."
            rows={3}
            className="w-full resize-y rounded-lg border border-white/10 bg-black p-3 text-xs leading-relaxed text-white outline-none placeholder:text-white/30 focus:border-white/30"
          />

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowRevisionInput(false);
                setRevisionText('');
              }}
              className="rounded-lg px-3 py-2 text-xs text-white/50 transition-colors hover:bg-white/[0.05] hover:text-white"
            >
              Cancel
            </button>

            <button
              type="button"
              disabled={!revisionText.trim()}
              onClick={() => {
                if (revisionText.trim()) {
                  onRequestRevision(revisionText.trim());
                  setShowRevisionInput(false);
                  setRevisionText('');
                }
              }}
              className="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Submit Revision
            </button>
          </div>
        </div>
      )}

      {/* Teacher Decision Actions */}
      <div className="space-y-3 border-t border-white/10 pt-4">
        <div className="flex items-stretch gap-2">
          <button
            type="button"
            onClick={() =>
              onApprove(
                teacherNote ||
                  `Approved with ${assignedMarks}/${currentQ.maxMarks} marks.`
              )
            }
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-white px-3 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85"
          >
            <ThumbsUp className="h-4 w-4" />
            <span>
              Approve ({assignedMarks}/{currentQ.maxMarks})
            </span>
          </button>

          <button
            type="button"
            onClick={() => setShowRevisionInput((prev) => !prev)}
            className="flex items-center justify-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-3 py-3 text-xs font-medium text-white/75 transition-colors hover:bg-white/10 hover:text-white"
            title="Request changes"
          >
            <RotateCcw className="h-4 w-4" />
            <span className="hidden sm:inline">Revise</span>
          </button>

          <button
            type="button"
            onClick={() =>
              onReject('Teacher flagged for physical re-checking')
            }
            className="rounded-xl border border-white/15 bg-white/[0.04] p-3 text-white/65 transition-colors hover:bg-white/10 hover:text-white"
            title="Flag for physical re-check"
            aria-label="Flag for physical re-check"
          >
            <ThumbsDown className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center justify-center gap-2 text-center text-[10px] text-white/40">
          <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
          <span>Teacher decision protected · No autonomous finalization</span>
        </div>
      </div>
    </div>
  );
};