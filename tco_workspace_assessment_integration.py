from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

ROOT = Path.cwd()
if not (ROOT / 'frontend' / 'src').exists():
    print('Run this script from the TCO project root (the folder containing frontend/src).', file=sys.stderr)
    raise SystemExit(2)

FILES = {
    'api': ROOT / 'frontend/src/services/api.ts',
    'fast': ROOT / 'frontend/src/services/fastApiService.ts',
    'chat': ROOT / 'frontend/src/hooks/useChat.ts',
    'workspace': ROOT / 'frontend/src/pages/Workspace.tsx',
    'window': ROOT / 'frontend/src/components/workspace/ChatWindow.tsx',
    'composer': ROOT / 'frontend/src/components/workspace/MessageComposer.tsx',
    'context': ROOT / 'frontend/src/components/workspace/ContextPanel.tsx',
}
missing = [str(p) for p in FILES.values() if not p.exists()]
if missing:
    print('Required files not found:\n' + '\n'.join(missing), file=sys.stderr)
    raise SystemExit(2)

text = {k: p.read_text(encoding='utf-8') for k, p in FILES.items()}

def sub_once(key, pattern, replacement, label, flags=0):
    new, n = re.subn(pattern, replacement, text[key], count=1, flags=flags)
    if n != 1:
        raise RuntimeError(f'{label}: expected 1 match in {FILES[key]}, found {n}.')
    text[key] = new

def insert_once(key, anchor, replacement, label):
    if text[key].count(anchor) != 1:
        raise RuntimeError(f'{label}: expected one anchor in {FILES[key]}, found {text[key].count(anchor)}.')
    text[key] = text[key].replace(anchor, replacement, 1)

# ---------------------------------------------------------------------------
# api.ts: define the request and workflow types and expose optional operations.
# ---------------------------------------------------------------------------
if 'export type WorkspaceSubmissionStage' not in text['api']:
    sub_once(
        'api',
        r"(export type WorkspaceAgentMode\s*=\s*\n\s*\| 'assessment'\s*\n\s*\| 'analytics'\s*\n\s*\| 'copy_checking';)",
        r"\1\n\nexport type WorkspaceSubmissionStage =\n  | 'conversation'\n  | 'assessment_requirements_ready';\n\nexport interface AssessmentGenerationRequest {\n  teacherRequest: string;\n  topic: string;\n  questionCount: number;\n  marks: number;\n  subject: string;\n  chapter: string;\n  classLevel: string;\n  section: string;\n  classroomCourseId?: string;\n}\n\nexport type AssessmentWorkflowState = Record<string, any>;\n\nexport type AssessmentWorkflowAction =\n  | 'approve-and-publish'\n  | 'regenerate'\n  | 'cancel'\n  | 'approve-source'\n  | 'send-to-students'\n  | 'do-not-send'\n  | 'evaluate'\n  | 'send-result-emails';",
        'shared assessment types',
        flags=re.M,
    )

if 'submissionStage?: WorkspaceSubmissionStage' not in text['api']:
    sub_once(
        'api',
        r"(sourceMode\?: WorkspaceSourceMode,\s*agentMode\?: WorkspaceAgentMode,?\s*)(\): Promise<\{\s*userMessage: ChatMessage;\s*tcoMessage: ChatMessage\s*\}>;)",
        r"\1submissionStage?: WorkspaceSubmissionStage,\n  \2",
        'add submission stage to API interface',
        flags=re.S,
    )
if 'generateAssessment?(' not in text['api']:
    insert_once(
        'api',
        "\n  respondToClarification(",
        """
  generateAssessment?(
    conversationId: string,
    request: AssessmentGenerationRequest,
    sourceMode: WorkspaceSourceMode,
    uploadedFile?: File,
  ): Promise<{
    userMessage: ChatMessage;
    tcoMessage: ChatMessage;
    workflow: AssessmentWorkflowState;
  }>;

  performAssessmentAction?(
    workflowId: string,
    action: AssessmentWorkflowAction,
    payload?: Record<string, unknown>,
  ): Promise<AssessmentWorkflowState>;

  respondToClarification(""",
        'add assessment workflow API methods',
    )

# ---------------------------------------------------------------------------
# fastApiService.ts: keep incomplete turns conversational; use the dedicated
# assessment lifecycle endpoints once the teacher has selected a source mode.
# ---------------------------------------------------------------------------
sub_once(
    'fast',
    r"import type \{[^}]*ITCOApiService[^}]*\} from './api';",
    """import type {
  ITCOApiService,
  WorkspaceAgentMode,
  WorkspaceSourceMode,
  WorkspaceSubmissionStage,
  AssessmentGenerationRequest,
  AssessmentWorkflowState,
  AssessmentWorkflowAction,
} from './api';""",
    'FastAPI service type imports',
)
sub_once(
    'fast',
    r"async sendMessage\(conversationId, content, attachments, sourceMode: WorkspaceSourceMode = 'general_knowledge', agentMode: WorkspaceAgentMode = 'assessment'\) \{",
    "async sendMessage(conversationId, content, attachments, sourceMode: WorkspaceSourceMode = 'general_knowledge', agentMode: WorkspaceAgentMode = 'assessment', submissionStage: WorkspaceSubmissionStage = 'conversation') {",
    'FastAPI sendMessage signature',
)

