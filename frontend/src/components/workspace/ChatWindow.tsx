import React, { useRef, useEffect, useState } from 'react';
import { Conversation, QuickActionItem } from '../../types/chat';
import { WorkflowType } from '../../types/workflow';
import type { AssessmentLifecycleData } from '../../types/workflow';
import type { ClassroomCourse, MessageAttachmentInput, WorkspaceAgentMode, WorkspaceSourceMode } from '../../services/api';
import { api } from '../../services/api';
import { ApiError, apiRequest, errorMessage, getApiBaseUrl } from '../../services/http';
import type { SourceCandidate } from '../../types/chat';
import { ChatMessageItem } from './ChatMessageItem';
import { MessageComposer } from './MessageComposer';
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
  ChevronDown,
  Brain,
} from 'lucide-react';

interface ChatWindowProps {
  conversation: Conversation | null;
  isProcessing: boolean;
  onSendMessage: (
    message: string,
    attachments?: MessageAttachmentInput[],
    sourceMode?: WorkspaceSourceMode,
    agentMode?: WorkspaceAgentMode
  ) => void;
  onClarification: (optionId: string, customValue?: string) => void;
  onApprove: (notes?: string) => void;
  onRequestRevision: (instructions: string) => void;
  onOpenReview: (type: WorkflowType, id?: string) => void;
  onStopProcessing: () => void;
  isReviewPanelOpen: boolean;
  onToggleReviewPanel: () => void;
  onOpenMobileSidebar?: () => void;
  onApproveWebSource: (workflowId: string, candidate: SourceCandidate) => void;
  assessmentLifecycle: AssessmentLifecycleData | null;
  onSendAssessmentToStudents: (target?: {
    school_id: string;
    class_level: string;
    section: string;
  }) => Promise<AssessmentLifecycleData>;
  onEvaluateAssessment: () => Promise<AssessmentLifecycleData>;
  onSendAssessmentResultEmails: () => Promise<AssessmentLifecycleData>;
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

const ASSESSMENT_SOURCE_MODES: {
  value: WorkspaceSourceMode;
  label: string;
  description: string;
}[] = [
  {
    value: 'general_knowledge',
    label: 'AI General Knowledge',
    description: 'Generate using general AI knowledge.',
  },
  {
    value: 'teacher_file',
    label: 'Upload Material',
    description: 'Use a teacher-provided PDF, PPTX, TXT or MD.',
  },
  {
    value: 'classroom',
    label: 'Google Classroom',
    description: 'Use material from a Classroom course.',
  },
  {
    value: 'web_search',
    label: 'Web Search',
    description: 'Find web sources for teacher approval.',
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
  onApproveWebSource,
  assessmentLifecycle,
  onSendAssessmentToStudents,
  onEvaluateAssessment,
  onSendAssessmentResultEmails,
}) => {

  // Dedicated upload flow for the existing Copy Checking FastAPI endpoint.
  const [copyUploadOpen, setCopyUploadOpen] = useState(false);
  const [copyQuestionPaper, setCopyQuestionPaper] = useState<File | null>(null);
  const [copyMarkingScheme, setCopyMarkingScheme] = useState<File | null>(null);
  const [copyAnswerSheet, setCopyAnswerSheet] = useState<File | null>(null);
  const [copyPageCount, setCopyPageCount] = useState('2');

  // Auto-load the backend page ceiling so multi-page PDFs are not
  // accidentally graded with the old two-page demo default.
  useEffect(() => {
    let active = true;

    const loadCopyPageLimit = async () => {
      try {
        const apiRoot = getApiBaseUrl().replace(/\/api\/v1\/?$/i, '');
        const response = await fetch(`${apiRoot}/openapi.json`);
        if (!response.ok) return;

        const schema = await response.json();
        const operation =
          schema.paths?.['/api/v1/copy-checking/grade']?.post ??
          schema.paths?.['/copy-checking/grade']?.post;

        const parameter = operation?.parameters?.find(
          (item: { name?: string }) => item.name === 'pages',
        );
        const maximum = Number(parameter?.schema?.maximum);

        if (active && Number.isFinite(maximum) && maximum > 0) {
          setCopyPageCount(String(maximum));
        }
      } catch {
        // Keep the manually editable page count if OpenAPI cannot be read.
      }
    };

    void loadCopyPageLimit();
    return () => {
      active = false;
    };
  }, []);


  const [copyUploadBusy, setCopyUploadBusy] = useState(false);
  const [copyUploadError, setCopyUploadError] = useState<string | null>(null);
  const [copyUploadResult, setCopyUploadResult] = useState<unknown>(null);

  const [copyReviewJobId, setCopyReviewJobId] = useState<string | null>(null);
  const [copyReviewRecord, setCopyReviewRecord] = useState<Record<string, unknown> | null>(null);
  const [copyReviewAnswers, setCopyReviewAnswers] = useState<Array<{ question_no: number; answer: string }>>([]);
  const [copyMissingQuestions, setCopyMissingQuestions] = useState<number[]>([]);
  const [copyConfirmedBlankQuestions, setCopyConfirmedBlankQuestions] = useState<number[]>([]);
  const [copyTeacherName, setCopyTeacherName] = useState('');
  const [copyAnswersReviewed, setCopyAnswersReviewed] = useState(false);
  const [copyMarkingSchemeLocked, setCopyMarkingSchemeLocked] = useState(false);
  const [copyReviewBusy, setCopyReviewBusy] = useState(false);
  const [copyReviewError, setCopyReviewError] = useState<string | null>(null);
  const [copyGradeResult, setCopyGradeResult] = useState<Record<string, unknown> | null>(null);
  const [copyCheckedCopyUrl, setCopyCheckedCopyUrl] = useState<string | null>(null);

  const [copyResultApproveBusy, setCopyResultApproveBusy] = useState(false);
  const [copyResultApproveError, setCopyResultApproveError] = useState<string | null>(null);

  const approveCopyCheckingResult = async () => {
    if (!copyGradeResult) return;

    const jobId = String(copyGradeResult.job_id ?? '').trim();
    if (!jobId) {
      setCopyResultApproveError('The grading response did not include a job ID. Please run Copy Checking again.');
      return;
    }

    setCopyResultApproveBusy(true);
    setCopyResultApproveError(null);

    try {
      const studentNumber = String(
        copyGradeResult.student_number ??
        copyAnswerSheet?.name?.replace(/\.[^.]+$/, '') ??
        'student'
      );

      const saved = await apiRequest<Record<string, unknown>>(
        `/copy-checking/jobs/${encodeURIComponent(jobId)}/approve-result`,
        {
          method: 'POST',
          body: JSON.stringify({
            student_number: studentNumber,
            grading_result: copyGradeResult,
          }),
        },
      );

      setCopyGradeResult((previous) =>
        previous ? { ...previous, ...saved, database_persisted: saved.database_persisted === true } : previous
      );
    } catch (error) {
      setCopyResultApproveError(errorMessage(error));
    } finally {
      setCopyResultApproveBusy(false);
    }
  };


  const resolveCopyCheckedCopyUrl = (route: unknown): string | null => {
    if (typeof route !== 'string' || !route.trim()) return null;
    if (/^https?:\/\//i.test(route)) return route;

    const base = getApiBaseUrl().replace(/\/$/, '');
    if (route.startsWith('/api/v1/')) {
      return `${base.replace(/\/api\/v1$/i, '')}${route}`;
    }
    return `${base}${route.startsWith('/') ? '' : '/'}${route}`;
  };

  const loadCopyCheckingReview = async (jobId: string) => {
    const review = await apiRequest<Record<string, unknown>>(
      `/copy-checking/jobs/${encodeURIComponent(jobId)}/review`,
    );

    setCopyReviewRecord(review);

    const submission =
      review.aggregated_submission && typeof review.aggregated_submission === 'object'
        ? review.aggregated_submission as Record<string, unknown>
        : {};

    const rawAnswers = Array.isArray(submission.answers) ? submission.answers : [];
    setCopyReviewAnswers(rawAnswers.map((raw, index) => {
      const item = raw && typeof raw === 'object'
        ? raw as Record<string, unknown>
        : {};
      const number = Number(item.question_no ?? item.question_number ?? index + 1);
      const rawAnswer =
        item.answer ??
        item.extracted_answer ??
        item.answer_text ??
        item.student_answer ??
        item.transcription ??
        item.text ??
        item.response ??
        '';
      return {
        question_no: Number.isFinite(number) ? number : index + 1,
        answer: typeof rawAnswer === 'string' ? rawAnswer : String(rawAnswer ?? ''),
      };
    }));

    const missing = Array.isArray(submission.missing_questions)
      ? submission.missing_questions.map(Number).filter(Number.isFinite)
      : [];
    setCopyMissingQuestions(missing);
    setCopyConfirmedBlankQuestions([]);
    setCopyAnswersReviewed(false);
    setCopyMarkingSchemeLocked(false);
    setCopyReviewError(null);
  };

  const approveCopyCheckingAndGrade = async () => {
    if (!copyReviewJobId) return;

    if (!copyTeacherName.trim()) {
      setCopyReviewError('Enter the teacher name before approving grading.');
      return;
    }
    if (!copyAnswersReviewed || !copyMarkingSchemeLocked) {
      setCopyReviewError('Confirm that all extracted answers were reviewed and the marking scheme is locked.');
      return;
    }

    const answeredNumbers = new Set(
      copyReviewAnswers.filter((item) => item.answer.trim()).map((item) => item.question_no),
    );
    const unconfirmedMissing = copyMissingQuestions.filter(
      (number) =>
        !answeredNumbers.has(number) &&
        !copyConfirmedBlankQuestions.includes(number),
    );
    if (unconfirmedMissing.length) {
      setCopyReviewError(
        `Review question(s) ${unconfirmedMissing.join(', ')}: enter the extracted answer or confirm it is blank.`,
      );
      return;
    }

    setCopyReviewBusy(true);
    setCopyReviewError(null);

    try {
      const uniqueAnswers = new Map<number, string>();
      for (const item of copyReviewAnswers) {
        if (item.answer.trim()) uniqueAnswers.set(item.question_no, item.answer.trim());
      }

      if (uniqueAnswers.size) {
        await apiRequest(
          `/copy-checking/jobs/${encodeURIComponent(copyReviewJobId)}/review/answers`,
          {
            method: 'PUT',
            body: JSON.stringify({
              answers: Array.from(uniqueAnswers, ([question_no, answer]) => ({
                question_no,
                answer,
              })),
            }),
          },
        );
      }

      const graded = await apiRequest<Record<string, unknown>>(
        `/copy-checking/jobs/${encodeURIComponent(copyReviewJobId)}/approve-and-grade`,
        {
          method: 'POST',
          body: JSON.stringify({
            teacher_name: copyTeacherName.trim(),
            confirm_all_answers_reviewed: true,
            confirm_marking_scheme_locked: true,
            confirmed_blank_questions: copyConfirmedBlankQuestions,
          }),
        },
      );

      setCopyGradeResult(graded);
      setCopyCheckedCopyUrl(resolveCopyCheckedCopyUrl(graded.checked_copy_url));
      setCopyReviewError(null);
    } catch (error) {
      setCopyReviewError(errorMessage(error));
    } finally {
      setCopyReviewBusy(false);
    }
  };



  const submitCopyCheckingUpload = async () => {
    setCopyUploadError(null);
    setCopyUploadResult(null);

    if (!copyQuestionPaper || !copyMarkingScheme || !copyAnswerSheet) {
      setCopyUploadError(
        'Please select the question paper, marking scheme/answer key, and student answer-sheet PDF.'
      );
      return;
    }

    if (!copyQuestionPaper.name.toLowerCase().endsWith('.txt')) {
      setCopyUploadError('Question Paper must be a .txt file.');
      return;
    }

    if (!copyMarkingScheme.name.toLowerCase().endsWith('.txt')) {
      setCopyUploadError('Marking Scheme / Answer Key must be a .txt file.');
      return;
    }

    if (!copyAnswerSheet.name.toLowerCase().endsWith('.pdf')) {
      setCopyUploadError('Student Answer Sheet must be a PDF.');
      return;
    }

    const pages = Number(copyPageCount);
    if (!Number.isInteger(pages) || pages < 1) {
      setCopyUploadError('Enter a valid positive page count.');
      return;
    }

    const form = new FormData();
    form.append('question_paper', copyQuestionPaper, copyQuestionPaper.name);
    form.append('marking_scheme', copyMarkingScheme, copyMarkingScheme.name);
    form.append('answer_copy', copyAnswerSheet, copyAnswerSheet.name);

    setCopyUploadOpen(false);
    setCopyReviewJobId(null);
    setCopyReviewRecord(null);
    setCopyReviewAnswers([]);
    setCopyMissingQuestions([]);
    setCopyConfirmedBlankQuestions([]);
    setCopyReviewError(null);
    setCopyGradeResult(null);
    setCopyCheckedCopyUrl(null);
    setCopyUploadResult(null);
    setCopyUploadBusy(true);

    try {
      const result = await apiRequest<unknown>(
        `/copy-checking/grade?pages=${encodeURIComponent(String(pages))}`,
        {
          method: 'POST',
          body: form,
        },
      );
      setCopyUploadResult(result);
      if (result && typeof result === 'object') {
        const resultRecord = result as Record<string, unknown>;
        if (resultRecord.status === 'success') {
          setCopyGradeResult(resultRecord);
          setCopyCheckedCopyUrl(resolveCopyCheckedCopyUrl(resultRecord.checked_copy_url));
        }
      }
    } catch (error) {
      const payload =
        error instanceof ApiError &&
        error.detail &&
        typeof error.detail === 'object'
          ? error.detail as Record<string, unknown>
          : null;

      if (
        error instanceof ApiError &&
        error.status === 409 &&
        payload?.status === 'review_required'
      ) {
        const detail =
          typeof payload.detail === 'string'
            ? payload.detail
            : typeof payload.message === 'string'
              ? payload.message
              : 'The backend requires complete answer-sheet processing before grading.';
        setCopyReviewJobId(null);
        setCopyReviewRecord(null);
        setCopyReviewError(
          `${detail} No grade was returned. Check that the page limit covers the entire PDF, then upload again.`
        );
      } else {
        setCopyReviewJobId(null);
        setCopyReviewRecord(null);
        setCopyUploadOpen(true);
        setCopyUploadError(errorMessage(error));
      }
    } finally {
      setCopyUploadBusy(false);
    }
  };

  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeAgentMode, setActiveAgentMode] =
    useState<WorkspaceAgentMode>('assessment');
  const [agentMenuOpen, setAgentMenuOpen] = useState(false);
  const [assessmentSourceMenuOpen, setAssessmentSourceMenuOpen] =
    useState(false);
  const [selectedSourceMode, setSelectedSourceMode] =
    useState<WorkspaceSourceMode | null>(null);
  const [classroomCourses, setClassroomCourses] = useState<ClassroomCourse[]>([]);
  const [classroomCourseId, setClassroomCourseId] = useState('');
  const [classroomCourseError, setClassroomCourseError] = useState<string | null>(null);
  const [loadingClassroomCourses, setLoadingClassroomCourses] = useState(false);

  const activeAgentLabel =
    activeAgentMode === 'analytics'
      ? 'Analytics Agent'
      : activeAgentMode === 'copy_checking'
        ? 'Copy Checking Agent'
        : 'Assessment Agent';

  // Auto-scroll to bottom as messages stream in
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation?.messages, isProcessing]);

  // Get the latest message's active clarification or approval
  const lastMsg =
    conversation?.messages[conversation.messages.length - 1];
  const teacherRequests = (conversation?.messages || [])
    .filter((message) => message.sender === 'teacher')
    .map((message) => message.content.trim())
    .filter(Boolean);
  const latestTeacherRequest = teacherRequests.length
    ? (() => {
        const latest = teacherRequests[teacherRequests.length - 1];
        const earlier = teacherRequests
          .slice(0, -1)
          .filter((request) => !latest.includes(request));
        return [...earlier, latest].join('\n\n');
      })()
    : '';

  useEffect(() => {
    if (
      activeAgentMode !== 'assessment' ||
      !lastMsg ||
      lastMsg.sender !== 'tco' ||
      lastMsg.workflowProgress?.state !== 'waiting_for_source_selection' ||
      lastMsg.clarification ||
      selectedSourceMode
    ) {
      return;
    }

    setAssessmentSourceMenuOpen(true);
  }, [activeAgentMode, lastMsg, selectedSourceMode]);

  useEffect(() => {
    if (
      selectedSourceMode &&
      lastMsg?.sender === 'tco' &&
      lastMsg.workflowProgress?.state !== 'waiting_for_source_selection'
    ) {
      setSelectedSourceMode(null);
    }
  }, [lastMsg, selectedSourceMode]);

  const activeClarification = lastMsg?.clarification;

  const activeApproval =
    lastMsg?.approval ||
    (lastMsg?.workflowProgress?.approval
      ? lastMsg.workflowProgress.approval
      : undefined);

  // After approval publishes a real assessment, replace the old checkpoint
  // with the assessment lifecycle actions in this same chat action area.
  const isPublishedAssessment = Boolean(
    assessmentLifecycle?.assessment_id != null &&
    assessmentLifecycle?.form_id &&
    assessmentLifecycle?.responder_url
  );

  const assessmentStatus = String(assessmentLifecycle?.status ?? '').toLowerCase();
  const evaluationStatus = String(assessmentLifecycle?.evaluation_status ?? '').toLowerCase();

  const evaluationReady =
    ['completed', 'complete', 'evaluation_completed', 'results_saved', 'saved'].includes(
      evaluationStatus
    ) ||
    ['evaluation_completed', 'results_saved', 'results_ready', 'result_emails_sent'].includes(
      assessmentStatus
    ) ||
    (Array.isArray(assessmentLifecycle?.evaluation_results) &&
      assessmentLifecycle.evaluation_results.length > 0) ||
    Number(assessmentLifecycle?.evaluation_summary?.evaluated ?? 0) > 0;

  const studentInvitationsSent =
    ['assessment_sent_to_students', 'students_notified'].includes(assessmentStatus) ||
    Number(assessmentLifecycle?.student_email_sent ?? 0) > 0;

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
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setAgentMenuOpen((open) => !open);
                setAssessmentSourceMenuOpen(false);
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/[0.05] px-3 py-2 text-xs font-medium text-white/85 transition-colors hover:bg-white/10"
              aria-haspopup="menu"
              aria-expanded={agentMenuOpen || assessmentSourceMenuOpen}
            >
              <Brain className="h-4 w-4 text-white/70" />
              <span className="hidden sm:inline">{activeAgentLabel}</span>
              <ChevronDown className="h-3.5 w-3.5 text-white/50" />
            </button>

            {agentMenuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-12 z-50 w-64 rounded-xl border border-white/15 bg-[#101010] p-2 shadow-2xl"
              >
                <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-white/40">
                  Choose an agent
                </p>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setActiveAgentMode('assessment');
                    setAgentMenuOpen(false);
                  }}
                  className="flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left hover:bg-white/[0.07]"
                >
                  <Brain className="mt-0.5 h-4 w-4 shrink-0 text-white/65" />
                  <span>
                    <strong className="block text-xs text-white">Assessment Agent</strong>
                    <small className="mt-1 block text-[10px] leading-relaxed text-white/45">
                      Choose how assessment content should be sourced.
                    </small>
                  </span>
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setActiveAgentMode('analytics');
                    setAgentMenuOpen(false);
                    setAssessmentSourceMenuOpen(false);
                  }}
                  className="flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left hover:bg-white/[0.07]"
                >
                  <BarChart3 className="mt-0.5 h-4 w-4 shrink-0 text-white/65" />
                  <span>
                    <strong className="block text-xs text-white">Analytics Agent</strong>
                    <small className="mt-1 block text-[10px] leading-relaxed text-white/45">
                      Ask about class performance and student results.
                    </small>
                  </span>
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setActiveAgentMode('copy_checking');
                    setAgentMenuOpen(false);
                    setAssessmentSourceMenuOpen(false);
                  }}
                  className="flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left hover:bg-white/[0.07]"
                >
                  <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-white/65" />
                  <span>
                    <strong className="block text-xs text-white">Copy Checking Agent</strong>
                    <small className="mt-1 block text-[10px] leading-relaxed text-white/45">
                      Select this agent for answer-sheet checking.
                    </small>
                  </span>
                </button>
              </div>
            )}

          </div>
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
                  onClick={() => {
                    const agent: WorkspaceAgentMode =
                      action.workflowType === 'analytics'
                        ? 'analytics'
                        : action.workflowType === 'answer_sheet_checking'
                          ? 'copy_checking'
                          : 'assessment';

                    setActiveAgentMode(agent);
                    onSendMessage(
                      action.prompt,
                      undefined,
                      selectedSourceMode,
                      agent,
                    );
                  }}
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
                onApproveWebSource={onApproveWebSource}
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

      {/* Approval checkpoint is replaced after a real assessment is published. */}
      {activeApproval &&
        !(isPublishedAssessment && activeApproval.reviewType === 'assessment') && (
          <ApprovalBar
            approval={activeApproval}
            onOpenReview={onOpenReview}
            onApprove={onApprove}
            onRequestRevision={onRequestRevision}
            disabled={isProcessing}
          />
        )}

      {isPublishedAssessment && (
        <div className="mx-4 mb-3 space-y-3 rounded-2xl border border-white/10 bg-[#0b0b0b] p-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Assessment Actions</h3>
            <p className="mt-1 text-xs leading-relaxed text-white/50">
              The assessment is published. Continue with student invitations, response evaluation,
              and result emails.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            {!studentInvitationsSent && (
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => {
                  if (window.confirm('Send the assessment invitation to the configured student cohort?')) {
                    void onSendAssessmentToStudents().catch(() => undefined);
                  }
                }}
                className="rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send to Students
              </button>
            )}

            {!evaluationReady && (
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => {
                  void onEvaluateAssessment().catch(() => undefined);
                }}
                className="rounded-xl border border-white/15 bg-white/[0.04] px-4 py-2.5 text-xs font-medium text-white transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Evaluate Student Responses
              </button>
            )}

            {evaluationReady && (
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => {
                  if (window.confirm('Send the evaluated results to students by email?')) {
                    void onSendAssessmentResultEmails().catch(() => undefined);
                  }
                }}
                className="rounded-xl border border-white/15 bg-white/[0.04] px-4 py-2.5 text-xs font-medium text-white transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send Result Emails
              </button>
            )}
          </div>
        </div>
      )}

      {assessmentSourceMenuOpen && activeAgentMode === 'assessment' && (
        <div
          role="dialog"
          aria-label="Choose assessment source mode"
          className="relative z-20 border-t border-white/[0.06] bg-[#090909] px-3 py-3 sm:px-4"
        >
          <div className="mx-auto max-w-4xl rounded-2xl border border-white/15 bg-[#101010] p-3 shadow-2xl">
            <div className="flex items-start justify-between gap-3 px-1 pb-2">
              <div>
                <h3 className="text-xs font-semibold text-white">
                  Which mode do you want for the assessment?
                </h3>
                <p className="mt-1 text-[10px] leading-relaxed text-white/45">
                  Select a source before assessment generation begins.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAssessmentSourceMenuOpen(false)}
                className="rounded px-2 text-white/50 hover:bg-white/10 hover:text-white"
                aria-label="Close source mode popup"
              >
                ×
              </button>
            </div>
            <div className="grid gap-1 sm:grid-cols-2">
              {ASSESSMENT_SOURCE_MODES.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={async () => {
                    setSelectedSourceMode(option.value);
                    if (option.value === 'classroom') {
                      setAssessmentSourceMenuOpen(true);
                      setLoadingClassroomCourses(true);
                      setClassroomCourseError(null);
                      try {
                        const courses = await api.listClassroomCourses();
                        setClassroomCourses(courses);
                        if (courses.length === 1) setClassroomCourseId(courses[0].id);
                      } catch (error) {
                        setClassroomCourseError(error instanceof Error ? error.message : 'Could not load Google Classroom courses.');
                      } finally {
                        setLoadingClassroomCourses(false);
                      }
                      return;
                    }
                    setAssessmentSourceMenuOpen(false);
                    if (option.value !== 'teacher_file') {
                      if (latestTeacherRequest.trim()) {
                        onSendMessage(
                          latestTeacherRequest,
                          undefined,
                          option.value,
                          'assessment',
                        );
                      }
                    }
                  }}
                  className="flex items-start gap-2 rounded-lg border border-transparent px-3 py-2 text-left hover:bg-white/[0.06]"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-white/15 text-[10px] text-white/60">
                    {selectedSourceMode === option.value ? '✓' : ''}
                  </span>
                  <span className="min-w-0">
                    <strong className="block text-xs text-white">{option.label}</strong>
                    <small className="mt-1 block text-[10px] leading-relaxed text-white/45">
                      {option.description}
                    </small>
                  </span>
                </button>
              ))}
            </div>
            {selectedSourceMode === 'classroom' && (
              <div className="mt-3 border-t border-white/10 pt-3">
                {loadingClassroomCourses && <div className="text-xs text-white/60">Loading authorized Classroom courses...</div>}
                {classroomCourseError && <div className="text-xs text-red-300">{classroomCourseError}</div>}
                {!loadingClassroomCourses && !classroomCourseError && classroomCourses.length === 0 && (
                  <div className="text-xs text-white/60">No authorized active Classroom courses were found.</div>
                )}
                {classroomCourses.length > 0 && (
                  <>
                    <label className="text-[10px] text-white/60" htmlFor="classroom-course-select">Choose a course</label>
                    <select
                      id="classroom-course-select"
                      value={classroomCourseId}
                      onChange={(event) => setClassroomCourseId(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/15 bg-black px-2 py-2 text-xs text-white"
                    >
                      <option value="">Select a course</option>
                      {classroomCourses.map((course) => <option key={course.id} value={course.id}>{course.name}{course.section ? ` — ${course.section}` : ''}</option>)}
                    </select>
                    <button
                      type="button"
                      disabled={!classroomCourseId}
                      onClick={() => {
                        localStorage.setItem(`tco.classroom_course.${conversation?.id || ''}`, classroomCourseId);
                        setAssessmentSourceMenuOpen(false);
                        if (latestTeacherRequest.trim()) onSendMessage(latestTeacherRequest, undefined, 'classroom', 'assessment');
                      }}
                      className="mt-2 rounded-lg border border-white/20 px-3 py-2 text-xs text-white disabled:opacity-40"
                    >
                      Continue with selected course
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Message Composer */}
      {(
          String(activeAgentMode) === 'copy_checking' ||
          String(lastMsg?.workflowProgress?.activeAgent ?? '') === 'copy_checking_agent'
        ) && (
          <div className="mx-auto w-full max-w-4xl px-4 pb-2">
            <button
              type="button"
              onClick={() => {
                setCopyUploadError(null);
                setCopyUploadResult(null);
                setCopyUploadOpen(true);
              }}
              disabled={isProcessing || copyUploadBusy}
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-[#111111] px-4 py-2.5 text-xs font-medium text-white/85 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <FileCheck2 className="h-4 w-4" />
              Upload Copy Checking Files
            </button>
          </div>
        )}

        {copyUploadOpen && (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/80 p-4 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="copy-upload-title"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget && !copyUploadBusy) {
                setCopyUploadOpen(false);
              }
            }}
          >
            <div className="my-auto w-full max-w-xl space-y-5 rounded-2xl border border-white/15 bg-[#101010] p-5 shadow-2xl sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 id="copy-upload-title" className="text-base font-semibold text-white">
                    Upload Answer-Sheet Checking Files
                  </h2>
                  <p className="mt-1 text-xs leading-relaxed text-white/50">
                    Select the three files used by the existing Copy Checking workflow.
                  </p>
                </div>
                <button
                  type="button"
                  aria-label="Close upload window"
                  disabled={copyUploadBusy}
                  onClick={() => setCopyUploadOpen(false)}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/70 hover:bg-white/10 disabled:opacity-40"
                >
                  Close
                </button>
              </div>

              <div className="space-y-4">
                <label className="block space-y-2">
                  <span className="block text-xs font-medium text-white/85">
                    1. Question Paper (.txt)
                  </span>
                  <input
                    type="file"
                    accept=".txt,text/plain"
                    disabled={copyUploadBusy}
                    onChange={(event) => setCopyQuestionPaper(event.target.files?.[0] ?? null)}
                    className="block w-full rounded-xl border border-white/10 bg-black p-3 text-xs text-white file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-2 file:text-xs file:font-medium file:text-black"
                  />
                  {copyQuestionPaper && (
                    <span className="block break-all text-[11px] text-white/45">
                      Selected: {copyQuestionPaper.name}
                    </span>
                  )}
                </label>

                <label className="block space-y-2">
                  <span className="block text-xs font-medium text-white/85">
                    2. Teacher-approved Marking Scheme / Answer Key (.txt)
                  </span>
                  <input
                    type="file"
                    accept=".txt,text/plain"
                    disabled={copyUploadBusy}
                    onChange={(event) => setCopyMarkingScheme(event.target.files?.[0] ?? null)}
                    className="block w-full rounded-xl border border-white/10 bg-black p-3 text-xs text-white file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-2 file:text-xs file:font-medium file:text-black"
                  />
                  {copyMarkingScheme && (
                    <span className="block break-all text-[11px] text-white/45">
                      Selected: {copyMarkingScheme.name}
                    </span>
                  )}
                </label>

                <label className="block space-y-2">
                  <span className="block text-xs font-medium text-white/85">
                    3. Student Answer Sheet (.pdf)
                  </span>
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    disabled={copyUploadBusy}
                    onChange={(event) => setCopyAnswerSheet(event.target.files?.[0] ?? null)}
                    className="block w-full rounded-xl border border-white/10 bg-black p-3 text-xs text-white file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-2 file:text-xs file:font-medium file:text-black"
                  />
                  {copyAnswerSheet && (
                    <span className="block break-all text-[11px] text-white/45">
                      Selected: {copyAnswerSheet.name}
                    </span>
                  )}
                </label>

                <label className="block space-y-1.5">
                  <span className="block text-xs font-medium text-white/85">
                    PDF pages to process
                  </span>
                  <input
                    type="number"
                    min={1}
                    step={1}
                    value={copyPageCount}
                    disabled={copyUploadBusy}
                    onChange={(event) => setCopyPageCount(event.target.value)}
                    className="w-32 rounded-lg border border-white/15 bg-black px-3 py-2 text-sm text-white outline-none focus:border-white/40 disabled:opacity-40"
                  />
                  <span className="block text-[11px] leading-relaxed text-white/40">
                    Include every page that must be checked. The backend enforces its configured page limit.
                  </span>
                </label>
              </div>

              {copyUploadError && (
                <div role="alert" className="rounded-xl border border-red-400/30 bg-red-950/30 p-3 text-xs leading-relaxed text-red-200">
                  {copyUploadError}
                </div>
              )}

              {copyUploadResult !== null && (
                <div className="space-y-2 rounded-xl border border-white/10 bg-black/60 p-3">
                  <p className="text-xs font-semibold text-white/85">Backend response</p>
                  <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-relaxed text-white/65">
                    {JSON.stringify(copyUploadResult, null, 2)}
                  </pre>
                </div>
              )}

              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  disabled={copyUploadBusy}
                  onClick={() => setCopyUploadOpen(false)}
                  className="rounded-xl border border-white/15 px-4 py-2.5 text-xs font-medium text-white/75 hover:bg-white/[0.06] disabled:opacity-40"
                >
                  Close
                </button>
                <button
                  type="button"
                  disabled={
                    copyUploadBusy ||
                    !copyQuestionPaper ||
                    !copyMarkingScheme ||
                    !copyAnswerSheet
                  }
                  onClick={() => void submitCopyCheckingUpload()}
                  className="rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-black hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {copyUploadBusy ? 'Uploading and checking?' : 'Upload and Check Copy'}
                </button>
              </div>
            </div>
          </div>
        )}

        {copyUploadBusy && (
          <div role="status" className="mx-auto mb-3 w-full max-w-4xl px-4">
            <div className="rounded-xl border border-white/10 bg-[#111111] p-4 text-xs text-white/75">
              Upload started. Copy Checking is extracting and validating the submitted files?
            </div>
          </div>
        )}

        {copyReviewError && !copyReviewJobId && !copyReviewRecord && (
          <div className="mx-auto mb-3 w-full max-w-4xl px-4">
            <div role="alert" className="rounded-xl border border-amber-300/30 bg-amber-950/20 p-4 text-xs leading-relaxed text-amber-100">
              <p>{copyReviewError}</p>
              <button
                type="button"
                onClick={() => {
                  setCopyReviewError(null);
                  setCopyUploadError(null);
                  setCopyUploadOpen(true);
                }}
                className="mt-2 underline underline-offset-2"
              >
                Try upload again
              </button>
            </div>
          </div>
        )}

        {copyReviewJobId && copyReviewError && !copyReviewRecord && (
          <div className="mx-auto mb-3 w-full max-w-4xl px-4">
            <div role="alert" className="rounded-xl border border-red-400/30 bg-red-950/30 p-4 text-xs text-red-200">
              {copyReviewError}
              <button
                type="button"
                disabled={copyReviewBusy}
                onClick={() => {
                  setCopyReviewBusy(true);
                  void loadCopyCheckingReview(copyReviewJobId)
                    .catch((error) => setCopyReviewError(errorMessage(error)))
                    .finally(() => setCopyReviewBusy(false));
                }}
                className="ml-3 underline disabled:opacity-50"
              >
                Retry loading review
              </button>
            </div>
          </div>
        )}

        {copyReviewJobId && copyReviewRecord && !copyGradeResult && (
          <div className="mx-auto mb-3 w-full max-w-4xl px-4">
            <section className="space-y-4 rounded-2xl border border-white/15 bg-[#101010] p-4 sm:p-5">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-300">
                  Teacher review required
                </p>
                <h3 className="mt-1 text-sm font-semibold text-white">
                  Review extracted answers before grading
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-white/50">
                  {String(copyReviewRecord.reason ?? 'Verify the extracted answers and marking scheme before grading.')}
                </p>
                <p className="mt-1 text-[11px] text-white/40">Job: {copyReviewJobId}</p>
              </div>

              <div className="max-h-[40vh] space-y-3 overflow-y-auto pr-1">
                {copyReviewAnswers.length === 0 && (
                  <p className="rounded-lg border border-white/10 p-3 text-xs text-white/50">
                    No answer text was returned in the review record. Check the saved extraction before approving.
                  </p>
                )}
                {copyReviewAnswers.map((item, index) => (
                  <label
                    key={`${item.question_no}-${index}`}
                    className="block space-y-1.5 rounded-xl border border-white/10 bg-black/40 p-3"
                  >
                    <span className="block text-xs font-medium text-white/85">
                      Question {item.question_no}
                    </span>
                    <textarea
                      value={item.answer}
                      rows={3}
                      disabled={copyReviewBusy}
                      onChange={(event) => {
                        const answer = event.target.value;
                        setCopyReviewAnswers((previous) =>
                          previous.map((current, currentIndex) =>
                            currentIndex === index ? { ...current, answer } : current,
                          ),
                        );
                      }}
                      className="w-full resize-y rounded-lg border border-white/10 bg-black px-3 py-2 text-xs leading-relaxed text-white outline-none focus:border-white/30 disabled:opacity-50"
                      placeholder="Verify or correct the extracted answer?"
                    />
                  </label>
                ))}
              </div>

              {copyMissingQuestions.length > 0 && (
                <div className="space-y-2 rounded-xl border border-amber-300/20 bg-amber-950/10 p-3">
                  <p className="text-xs font-medium text-white/85">
                    Questions flagged as missing
                  </p>
                  {copyMissingQuestions.map((number) => (
                    <label key={number} className="flex items-start gap-2 text-xs text-white/70">
                      <input
                        type="checkbox"
                        checked={copyConfirmedBlankQuestions.includes(number)}
                        disabled={copyReviewBusy}
                        onChange={(event) => {
                          setCopyConfirmedBlankQuestions((previous) =>
                            event.target.checked
                              ? [...previous, number]
                              : previous.filter((item) => item !== number),
                          );
                        }}
                        className="mt-0.5"
                      />
                      I checked question {number}; confirm it is intentionally blank/unanswered.
                    </label>
                  ))}
                </div>
              )}

              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-white/85">Teacher name</span>
                <input
                  value={copyTeacherName}
                  onChange={(event) => setCopyTeacherName(event.target.value)}
                  disabled={copyReviewBusy}
                  placeholder="Enter teacher name"
                  className="w-full rounded-lg border border-white/15 bg-black px-3 py-2 text-xs text-white outline-none focus:border-white/30 disabled:opacity-50"
                />
              </label>

              <div className="space-y-2 rounded-xl border border-white/10 p-3">
                <label className="flex items-start gap-2 text-xs text-white/75">
                  <input
                    type="checkbox"
                    checked={copyAnswersReviewed}
                    disabled={copyReviewBusy}
                    onChange={(event) => setCopyAnswersReviewed(event.target.checked)}
                    className="mt-0.5"
                  />
                  I have reviewed all extracted answers and corrected them where necessary.
                </label>
                <label className="flex items-start gap-2 text-xs text-white/75">
                  <input
                    type="checkbox"
                    checked={copyMarkingSchemeLocked}
                    disabled={copyReviewBusy}
                    onChange={(event) => setCopyMarkingSchemeLocked(event.target.checked)}
                    className="mt-0.5"
                  />
                  The teacher-approved marking scheme/answer key is locked for grading.
                </label>
              </div>

              {copyReviewError && (
                <div role="alert" className="rounded-xl border border-red-400/30 bg-red-950/30 p-3 text-xs text-red-200">
                  {copyReviewError}
                </div>
              )}

              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  disabled={copyReviewBusy}
                  onClick={() => {
                    setCopyReviewRecord(null);
                    setCopyReviewJobId(null);
                    setCopyReviewError(null);
                  }}
                  className="rounded-xl border border-white/15 px-4 py-2.5 text-xs text-white/70 hover:bg-white/[0.06] disabled:opacity-50"
                >
                  Dismiss
                </button>
                <button
                  type="button"
                  disabled={copyReviewBusy || !copyTeacherName.trim() || !copyAnswersReviewed || !copyMarkingSchemeLocked}
                  onClick={() => void approveCopyCheckingAndGrade()}
                  className="rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-black hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {copyReviewBusy ? 'Saving review and grading?' : 'Approve & Grade'}
                </button>
              </div>
            </section>
          </div>
        )}

        {copyGradeResult && (
          <div className="mx-auto mb-3 w-full max-w-4xl px-4">
            <section className="space-y-3 rounded-2xl border border-white/15 bg-[#101010] p-4 sm:p-5">
              <div>
                <h3 className="text-sm font-semibold text-white">Copy checking completed</h3>
                <p className="mt-1 text-xs text-white/60">
                  Marks: {String(
                    copyGradeResult.obtained_marks ??
                    ((copyGradeResult.grading as Record<string, unknown> | undefined)?.obtained_marks ?? '?')
                  )} / {String(
                    copyGradeResult.total_marks ??
                    ((copyGradeResult.grading as Record<string, unknown> | undefined)?.total_marks ?? '?')
                  )}
                  {' ? '}
                  {String(
                    copyGradeResult.percentage ??
                    ((copyGradeResult.grading as Record<string, unknown> | undefined)?.percentage ?? '?')
                  )}%
                </p>
                <p className="mt-1 text-[11px] text-white/45">
                  Result stored in database: {copyGradeResult.database_persisted === true ? 'Yes' : 'Not confirmed by API'}
                </p>
              </div>

              {copyCheckedCopyUrl && (
                <>
                  <a
                    href={copyCheckedCopyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex rounded-xl border border-white/15 px-4 py-2.5 text-xs font-medium text-white/80 hover:bg-white/[0.06]"
                  >
                    Open / Download checked PDF
                  </a>
                  <div className="overflow-hidden rounded-xl border border-white/10 bg-white">
                    <iframe
                      src={copyCheckedCopyUrl}
                      title="Checked student answer sheet"
                      className="h-[70vh] min-h-[480px] w-full bg-white"
                    />
                  </div>
                  {copyResultApproveError && (
                    <div role="alert" className="mt-3 rounded-xl border border-red-400/30 bg-red-950/30 p-3 text-xs text-red-200">
                      {copyResultApproveError}
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 p-3">
                    <p className="text-xs leading-relaxed text-white/55">
                      Review the marks and checked copy. Approve to save the final result.
                    </p>
                    <button
                      type="button"
                      disabled={copyResultApproveBusy || copyGradeResult.database_persisted === true}
                      onClick={() => void approveCopyCheckingResult()}
                      className="rounded-xl bg-white px-4 py-2.5 text-xs font-semibold text-black hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {copyGradeResult.database_persisted === true
                        ? 'Approved & Saved'
                        : copyResultApproveBusy
                          ? 'Saving result?'
                          : 'Approve Result & Save'}
                    </button>
                  </div>
                </>
              )}
            </section>
          </div>
        )}

        <MessageComposer
        onSend={(message, attachments, sourceMode) =>
          onSendMessage(
            message,
            attachments,
            sourceMode,
            activeAgentMode,
          )
        }
        isProcessing={isProcessing}
        onStop={onStopProcessing}
        selectedSourceMode={selectedSourceMode || undefined}
        onSourceModeChange={setSelectedSourceMode}
        showSourceModeSelector={false}
      />
    </div>
  );
};
