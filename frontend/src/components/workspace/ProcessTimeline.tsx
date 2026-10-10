
import React from 'react';
import { motion } from 'framer-motion';
import type { WorkflowProgress, WorkflowStep } from '../../types/workflow';
import {
  CheckCircle2,
  Loader2,
  Clock,
  Cpu,
  Sparkles,
  AlertTriangle,
  Circle,
} from 'lucide-react';

interface ProcessTimelineProps {
  progress: WorkflowProgress;
}

type TimelineStatus = 'completed' | 'active' | 'pending' | 'failed';

interface DisplayStep {
  id: string;
  agent: string;
  label: string;
  description: string;
  status: TimelineStatus;
}

const completedAssessmentStates = new Set([
  'assessment_ready_for_review',
  'assessment_ready_for_teacher',
  'assessment_approved',
]);

function buildAssessmentTimeline(
  progress: WorkflowProgress,
): DisplayStep[] {
  const state = String(progress.state || '').toLowerCase();
  const summary = (progress as any).resultSummary || {};
  const reviewStatus = String(
    summary.review_status ||
      summary.assessment_review_status ||
      '',
  ).toLowerCase();

  const draftGenerated = completedAssessmentStates.has(state);
  const reviewFailed =
    reviewStatus === 'failed' ||
    state === 'assessment_review_failed';

  const reviewPassed = reviewStatus === 'passed';
  const teacherApproved = state === 'assessment_approved';

  return [
    {
      id: 'master-agent',
      agent: 'TCO Master Agent',
      label: 'Understand teacher request',
      description:
        'The workspace request was received and processed by the TCO workflow.',
      status: 'completed',
    },
    {
      id: 'assessment-agent',
      agent: 'Assessment Agent',
      label: 'Generate assessment draft',
      description: draftGenerated
        ? 'The generated assessment is available for teacher review.'
        : 'The assessment generation result has not been confirmed yet.',
      status: draftGenerated ? 'completed' : 'pending',
    },
    {
      id: 'assessment-review-agent',
      agent: 'Assessment Review Agent',
      label: reviewFailed
        ? 'Automated review needs manual verification'
        : 'Review generated assessment',
      description: reviewFailed
        ? 'Automated review did not pass. The draft is retained for manual teacher review.'
        : reviewPassed
          ? 'The assessment passed the automated review.'
          : state === 'assessment_ready_for_review'
            ? 'The assessment is waiting for its review result.'
            : 'The API has not supplied a detailed review result for this step.',
      status: reviewFailed
        ? 'failed'
        : reviewPassed
          ? 'completed'
          : state === 'assessment_ready_for_review'
            ? 'active'
            : 'pending',
    },
    {
      id: 'teacher-review',
      agent: 'Teacher',
      label: teacherApproved
        ? 'Teacher approved assessment'
        : 'Teacher review and decision',
      description: teacherApproved
        ? 'The teacher decision has been recorded.'
        : 'Inspect the questions and answer key before approving or requesting changes.',
      status: teacherApproved
        ? 'completed'
        : draftGenerated
          ? 'active'
          : 'pending',
    },
  ];
}

function mapBackendStep(
  step: WorkflowStep,
  index: number,
): DisplayStep {
  const rawStatus = String(step.status || 'pending').toLowerCase();

  let status: TimelineStatus = 'pending';

  if (['completed', 'done', 'success'].includes(rawStatus)) {
    status = 'completed';
  } else if (['active', 'running', 'in_progress'].includes(rawStatus)) {
    status = 'active';
  } else if (['failed', 'error'].includes(rawStatus)) {
    status = 'failed';
  }

  return {
    id: String(step.id || `step-${index + 1}`),
    agent: String(step.agent || 'TCO Agent'),
    label: String(step.label || `Step ${index + 1}`),
    description: String(step.description || ''),
    status,
  };
}

function statusLabel(status: TimelineStatus): string {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'active':
      return 'In progress';
    case 'failed':
      return 'Needs attention';
    default:
      return 'Pending';
  }
}

