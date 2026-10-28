
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { WorkflowType } from '../../types/workflow';
import type { AssessmentLifecycleData } from '../../types/workflow';
import { api } from '../../services/api';
import { AnswerSheetReview } from './reviews/AnswerSheetReview';
import { QuestionPaperReview } from './reviews/QuestionPaperReview';
import { MarksheetPreview } from './reviews/MarksheetPreview';
import { AttendancePreview } from './reviews/AttendancePreview';
import { PPTPreview } from './reviews/PPTPreview';
import { AnalyticsPreview } from './reviews/AnalyticsPreview';
import {
  X,
  Maximize2,
  Minimize2,
  Eye,
  Loader2,
  AlertTriangle,
  FileText,
  CheckCircle2,
  Circle,
  Send,
} from 'lucide-react';

interface ContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  reviewType: WorkflowType | null;
  reviewId: string | null;
  lifecycle?: AssessmentLifecycleData;
  onApprove: (notes?: string) => void;
  onReject: (reason?: string) => void;
  onRequestRevision: (instructions: string) => void;
  onSendAssessmentToStudents?: (target?: { school_id: string; class_level: string; section: string }) => Promise<AssessmentLifecycleData>;
  onPreviewAssessmentRecipients?: () => Promise<AssessmentLifecycleData>;
  onEvaluateAssessment?: () => Promise<AssessmentLifecycleData>;
  onSendAssessmentResultEmails?: () => Promise<AssessmentLifecycleData>;
  isMobile?: boolean;
}

interface AssessmentReviewViewProps {
  data: any;
  onApprove: (notes?: string) => void;
  onReject: (reason?: string) => void;
  onRequestRevision: (instructions: string) => void;
  lifecycle?: AssessmentLifecycleData;
  onSendAssessmentToStudents?: (target?: { school_id: string; class_level: string; section: string }) => Promise<AssessmentLifecycleData>;
  onPreviewAssessmentRecipients?: () => Promise<AssessmentLifecycleData>;
  onEvaluateAssessment?: () => Promise<AssessmentLifecycleData>;
  onSendAssessmentResultEmails?: () => Promise<AssessmentLifecycleData>;
}