# Insert local-only confirmation after incomplete requirements have been checked.
if "submissionStage === 'assessment_requirements_ready'" not in text['fast']:
    anchor = """    if (attachments?.length) {
      throw new Error(
        'File upload is not connected to the current FastAPI Workspace API yet. Text messages are supported.',
      );
    }
"""
    local_branch = anchor + r'''

    if (submissionStage === 'assessment_requirements_ready') {
      const readyUserMessage = normalizeMessage({
        id: `teacher-${createId()}`,
        sender: 'teacher',
        content,
        timestamp: new Date().toISOString(),
      }, 'teacher');
      const readyTcoMessage = normalizeMessage({
        id: createId(),
        sender: 'tco',
        content: 'I have collected the required assessment details. Choose the source mode to continue.',
        timestamp: new Date().toISOString(),
        workflowProgress: {
          workflow_id: createId(),
          intent: 'assessment',
          state: 'needs_input',
          active_agent: 'TCO Master Agent',
          steps: [],
        },
      });
      updateConversationMessages(conversationId, readyUserMessage, readyTcoMessage, content);
      return { userMessage: readyUserMessage, tcoMessage: readyTcoMessage };
    }
'''
    if text['fast'].count(anchor) != 1:
        raise RuntimeError('FastAPI sendMessage attachment guard anchor not found exactly once.')
    text['fast'] = text['fast'].replace(anchor, local_branch, 1)

# Pass accumulated teacher turns so an agent clarification can be answered in context.
if 'const fullTeacherRequest' not in text['fast']:
    sub_once(
        'fast',
        r"(    if \(submissionStage === 'assessment_requirements_ready'\) \{[\s\S]*?return \{ userMessage: readyUserMessage, tcoMessage: readyTcoMessage \};\n    \}\n)(\s*const response = await apiRequest<unknown>\()",
        r"\1\n    const savedConversation = readStoredConversations().find((item) => item.id === conversationId);\n    const fullTeacherRequest = [\n      ...(savedConversation?.messages || []).filter((message) => message.sender === 'teacher').map((message) => message.content),\n      content,\n    ].filter(Boolean).join('\\n');\n\2",
        'include earlier teacher messages in request',
        flags=re.S,
    )
    # Above anchor is after the local branch; if older source layout differs, fail safely.
    sub_once(
        'fast',
        r"(async sendMessage\([\s\S]*?)(teacher_request: content,)",
        r"\1teacher_request: fullTeacherRequest,",
        'send accumulated conversation to Master Agent',
        flags=re.S,
    )

if 'async generateAssessment(' not in text['fast']:
    methods = r'''
  async generateAssessment(
    conversationId,
    request: AssessmentGenerationRequest,
    sourceMode: WorkspaceSourceMode,
    uploadedFile?: File,
  ) {
    const topic = request.topic.trim();
    const body = {
      teacher_request: request.teacherRequest,
      teacher_id: getTeacherId(),
      school_id: getSchoolId(),
      topic,
      question_count: request.questionCount,
      marks: request.marks,
      mode: sourceMode,
      subject: request.subject || 'General',
      chapter: request.chapter || topic,
      class_level: request.classLevel,
      student_class_level: request.classLevel,
      section: request.section,
      classroom_course_id: request.classroomCourseId || '',
      conversation_id: conversationId,
    };

    let raw: unknown;
    if (sourceMode === 'teacher_file') {
      if (!uploadedFile) {
        throw new Error('Upload a PDF, PPTX, TXT or MD source file before generating.');
      }
      const form = new FormData();
      Object.entries(body).forEach(([key, value]) => form.append(key, String(value ?? '')));
      form.append('file', uploadedFile);
      raw = await apiRequest<unknown>('/assessment-workflows/generate-with-file', {
        method: 'POST',
        body: form,
      });
    } else {
      raw = await apiRequest<unknown>('/assessment-workflows/generate', jsonPost(body));
    }

    const workflow = object(raw) as AssessmentWorkflowState;
    const workflowId = String(first(workflow.workflow_id, workflow.request_id, ''));
    if (!workflowId) throw new Error('Assessment API response is missing workflow_id.');

    const status = String(workflow.status || 'unknown');
    const questions = Array.isArray(workflow.questions) ? workflow.questions : [];
    const candidates = Array.isArray(workflow.source_candidates) ? workflow.source_candidates : [];
    const reply = candidates.length && !workflow.source_approved
      ? `The Web Search workflow returned ${candidates.length} source candidate(s). Review and approve a source in the right-side panel.`
      : questions.length
        ? `Assessment generated: ${questions.length} question(s) on ${topic}. Status: ${status}. Review the questions and answer key in the right-side panel. Nothing has been published or emailed.`
        : `Assessment workflow status: ${status}. ${String(workflow.error_message || workflow.clarification_message || 'Review the workflow state in the right-side panel.')}`;

    const userMessage = normalizeMessage({
      id: `teacher-${createId()}`,
      sender: 'teacher',
      content: `Generate assessment using ${sourceMode} for ${topic}.`,
      timestamp: new Date().toISOString(),
    }, 'teacher');
    const tcoMessage = normalizeMessage({
      id: createId(),
      sender: 'tco',
      content: reply,
      timestamp: new Date().toISOString(),
      reviewType: 'assessment',
      reviewDataId: workflowId,
      workflowProgress: {
        workflow_id: workflowId,
        intent: 'assessment',
        state: status,
        active_agent: 'Assessment Agent',
        steps: [],
        result_summary: reply,
      },
    });

    updateConversationMessages(conversationId, userMessage, tcoMessage, topic);
    return { userMessage, tcoMessage, workflow };
  },

  async performAssessmentAction(
    workflowId: string,
    action: AssessmentWorkflowAction,
    payload: Record<string, unknown> = {},
  ) {
    const allowed: AssessmentWorkflowAction[] = [
      'approve-and-publish', 'regenerate', 'cancel', 'approve-source',
      'send-to-students', 'do-not-send', 'evaluate', 'send-result-emails',
    ];
    if (!allowed.includes(action)) throw new Error(`Unsupported assessment action: ${action}`);
    const response = await apiRequest<unknown>(
      `/assessment-workflows/${encoded(workflowId)}/${action}`,
      jsonPost(payload),
    );
    return object(response) as AssessmentWorkflowState;
  },
'''
    insert_once('fast', '\n  async respondToClarification(', '\n' + methods + '\n  async respondToClarification(', 'insert lifecycle service methods')

