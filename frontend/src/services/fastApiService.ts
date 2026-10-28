
import type { ChatMessage, Conversation, SourceCandidate } from '../types/chat';
import type { WorkflowProgress, WorkflowType } from '../types/workflow';
import type { AssessmentLifecycleData } from '../types/workflow';
import type { ClassroomCourse, ITCOApiService, WorkspaceAgentMode, WorkspaceSourceMode } from './api';
import { apiRequest } from './http';

type RecordLike = Record<string, any>;

type MessageAttachmentInput = {
  name: string;
  size: string;
  type: string;
  file?: File;
};

const STORAGE_KEY = 'tco.fastapi.workspace.conversations.v1';
const pendingAssessmentAttachments = new Map<
  string,
  MessageAttachmentInput[]
>();

const object = (value: unknown): RecordLike =>
  value && typeof value === 'object'
    ? value as RecordLike
    : {};

const first = (...values: any[]) =>
  values.find((value) => value !== undefined && value !== null);

const encoded = (value: string) => encodeURIComponent(value);

const jsonPost = (value: unknown): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(value),
  headers: {
    'Content-Type': 'application/json',
  },
});

function createId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `tco-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getTeacherId(): string {
  try {
    return (
      localStorage.getItem('tco.teacher_id') ||
      import.meta.env.VITE_TCO_TEACHER_ID ||
      'teacher-001'
    );
  } catch {
    return import.meta.env.VITE_TCO_TEACHER_ID || 'teacher-001';
  }
}

function getSchoolId(): string {
  return import.meta.env.VITE_TCO_SCHOOL_ID || 'school-001';
}

function readStoredConversations(): Conversation[] {
  if (typeof window === 'undefined') return [];

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    const parsed: unknown = JSON.parse(stored);

    return Array.isArray(parsed)
      ? parsed.map(normalizeConversation)
      : [];
  } catch {
    return [];
  }
}

function saveStoredConversations(
  conversations: Conversation[],
): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(conversations),
    );
  } catch (error) {
    console.error('Could not save local workspace history:', error);
  }
}

function normalizeWorkflow(raw: unknown): WorkflowProgress | undefined {
  if (!raw || typeof raw !== 'object') return undefined;

  const value = object(raw);
  const stepsRaw = first(value.steps, value.workflow_steps, []);
  const rawState = first(value.state, value.status, 'running');

  return {
    workflowId: String(
      first(value.workflowId, value.workflow_id, value.id, 'wf-active'),
    ),
    type: first(
      value.type,
      value.workflow_type,
      value.intent,
      'assessment',
    ) as WorkflowType,
    state: String(rawState).toLowerCase().replace(/ /g, '_') as
      WorkflowProgress['state'],
    activeAgent: first(
      value.activeAgent,
      value.active_agent,
      'TCO Master Agent',
    ),
    steps: Array.isArray(stepsRaw)
      ? stepsRaw.map((rawStep: unknown, index: number) => {
          const step = object(rawStep);

          return {
            id: String(first(step.id, `step-${index + 1}`)),
            agent: first(step.agent, step.agent_name, 'TCO Master Agent'),
            label: String(first(step.label, step.name, `Step ${index + 1}`)),
            description: String(first(step.description, '')),
            status: first(step.status, 'pending'),
            timestamp: first(step.timestamp, step.created_at),
          };
        })
      : [],
    clarification: first(
      value.clarification,
      value.clarification_request,
    ),
    approval: first(value.approval, value.approval_request),
    resultSummary: first(
      value.resultSummary,
      value.result_summary,
    ),
  } as WorkflowProgress;
}

function normalizeMessage(
  raw: unknown,
  fallbackSender: 'teacher' | 'tco' = 'tco',
): ChatMessage {
  const value = object(raw);

  const rawSender = String(
    first(value.sender, value.role, value.sender_role, fallbackSender),
  ).toLowerCase();

  return {
    id: String(
      first(value.id, value.message_id, `msg-${Date.now()}`),
    ),
    sender: ['teacher', 'user', 'human'].includes(rawSender)
      ? 'teacher'
      : 'tco',
    timestamp: String(
      first(
        value.timestamp,
        value.created_at,
        value.time,
        new Date().toISOString(),
      ),
    ),
    content: String(
      first(value.content, value.text, value.message, ''),
    ),
    workflowProgress: normalizeWorkflow(
      first(
        value.workflowProgress,
        value.workflow_progress,
        value.workflow,
      ),
    ),
    clarification: first(
      value.clarification,
      value.clarification_request,
    ),
    approval: first(value.approval, value.approval_request),
    attachments: Array.isArray(value.attachments)
      ? value.attachments.map(
          (rawAttachment: unknown, index: number) => {
            const attachment = object(rawAttachment);

            return {
              id: String(first(attachment.id, `att-${index + 1}`)),
              name: String(
                first(attachment.name, attachment.filename, 'Attachment'),
              ),
              size: String(first(attachment.size, '')),
              type: String(
                first(
                  attachment.type,
                  attachment.content_type,
                  'application/octet-stream',
                ),
              ),
            };
          },
        )
      : undefined,
    reviewType: first(value.reviewType, value.review_type),
    reviewDataId: first(
      value.reviewDataId,
      value.review_data_id,
      value.review_id,
    ),
    sourceCandidates: Array.isArray(value.sourceCandidates)
      ? value.sourceCandidates as SourceCandidate[]
      : Array.isArray(value.source_candidates)
        ? value.source_candidates as SourceCandidate[]
        : undefined,
  } as ChatMessage;
}

function normalizeConversation(raw: unknown): Conversation {
  const value = object(raw);
  const rawMessages = first(value.messages, value.history, []);

  return {
    id: String(first(value.id, value.conversation_id, value.thread_id, '')),
    title: String(first(value.title, value.name, 'New Conversation')),
    status: first(value.status, 'Draft'),
    group: first(value.group, 'Today'),
    lastUpdated: String(
      first(
        value.lastUpdated,
        value.last_updated,
        value.updated_at,
        value.created_at,
        new Date().toISOString(),
      ),
    ),
    preview: String(
      first(value.preview, value.last_message, value.summary, ''),
    ),
    messages: Array.isArray(rawMessages)
      ? rawMessages.map((message: unknown) => normalizeMessage(message))
      : [],
    activeWorkflowType: first(
      value.activeWorkflowType,
      value.active_workflow_type,
    ),
  } as Conversation;
}

function updateConversationMessages(
  conversationId: string,
  userMessage: ChatMessage,
  tcoMessage: ChatMessage,
  titleFromMessage: string,
): void {
  const conversations = readStoredConversations();
  const index = conversations.findIndex(
    (conversation) => conversation.id === conversationId,
  );

  const now = new Date().toISOString();

  if (index === -1) {
    const newConversation = normalizeConversation({
      id: conversationId,
      title: titleFromMessage.slice(0, 60) || 'New Conversation',
      status: 'Running',
      group: 'Today',
      lastUpdated: now,
      preview: tcoMessage.content,
      messages: [userMessage, tcoMessage],
      activeWorkflowType: tcoMessage.workflowProgress?.type,
    });

    saveStoredConversations([newConversation, ...conversations]);
    return;
  }

  const current = conversations[index];

  conversations[index] = {
    ...current,
    status: 'Running',
    lastUpdated: now,
    preview: tcoMessage.content,
    messages: [
      ...(current.messages || []),
      userMessage,
      tcoMessage,
    ],
    activeWorkflowType:
      tcoMessage.workflowProgress?.type ||
      current.activeWorkflowType,
  } as Conversation;

  saveStoredConversations(conversations);
}

function updateStoredWorkflow(
  conversationId: string,
  workflowId: string,
  newState: string,
  approval: unknown,
): void {
  const conversations = readStoredConversations();

  const updated = conversations.map((conversation) => {
    if (conversation.id !== conversationId) return conversation;

    return {
      ...conversation,
      lastUpdated: new Date().toISOString(),
      messages: (conversation.messages || []).map((message) => {
        if (
          message.workflowProgress?.workflowId !== workflowId
        ) {
          return message;
        }

        return {
          ...message,
          approval,
          workflowProgress: {
            ...message.workflowProgress,
            state: newState as WorkflowProgress['state'],
            approval,
          },
        };
      }),
    } as Conversation;
  });

  saveStoredConversations(updated);
}


function mapWorkspaceResponse(
  rawResponse: unknown,
  content: string,
) {
  const payload = object(rawResponse);
  const metadata = object(payload.metadata);
  const decision = object(metadata.master_decision);
  const result = object(payload.result);
  const task = object(payload.current_task);
  const taskResult = object(task.result);

  const requestId = String(
    first(payload.workflow_id, payload.request_id, createId()),
  );
  const intent = String(first(payload.intent, decision.intent, "general"));
  const status = String(first(payload.status, "completed"));
  const nextAction = String(first(payload.next_action, ""));
  const clarification = String(first(payload.clarification_message, ""));

  const missingInformation = Array.isArray(payload.missing_information)
    ? payload.missing_information.map(String)
    : [];

  const questions = Array.isArray(payload.questions)
    ? payload.questions
    : Array.isArray(result.questions)
      ? result.questions
      : Array.isArray(taskResult.questions)
        ? taskResult.questions
        : [];

  const analyticsResult = first(
    payload.analytics_result,
    result.analytics_result,
    taskResult.analytics_result,
  );

  const evaluationResult = first(
    payload.evaluation_result,
    payload.evaluation_results,
    result.evaluation_result,
    taskResult.evaluation_result,
  );

  const copyCheckingResult = first(
    payload.copy_checking_result,
    result.copy_checking_result,
    taskResult.copy_checking_result,
  );
  const sourceCandidates = Array.isArray(payload.source_candidates)
    ? payload.source_candidates as SourceCandidate[]
    : [];

  const displayValue = (value: unknown): string => {
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value, null, 2) ?? String(value);
    } catch {
      return String(value);
    }

  };

  let reply: string;

  if (sourceCandidates.length > 0) {
    reply = `I found ${sourceCandidates.length} web source candidates. Select one below to approve it and continue.`;
  } else if (nextAction === "ask_teacher" || status === "waiting_for_teacher") {
    reply =
      clarification ||
      (missingInformation.length
        ? `Please provide: ${missingInformation.join(", ")}.`
        : "I need some additional information before continuing.");
  } else if (
    status === "error" ||
    status.endsWith("_failed") ||
    payload.error_message
  ) {
    reply = String(
      first(payload.error_message, "TCO could not complete this request."),
    );
  } else if (questions.length > 0) {
    const formattedQuestions = questions.map(
      (rawQuestion: unknown, index: number) => {
        if (typeof rawQuestion === "string") {
          return `${index + 1}. ${rawQuestion}`;
        }

        const question = object(rawQuestion);
        const number = first(
          question.question_number,
          question.number,
          index + 1,
        );
        const text = first(
          question.question,
          question.question_text,
          question.text,
          question.prompt,
          displayValue(rawQuestion),
        );
        const options = Array.isArray(question.options)
          ? question.options.map((option: unknown) => String(option)).join("\n   ")
          : "";

        return `Q${number}. ${String(text)}${options ? `\n   ${options}` : ""}`;
      },
    );

    reply = [
      String(first(payload.assessment_message, "Assessment draft returned by TCO:")),
      "",
      ...formattedQuestions,
    ].join("\n");
  } else if (analyticsResult != null) {
    reply = `Analytics result:\n${displayValue(analyticsResult)}`;
  } else if (evaluationResult != null) {
    reply = `Evaluation result:\n${displayValue(evaluationResult)}`;
  } else if (copyCheckingResult != null) {
    reply = `Copy Checking result:\n${displayValue(copyCheckingResult)}`;
  } else if (status === "analytics_completed") {
    reply =
      "Analytics completed, but no analytics result was included in the API response. Check backend result propagation.";
  } else {
    reply = String(
      first(
        payload.assessment_message,
        payload.reply,
        payload.message,
        `TCO processed the request. Status: ${status}.`,
      ),
    );
  }

  const userMessage = normalizeMessage(
    {
      id: `teacher-${createId()}`,
      sender: "teacher",
      content,
      timestamp: new Date().toISOString(),
    },
    "teacher",
  );

  const tcoMessage = normalizeMessage({
    id: requestId,
    sender: "tco",
    content: reply,
    timestamp: new Date().toISOString(),
    reviewType:
      intent === 'assessment' &&
      ['assessment_ready_for_teacher', 'assessment_ready_for_review'].includes(status)
        ? 'assessment'
        : undefined,
    reviewDataId:
      intent === 'assessment' &&
      ['assessment_ready_for_teacher', 'assessment_ready_for_review'].includes(status)
        ? requestId
        : undefined,
    sourceCandidates: sourceCandidates.length > 0 ? sourceCandidates : undefined,
    approval:
      intent === 'assessment' &&
      ['assessment_ready_for_teacher', 'assessment_ready_for_review'].includes(status)
        ? {
            id: requestId,
            title: 'Assessment ready for teacher review',
            summary: 'Review the generated questions and answer key before approval.',
            reviewType: 'assessment',
            requiresReview: true,
          }
        : undefined,
    workflowProgress: normalizeWorkflow({
      workflow_id: requestId,
      intent,
      state: status,
      active_agent: first(
        metadata.executing_provider,
        metadata.task_provider,
        task.assigned_to,
        "TCO Master Agent",
      ),
      steps: [],
      result_summary: first(
        payload.assessment_message,
        payload.analytics_result,
        payload.evaluation_result,
      ),
    }),
  });

  return { userMessage, tcoMessage, requestId };
}

function extractPositiveNumber(
  content: string,
  patterns: RegExp[],
): number | null {
  for (const pattern of patterns) {
    const match = content.match(pattern);
    if (!match?.[1]) continue;
    const value = Number(match[1]);
    if (Number.isInteger(value) && value > 0) return value;
  }
  return null;
}

function extractAssessmentFields(content: string) {
  const topicMatch = content.match(
    /\b(?:on|about|topic(?:\s+is)?|chapter(?:\s+is)?)\s+(.+?)(?=\s+(?:for|with|having|containing|consisting)\b|[,;.!?]|$)/i,
  );
  const subjectMatch = content.match(
    /\b(?:subject|course)\s*(?:is|:)?\s*([^,.;\n]+)/i,
  );
  const classMatch = content.match(
    /\b((?:B\.?Tech|M\.?Tech|BCA|MCA|class|grade)\s*[^,.;\n]*)/i,
  );

  return {
    topic: (content.match(/(?:^|[|;\n])\s*topic\s*[:=]\s*([^|;\n.]+)/i)?.[1]?.trim() || (topicMatch?.[1]?.trim() || content.trim().slice(0, 500))),
    subject: subjectMatch?.[1]?.trim() || '',
    class_level: classMatch?.[1]?.trim() || '',
    question_count: extractPositiveNumber(content, [
      /\b(\d{1,3})\s*(?:mcqs?|questions?|ques(?:tions?)?)\b/i,
      /\b(?:question\s*count|number\s+of\s+questions?|questions?|mcqs?)\s*(?:=|:|of)?\s*(\d{1,3})\b/i,
    ]),
    marks: extractPositiveNumber(content, [
      /\btotal\s*marks?\s*[:=]\s*(\d{1,4})\b/i,
      /\b(\d{1,4})\s*(?:total\s*)?marks?\b/i,
      /\bfor\s+(\d{1,4})\s+marks?\b/i,
      /\bmarks?\s*(?:of|=|:)?\s*(\d{1,4})\b/i,
    ]),
  };
}

function createUpdatedWorkflow(
  workflowId: string,
  reviewType: WorkflowType,
  state: string,
): WorkflowProgress {
  return {
    workflowId,
    type: reviewType,
    state: state as WorkflowProgress['state'],
    activeAgent: 'TCO Master Agent',
    steps: [],
  } as WorkflowProgress;
}

export const fastApiService: ITCOApiService = {
  async getConversations() {
    // The current FastAPI backend does not expose a conversations-list
    // endpoint, so conversation history is stored locally in this browser.
    return readStoredConversations().sort(
      (a, b) =>
        new Date(b.lastUpdated).getTime() -
        new Date(a.lastUpdated).getTime(),
    );
  },

  async getConversation(id) {
    return readStoredConversations().find(
      (conversation) => conversation.id === id,
    ) || null;
  },

  async createConversation(
    initialTitle = 'New Conversation',
    initialMessage = '',
  ) {
    const id = createId();
    const now = new Date().toISOString();

    const messages = initialMessage
      ? [
          normalizeMessage({
            id: createId(),
            sender: 'teacher',
            content: initialMessage,
            timestamp: now,
          }, 'teacher'),
        ]
      : [];

    const conversation = normalizeConversation({
      id,
      title: initialTitle || 'New Conversation',
      status: 'Draft',
      group: 'Today',
      lastUpdated: now,
      preview: initialMessage,
      messages,
    });

    saveStoredConversations([
      conversation,
      ...readStoredConversations(),
    ]);

    return conversation;
  },

  async sendMessage(conversationId, content, attachments, sourceMode?: WorkspaceSourceMode, agentMode: WorkspaceAgentMode = 'assessment') {
    const originalAssessmentRequest = readStoredConversations()
      .find((conversation) => conversation.id === conversationId)
      ?.messages
      .filter((message) => message.sender === 'teacher')
      .map((message) => message.content)
      .join('\n') || '';
    const requestContent =
      content.trim() || originalAssessmentRequest.trim();
    const assessmentFields =
      agentMode === 'assessment'
        ? extractAssessmentFields(requestContent)
        : null;

    const effectiveSourceMode =
      attachments?.length && agentMode === 'assessment'
        ? 'teacher_file'
        : sourceMode;

    if (attachments?.length) {
      if (
        agentMode !== 'assessment' ||
        effectiveSourceMode !== 'teacher_file' ||
        attachments.length !== 1 ||
        !attachments[0].file
      ) {
        throw new Error(
          'Upload Material requires one source file in Assessment Agent mode.',
        );
      }

      const questionCount = assessmentFields?.question_count;
      const marks = assessmentFields?.marks;

      if (!questionCount || !marks) {
        throw new Error(
          'Please include the question count and total marks before uploading material.',
        );
      }

      const form = new FormData();
      form.append('teacher_request', requestContent);
      form.append('teacher_id', getTeacherId());
      form.append('school_id', getSchoolId());
      form.append('topic', assessmentFields?.topic || requestContent);
      form.append('question_count', String(questionCount));
      form.append('marks', String(marks));
      form.append('conversation_id', conversationId);
      form.append('file', attachments[0].file, attachments[0].name);

      const response = await apiRequest<unknown>(
        '/assessment-workflows/generate-with-file',
        { method: 'POST', body: form },
      );
      const mapped = mapWorkspaceResponse(response, requestContent);

      updateConversationMessages(
        conversationId,
        mapped.userMessage,
        mapped.tcoMessage,
        requestContent,
      );

      if (String(mapped.tcoMessage.workflowProgress?.state) === 'waiting_for_teacher') {
        pendingAssessmentAttachments.set(conversationId, attachments);
      } else {
        pendingAssessmentAttachments.delete(conversationId);
      }

      return {
        userMessage: mapped.userMessage,
        tcoMessage: mapped.tcoMessage,
      };
    }

    if (agentMode === 'assessment' && effectiveSourceMode) {
      if (
        !assessmentFields?.question_count ||
        !assessmentFields.marks ||
        !assessmentFields.topic
      ) {
        throw new Error(
          'Please provide the topic, question count and total marks before generating the assessment.',
        );
      }

      const classroomCourseId = effectiveSourceMode === 'classroom'
        ? (() => {
            try {
              return localStorage.getItem(`tco.classroom_course.${conversationId}`) || '';
            } catch {
              return '';
            }
          })()
        : '';

      if (effectiveSourceMode === 'classroom' && !classroomCourseId) {
        throw new Error('Select an authorized Google Classroom course before continuing.');
      }

      const response = await apiRequest<unknown>(
        '/assessment-workflows/generate',
        jsonPost({
          teacher_request: requestContent,
          teacher_id: getTeacherId(),
          school_id: getSchoolId(),
          topic: assessmentFields.topic,
          question_count: assessmentFields.question_count,
          marks: assessmentFields.marks,
          mode: effectiveSourceMode,
          subject: assessmentFields.subject,
          class_level: assessmentFields.class_level,
          classroom_course_id: classroomCourseId,
          conversation_id: conversationId,
        }),
      );
      const mapped = mapWorkspaceResponse(response, requestContent);

      updateConversationMessages(
        conversationId,
        mapped.userMessage,
        mapped.tcoMessage,
        requestContent,
      );

      return {
        userMessage: mapped.userMessage,
        tcoMessage: mapped.tcoMessage,
      };
    }

    const response = await apiRequest<unknown>(
      '/tco/execute',
      jsonPost({
        teacher_request: requestContent,
        request_id: createId(),
        teacher_id: getTeacherId(),
        school_id: getSchoolId(),
        conversation_id: conversationId,
        intent:
          agentMode === 'analytics'
            ? 'analytics'
            : agentMode === 'copy_checking'
              ? 'copy_checking'
              : 'assessment',
        source_preference:
          agentMode === 'assessment'
            ? 'awaiting_source_selection'
            : undefined,
      }),
    );

    const mapped = mapWorkspaceResponse(response, requestContent);

    updateConversationMessages(
      conversationId,
      mapped.userMessage,
      mapped.tcoMessage,
      requestContent,
    );

    return {
      userMessage: mapped.userMessage,
      tcoMessage: mapped.tcoMessage,
    };
  },

  async respondToClarification(
    conversationId,
    optionId,
    customValue,
  ) {
    const responseText = customValue?.trim() || optionId;
    const previousRequest = readStoredConversations()
      .find((conversation) => conversation.id === conversationId)
      ?.messages
      .filter((message) => message.sender === 'teacher')
      .map((message) => message.content)
      .join('\n') || '';

    return this.sendMessage(
      conversationId,
      [previousRequest, responseText].filter(Boolean).join('\n'),
      pendingAssessmentAttachments.get(conversationId),
      pendingAssessmentAttachments.has(conversationId)
        ? 'teacher_file'
        : undefined,
    );
  },

  async approveWebSource(workflowId, conversationId, candidate) {
    const response = await apiRequest<unknown>(
      `/assessment-workflows/${encoded(workflowId)}/approve-source`,
      {
        method: 'POST',
        body: JSON.stringify({
          selected_url: candidate.url,
          approval_comment: 'Approved by teacher in Workspace.',
        }),
        headers: { 'Content-Type': 'application/json' },
      },
    );
    const mapped = mapWorkspaceResponse(response, candidate.title);
    updateConversationMessages(
      conversationId,
      mapped.userMessage,
      mapped.tcoMessage,
      candidate.title,
    );
    return {
      userMessage: mapped.userMessage,
      tcoMessage: mapped.tcoMessage,
    };
  },

  async listClassroomCourses(): Promise<ClassroomCourse[]> {
    const response = await apiRequest<unknown>('/assessment-workflows/classroom/courses');
    const payload = object(response);
    return Array.isArray(payload.courses)
      ? payload.courses.map((course: unknown) => {
          const value = object(course);
          return {
            id: String(first(value.id, '')),
            name: String(first(value.name, 'Unnamed course')),
            section: String(first(value.section, '')),
            descriptionHeading: String(first(value.descriptionHeading, '')),
            courseState: String(first(value.courseState, 'ACTIVE')),
          };
        }).filter((course) => course.id)
      : [];
  },

  async approveWorkflow(
    workflowId,
    conversationId,
    reviewType,
    notes,
  ) {
    const response = await apiRequest<unknown>(
      `/assessment-workflows/${encoded(workflowId)}/approve-and-publish`,
      { method: 'POST' },
    );

    const payload = object(response);
    const approval = object(payload.approval);
    const status = String(first(payload.status, 'assessment_approved'));

    updateStoredWorkflow(
      conversationId,
      workflowId,
      status,
      approval,
    );

    return {
      status,
      updatedWorkflow: createUpdatedWorkflow(
        workflowId,
        reviewType,
        status,
      ),
      lifecycle: payload as AssessmentLifecycleData,
    };
  },

  async rejectWorkflow(
    workflowId,
    conversationId,
    reason,
  ) {
    const response = await apiRequest<unknown>(
      `/assessment-workflows/${encoded(workflowId)}/cancel`,
      { method: 'POST' },
    );

    const payload = object(response);
    const status = String(
      first(payload.status, 'assessment_needs_regeneration'),
    );

    updateStoredWorkflow(
      conversationId,
      workflowId,
      status,
      payload.approval,
    );

    return {
      status,
      updatedWorkflow: createUpdatedWorkflow(
        workflowId,
        'assessment',
        status,
      ),
    };
  },

  async requestRevision(
    workflowId,
    conversationId,
    instructions,
  ) {
    const response = await apiRequest<unknown>(
      `/assessment-workflows/${encoded(workflowId)}/regenerate`,
      jsonPost({ feedback: instructions }),
    );

    const payload = object(response);
    const status = String(first(payload.status, 'assessment_ready_for_teacher'));
    updateStoredWorkflow(
      conversationId,
      workflowId,
      status,
      payload.approval,
    );

    return {
      status,
      updatedWorkflow: createUpdatedWorkflow(
        workflowId,
        'assessment',
        status,
      ),
    };
  },

  async getReviewDetails<T>(
    reviewType: WorkflowType,
    reviewId: string,
  ): Promise<T | null> {
    try {
      const response = await apiRequest<unknown>(
        `/assessment-workflows/${encoded(reviewId)}`,
      );

      const payload = object(response);
      const assessment = object(payload.assessment);
      const review = object(payload.review);
      const approval = object(payload.approval);

      // Keep the backend response while exposing common fields directly
      // for review panels that expect title/questions/status on one object.
      return {
        ...payload,
        id: reviewId,
        review_id: reviewId,
        type: reviewType,
        title: assessment.title,
        assessment_title: assessment.title,
        instructions: assessment.instructions,
        questions: assessment.questions || payload.questions || [],
        answer_key: assessment.answer_key || payload.answer_key || [],
        marking_scheme: assessment.marking_scheme || payload.marking_scheme || [],
        review,
        approval,
      } as T;
    } catch (error) {
      if ((error as { status?: number }).status === 404) {
        return null;
      }

      throw error;
    }
  },

  async getAssessmentLifecycle(workflowId) {
    try {
      return await apiRequest<AssessmentLifecycleData>(
        `/assessment-workflows/${encoded(workflowId)}`,
      );
    } catch (error) {
      if ((error as { status?: number })?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  async sendAssessmentToStudents(
    workflowId: string,
    target: { school_id: string; class_level: string; section: string },
  ): Promise<AssessmentLifecycleData> {
    return apiRequest<AssessmentLifecycleData>(
      `/assessment-workflows/${encoded(workflowId)}/send-to-students`,
      { method: 'POST', body: JSON.stringify(target) },
    );
  },

  async previewAssessmentRecipients(workflowId) {
    return apiRequest<AssessmentLifecycleData>(
      `/assessment-workflows/${encoded(workflowId)}/recipients`,
    );
  },

  async evaluateAssessment(workflowId) {
    return apiRequest<AssessmentLifecycleData>(
      `/assessment-workflows/${encoded(workflowId)}/evaluate`,
      { method: 'POST' },
    );
  },

  async sendAssessmentResultEmails(workflowId) {
    return apiRequest<AssessmentLifecycleData>(
      `/assessment-workflows/${encoded(workflowId)}/send-result-emails`,
      { method: 'POST' },
    );
  },

  async renameConversation(conversationId, newTitle) {
    const conversations = readStoredConversations();

    const updated = conversations.map((conversation) =>
      conversation.id === conversationId
        ? { ...conversation, title: newTitle }
        : conversation,
    );

    saveStoredConversations(updated);

    return updated.some(
      (conversation) =>
        conversation.id === conversationId &&
        conversation.title === newTitle,
    );
  },

  async archiveConversation(conversationId) {
    const conversations = readStoredConversations();

    const updated = conversations.map((conversation) =>
      conversation.id === conversationId
        ? { ...conversation, status: 'Archived' as const }
        : conversation,
    );

    saveStoredConversations(updated);

    return updated.some(
      (conversation) =>
        conversation.id === conversationId &&
        conversation.status === 'Archived',
    );
  },

  async deleteConversation(conversationId) {
    saveStoredConversations(
      readStoredConversations().filter(
        (conversation) => conversation.id !== conversationId,
      ),
    );

    return true;
  },
};
