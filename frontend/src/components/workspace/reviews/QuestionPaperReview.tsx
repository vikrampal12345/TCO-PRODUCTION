import React, { useState } from 'react';
import {
  QuestionPaperReviewData,
  QuestionPaperItem,
} from '../../../types/review';
import {
  FileSpreadsheet,
  Edit2,
  Trash2,
  RefreshCw,
  ThumbsUp,
  Download,
  Plus,
  CheckCircle2,
  X,
} from 'lucide-react';

interface QuestionPaperReviewProps {
  data: QuestionPaperReviewData;
  onApprove: (notes?: string) => void;
  onRequestRevision: (instructions: string) => void;
}

export const QuestionPaperReview: React.FC<QuestionPaperReviewProps> = ({
  data,
  onApprove,
  onRequestRevision,
}) => {
  const [questions, setQuestions] = useState<QuestionPaperItem[]>(
    data.questions
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState<string>('');
  const [editMarks, setEditMarks] = useState<number>(2);

  const handleDelete = (id: string) => {
    setQuestions((previousQuestions) =>
      previousQuestions.filter((question) => question.id !== id)
    );

    if (editingId === id) {
      setEditingId(null);
    }
  };

  const handleStartEdit = (question: QuestionPaperItem) => {
    setEditingId(question.id);
    setEditText(question.question);
    setEditMarks(question.marks);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditText('');
    setEditMarks(2);
  };

  const handleSaveEdit = (id: string) => {
    const trimmedText = editText.trim();

    if (!trimmedText || !Number.isFinite(editMarks) || editMarks < 1) {
      return;
    }

    setQuestions((previousQuestions) =>
      previousQuestions.map((question) =>
        question.id === id
          ? {
              ...question,
              question: trimmedText,
              marks: editMarks,
            }
          : question
      )
    );

    setEditingId(null);
  };

  const totalCalculatedMarks = questions.reduce(
    (sum, question) => sum + question.marks,
    0
  );

  return (
    <div className="flex h-full flex-col space-y-5 text-white/80">
      {/* Assessment Header */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/75">
              <FileSpreadsheet className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-white">
                {data.subject}
              </h3>

              <p className="mt-1 text-xs text-white/45">
                {data.gradeOrClass}
              </p>
            </div>
          </div>

          <span className="shrink-0 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/65">
            Draft Assessment
          </span>
        </div>

        {/* Assessment Statistics */}
        <div className="grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-3">
          <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-2.5 text-center">
            <span className="block text-[9px] font-medium tracking-wider text-white/40">
              QUESTIONS
            </span>

            <span className="mt-1 block text-base font-semibold text-white">
              {questions.length}
            </span>
          </div>

          <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-2.5 text-center">
            <span className="block text-[9px] font-medium tracking-wider text-white/40">
              TOTAL MARKS
            </span>

            <span className="mt-1 block text-base font-semibold text-white">
              {totalCalculatedMarks}
              <span className="text-xs font-normal text-white/40">
                {' '}
                / {data.totalMarks}
              </span>
            </span>
          </div>

          <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-2.5 text-center">
            <span className="block text-[9px] font-medium tracking-wider text-white/40">
              DURATION
            </span>

            <span className="mt-1 block text-base font-semibold text-white">
              {data.durationMinutes}
              <span className="ml-1 text-[10px] font-normal text-white/40">
                min
              </span>
            </span>
          </div>
        </div>

        {/* Exam Instructions */}
        {data.instructions.length > 0 && (
          <div className="space-y-2 rounded-lg border border-white/[0.08] bg-white/[0.02] p-3">
            <div className="text-[11px] font-semibold text-white/70">
              Exam Instructions
            </div>

            <ul className="list-disc space-y-1 pl-4 text-[11px] leading-relaxed text-white/45">
              {data.instructions.map((instruction, index) => (
                <li key={`${instruction}-${index}`}>{instruction}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Questions List */}
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-white/80">
            Question Paper Review
          </span>

          <span className="text-[10px] text-white/40">
            Edit and customize
          </span>
        </div>

        {questions.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-10 text-center">
            <FileSpreadsheet className="mb-3 h-7 w-7 text-white/25" />

            <p className="text-sm font-medium text-white/65">
              No questions available
            </p>

            <p className="mt-1 text-xs text-white/40">
              Add questions to prepare the assessment.
            </p>

            <button
              type="button"
              onClick={() =>
                onRequestRevision('Generate questions for this assessment.')
              }
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-medium text-white/75 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Plus className="h-3.5 w-3.5" />
              Generate Questions
            </button>
          </div>
        ) : (
          questions.map((question, index) => {
            const isEditing = editingId === question.id;

            return (
              <div
                key={question.id}
                className="group space-y-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-3.5 transition-colors hover:border-white/20"
              >
                <div className="flex items-start gap-3">
                  {/* Question Number */}
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] font-mono text-[10px] font-semibold text-white/70">
                    Q{index + 1}
                  </div>

                  {/* Question Content */}
                  <div className="min-w-0 flex-1">
                    {isEditing ? (
                      <div className="space-y-3">
                        <textarea
                          value={editText}
                          onChange={(event) =>
                            setEditText(event.target.value)
                          }
                          rows={3}
                          aria-label="Edit question text"
                          className="w-full resize-y rounded-lg border border-white/15 bg-black p-3 text-xs leading-relaxed text-white outline-none transition-colors placeholder:text-white/25 focus:border-white/40"
                          placeholder="Enter question text..."
                        />

                        <div className="flex flex-wrap items-end justify-between gap-3">
                          <div className="space-y-1">
                            <label className="block text-[10px] text-white/45">
                              Marks
                            </label>

                            <input
                              type="number"
                              min={1}
                              step={1}
                              value={editMarks}
                              onChange={(event) =>
                                setEditMarks(Number(event.target.value))
                              }
                              aria-label="Question marks"
                              className="w-20 rounded-lg border border-white/10 bg-black px-2.5 py-2 text-xs text-white outline-none focus:border-white/35"
                            />
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={handleCancelEdit}
                              className="rounded-lg border border-white/10 px-3 py-2 text-[11px] font-medium text-white/55 transition-colors hover:bg-white/[0.05] hover:text-white"
                            >
                              Cancel
                            </button>

                            <button
                              type="button"
                              onClick={() => handleSaveEdit(question.id)}
                              disabled={
                                !editText.trim() ||
                                !Number.isFinite(editMarks) ||
                                editMarks < 1
                              }
                              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-[11px] font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Save
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="text-xs font-medium leading-relaxed text-white/85">
                          {question.question}
                        </p>

                        <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px]">
                          <span className="rounded-md border border-white/10 bg-white/[0.05] px-2 py-1 font-medium text-white/75">
                            {question.marks}{' '}
                            {question.marks === 1 ? 'Mark' : 'Marks'}
                          </span>

                          <span className="rounded-md bg-white/[0.03] px-2 py-1 text-white/45">
                            Type: {question.type}
                          </span>

                          {question.bloomLevel && (
                            <span className="rounded-md bg-white/[0.03] px-2 py-1 text-white/45">
                              Bloom: {question.bloomLevel}
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Question Actions */}
                  {!isEditing && (
                    <div className="flex shrink-0 items-center gap-0.5">
                      <button
                        type="button"
                        onClick={() => handleStartEdit(question)}
                        title="Edit question"
                        aria-label={`Edit question ${index + 1}`}
                        className="rounded-lg p-2 text-white/40 transition-colors hover:bg-white/[0.07] hover:text-white"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          onRequestRevision(
                            `Regenerate question ${index + 1} with a numerical example.`
                          )
                        }
                        title="Regenerate alternative"
                        aria-label={`Regenerate question ${index + 1}`}
                        className="rounded-lg p-2 text-white/40 transition-colors hover:bg-white/[0.07] hover:text-white"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDelete(question.id)}
                        title="Delete question"
                        aria-label={`Delete question ${index + 1}`}
                        className="rounded-lg p-2 text-white/40 transition-colors hover:bg-white/[0.07] hover:text-white"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Approval Footer */}
      <div className="space-y-3 border-t border-white/10 pt-4">
        {/* Marks Validation */}
        {totalCalculatedMarks !== data.totalMarks && (
          <div className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <div className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/60" />

            <p className="text-[11px] leading-relaxed text-white/55">
              Question marks total {totalCalculatedMarks}, while the
              assessment target is {data.totalMarks}. Review the total before
              approving.
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={() =>
            onApprove(
              `Question paper with ${questions.length} questions and ${totalCalculatedMarks} total marks approved for printing.`
            )
          }
          disabled={questions.length === 0 || editingId !== null}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ThumbsUp className="h-4 w-4" />

          <span>
            Approve Question Paper ({questions.length} Questions,{' '}
            {totalCalculatedMarks} Marks)
          </span>
        </button>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() =>
              onRequestRevision(
                'Add 2 more application-level numerical questions.'
              )
            }
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2 py-3 text-[10px] font-medium text-white/55 transition-colors hover:bg-white/[0.07] hover:text-white sm:text-[11px]"
          >
            <Plus className="h-3.5 w-3.5" />
            Add More Questions
          </button>

          <button
            type="button"
            onClick={() => onApprove('Export PDF format')}
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2 py-3 text-[10px] font-medium text-white/55 transition-colors hover:bg-white/[0.07] hover:text-white sm:text-[11px]"
          >
            <Download className="h-3.5 w-3.5" />
            Export Clean PDF
          </button>
        </div>

        <p className="text-center text-[10px] text-white/35">
          AI assists. Teachers decide.
        </p>
      </div>
    </div>
  );
};