# Review details: the assessment workflow uses its own ID-based status route.
if "'/assessment-workflows/'" not in text['fast']:
    sub_once(
        'fast',
        r"const response = await apiRequest<unknown>\(\n\s*`/workspace/assessments/\$\{encoded\(reviewId\)\}`,\n\s*\);\n\n\s*const payload = object\(response\);\n\s*const assessment = object\(payload\.assessment\);",
        """const response = await apiRequest<unknown>(
        reviewType === 'assessment'
          ? `/assessment-workflows/${encoded(reviewId)}`
          : `/workspace/assessments/${encoded(reviewId)}`,
      );

      const payload = object(response);
      const assessment = object(payload.assessment || payload);""",
        'assessment review endpoint selection',
    )
    sub_once(
        'fast',
        r"title: assessment\.title,\n\s*assessment_title: assessment\.title,\n\s*instructions: assessment\.instructions,\n\s*questions: assessment\.questions \|\| \[\],\n\s*answer_key: assessment\.answer_key \|\| \[\],\n\s*marking_scheme: assessment\.marking_scheme \|\| \[\],",
        """title: assessment.title || payload.topic || 'MCQ Assessment',
        assessment_title: assessment.title || payload.topic || 'MCQ Assessment',
        instructions: assessment.instructions || payload.teacher_request || '',
        questions: assessment.questions || payload.questions || [],
        answer_key: assessment.answer_key || payload.answer_key || [],
        marking_scheme: assessment.marking_scheme || payload.marking_scheme || [],
        status: payload.status,
        workflow_id: payload.workflow_id || reviewId,
        responder_url: payload.responder_url,
        edit_url: payload.edit_url,
        form_id: payload.form_id,
        assessment_id: payload.assessment_id,
        approval_status: payload.approval_status,
        source_candidates: payload.source_candidates || [],
        source_approved: payload.source_approved,
        assessment_review_status: payload.assessment_review_status,
        assessment_review_feedback: payload.assessment_review_feedback,
        evaluation_status: payload.evaluation_status,
        evaluation_results: payload.evaluation_results,
        result_email_summary: payload.result_email_summary,
        student_email_total: payload.student_email_total,
        student_email_sent: payload.student_email_sent,
        student_email_failed: payload.student_email_failed,
        error_message: payload.error_message,""",
        'map assessment workflow state into review panel',
    )

# ---------------------------------------------------------------------------
# useChat.ts: stage-aware message send and expose a generation callback.
# ---------------------------------------------------------------------------
if 'WorkspaceSubmissionStage' not in text['chat']:
    sub_once(
        'chat',
        r"import type \{ MessageAttachmentInput, WorkspaceAgentMode, WorkspaceSourceMode \} from '../services/api';",
        "import type { MessageAttachmentInput, WorkspaceAgentMode, WorkspaceSourceMode, WorkspaceSubmissionStage, AssessmentGenerationRequest } from '../services/api';",
        'useChat imports',
    )
sub_once(
    'chat',
    r"async \(content: string, attachments\?: MessageAttachmentInput\[\]\, sourceMode\?: WorkspaceSourceMode\, agentMode\?: WorkspaceAgentMode\) => \{",
    "async (content: string, attachments?: MessageAttachmentInput[], sourceMode?: WorkspaceSourceMode, agentMode?: WorkspaceAgentMode, submissionStage?: WorkspaceSubmissionStage) => {",
    'useChat sendMessage stage signature',
)
sub_once(
    'chat',
    r"(const \{ tcoMessage \} = await api\.sendMessage\(\s*targetConversationId,\s*content,\s*attachments,\s*sourceMode,\s*agentMode)\s*,?\s*(\);)",
    r"\1,\n          submissionStage,\n        \2",
    'pass stage through useChat',
    flags=re.S,
)

