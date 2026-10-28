import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./workspace-preview.css";

type ToolName = "assessment" | "analytics" | "copy";
type SourceMode = "general_knowledge" | "teacher_file" | "classroom" | "web_search";
type MissingField = "topic" | "question_count" | "marks" | null;

type ChatMessage = {
  id: string;
  role: "teacher" | "assistant";
  text: string;
  time: string;
};

type Question = {
  question?: string;
  options?: string[];
  correct_answer?: string;
  answer?: string;
  explanation?: string;
  marks?: number;
};

type WorkflowState = {
  workflow_id?: string;
  request_id?: string;
  status?: string;
  topic?: string;
  subject?: string;
  chapter?: string;
  marks?: number;
  question_count?: number;
  questions?: Question[];
  source_candidates?: Array<{
    title?: string;
    url?: string;
    snippet?: string;
    domain?: string;
  }>;
  responder_url?: string;
  edit_url?: string;
  form_id?: string;
  assessment_id?: number | string;
  approval_status?: string;
  error_message?: string;
  error_code?: string;
  evaluation_status?: string;
  evaluation_results?: Array<Record<string, unknown>>;
  result_email_summary?: Record<string, unknown>;
  student_email_total?: number;
  student_email_sent?: number;
  student_email_failed?: number;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
};

type Draft = {
  raw: string;
  topic: string;
  questionCount: number | null;
  marks: number | null;
  subject: string;
  classLevel: string;
};

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

const API_ROOT = API_BASE.replace(/\/api\/v1$/, "");

const TEST_TEACHER_ID = "teacher-test-01";
const TEST_SCHOOL_ID = "school-test-01";
const WORKFLOW_STORAGE_KEY = "tco_preview_assessment_workflow_id";

const emptyDraft = (): Draft => ({
  raw: "",
  topic: "",
  questionCount: null,
  marks: null,
  subject: "",
  classLevel: "B.Tech 2nd Year",
});

function nowLabel() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function makeMessage(role: ChatMessage["role"], text: string): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    text,
    time: nowLabel(),
  };
}

function findTopic(text: string): string {
  const match = text.match(
    /\b(?:on|about|topic(?:\s+is)?|chapter(?:\s+is)?)\s+(.+?)(?=\s+(?:for|with|having|containing|consisting)\b|[,;.!?]|$)/i,
  );

  if (!match?.[1]) return "";
  return match[1].trim().replace(/^["']|["']$/g, "");
}

function parseQuestionCount(text: string): number | null {
  const matches = [
    /\b(\d{1,3})\s*(?:mcqs?|questions?|ques(?:tions?)?|qns?)\b/i,
    /\b(?:questions?|mcqs?)\s*(?:=|:|of)?\s*(\d{1,3})\b/i,
  ];

  for (const pattern of matches) {
    const match = text.match(pattern);
    if (match?.[1]) {
      const value = Number(match[1]);
      if (value >= 1 && value <= 200) return value;
    }
  }

  return null;
}

function parseMarks(text: string): number | null {
  const matches = [
    /\b(\d{1,4})\s*(?:total\s*)?marks?\b/i,
    /\bfor\s+(\d{1,4})\s+marks?\b/i,
    /\bmarks?\s*(?:of|=|:)?\s*(\d{1,4})\b/i,
  ];

  for (const pattern of matches) {
    const match = text.match(pattern);
    if (match?.[1]) {
      const value = Number(match[1]);
      if (value >= 1 && value <= 10000) return value;
    }
  }

  return null;
}

function parseSubject(text: string): string {
  const explicit = text.match(
    /\b(?:subject|course)\s*(?:is|:)?\s*([^,.;\n]+)/i,
  );
  if (explicit?.[1]) return explicit[1].trim();

  if (/\bcomputer architecture\b/i.test(text)) return "Computer Architecture";
  if (/\boperating systems?\b/i.test(text)) return "Operating Systems";
  if (/\bdata structures?\b/i.test(text)) return "Data Structures";
  if (/\bpython\b/i.test(text)) return "Python";
  if (/\bmachine learning\b/i.test(text)) return "Machine Learning";

  return "";
}

function firstMissing(draft: Draft): MissingField {
  if (!draft.topic.trim()) return "topic";
  if (!draft.questionCount) return "question_count";
  if (!draft.marks) return "marks";
  return null;
}

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers || {}),
    },
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail =
      payload?.detail ??
      payload?.message ??
      `Request failed with HTTP ${response.status}`;

    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }

  return payload as T;
}