export const ProcessTimeline: React.FC<ProcessTimelineProps> = ({
  progress,
}) => {
  const state = String(progress.state || 'running').toLowerCase();

  const hasBackendSteps =
    Array.isArray(progress.steps) && progress.steps.length > 0;

  const isAssessment =
    String(progress.type).toLowerCase().includes('assessment') ||
    state.startsWith('assessment_') ||
    Boolean(
      (progress as any).resultSummary?.review_status ||
      (progress as any).resultSummary?.assessment_review_status,
    );

  const steps: DisplayStep[] = hasBackendSteps
    ? progress.steps.map(mapBackendStep)
    : isAssessment
      ? buildAssessmentTimeline(progress)
      : [];

  const showReviewWarning =
    state === 'assessment_review_failed' ||
    String((progress as any).resultSummary?.review_status || '')
      .toLowerCase() === 'failed';

  const formattedState = state.replace(/_/g, ' ');

  return (
    <section
      className="my-3 space-y-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-4"
      aria-label="TCO workflow process"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-white/[0.08] pb-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/75">
            <Cpu className="h-4 w-4" />
          </div>

          <div className="min-w-0">
            <p className="truncate text-xs font-semibold text-white">
              {progress.activeAgent || 'TCO Workflow'}
            </p>

            <p className="mt-0.5 text-[10px] uppercase text-white/40">
              {String(progress.type).replace(/_/g, ' ')}
            </p>
          </div>
        </div>

        <div className="flex max-w-[55%] shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-medium text-white/70">
          {state === 'running' ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>In progress</span>
            </>
          ) : state === 'assessment_approved' ||
            state === 'approved' ? (
            <>
              <CheckCircle2 className="h-3 w-3" />
              <span>Approved</span>
            </>
          ) : showReviewWarning ? (
            <>
              <AlertTriangle className="h-3 w-3 text-gray-300" />
              <span>Manual review</span>
            </>
          ) : (
            <span className="truncate">{formattedState}</span>
          )}
        </div>
      </div>

      {/* Timeline */}
      {steps.length > 0 ? (
        <div className="space-y-2 pt-1">
          {steps.map((step, index) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.06, duration: 0.2 }}
              className={`flex items-start gap-3 rounded-lg border p-3 ${
                step.status === 'active'
                  ? 'border-white/20 bg-white/[0.06]'
                  : step.status === 'failed'
                    ? 'border-white/10 bg-white/[0.03]'
                    : step.status === 'completed'
                      ? 'border-white/[0.06] bg-white/[0.02]'
                      : 'border-transparent bg-transparent'
              }`}
            >
              <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
                {step.status === 'completed' ? (
                  <CheckCircle2 className="h-4 w-4 text-white/85" />
                ) : step.status === 'active' ? (
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                ) : step.status === 'failed' ? (
                  <AlertTriangle className="h-4 w-4 text-gray-300" />
                ) : (
                  <Circle className="h-4 w-4 text-white/25" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
                  <span className="text-xs font-medium text-white/85">
                    {step.label}
                  </span>

                  <span className="text-[10px] text-white/40">
                    {step.agent}
                  </span>
                </div>

                <p className="mt-1 text-[11px] leading-relaxed text-white/50">
                  {step.description}
                </p>

                <p
                  className={`mt-1 text-[10px] ${
                    step.status === 'failed'
                      ? 'text-gray-200/80'
                      : 'text-white/35'
                  }`}
                >
                  {statusLabel(step.status)}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3">
          <p className="text-xs font-medium text-white/70">
            Workflow status received
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-white/45">
            The backend has not provided detailed process steps for this
            workflow yet. Only the reported status is shown.
          </p>
        </div>
      )}

      {/* Review warning */}
      {showReviewWarning && (
        <div className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/[0.04] p-3">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-300" />
          <p className="text-[11px] leading-relaxed text-gray-200/80">
            Automated review did not pass. The teacher can inspect the draft
            manually; this does not mean the answer key is verified.
          </p>
        </div>
      )}
    </section>
  );
};