if 'const generateAssessment = useCallback(' not in text['chat']:
    hook = r'''
  const generateAssessment = useCallback(
    async (
      request: AssessmentGenerationRequest,
      sourceMode: WorkspaceSourceMode,
      uploadedFile?: File,
    ) => {
      if (!api.generateAssessment) {
        setError('The selected API service does not support assessment generation.');
        return;
      }

      setIsProcessing(true);
      setError(null);
      let conversationId = activeConversationId;

      try {
        if (!conversationId) {
          const created = await api.createConversation(`Assessment: ${request.topic}`.slice(0, 60));
          conversationId = created.id;
          setActiveConversationId(created.id);
          setActiveConversation(created);
          setConversations((previous) => [created, ...previous.filter((item) => item.id !== created.id)]);
        }

        if (!conversationId) {
          throw new Error('Could not create or select a conversation for this assessment.');
        }

        const result = await api.generateAssessment(
          conversationId,
          request,
          sourceMode,
          uploadedFile,
        );

        setActiveConversation((previous) => {
          if (!previous || previous.id !== conversationId) return previous;
          return {
            ...previous,
            title: previous.title === 'New Conversation'
              ? `Assessment: ${request.topic}`.slice(0, 60)
              : previous.title,
            status: 'In Review',
            lastUpdated: new Date().toISOString(),
            preview: result.tcoMessage.content,
            messages: [...previous.messages, result.userMessage, result.tcoMessage],
            activeWorkflowType: 'question_paper_generation',
          };
        });

        setActiveReviewType('assessment');
        setActiveReviewId(String(result.workflow.workflow_id || result.workflow.request_id || ''));
        setIsReviewPanelOpen(true);
        await refreshConversations();
      } catch (err) {
        console.error('Assessment generation failed:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [activeConversationId, refreshConversations],
  );
'''
    insert_once('chat', '\n  const handleClarification = useCallback(', '\n' + hook + '\n  const handleClarification = useCallback(', 'add useChat assessment generation')
    sub_once(
        'chat',
        r"(    createNewChat,\n    sendMessage,\n)(\s*handleClarification,)",
        r"\1    generateAssessment,\n\2",
        'export assessment callback from useChat',
    )

# ---------------------------------------------------------------------------
# Workspace.tsx: wire the new callback to the existing ChatWindow.
# ---------------------------------------------------------------------------
if 'AssessmentGenerationRequest' not in text['workspace']:
    sub_once(
        'workspace',
        r"(import React, \{ useEffect, useState \} from 'react';)",
        r"\1\nimport type { AssessmentGenerationRequest, WorkspaceSourceMode } from '../services/api';",
        'Workspace request type import',
    )
sub_once(
    'workspace',
    r"(\s*sendMessage,\n)(\s*handleClarification,)",
    r"\1    generateAssessment,\n\2",
    'Workspace destructure generateAssessment',
)
sub_once(
    'workspace',
    r"(          onSendMessage=\{sendMessage\}\n)(\s*onClarification=\{handleClarification\})",
    r"\1          onGenerateAssessment={(request: AssessmentGenerationRequest, sourceMode: WorkspaceSourceMode, file?: File) => generateAssessment(request, sourceMode, file)}\n\2",
    'pass generator into ChatWindow',
)

# ---------------------------------------------------------------------------
# ChatWindow.tsx: parse requirements conversationally; only then open modal.
# ---------------------------------------------------------------------------
sub_once(
    'window',
    r"import type \{ MessageAttachmentInput, WorkspaceAgentMode, WorkspaceSourceMode \} from '../../services/api';",
    "import type { MessageAttachmentInput, WorkspaceAgentMode, WorkspaceSourceMode, WorkspaceSubmissionStage, AssessmentGenerationRequest } from '../../services/api';",
    'ChatWindow workflow type imports',
)
sub_once(
    'window',
    r"(  onSendMessage: \(\n    message: string,\n    attachments\?: MessageAttachmentInput\[\],\n    sourceMode\?: WorkspaceSourceMode,\n    agentMode\?: WorkspaceAgentMode)(\n  \) => void;)",
    r"\1,\n    submissionStage?: WorkspaceSubmissionStage,\2\n  onGenerateAssessment: (request: AssessmentGenerationRequest, sourceMode: WorkspaceSourceMode, uploadedFile?: File) => Promise<void>;",
    'ChatWindow generation callback prop',
)

if 'function parseAssessmentRequest(' not in text['window']:
    helper = r'''
function parseAssessmentRequest(text: string): {
  request: AssessmentGenerationRequest;
  missing: string[];
} {
  const topicMatch =
    text.match(/\b(?:topic|chapter)\s*(?:is|:|=)?\s*([^,.;\n]+)/i) ||
    text.match(/\b(?:on|about)\s+(.+?)(?=\s+(?:with|having|containing|consisting|for\s+\d|for\s+(?:b\.?\s?tech|class|grade)|total\s+\d)|[,;.!?\n]|$)/i);
  const countMatch =
    text.match(/\b(\d{1,3})\s*(?:mcqs?|questions?|ques|qns?)\b/i) ||
    text.match(/\b(?:questions?|mcqs?)\s*(?:count|:|=|of)?\s*(\d{1,3})\b/i);
  const marksMatch =
    text.match(/\b(\d{1,4})\s*(?:total\s*)?marks?\b/i) ||
    text.match(/\bmarks?\s*(?:of|=|:)?\s*(\d{1,4})\b/i);
  const classMatch =
    text.match(/\bB\.?\s?Tech(?:nology)?\s+(?:1st|2nd|3rd|4th|first|second|third|fourth|\d+(?:st|nd|rd|th)?)(?:[\s-]*year)?\b/i) ||
    text.match(/\b(?:class|grade)\s+\w+(?:\s+\w+)?\b/i) ||
    text.match(/\b(?:1st|2nd|3rd|4th|first|second|third|fourth)\s+year\b/i);
  const sectionMatch =
    text.match(/\bsection\s*[:\-]?\s*([A-Za-z0-9-]+)\b/i) ||
    text.match(/\b([A-Z]{2,10}-\d{1,2})\b/i);

  const topic = topicMatch?.[1]?.trim().replace(/^['"]|['"]$/g, '') || '';
  const questionCount = countMatch ? Number(countMatch[1]) : 0;
  const marks = marksMatch ? Number(marksMatch[1]) : 0;
  const classLevel = classMatch?.[0]?.trim() || import.meta.env.VITE_TCO_CLASS_LEVEL || '';
  const section = sectionMatch?.[1]?.trim() || sectionMatch?.[0]?.trim() || import.meta.env.VITE_TCO_SECTION || '';
  const explicitSubject = text.match(/\bsubject\s*(?:is|:|=)?\s*([^,.;\n]+)/i);
  const knownSubjects = [
    'Computer Architecture', 'Operating Systems', 'Data Structures',
    'Database Management Systems', 'DBMS', 'Python', 'Machine Learning',
    'Artificial Intelligence', 'Mathematics',
  ];
  const subject = explicitSubject?.[1]?.trim() || knownSubjects.find((value) => new RegExp(value, 'i').test(text)) || 'General';
  const missing: string[] = [];
  if (!topic) missing.push('topic or chapter');
  if (!questionCount || questionCount < 1 || questionCount > 200) missing.push('number of questions');
  if (!marks || marks < 1) missing.push('total marks');
  if (!classLevel) missing.push('class/year');
  if (!section) missing.push('section or student group');
  return {
    request: {
      teacherRequest: text,
      topic,
      questionCount,
      marks,
      subject,
      chapter: topic,
      classLevel,
      section,
    },
    missing,
  };
}

'''
    insert_once('window', 'const QUICK_ACTIONS: QuickActionItem[] = [', helper + 'const QUICK_ACTIONS: QuickActionItem[] = [', 'add conversational requirements parser')