const AssessmentReviewView: React.FC<AssessmentReviewViewProps> = ({
  data,
  onApprove,
  onReject,
  onRequestRevision,
  lifecycle,
  onSendAssessmentToStudents,
  onPreviewAssessmentRecipients,
  onEvaluateAssessment,
  onSendAssessmentResultEmails,
}) => {
  const [deliverySchoolId, setDeliverySchoolId] = useState('electro');
  const [deliveryClassLevel, setDeliveryClassLevel] = useState('Electro');
  const [deliverySection, setDeliverySection] = useState('1');


  const [teacherFeedback, setTeacherFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [recipientPreviewLoaded, setRecipientPreviewLoaded] = useState(false);

  const assessment = data?.assessment || data || {};
  const review = data?.review || {};
  const approval = data?.approval || {};

  const questions: any[] = Array.isArray(assessment.questions)
    ? assessment.questions
    : Array.isArray(data?.questions)
      ? data.questions
      : [];

  const answerKey: any[] = Array.isArray(assessment.answer_key)
    ? assessment.answer_key
    : Array.isArray(data?.answer_key)
      ? data.answer_key
      : [];

  const markingScheme: any[] = Array.isArray(assessment.marking_scheme)
    ? assessment.marking_scheme
    : Array.isArray(data?.marking_scheme)
      ? data.marking_scheme
      : [];

  const reviewStatus = String(
    review.status ||
      data?.assessment_review_status ||
      'unknown',
  ).toLowerCase();

  const reviewFeedback = String(
    review.feedback ||
      data?.assessment_review_feedback ||
      review.assessment_review_feedback ||
      '',
  );

  const manualReviewRequired =
    review.manual_teacher_review_required === true ||
    data?.manual_teacher_review_required === true;

  const automatedReviewFailed =
    review.automated_review_failed === true ||
    data?.automated_review_failed === true;

  // The latest lifecycle response must override stale review data after
  // approval/publication and subsequent delivery/evaluation actions.
  const lifecycleState = {
    ...(data || {}),
    ...(lifecycle || {}),
  };
  const lifecycleStatus = String(lifecycleState.status || '');
  const isPublished = Boolean(
    lifecycleState.form_id &&
      lifecycleState.assessment_id &&
      lifecycleStatus !== 'assessment_generation_failed',
  );
  const evaluationResults = Array.isArray(lifecycleState.evaluation_results)
    ? lifecycleState.evaluation_results
    : [];
  const hasSavedResults = evaluationResults.some((item: any) =>
    Boolean(item?.saved_result?.result_id),
  );
  const resultEmailSummary =
    lifecycleState.result_email_summary &&
    typeof lifecycleState.result_email_summary === 'object'
      ? lifecycleState.result_email_summary
      : {};

  const isPending =
    approval.status === 'pending' ||
    approval.approval_status === 'pending';

  const getCorrectOption = (question: any): number | undefined => {
    const answer = answerKey.find(
      (item: any) =>
        Number(item.question_number) ===
        Number(question.question_number),
    );

    const value = answer?.correct_option ?? question.correct_option;
    const number = Number(value);

    return Number.isInteger(number) && number >= 1
      ? number
      : undefined;
  };

  return (
    <div className="space-y-5 pb-4">
      {/* Assessment header */}
      <section className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.05]">
            <FileText className="h-5 w-5 text-white/75" />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-white">
              {assessment.title ||
                data?.assessment_title ||
                data?.title ||
                'MCQ Assessment'}
            </h3>

            <p className="mt-1 text-xs leading-relaxed text-white/55">
              {assessment.instructions || data?.instructions ||
                'Review every question, option and answer key before making a decision.'}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <div className="rounded-lg border border-white/[0.08] bg-black/30 p-3">
            <p className="text-[10px] text-white/45">Questions</p>
            <p className="mt-1 text-lg font-semibold text-white">
              {questions.length}
            </p>
          </div>

          <div className="rounded-lg border border-white/[0.08] bg-black/30 p-3">
            <p className="text-[10px] text-white/45">Total marks</p>
            <p className="mt-1 text-lg font-semibold text-white">
              {(Number(assessment.marks ?? data?.marks ?? 0) ||
                questions.reduce(
                (sum: number, question: any) =>
                  sum + Number(question.marks || 0),
                0,
              ))}
            </p>
          </div>

          <div className="rounded-lg border border-white/[0.08] bg-black/30 p-3">
            <p className="text-[10px] text-white/45">Per question</p>
            <p className="mt-1 text-lg font-semibold text-white">
              {assessment.marks_per_question ??
                data?.marks_per_question ??
                '—'}
            </p>
          </div>
        </div>
      </section>

      {/* Published assessment lifecycle */}
      {isPublished && (
        <section className="space-y-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <div>
            <h3 className="text-sm font-semibold text-white">
              Assessment delivery and results
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-white/45">
              These actions remain teacher-controlled and use the saved workflow
              returned by the backend.
            </p>
          </div>

          <div className="space-y-2 text-xs text-white/65">
            <p>
              Form:{' '}
              {lifecycleState.responder_url ? (
                <a
                  href={String(lifecycleState.responder_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-white underline"
                >
                  Open published form
                </a>
              ) : (
                'Published'
              )}
            </p>
            <p>Assessment ID: {String(lifecycleState.assessment_id)}</p>
            <p>
              Topic: {String(lifecycleState.topic || data?.topic || 'Not provided')}
            </p>
            <p>
              Publication:{' '}
              {lifecycleState.form_is_published === false
                ? 'Not published'
                : lifecycleStatus || 'Published'}
            </p>
            <p>
              Responses:{' '}
              {lifecycleState.form_accepting_responses === true
                ? 'Accepting responses'
                : lifecycleState.form_accepting_responses === false
                  ? 'Not accepting responses'
                  : 'Provider status unavailable'}
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {lifecycleState.responder_url && (
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard?.writeText(
                      String(lifecycleState.responder_url),
                    );
                  }}
                  className="rounded-lg border border-white/15 px-3 py-2 text-[11px] text-white/80 hover:bg-white/[0.06]"
                >
                  Copy responder URL
                </button>
              )}
            </div>
          </div>


          {isPublished &&
            lifecycleStatus !== 'assessment_sent_to_students' &&
            Number(lifecycleState.student_email_sent || 0) === 0 &&
            onSendAssessmentToStudents && (
              <div className="space-y-3 rounded-xl border border-white/10 bg-black/20 p-3">
                <p className="text-xs leading-relaxed text-white/65">
                  The assessment is published. Send the invitation to students
                  registered for the selected school, class and section.
                </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="block text-xs text-white/70">
              School
              <select
                required
                value={deliverySchoolId}
                onChange={(event) => {
                  const next = event.target.value;
                  setDeliverySchoolId(next);
                  setDeliveryClassLevel(next === 'electro' ? 'Electro' : 'TCO LiveTest');
                  setDeliverySection(next === 'electro' ? '1' : 'LIVE');
                }}
                className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              >
                <option value="electro">Electro</option>
                <option value="TCO_LIVE_TEST">TCO LiveTest</option>
              </select>
            </label>
            <label className="block text-xs text-white/70">
              Class
              <select
                required
                value={deliveryClassLevel}
                onChange={(event) => {
                  const next = event.target.value;
                  setDeliveryClassLevel(next);
                  setDeliverySection(next === 'Electro' ? '1' : 'LIVE');
                }}
                className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              >
                {deliverySchoolId === 'electro' ? (
                  <option value="Electro">Electro</option>
                ) : (
                  <option value="TCO LiveTest">TCO LiveTest</option>
                )}
              </select>
            </label>
            <label className="block text-xs text-white/70">
              Section
              <select
                required
                value={deliverySection}
                onChange={(event) => setDeliverySection(event.target.value)}
                className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              >
                {deliveryClassLevel === 'Electro' ? (
                  <option value="1">Section 1</option>
                ) : (
                  <option value="LIVE">Section LIVE</option>
                )}
              </select>
            </label>
          </div>

                <button
                  type="button"
                  onClick={() => {
                    if (
                      window.confirm(
                        'Send this published assessment to students in the saved school, class and section?'
                      )
                    ) {
                      void onSendAssessmentToStudents({
                      school_id: deliverySchoolId,
                      class_level: deliveryClassLevel,
                      section: deliverySection,
                    });
                    }
                  }}
                  className="w-full rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black hover:bg-white/85"
                >
                  Send to Students
                </button>
              </div>
            )}

         {['assessment_sent_to_students', 'student_email_send_failed', 'no_student_recipients'].includes(lifecycleStatus) && (
            <p className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-white/70">
              Delivery: {String(lifecycleState.student_email_sent || 0)} sent,{' '}
              {String(lifecycleState.student_email_failed || 0)} failed,{' '}
              {String(lifecycleState.student_email_skipped || 0)} skipped,{' '}
              {String(lifecycleState.student_email_total || 0)} recipients.
            </p>
          )}

          {[
            'assessment_form_published',
            'assessment_created_not_sent',
            'assessment_sent_to_students',
            'no_student_recipients',
            'no_responses',
          ].includes(lifecycleStatus) &&
            onEvaluateAssessment && (
              <button
                type="button"
                onClick={() => void onEvaluateAssessment()}
                className="w-full rounded-xl border border-white/15 px-4 py-3 text-xs font-medium text-white/80 hover:bg-white/[0.05]"
              >
                Evaluate student responses
              </button>
            )}

          {lifecycleStatus === 'no_responses' && (
            <p className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-white/70">
              No responses received yet. Submit the published form, then check
              responses again.
            </p>
          )}

          {lifecycleStatus === 'evaluation_completed' && (
            <div className="space-y-2 rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-white/70">
              <p>
                Evaluation completed. Saved results:{' '}
                {String(evaluationResults.length)}
              </p>
              {evaluationResults.map((item: any, index: number) => {
                const evaluation = item.evaluation_result || item.evaluation || {};
                const saved = item.saved_result || {};
                return (
                  <p key={String(saved.result_id || item.response_id || index)}>
                    {String(saved.student_name || evaluation.student_name || 'Student')}:{' '}
                    {String(evaluation.obtained_marks ?? saved.obtained_marks ?? 0)} /{' '}
                    {String(evaluation.total_marks ?? saved.total_marks ?? 0)} (
                    {String(evaluation.percentage ?? saved.percentage ?? 0)}%)
                  </p>
                );
              })}
            </div>
          )}

          {lifecycleStatus === 'evaluation_completed' &&
            hasSavedResults &&
            onSendAssessmentResultEmails && (
              <button
                type="button"
                onClick={() => void onSendAssessmentResultEmails()}
                className="w-full rounded-xl border border-white/15 px-4 py-3 text-xs font-medium text-white/80 hover:bg-white/[0.05]"
              >
                Send saved results by email
              </button>
            )}

          {lifecycleState.result_email_status && (
            <p className="text-xs text-white/60">
              Result email status: {String(lifecycleState.result_email_status)}
              {resultEmailSummary.total !== undefined
                ? ` (${String(resultEmailSummary.sent || 0)} sent, ${String(resultEmailSummary.failed || 0)} failed)`
                : ''}
            </p>
          )}
        </section>
      )}

      {/* Automated review status */}
      <section className="rounded-xl border border-white/15 bg-white/[0.04] p-4">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-gray-300" />

          <div className="min-w-0">
            <h4 className="text-xs font-semibold text-gray-200">
              {reviewStatus === 'failed'
                ? 'Automated review did not pass'
                : reviewStatus === 'passed'
                  ? 'Automated review passed'
                  : 'Assessment review status'}
            </h4>

            <p className="mt-1 text-xs leading-relaxed text-white/65">
              {reviewStatus === 'failed'
                ? 'Please manually check the answer key. The current key below is the model-provided key and may contain errors.'
                : reviewStatus === 'passed'
                  ? 'Please review the assessment before final teacher approval.'
                  : `Current status: ${reviewStatus}`}
            </p>

            {(manualReviewRequired || automatedReviewFailed) && (
              <p className="mt-2 text-[11px] font-medium text-gray-200/90">
                Manual teacher review is required.
              </p>
            )}

            {isPending && (
              <p className="mt-1 text-[11px] text-white/45">
                Teacher decision: pending
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Questions */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Questions and answer key
          </h3>

          <span className="text-[10px] text-white/40">
            {questions.length} questions
          </span>
        </div>

        {questions.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 text-center">
            <FileText className="mx-auto h-6 w-6 text-white/30" />
            <p className="mt-2 text-xs text-white/55">
              No questions were returned by the backend.
            </p>
          </div>
        ) : (
          questions.map((question: any, index: number) => {
            const correctOption = getCorrectOption(question);
            const options: string[] = Array.isArray(question.options)
              ? question.options
              : [];

            return (
              <article
                key={question.question_number ?? index}
                className="rounded-xl border border-white/10 bg-white/[0.025] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <h4 className="text-xs font-semibold leading-relaxed text-white/90">
                    Q{question.question_number ?? index + 1}.{' '}
                    {question.question || 'Question text unavailable'}
                  </h4>

                  <span className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-[10px] text-white/55">
                    {question.marks ?? 0} marks
                  </span>
                </div>

                <div className="mt-3 space-y-2">
                  {options.map((option: string, optionIndex: number) => {
                    const optionNumber = optionIndex + 1;
                    const isModelKey = optionNumber === correctOption;

                    return (
                      <div
                        key={`${question.question_number}-${optionIndex}`}
                        className={`flex items-start gap-2.5 rounded-lg border p-2.5 ${
                          isModelKey
                            ? 'border-white/15 bg-white/[0.04]'
                            : 'border-white/[0.06] bg-black/20'
                        }`}
                      >
                        {isModelKey ? (
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-300" />
                        ) : (
                          <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-white/25" />
                        )}

                        <span className="text-xs leading-relaxed text-white/75">
                          <span className="mr-1.5 text-white/40">
                            {String.fromCharCode(64 + optionNumber)}.
                          </span>
                          {option}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {correctOption !== undefined && (
                  <p className="mt-2 text-[10px] text-gray-200/80">
                    Model-provided answer: Option{' '}
                    {String.fromCharCode(64 + correctOption)}
                  </p>
                )}

                {question.explanation && (
                  <div className="mt-3 rounded-lg bg-white/[0.025] p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-white/40">
                      Explanation
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-white/60">
                      {question.explanation}
                    </p>
                  </div>
                )}
              </article>
            );
          })
        )}
      </section>

      {/* Reviewer feedback */}
      {reviewFeedback && (
        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <h3 className="text-xs font-semibold text-white">
            Automated review feedback
          </h3>

          <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-white/65">
            {reviewFeedback}
          </pre>
        </section>
      )}

      {/* Marking scheme */}
      {markingScheme.length > 0 && (
        <details className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <summary className="cursor-pointer text-xs font-semibold text-white/80">
            View marking scheme
          </summary>

          <div className="mt-3 space-y-2">
            {markingScheme.map((item: any, index: number) => (
              <div
                key={item.question_number ?? index}
                className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2 text-xs"
              >
                <span className="text-white/65">
                  Question {item.question_number ?? index + 1}
                </span>
                <span className="text-white/85">
                  {item.marks} marks
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Teacher decisions */}
      <section className="space-y-3 border-t border-white/10 pt-4">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Teacher decision
          </h3>

          <p className="mt-1 text-xs leading-relaxed text-white/45">
            Confirm the answer key yourself. Your approval records the
            teacher's decision; it does not change the automated review result.
          </p>
        </div>

        {showFeedback && (
          <textarea
            value={teacherFeedback}
            onChange={(event) => setTeacherFeedback(event.target.value)}
            rows={3}
            placeholder="Describe the questions or answers that need to change..."
            className="w-full resize-y rounded-lg border border-white/10 bg-black px-3 py-2.5 text-xs leading-relaxed text-white outline-none placeholder:text-white/25 focus:border-white/30"
          />
        )}

        {!isPublished && (
<div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() =>
              onApprove('Manually reviewed by teacher.')
            }
            className="flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85"
          >
            <CheckCircle2 className="h-4 w-4" />
            Approve after manual review
          </button>

          {!showFeedback ? (
            <button
              type="button"
              onClick={() => setShowFeedback(true)}
              className="flex items-center justify-center gap-2 rounded-xl border border-white/15 px-4 py-3 text-xs font-medium text-white/80 transition-colors hover:bg-white/[0.05]"
            >
              <Send className="h-3.5 w-3.5" />
              Ask for changes
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  const feedback = teacherFeedback.trim();

                  if (!feedback) return;

                  onRequestRevision(feedback);
                }}
                disabled={!teacherFeedback.trim()}
                className="flex-1 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40"
              >
                Submit changes
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowFeedback(false);
                  setTeacherFeedback('');
                  onReject();
                }}
                className="rounded-xl border border-white/10 px-3 py-3 text-xs text-white/70 hover:bg-white/[0.05]"
              >
                Reject
              </button>
            </div>
          )}
        </div>
        )}
      </section>
    </div>
  );
};

export const ContextPanel: React.FC<ContextPanelProps> = ({
  isOpen,
  onClose,
  reviewType,
  reviewId,
  lifecycle,
  onApprove,
  onReject,
  onRequestRevision,
  onSendAssessmentToStudents,
  onPreviewAssessmentRecipients,
  onEvaluateAssessment,
  onSendAssessmentResultEmails,
  isMobile = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !reviewType || !reviewId) {
      setData(null);
      setLoadError(null);
      return;
    }

    let cancelled = false;

    setLoading(true);
    setData(null);
    setLoadError(null);

    api
      .getReviewDetails(reviewType, reviewId)
      .then((result) => {
        if (cancelled) return;

        if (!result) {
          setLoadError(
            'No assessment was found for this request ID. Send the workspace request again and reopen the review panel.',
          );
          return;
        }

        setData(result);
      })
      .catch((error) => {
        if (cancelled) return;

        console.error('Failed to load review details:', error);
        setLoadError(
          error instanceof Error
            ? error.message
            : 'Unable to load review details from FastAPI.',
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, reviewType, reviewId]);

  const runLifecycleAction = async (
    action?: () => Promise<AssessmentLifecycleData>,
  ): Promise<AssessmentLifecycleData> => {
    if (!action) {
      throw new Error('This assessment lifecycle action is unavailable.');
    }
    const result = await action();
    setData((previous: any) => ({
      ...(previous || {}),
      ...result,
    }));
    return result;
  };

  if (!isOpen) return null;

  const type = String(reviewType || '');

  const getTitle = () => {
    switch (type) {
      case 'assessment':
        return 'MCQ Assessment Review';
      case 'answer_sheet_checking':
        return 'Answer Sheet Review (STU047)';
      case 'question_paper_generation':
        return 'Question Paper Review';
      case 'marksheet':
        return 'Marksheet Compilation Preview';
      case 'attendance':
        return 'Classroom Attendance Verification';
      case 'ppt_generation':
        return 'Lecture Presentation Slides';
      case 'analytics':
        return 'Diagnostic Class Analytics';
      default:
        return 'Artifact Review';
    }
  };

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: '100%', opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 26, stiffness: 240 }}
        className={`fixed bottom-0 right-0 top-0 z-40 flex flex-col border-l border-white/10 bg-black shadow-2xl lg:relative ${
          isMobile
            ? 'h-full w-full'
            : isExpanded
              ? 'w-full lg:w-[720px]'
              : 'w-full lg:w-[520px]'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 bg-[#080808] p-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.05] text-white/80">
              <Eye className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold text-white">
                {getTitle()}
              </h2>

              <div className="mt-1 flex items-center gap-1.5 text-[10px] text-white/45">
                <span className="h-1.5 w-1.5 rounded-full bg-white/70" />
                <span>Teacher review checkpoint</span>
              </div>
            </div>
          </div>

          <div className="ml-2 flex shrink-0 items-center gap-1">
            {!isMobile && (
              <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="rounded-lg p-2 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
                title={isExpanded ? 'Collapse panel' : 'Expand panel'}
                aria-label={isExpanded ? 'Collapse panel' : 'Expand panel'}
              >
                {isExpanded ? (
                  <Minimize2 className="h-4 w-4" />
                ) : (
                  <Maximize2 className="h-4 w-4" />
                )}
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
              title="Close panel"
              aria-label="Close panel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {loading ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3">
              <Loader2 className="h-7 w-7 animate-spin text-white/70" />
              <p className="text-xs text-white/45">
                Loading review details from TCO...
              </p>
            </div>
          ) : loadError ? (
            <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <AlertTriangle className="mb-3 h-6 w-6 text-gray-300" />
              <h3 className="text-sm font-medium text-white/80">
                Unable to load review
              </h3>
              <p className="mt-2 max-w-sm break-words text-xs leading-relaxed text-white/45">
                {loadError}
              </p>
              <p className="mt-2 text-[10px] text-white/35">
                Request ID: {reviewId || 'Not available'}
              </p>
            </div>
          ) : !data ? (
            <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <Eye className="mb-3 h-5 w-5 text-white/40" />
              <h3 className="text-sm font-medium text-white/80">
                No review data available
              </h3>
              <p className="mt-1 max-w-xs text-xs leading-relaxed text-white/40">
                Send an assessment request in the Workspace, then open its review panel.
              </p>
            </div>
          ) : (
            <>
              {type === 'assessment' && (
                <AssessmentReviewView
                  data={data}
                  onApprove={async (notes) => {
                    await onApprove(notes);
                    if (reviewType && reviewId) {
                      const refreshed = await api.getReviewDetails(
                        reviewType,
                        reviewId,
                      );
                      if (refreshed) setData(refreshed);
                    }
                  }}
                  onReject={onReject}
                  onRequestRevision={onRequestRevision}
                  lifecycle={lifecycle}
                  onSendAssessmentToStudents={(target) => runLifecycleAction(() => onSendAssessmentToStudents(target))}
                  onPreviewAssessmentRecipients={() =>
                    runLifecycleAction(onPreviewAssessmentRecipients)
                  }
                  onEvaluateAssessment={() =>
                    runLifecycleAction(onEvaluateAssessment)
                  }
                  onSendAssessmentResultEmails={() =>
                    runLifecycleAction(onSendAssessmentResultEmails)
                  }
                />
              )}

              {type === 'answer_sheet_checking' && (
                <AnswerSheetReview
                  data={data}
                  onApprove={onApprove}
                  onReject={onReject}
                  onRequestRevision={onRequestRevision}
                />
              )}

              {type === 'question_paper_generation' && (
                <QuestionPaperReview
                  data={data}
                  onApprove={onApprove}
                  onRequestRevision={onRequestRevision}
                />
              )}

              {type === 'marksheet' && (
                <MarksheetPreview
                  data={data}
                  onApprove={onApprove}
                />
              )}

              {type === 'attendance' && (
                <AttendancePreview
                  data={data}
                  onApprove={onApprove}
                />
              )}

              {type === 'ppt_generation' && (
                <PPTPreview
                  data={data}
                  onApprove={onApprove}
                  onRequestRevision={onRequestRevision}
                />
              )}

              {type === 'analytics' && (
                <AnalyticsPreview data={data} />
              )}

              {![
                'assessment',
                'answer_sheet_checking',
                'question_paper_generation',
                'marksheet',
                'attendance',
                'ppt_generation',
                'analytics',
              ].includes(type) && (
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-white/60">
                    No renderer is configured for review type: {type}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  );
};