export default function WorkspacePreview() {
  const [activeTool, setActiveTool] = useState<ToolName>("assessment");
  const [messages, setMessages] = useState<ChatMessage[]>([
    makeMessage(
      "assistant",
      "Hi! Tell me what assessment you need. I will collect any missing details in the conversation, then let you choose the source mode.",
    ),
  ]);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [awaiting, setAwaiting] = useState<MissingField>(null);
  const [sourceMode, setSourceMode] = useState<SourceMode | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [classroomCourseId, setClassroomCourseId] = useState("");
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [busy, setBusy] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [analyticsResult, setAnalyticsResult] = useState<unknown>(null);
  const [regenerationFeedback, setRegenerationFeedback] = useState("");

  function addMessage(role: ChatMessage["role"], text: string) {
    setMessages((current) => [...current, makeMessage(role, text)]);
  }

  async function checkBackend() {
    setBackendStatus("checking");
    try {
      const response = await fetch(`${API_ROOT}/health`);
      if (!response.ok) throw new Error("Health check failed");
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    }
  }

  useEffect(() => {
    void checkBackend();

    const savedWorkflowId = window.localStorage.getItem(WORKFLOW_STORAGE_KEY);
    if (!savedWorkflowId) return;

    apiRequest<WorkflowState>(`/assessment-workflows/${encodeURIComponent(savedWorkflowId)}`)
      .then((state) => {
        setWorkflow(state);
        addMessage(
          "assistant",
          `Restored workflow ${savedWorkflowId}. Current status: ${state.status || "unknown"}.`,
        );
      })
      .catch(() => {
        window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
      });
    // Initial session restoration only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function askForMissing(field: MissingField, nextDraft: Draft) {
    setAwaiting(field);

    const prompt =
      field === "topic"
        ? "What topic or chapter should the assessment cover?"
        : field === "question_count"
          ? "How many questions should I create?"
          : "What should the total marks be?";

    setDraft(nextDraft);
    addMessage("assistant", prompt);
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    addMessage("teacher", text);

    if (activeTool === "copy") {
      addMessage(
        "assistant",
        "Copy Checking is a separate workflow. The upload UI will be connected after the multipart field names of the existing orchestrated-grade endpoint are verified; I will not submit files using unverified field names.",
      );
      return;
    }

    if (activeTool === "analytics") {
      setBusy(true);
      try {
        const result = await apiRequest<unknown>("/tco/execute", {
          method: "POST",
          body: JSON.stringify({
            teacher_request: text,
            request_id: `workspace-analytics-${Date.now()}`,
            teacher_id: TEST_TEACHER_ID,
            school_id: TEST_SCHOOL_ID,
            conversation_id: "workspace-preview-analytics",
            intent: "analytics",
          }),
        });
        setAnalyticsResult(result);
        addMessage("assistant", "Analytics request returned from the Master Agent. See the response panel.");
      } catch (error) {
        addMessage("assistant", `Analytics request failed: ${String(error)}`);
      } finally {
        setBusy(false);
      }
      return;
    }

    if (workflow) {
      addMessage(
        "assistant",
        "This assessment already has a workflow. Use its review, regenerate, publish, delivery or evaluation actions below, or start a new assessment.",
      );
      return;
    }

    let next: Draft = {
      ...draft,
      raw: draft.raw ? `${draft.raw}\n${text}` : text,
    };

    if (awaiting === "topic") {
      next.topic = findTopic(text) || text.replace(/[.!?]+$/, "").trim();
      next.subject = next.subject || parseSubject(text);
    } else if (awaiting === "question_count") {
      next.questionCount = parseQuestionCount(text) ?? (Number(text.match(/\b(\d{1,3})\b/)?.[1] || 0) || null);
    } else if (awaiting === "marks") {
      next.marks = parseMarks(text) ?? (Number(text.match(/\b(\d{1,4})\b/)?.[1] || 0) || null);
    } else {
      const parsedTopic = findTopic(next.raw);
      const parsedCount = parseQuestionCount(next.raw);
      const parsedMarks = parseMarks(next.raw);

      next.topic = next.topic || parsedTopic;
      next.questionCount = next.questionCount || parsedCount;
      next.marks = next.marks || parsedMarks;
      next.subject = next.subject || parseSubject(next.raw);
    }

    const missing = firstMissing(next);
    if (missing) {
      askForMissing(missing, next);
      return;
    }

    setDraft(next);
    setAwaiting(null);
    setSourceMode(null);
    addMessage(
      "assistant",
      `Got it. Topic: ${next.topic}; Questions: ${next.questionCount}; Total marks: ${next.marks}. Choose a source mode below.`,
    );
  }

  async function generateAssessment(mode: SourceMode) {
    if (busy) return;

    if (mode === "teacher_file" && !file) {
      addMessage("assistant", "Please choose a PDF, PPTX, TXT or MD source file first.");
      return;
    }

    if (mode === "classroom" && !classroomCourseId.trim()) {
      addMessage("assistant", "Please enter the Google Classroom Course ID first.");
      return;
    }

    setBusy(true);
    setSourceMode(mode);

    const body = {
      teacher_request: draft.raw || `Create an assessment on ${draft.topic}`,
      teacher_id: TEST_TEACHER_ID,
      school_id: TEST_SCHOOL_ID,
      topic: draft.topic,
      question_count: draft.questionCount,
      marks: draft.marks,
      mode,
      subject: draft.subject || "General",
      chapter: draft.topic,
      class_level: draft.classLevel,
      student_class_level: draft.classLevel,
      section: "CSE-2",
      classroom_course_id: mode === "classroom" ? classroomCourseId.trim() : "",
      conversation_id: `workspace-preview-${Date.now()}`,
    };

    try {
      let result: WorkflowState;

      if (mode === "teacher_file") {
        const form = new FormData();
        form.append("teacher_request", body.teacher_request);
        form.append("teacher_id", body.teacher_id);
        form.append("school_id", body.school_id);
        form.append("topic", body.topic);
        form.append("question_count", String(body.question_count));
        form.append("marks", String(body.marks));
        form.append("subject", body.subject);
        form.append("chapter", body.chapter);
        form.append("class_level", body.class_level);
        form.append("student_class_level", body.student_class_level);
        form.append("section", body.section);
        form.append("conversation_id", body.conversation_id);
        form.append("file", file as File);

        result = await apiRequest<WorkflowState>("/assessment-workflows/generate-with-file", {
          method: "POST",
          body: form,
        });
      } else {
        result = await apiRequest<WorkflowState>("/assessment-workflows/generate", {
          method: "POST",
          body: JSON.stringify(body),
        });
      }

      setWorkflow(result);
      if (result.workflow_id) {
        window.localStorage.setItem(WORKFLOW_STORAGE_KEY, result.workflow_id);
      }

      if (result.status === "assessment_ready_for_teacher") {
        addMessage(
          "assistant",
          `Assessment generated successfully. Review the ${result.questions?.length ?? body.question_count} questions below. Nothing has been published or emailed yet.`,
        );
      } else if (result.source_candidates?.length) {
        addMessage(
          "assistant",
          `I found ${result.source_candidates.length} web source candidate(s). Review and approve one before fetching its content.`,
        );
      } else if (result.status === "waiting_for_teacher") {
        addMessage(
          "assistant",
          String(result.error_message || "The workflow needs more source information before generation can continue."),
        );
      } else {
        addMessage(
          "assistant",
          `Workflow returned status "${result.status || "unknown"}". ${result.error_message || "Review the workflow result panel below."}`,
        );
      }
    } catch (error) {
      addMessage("assistant", `Assessment generation failed: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function performWorkflowAction(
    action: string,
    confirmText?: string,
    body?: unknown,
  ) {
    if (!workflow?.workflow_id || busy) return;

    if (confirmText && !window.confirm(confirmText)) return;

    setBusy(true);
    try {
      const result = await apiRequest<WorkflowState>(
        `/assessment-workflows/${encodeURIComponent(workflow.workflow_id)}/${action}`,
        {
          method: "POST",
          body: JSON.stringify(body ?? {}),
        },
      );

      setWorkflow(result);

      if (result.status === "assessment_ready_for_teacher" && action === "regenerate") {
        addMessage("assistant", "A revised assessment is ready for your review. It has not been published.");
      } else if (result.status === "assessment_form_published") {
        addMessage("assistant", "The assessment has been published and saved. Student emails have not been sent.");
      } else if (result.status === "assessment_sent_to_students") {
        addMessage(
          "assistant",
          `Student delivery completed. Sent: ${result.student_email_sent ?? 0}; failed: ${result.student_email_failed ?? 0}; recipients: ${result.student_email_total ?? 0}.`,
        );
      } else if (result.status === "evaluation_completed") {
        addMessage("assistant", "Response evaluation completed. Result emails have not been sent.");
      } else if (action === "send-result-emails") {
        addMessage("assistant", "The result-email service returned a summary. See the result panel for details.");
      } else {
        addMessage("assistant", `Workflow action completed. Status: ${result.status || "unknown"}.`);
      }
    } catch (error) {
      addMessage("assistant", `${action} failed: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function approveSource(url: string) {
    await performWorkflowAction(
      "approve-source",
      `Approve this web source and continue with its retrieved content?\n\n${url}`,
      { selected_url: url, approval_comment: "Teacher approved source in React Workspace." },
    );
  }

  function startNewAssessment() {
    if (busy) return;

    setWorkflow(null);
    setDraft(emptyDraft());
    setAwaiting(null);
    setSourceMode(null);
    setFile(null);
    setClassroomCourseId("");
    setRegenerationFeedback("");
    window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
    addMessage("assistant", "Ready for a new assessment. What would you like to create?");
  }

  function resetConversation() {
    setMessages([
      makeMessage("assistant", "Hi! Tell me what assessment you need. I will collect any missing details in the conversation, then let you choose the source mode."),
    ]);
    setDraft(emptyDraft());
    setAwaiting(null);
    setWorkflow(null);
    setSourceMode(null);
    setAnalyticsResult(null);
    setFile(null);
    setClassroomCourseId("");
    window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
  }

  const status = String(workflow?.status || "");
  const hasQuestions = (workflow?.questions?.length ?? 0) > 0;
  const isPublished = Boolean(workflow?.form_id) && [
    "assessment_form_published",
    "assessment_created_not_sent",
    "assessment_sent_to_students",
    "evaluation_completed",
  ].includes(status);

  return (
    <div className="tco-app-shell">
      <aside className="tco-sidebar">
        <div className="tco-brand">
          <div className="tco-brand-mark">T</div>
          <div>
            <div className="tco-brand-name">TCO</div>
            <div className="tco-brand-subtitle">Teacher Co-Worker</div>
          </div>
        </div>

        <div className="tco-sidebar-label">WORKSPACE</div>
        <button className={`tco-nav-item ${activeTool === "assessment" ? "active" : ""}`} onClick={() => setActiveTool("assessment")}>
          <span className="tco-nav-icon">A</span>
          Assessment
        </button>
        <button className={`tco-nav-item ${activeTool === "analytics" ? "active" : ""}`} onClick={() => setActiveTool("analytics")}>
          <span className="tco-nav-icon">?</span>
          Analytics
        </button>
        <button className={`tco-nav-item ${activeTool === "copy" ? "active" : ""}`} onClick={() => setActiveTool("copy")}>
          <span className="tco-nav-icon">?</span>
          Copy Checking
        </button>

        <div className="tco-sidebar-bottom">
          <div className="tco-preview-tag">Temporary preview</div>
          <div className="tco-sidebar-note">Auth is bypassed for this local preview only.</div>
          <button className="tco-secondary-button tco-full-button" onClick={resetConversation} disabled={busy}>
            Reset preview
          </button>
        </div>
      </aside>

      <main className="tco-main">
        <header className="tco-topbar">
          <div>
            <div className="tco-eyebrow">TEACHER WORKSPACE</div>
            <h1>
              {activeTool === "assessment" ? "Assessment Studio" : activeTool === "analytics" ? "Class Analytics" : "Copy Checking"}
            </h1>
          </div>
          <div className={`tco-connection ${backendStatus}`}>
            <span className="tco-connection-dot" />
            {backendStatus === "checking" ? "Checking API" : backendStatus === "online" ? "API connected" : "API offline"}
            <button className="tco-icon-button" title="Check backend again" onClick={() => void checkBackend()}>?</button>
          </div>
        </header>

        <div className="tco-workspace-grid">
          <section className="tco-chat-column">
            <div className="tco-section-heading">
              <div>
                <h2>{activeTool === "assessment" ? "Assessment assistant" : activeTool === "analytics" ? "Analytics assistant" : "Copy Checking assistant"}</h2>
                <p>
                  {activeTool === "assessment"
                    ? "Describe what you need in natural language. TCO will ask for missing details."
                    : activeTool === "analytics"
                      ? "Ask about class performance or student results."
                      : "Handwritten and typed answer-sheet checking."}
                </p>
              </div>
              {workflow?.workflow_id && <span className="tco-workflow-id">ID {workflow.workflow_id.slice(0, 15)}</span>}
            </div>

            <div className="tco-messages" aria-live="polite">
              {messages.map((message) => (
                <div key={message.id} className={`tco-message-row ${message.role}`}>
                  <div className="tco-avatar">{message.role === "assistant" ? "T" : "V"}</div>
                  <div className="tco-message-content">
                    <div className="tco-message-meta">
                      <strong>{message.role === "assistant" ? "TCO Master Agent" : "You"}</strong>
                      <span>{message.time}</span>
                    </div>
                    <div className="tco-message-bubble">{message.text}</div>
                  </div>
                </div>
              ))}
              {busy && <div className="tco-working"><span className="tco-spinner" /> TCO is working?</div>}
            </div>

            {activeTool === "assessment" && !workflow && awaiting === null && (
              <div className="tco-hint-row">
                <span>Try:</span>
                <button onClick={() => setInput("Create an MCQ assessment on Booth Algorithm for B.Tech 2nd-year Computer Architecture, with 5 questions for 20 total marks.")}>
                  Booth Algorithm ? 5 questions ? 20 marks
                </button>
              </div>
            )}

            {activeTool === "assessment" && !workflow && sourceMode === null && !awaiting && draft.topic && draft.questionCount && draft.marks && (
              <div className="tco-requirements-summary">
                <strong>Requirements collected</strong>
                <span>{draft.topic}</span>
                <span>{draft.questionCount} questions</span>
                <span>{draft.marks} total marks</span>
              </div>
            )}

            <form className="tco-composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={
                  activeTool === "assessment"
                    ? "Tell TCO what assessment you need?"
                    : activeTool === "analytics"
                      ? "Ask about class performance?"
                      : "Describe the copy-checking task?"
                }
                rows={2}
                disabled={busy}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void sendMessage();
                  }
                }}
              />
              <div className="tco-composer-footer">
                <span>Enter to send ? Shift+Enter for a new line</span>
                <button className="tco-primary-button" type="submit" disabled={busy || !input.trim()}>
                  Send <span>?</span>
                </button>
              </div>
            </form>
          </section>

          <aside className="tco-review-column">
            {activeTool === "assessment" && !workflow && firstMissing(draft) === null && (
              <div className="tco-panel">
                <div className="tco-panel-top">
                  <div>
                    <div className="tco-eyebrow">NEXT STEP</div>
                    <h2>Choose source mode</h2>
                  </div>
                  <span className="tco-step-number">02</span>
                </div>
                <p className="tco-panel-copy">Choose where the assessment content should come from.</p>

                <button className="tco-source-option" onClick={() => void generateAssessment("general_knowledge")} disabled={busy}>
                  <span className="tco-source-icon">AI</span>
                  <span><strong>AI General Knowledge</strong><small>Generate from general knowledge</small></span>
                  <span className="tco-chevron">?</span>
                </button>

                <div className="tco-source-config">
                  <label className="tco-upload-zone">
                    <span className="tco-source-icon">?</span>
                    <strong>Upload Material</strong>
                    <small>PDF, PPTX, TXT or MD ? max 25 MB</small>
                    <input
                      type="file"
                      accept=".pdf,.pptx,.txt,.md"
                      onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                      disabled={busy}
                    />
                    {file && <span className="tco-file-selected">{file.name}</span>}
                  </label>
                  <button className="tco-secondary-button tco-full-button" onClick={() => void generateAssessment("teacher_file")} disabled={busy || !file}>
                    Generate from uploaded material
                  </button>
                </div>

                <div className="tco-source-config">
                  <label className="tco-field-label" htmlFor="classroom-course-id">Google Classroom Course ID</label>
                  <input
                    id="classroom-course-id"
                    value={classroomCourseId}
                    onChange={(event) => setClassroomCourseId(event.target.value)}
                    placeholder="Enter course ID"
                    disabled={busy}
                  />
                  <button className="tco-secondary-button tco-full-button" onClick={() => void generateAssessment("classroom")} disabled={busy || !classroomCourseId.trim()}>
                    Generate from Classroom
                  </button>
                </div>

                <button className="tco-source-option" onClick={() => void generateAssessment("web_search")} disabled={busy}>
                  <span className="tco-source-icon">?</span>
                  <span><strong>Web Search</strong><small>Find sources for teacher approval</small></span>
                  <span className="tco-chevron">?</span>
                </button>
                <p className="tco-safety-note">Nothing is published or emailed by choosing a source mode.</p>
              </div>
            )}

            {activeTool === "assessment" && workflow && (
              <div className="tco-panel">
                <div className="tco-panel-top">
                  <div>
                    <div className="tco-eyebrow">WORKFLOW STATUS</div>
                    <h2>{status.replace(/_/g, " ") || "Assessment workflow"}</h2>
                  </div>
                  <span className={`tco-status-dot ${status.includes("failed") || status.includes("error") ? "error" : "success"}`} />
                </div>

                <div className="tco-detail-list">
                  <div><span>Topic</span><strong>{String(workflow.topic || draft.topic || "?")}</strong></div>
                  <div><span>Questions</span><strong>{workflow.questions?.length ?? draft.questionCount ?? "?"}</strong></div>
                  <div><span>Total marks</span><strong>{String(workflow.marks ?? draft.marks ?? "?")}</strong></div>
                  <div><span>Workflow ID</span><strong className="tco-small-value">{workflow.workflow_id || "?"}</strong></div>
                </div>

                {workflow.error_message && <div className="tco-error-box">{workflow.error_message}</div>}

                {workflow.source_candidates && workflow.source_candidates.length > 0 && !workflow.source_approved && (
                  <div className="tco-source-candidates">
                    <h3>Review web sources</h3>
                    {workflow.source_candidates.map((candidate, index) => (
                      <div className="tco-candidate" key={`${candidate.url}-${index}`}>
                        <strong>{candidate.title || candidate.domain || `Source ${index + 1}`}</strong>
                        {candidate.snippet && <p>{candidate.snippet}</p>}
                        {candidate.url && <a href={candidate.url} target="_blank" rel="noreferrer">{candidate.url}</a>}
                        {candidate.url && (
                          <button className="tco-primary-button tco-full-button" onClick={() => void approveSource(candidate.url as string)} disabled={busy}>
                            Approve source & continue
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {status === "assessment_ready_for_teacher" && (
                  <div className="tco-actions-stack">
                    <button
                      className="tco-primary-button tco-full-button"
                      disabled={busy}
                      onClick={() => void performWorkflowAction(
                        "approve-and-publish",
                        "Approve this assessment and create/publish a real Google Form? This will also save the assessment to the database.",
                      )}
                    >
                      Approve & Publish
                    </button>
                    <label className="tco-field-label" htmlFor="regeneration-feedback">Regeneration feedback (optional)</label>
                    <textarea
                      id="regeneration-feedback"
                      rows={2}
                      value={regenerationFeedback}
                      onChange={(event) => setRegenerationFeedback(event.target.value)}
                      placeholder="What should be improved?"
                      disabled={busy}
                    />
                    <button
                      className="tco-secondary-button tco-full-button"
                      disabled={busy}
                      onClick={() => void performWorkflowAction(
                        "regenerate",
                        "Regenerate the assessment? The existing draft will be replaced.",
                        { feedback: regenerationFeedback },
                      )}
                    >
                      Regenerate assessment
                    </button>
                    <button
                      className="tco-danger-button"
                      disabled={busy}
                      onClick={() => void performWorkflowAction("cancel", "Cancel this draft assessment?")}
                    >
                      Cancel assessment
                    </button>
                  </div>
                )}

                {isPublished && (
                  <div className="tco-actions-stack">
                    {workflow.responder_url && (
                      <a className="tco-form-link" href={workflow.responder_url} target="_blank" rel="noreferrer">
                        Open student Google Form ?
                      </a>
                    )}
                    {workflow.edit_url && (
                      <a className="tco-form-link" href={workflow.edit_url} target="_blank" rel="noreferrer">
                        Open form editor ?
                      </a>
                    )}
                    <div className="tco-warning-box">
                      Sending uses real Gmail delivery to the students returned by the database lookup.
                    </div>
                    {status === "assessment_form_published" && (
                      <>
                        <button
                          className="tco-primary-button tco-full-button"
                          disabled={busy}
                          onClick={() => void performWorkflowAction(
                            "send-to-students",
                            "Send the published assessment link by email to students returned from the database? This sends real emails.",
                          )}
                        >
                          Send to Students
                        </button>
                        <button
                          className="tco-secondary-button tco-full-button"
                          disabled={busy}
                          onClick={() => void performWorkflowAction("do-not-send", "Keep the assessment published but do not send it to students?")}
                        >
                          Do Not Send
                        </button>
                      </>
                    )}
                    {["assessment_form_published", "assessment_sent_to_students", "assessment_created_not_sent"].includes(status) && (
                      <button
                        className="tco-secondary-button tco-full-button"
                        disabled={busy}
                        onClick={() => void performWorkflowAction(
                          "evaluate",
                          "Fetch the current Google Form responses and save evaluation results? This does not send result emails.",
                        )}
                      >
                        Evaluate Student Responses
                      </button>
                    )}
                  </div>
                )}

                {workflow.evaluation_status === "completed" && (
                  <div className="tco-actions-stack">
                    <div className="tco-success-box">Evaluation completed. Result emails have not been sent yet.</div>
                    <button
                      className="tco-primary-button tco-full-button"
                      disabled={busy}
                      onClick={() => void performWorkflowAction(
                        "send-result-emails",
                        "Send result emails using the saved result records to eligible student email addresses? This sends real Gmail messages.",
                      )}
                    >
                      Send Result Emails
                    </button>
                    {workflow.evaluation_results && (
                      <pre className="tco-json-panel">{JSON.stringify(workflow.evaluation_results, null, 2)}</pre>
                    )}
                  </div>
                )}

                {workflow.result_email_summary && (
                  <div className="tco-result-summary">
                    <h3>Result email summary</h3>
                    <pre className="tco-json-panel">{JSON.stringify(workflow.result_email_summary, null, 2)}</pre>
                  </div>
                )}

                <button className="tco-secondary-button tco-full-button" disabled={busy} onClick={startNewAssessment}>
                  Start new assessment
                </button>
              </div>
            )}

            {activeTool === "analytics" && (
              <div className="tco-panel">
                <div className="tco-eyebrow">MASTER AGENT</div>
                <h2>Class analytics</h2>
                <p className="tco-panel-copy">Send an analytics request in the chat. It is routed through the existing <code>/tco/execute</code> endpoint.</p>
                {analyticsResult !== null && <pre className="tco-json-panel">{JSON.stringify(analyticsResult, null, 2)}</pre>}
              </div>
            )}

            {activeTool === "copy" && (
              <div className="tco-panel">
                <div className="tco-eyebrow">COPY CHECKING AGENT</div>
                <h2>Answer-sheet checking</h2>
                <p className="tco-panel-copy">The current API exposes the orchestrated grading endpoint separately.</p>
                <div className="tco-warning-box">
                  The upload form is not submitted yet because its exact multipart parameter names and required fields need to match the existing route contract. The working copy-checking backend remains unchanged.
                </div>
                <a className="tco-form-link" href={`${API_ROOT}/docs`} target="_blank" rel="noreferrer">Inspect backend API contract ?</a>
              </div>
            )}

            <div className="tco-footer-note">
              <span>React + FastAPI preview</span>
              <span>Teacher actions stay explicit</span>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error('Workspace preview could not find the HTML element with id="root".');
}

createRoot(rootElement).render(<WorkspacePreview />);