# Prop destructuring and state.
sub_once(
    'window',
    r"(export const ChatWindow: React\.FC<ChatWindowProps> = \(\{\n[\s\S]*?\n  onSendMessage,\n)([\s\S]*?\n\}\) => \{)",
    r"\1  onGenerateAssessment,\n\2",
    'ChatWindow receive generator callback',
    flags=re.S,
)
if 'pendingAssessmentRequest' not in text['window']:
    sub_once(
        'window',
        r"(  const \[selectedSourceMode, setSelectedSourceMode\]\s*=\s*useState<WorkspaceSourceMode>\('general_knowledge'\);)",
        r"\1\n  const [pendingAssessmentRequest, setPendingAssessmentRequest] = useState<AssessmentGenerationRequest | null>(null);\n  const [pendingSourceFile, setPendingSourceFile] = useState<File | null>(null);\n  const [classroomCourseId, setClassroomCourseId] = useState('');\n  const [assessmentModeError, setAssessmentModeError] = useState<string | null>(null);",
        'ChatWindow assessment staging state',
    )

# Do not display the modal just because the agent was selected.
sub_once(
    'window',
    r"(setActiveAgentMode\('assessment'\);\s*setAgentMenuOpen\(false\);\s*)setAssessmentSourceMenuOpen\(true\);",
    r"\1setAssessmentSourceMenuOpen(false);",
    'only open mode popup after query validation',
)

# Add shared handlers before ChatWindow's return.
if 'const handleAgentMessage = async (' not in text['window']:
    handler = r'''
  const startAssessmentGeneration = async (
    mode: WorkspaceSourceMode,
    requestOverride?: AssessmentGenerationRequest | null,
    fileOverride?: File | null,
  ) => {
    const request = requestOverride || pendingAssessmentRequest;
    const sourceFile = fileOverride || pendingSourceFile;
    if (!request) {
      setAssessmentModeError('Please provide the assessment requirements in chat first.');
      return;
    }
    if (mode === 'teacher_file' && !sourceFile) {
      setSelectedSourceMode('teacher_file');
      setAssessmentModeError('Upload a PDF, PPTX, TXT or MD source file to continue.');
      setAssessmentSourceMenuOpen(true);
      return;
    }
    if (mode === 'classroom' && !classroomCourseId.trim()) {
      setSelectedSourceMode('classroom');
      setAssessmentModeError('Enter the Google Classroom Course ID to continue.');
      setAssessmentSourceMenuOpen(true);
      return;
    }
    setSelectedSourceMode(mode);
    setAssessmentModeError(null);
    setAssessmentSourceMenuOpen(false);
    await onGenerateAssessment(
      { ...request, classroomCourseId: mode === 'classroom' ? classroomCourseId.trim() : '' },
      mode,
      mode === 'teacher_file' ? sourceFile || undefined : undefined,
    );
  };

  const handleSelectAssessmentSource = async (mode: WorkspaceSourceMode) => {
    setSelectedSourceMode(mode);
    setAssessmentModeError(null);
    if (mode === 'teacher_file') {
      if (pendingSourceFile) await startAssessmentGeneration(mode, pendingAssessmentRequest, pendingSourceFile);
      return;
    }
    if (mode === 'classroom') {
      if (classroomCourseId.trim()) await startAssessmentGeneration(mode, pendingAssessmentRequest);
      return;
    }
    await startAssessmentGeneration(mode, pendingAssessmentRequest);
  };

  const handleAgentMessage = async (
    message: string,
    attachments?: MessageAttachmentInput[],
    composerMode?: WorkspaceSourceMode,
    agentOverride?: WorkspaceAgentMode,
  ) => {
    const agent = agentOverride || activeAgentMode;
    const uploadedFile = attachments?.find((item) => item.file)?.file;
    if (uploadedFile) {
      setPendingSourceFile(uploadedFile);
      setSelectedSourceMode('teacher_file');
    }

    if (agent !== 'assessment') {
      await onSendMessage(
        uploadedFile ? `${message}\n[Attached file: ${uploadedFile.name}]` : message,
        undefined,
        composerMode || selectedSourceMode,
        agent,
        'conversation',
      );
      return;
    }

    const visibleMessage = uploadedFile
      ? `${message}\n[Source file uploaded: ${uploadedFile.name}]`
      : message;
    const priorTeacherMessages = (conversation?.messages || [])
      .filter((item) => item.sender === 'teacher')
      .map((item) => item.content);
    const combinedRequest = [...priorTeacherMessages, visibleMessage].filter(Boolean).join('\\n');
    const parsed = parseAssessmentRequest(combinedRequest);
    const chosenMode = uploadedFile || pendingSourceFile
      ? 'teacher_file'
      : composerMode || selectedSourceMode;

    if (parsed.missing.length) {
      // The unfinished request goes to the existing Master Agent endpoint.
      // The source popup is deliberately withheld until all delivery fields exist.
      await onSendMessage(
        visibleMessage,
        undefined,
        'general_knowledge',
        'assessment',
        'conversation',
      );
      return;
    }

    parsed.request.teacherRequest = combinedRequest;
    setPendingAssessmentRequest(parsed.request);
    await onSendMessage(
      visibleMessage,
      undefined,
      chosenMode,
      'assessment',
      'assessment_requirements_ready',
    );

    // A material uploaded in the composer automatically selects Teacher File
    // mode and proceeds as soon as the requirements are complete.
    if (chosenMode === 'teacher_file' && (uploadedFile || pendingSourceFile)) {
      await startAssessmentGeneration('teacher_file', parsed.request, uploadedFile || pendingSourceFile);
    } else {
      setAssessmentModeError(null);
      setAssessmentSourceMenuOpen(true);
    }
  };

'''
    sub_once(
        'window',
        r"(  const getActionIcon = \(iconName: string\) => \{[\s\S]*?\n  \};\n)(\n  return \()",
        r"\1\n" + handler + r"\2",
        'insert agent-aware conversational handlers',
        flags=re.S,
    )

# Quick action uses the agent-aware pathway.
sub_once(
    'window',
    r"onSendMessage\(action\.prompt,\s*undefined,\s*selectedSourceMode,\s*agent,?\s*\);",
    "void handleAgentMessage(action.prompt, undefined, selectedSourceMode, agent);",
    'route quick actions through mode validation',
)

# Modal buttons start the selected workflow. Add file and Classroom controls.
sub_once(
    'window',
    r"onClick=\{\(\) => \{\s*setSelectedSourceMode\(option\.value\);\s*setAssessmentSourceMenuOpen\(false\);\s*\}\}",
    "onClick={() => { void handleSelectAssessmentSource(option.value); }}",
    'source modal selection starts the chosen workflow',
)
if 'Upload source material' not in text['window']:
    # Find the closing list/dialog/backdrop tags after the option map; ignore indentation drift.
    modal_choices = text['window'].find('{ASSESSMENT_SOURCE_MODES.map')
    controls = r'''                </div>
                {selectedSourceMode === 'teacher_file' && (
                  <div className="mt-3 space-y-2 rounded-lg border border-white/10 bg-white/[0.025] p-3">
                    <label className="block text-[11px] font-medium text-white/80">Upload source material (PDF, PPTX, TXT or MD)</label>
                    <input type="file" accept=".pdf,.pptx,.txt,.md" onChange={(event) => {
                      const file = event.target.files?.[0] || null;
                      if (file) { setPendingSourceFile(file); setAssessmentModeError(null); }
                    }} className="w-full text-[10px] text-white/70 file:mr-3 file:rounded-md file:border-0 file:bg-white file:px-3 file:py-2 file:text-[10px] file:font-semibold file:text-black" />
                    {pendingSourceFile && <>
                      <p className="break-all text-[10px] text-white/55">Selected: {pendingSourceFile.name}</p>
                      <button type="button" onClick={() => void startAssessmentGeneration('teacher_file')} className="w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black hover:bg-white/85">Generate from uploaded material</button>
                    </>}
                  </div>
                )}
                {selectedSourceMode === 'classroom' && (
                  <div className="mt-3 space-y-2 rounded-lg border border-white/10 bg-white/[0.025] p-3">
                    <label htmlFor="tco-classroom-course-id" className="block text-[11px] font-medium text-white/80">Google Classroom Course ID</label>
                    <input id="tco-classroom-course-id" value={classroomCourseId} onChange={(event) => setClassroomCourseId(event.target.value)} placeholder="Enter course ID" className="w-full rounded-lg border border-white/10 bg-black px-3 py-2.5 text-xs text-white outline-none focus:border-white/30" />
                    <button type="button" disabled={!classroomCourseId.trim()} onClick={() => void startAssessmentGeneration('classroom')} className="w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black hover:bg-white/85 disabled:opacity-40">Continue with Google Classroom</button>
                  </div>
                )}
                {assessmentModeError && <p role="alert" className="mt-3 rounded-lg border border-white/15 bg-white/[0.04] p-3 text-[11px] leading-relaxed text-white/70">{assessmentModeError}</p>}
              </div>
              </div>
            )}'''
    if modal_choices < 0:
        raise RuntimeError('Assessment source options were not found; no source controls were inserted.')
    tail = text['window'][modal_choices:]
    closings = re.search(r"\s*</div>\s*</div>\s*</div>\s*\)\}", tail)
    if not closings:
        raise RuntimeError('Assessment modal closing tags were not found after the source options; no source controls were inserted.')
    marker_start = modal_choices + closings.start()
    marker_end = modal_choices + closings.end()
    text['window'] = text['window'][:marker_start] + controls + text['window'][marker_end:]

# Bottom composer sends through the Master Agent / assessment gate.
sub_once(
    'window',
    r"<MessageComposer[\s\S]*?\/>",
    """<MessageComposer
        onSend={(message, attachments, sourceMode) => {
          void handleAgentMessage(message, attachments, sourceMode, activeAgentMode);
        }}
        isProcessing={isProcessing}
        onStop={onStopProcessing}
        selectedSourceMode={selectedSourceMode}
        onSourceModeChange={setSelectedSourceMode}
        showSourceModeSelector={false}
        autoSelectTeacherFile={activeAgentMode === 'assessment'}
      />""",
    'composer sends through conversational requirements gate',
    flags=re.S,
)

# ---------------------------------------------------------------------------
# MessageComposer.tsx: uploaded files automatically select Teacher File.
# ---------------------------------------------------------------------------
if 'autoSelectTeacherFile?: boolean' not in text['composer']:
    sub_once(
        'composer',
        r"(  showSourceModeSelector\?: boolean;\n)(\})",
        r"\1  autoSelectTeacherFile?: boolean;\n\2",
        'composer automatic upload mode prop',
    )
sub_once(
    'composer',
    r"(  showSourceModeSelector = true,\n)(\}\) => \{)",
    r"\1  autoSelectTeacherFile = false,\n\2",
    'composer automatic upload mode default',
)
if "if (autoSelectTeacherFile)" not in text['composer']:
    sub_once(
        'composer',
        r"(const handleFilesSelected = \([\s\S]*?if \(selected\.length > 0\) \{[\s\S]*?\n\s*\}\n)(\s*// Allow selecting the same file after removing it\.)",
        r"\1\n    if (selected.length > 0 && autoSelectTeacherFile) {\n      setSourceMode('teacher_file');\n      onSourceModeChange?.('teacher_file');\n    }\n\2",
        'select Teacher File when files are attached',
        flags=re.S,
    )

# Extend the existing attachment picker to the formats accepted by the source-ingestion route.
if '.pptx' not in text['composer'] or '.md' not in text['composer']:
    sub_once(
        'composer',
        r'accept="\.pdf,\.doc,\.docx,\.txt,\.png,\.jpg,\.jpeg,\.webp,\.xlsx,\.csv"',
        'accept=".pdf,.pptx,.md,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp,.xlsx,.csv"',
        'include PPTX and Markdown source file types',
    )

# ---------------------------------------------------------------------------
# ContextPanel: reload the workflow state and expose lifecycle actions.
# ---------------------------------------------------------------------------
if 'const [actionBusy, setActionBusy]' not in text['context']:
    sub_once(
        'context',
        r"(  const \[loadError, setLoadError\] = useState<string \| null>\(null\);)",
        r"\1\n  const [actionBusy, setActionBusy] = useState(false);\n  const [actionError, setActionError] = useState<string | null>(null);",
        'context panel action state',
    )

if 'const runAssessmentAction = async (' not in text['context']:
    action_helper = r'''
  const runAssessmentAction = async (
    action: import('../../services/api').AssessmentWorkflowAction,
    payload: Record<string, unknown> = {},
    confirmation?: string,
  ) => {
    if (actionBusy) return;
    if (!reviewId) {
      setActionError('Assessment workflow ID is missing.');
      return;
    }
    if (!api.performAssessmentAction) {
      setActionError('The configured API service does not support assessment lifecycle actions.');
      return;
    }
    if (confirmation && !window.confirm(confirmation)) return;
    setActionBusy(true);
    setActionError(null);
    try {
      const updated = await api.performAssessmentAction(reviewId, action, payload);
      setData(updated);
      setLoadError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'The assessment action failed.');
    } finally {
      setActionBusy(false);
    }
  };
'''
    sub_once(
        'context',
        r"(  useEffect\(\(\) => \{[\s\S]*?\}, \[isOpen, reviewType, reviewId\]\);\n)(\n  if \(!isOpen\) return null;)",
        r"\1\n" + action_helper + r"\2",
        'insert workflow action helper',
        flags=re.S,
    )

# Expose status-aware teacher actions inside the existing sliding assessment review panel.
sub_once(
    'context',
    r"const isPending =\s*approval\.status === 'pending' \|\|\s*approval\.approval_status === 'pending';",
    "const isPending = data?.status === 'assessment_ready_for_teacher' || data?.approval_status === 'pending' || approval.status === 'pending' || approval.approval_status === 'pending';",
    'make assessment approval status aware of top-level workflow state',
)

old_assessment_view = r'''{type === 'assessment' && \(\s*<AssessmentReviewView\s+data=\{data\}\s+onApprove=\{onApprove\}\s+onReject=\{onReject\}\s+onRequestRevision=\{onRequestRevision\}\s*/>\s*\)}'''
new_assessment_view = r'''{type === 'assessment' && (
                <>
                  <AssessmentReviewView
                    data={data}
                    onApprove={() => void runAssessmentAction(
                      'approve-and-publish', {},
                      'Approve this assessment, publish it as a Google Form, and save it to the database?'
                    )}
                    onReject={(reason) => void runAssessmentAction(
                      reason ? 'regenerate' : 'cancel',
                      reason ? { feedback: reason } : {},
                      reason ? 'Regenerate this assessment using the feedback?' : 'Cancel this assessment draft?'
                    )}
                    onRequestRevision={(instructions) => void runAssessmentAction(
                      'regenerate', { feedback: instructions },
                      'Regenerate this assessment using the requested changes?'
                    )}
                  />

                  {Array.isArray(data?.source_candidates) && data.source_candidates.length > 0 && !data?.source_approved && (
                    <section className="mt-5 space-y-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                      <h3 className="text-sm font-semibold text-white">Choose a web source</h3>
                      <p className="text-xs leading-relaxed text-white/50">Approve a source before its content is retrieved.</p>
                      {data.source_candidates.map((candidate: any, index: number) => (
                        <div key={`${candidate.url || candidate.title}-${index}`} className="rounded-lg border border-white/10 p-3">
                          <p className="text-xs font-medium text-white/85">{candidate.title || candidate.domain || `Source ${index + 1}`}</p>
                          {candidate.snippet && <p className="mt-1 text-[11px] leading-relaxed text-white/50">{candidate.snippet}</p>}
                          {candidate.url && <a className="mt-2 block break-all text-[10px] text-blue-300 underline" href={candidate.url} target="_blank" rel="noreferrer">{candidate.url}</a>}
                          <button type="button" disabled={actionBusy || !candidate.url} onClick={() => void runAssessmentAction(
                            'approve-source',
                            { selected_url: candidate.url, approval_comment: 'Teacher approved the web source in the Workspace.' },
                            `Approve this web source?\n\n${candidate.url}`
                          )} className="mt-3 w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black disabled:opacity-40">Approve source & continue</button>
                        </div>
                      ))}
                    </section>
                  )}

                  {data?.status === 'assessment_form_published' && (
                    <section className="mt-5 space-y-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                      <h3 className="text-sm font-semibold text-white">Published Google Form</h3>
                      {data.responder_url && <a className="block break-all rounded-lg border border-white/10 p-3 text-xs text-blue-300 underline" href={data.responder_url} target="_blank" rel="noreferrer">Open student form</a>}
                      {data.edit_url && <a className="block break-all rounded-lg border border-white/10 p-3 text-xs text-blue-300 underline" href={data.edit_url} target="_blank" rel="noreferrer">Open form editor</a>}
                      <p className="text-[11px] leading-relaxed text-white/50">Student delivery is a separate action and sends real emails to matched student records.</p>
                      <button type="button" disabled={actionBusy} onClick={() => void runAssessmentAction('send-to-students', {}, 'Send the published assessment link by email to the students returned by the database lookup? This sends real emails.')} className="w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black disabled:opacity-40">Send to Students</button>
                      <button type="button" disabled={actionBusy} onClick={() => void runAssessmentAction('do-not-send', {}, 'Keep the assessment published but do not email it to students?')} className="w-full rounded-lg border border-white/15 px-3 py-2.5 text-xs font-medium text-white/80 disabled:opacity-40">Do Not Send</button>
                    </section>
                  )}

                  {['assessment_form_published', 'assessment_sent_to_students', 'assessment_created_not_sent'].includes(String(data?.status)) && (
                    <section className="mt-5 space-y-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                      <h3 className="text-sm font-semibold text-white">Evaluation</h3>
                      <p className="text-xs leading-relaxed text-white/50">Fetch available Google Form responses, evaluate them, and store results. No result email is sent by this step.</p>
                      <button type="button" disabled={actionBusy} onClick={() => void runAssessmentAction('evaluate', {}, 'Fetch submitted Google Form responses and store evaluation results in the database?')} className="w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black disabled:opacity-40">Evaluate Student Responses</button>
                    </section>
                  )}

                  {data?.evaluation_status === 'completed' && (
                    <section className="mt-5 space-y-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                      <h3 className="text-sm font-semibold text-white">Evaluation results saved</h3>
                      <p className="text-xs leading-relaxed text-white/50">Results are saved. Sending result emails is a separate action.</p>
                      {data.evaluation_results && <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black p-3 text-[10px] leading-relaxed text-white/70">{JSON.stringify(data.evaluation_results, null, 2)}</pre>}
                      <button type="button" disabled={actionBusy} onClick={() => void runAssessmentAction('send-result-emails', {}, 'Send saved assessment results by email to eligible students? This sends real emails.')} className="w-full rounded-lg bg-white px-3 py-2.5 text-xs font-semibold text-black disabled:opacity-40">Send Result Emails</button>
                    </section>
                  )}
                  {data?.result_email_summary && <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black p-3 text-[10px] text-white/70">{JSON.stringify(data.result_email_summary, null, 2)}</pre>}
                  {actionBusy && <p className="mt-4 text-xs text-white/55">Updating assessment workflow…</p>}
                  {actionError && <p role="alert" className="mt-4 rounded-lg border border-white/15 bg-white/[0.04] p-3 text-xs leading-relaxed text-white/75">{actionError}</p>}
                </>
              )}'''
sub_once('context', old_assessment_view, new_assessment_view, 'assessment review drawer lifecycle controls', flags=re.S)

# Validate all sources have actually changed in memory before writing anything.
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
for key, path in FILES.items():
    backup = path.with_name(f'{path.name}.backup-assessment-flow-{stamp}')
    shutil.copy2(path, backup)
    path.write_text(text[key], encoding='utf-8')
    print(f'UPDATED  {path.relative_to(ROOT)}')
    print(f'BACKUP   {backup.relative_to(ROOT)}')

print('\nAssessment workflow frontend patch applied. Run npm run build next.')
