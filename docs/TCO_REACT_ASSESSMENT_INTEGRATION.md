# React Assessment Integration Map

Date: 2026-10-22

## Purpose and reference implementation

The working behavioral reference is
[`frontend_streamlit/streamlit_app_backup.py`](../frontend_streamlit/streamlit_app_backup.py).
It directly calls the existing Python workflow and services. The React
workspace must remain a UI/API adapter and must not duplicate assessment
business logic.

The relevant backend implementation is:

- [`MasterAgent.run`](../backend/agents/master_agent.py): extracts and validates
  assessment intent, accumulates structured fields, asks clarification, and
  creates the `assessment.create` task only after required details are present.
- [`workflow`](../backend/graph.py): routes clarification, source retrieval, and
  specialist execution.
- [`AssessmentDeliveryWorkflow.generate_and_review`](../backend/workflows/assessment_delivery.py):
  routes the Assessment Agent and returns the teacher-approval state.
- [`AssessmentDeliveryWorkflow.request_teacher_approval`](../backend/workflows/assessment_delivery.py):
  records the explicit teacher decision.
- [`AssessmentDeliveryWorkflow.create_and_publish_form`](../backend/workflows/assessment_delivery.py):
  invokes the Google Forms tool and stores the responder metadata in workflow
  state.
- [`AssessmentDeliveryWorkflow.save_assessment`](../backend/workflows/assessment_delivery.py):
  persists the approved assessment and questions.
- [`AssessmentDeliveryWorkflow.request_student_send`](../backend/workflows/assessment_delivery.py):
  resolves students using school/class/section and invokes Gmail delivery.
- [`EvaluationCycleService`](../backend/services/evaluation_cycle.py):
  retrieves Form metadata/responses, invokes the Evaluation Agent, and delegates
  finalized result persistence.
- [`AssessmentResultService`](../backend/services/assessment_result_service.py):
  resolves student identity and saves evaluated attempts.
- [`ResultEmailService`](../backend/services/result_email_service.py):
  sends only saved results and updates email status with duplicate protection.

## Streamlit-to-backend map

| Streamlit stage | Reference code and state | Existing backend contract | React integration |
|---|---|---|---|
| Natural-language request | `teacher_request` in the Teacher Input tab | `POST /api/v1/tco/execute` | `ChatWindow.tsx` → `useChat.sendMessage` → `fastApiService.sendMessage` |
| Requirement extraction | `build_state_from_form`; `MasterAgent.run` | `intent`, `topic`, `question_count`, `marks`, `class_level`, `subject`, `section`, `student_class_level` | Initial React request uses `source_preference=awaiting_source_selection`; response maps `waiting_for_teacher` and `missing_information` |
| Clarification accumulation | Streamlit keeps `st.session_state.workflow_state` and updates `teacher_request` | Master Agent receives the accumulated `teacher_request` and structured fields | `fastApiService.respondToClarification` reconstructs the prior request and sends the reply through the same `/tco/execute` path |
| Source selection | Streamlit mode constants and `build_state_from_form` | `general_knowledge`, `teacher_file`, `classroom`, `web_search` | Centered `ChatWindow` source modal opens only for `waiting_for_source_selection`; no generation request is made before selection |
| AI General Knowledge | `mode=MODE_LLM`, `generation_mode=llm_generated` | `POST /api/v1/assessment-workflows/generate`, `mode=general_knowledge` | `fastApiService` sends the selected mode and accumulated request |
| Teacher File/RAG | `save_teacher_upload`; `master_workflow.invoke` | `POST /api/v1/assessment-workflows/generate-with-file` multipart contract | `fastApiService` sends `FormData`; fields include `teacher_request`, IDs, topic, count, marks, context, and `file` |
| Classroom/RAG | `classroom_course_id`; `master_workflow.invoke` | `generate` with `mode=classroom` and required `classroom_course_id` | Request shape is mapped; original React workspace has no authorized course discovery/selection surface, so live Classroom remains blocked |
| Web Search/RAG | source candidates and `approve_source` button | `/{workflow_id}/approve-source`, then source retrieval/generation | Backend route exists; original React source modal selects `web_search`, but candidate approval UI is not yet part of the main `ChatWindow` lifecycle |
| Assessment review | `display_questions`; approval section | `GET /api/v1/assessment-workflows/{workflow_id}` | `ContextPanel` and `QuestionPaperReview` render the returned questions, answer key, and marking scheme |
| Revision | Streamlit calls `request_teacher_approval(... approved=False)` in its legacy flow | `POST /{workflow_id}/regenerate` with `{feedback}` | `ApprovalBar` → `useChat.handleRequestRevision` → `fastApiService.requestRevision` |
| Cancellation/rejection | Streamlit rejected approval | `POST /{workflow_id}/cancel` | `useChat.handleReject` → `fastApiService.rejectWorkflow` |
| Teacher approval | Streamlit calls `request_teacher_approval(approved=True)` before publication | `POST /{workflow_id}/approve-and-publish` | `useChat.handleApprove` → `fastApiService.approveWorkflow`; this endpoint intentionally includes publication and database save |
| Google Form publication | Streamlit calls `create_and_publish_form` | Same approval/publish endpoint; returns `form_id`, `responder_url`, and status | API wiring exists; no safe isolated live Form was available for execution |
| Assessment persistence | Streamlit calls `save_assessment` after publication | Same approval/publish endpoint persists the approved assessment | API wiring exists; persistence is blocked until safe publication is authorized |
| Student invitation | Streamlit calls `request_student_send` only after publication | `POST /{workflow_id}/send-to-students` | Backend route exists; original React workspace does not yet expose this post-publication action |
| Response retrieval/evaluation | `get_result_lifecycle_services`; `evaluate_current_assessment` | `POST /{workflow_id}/evaluate`; internally uses Forms metadata/responses, Evaluation Agent, and ResultStore | Backend route exists; original React workspace does not yet expose this post-publication action |
| Result persistence | `EvaluationCycleService` → `AssessmentResultService` → `ResultStore` | Included in `/evaluate` | Fixture PASS; live Form response was unavailable |
| Result email | `ResultEmailService.send_pending_results` | `POST /{workflow_id}/send-result-emails` | Backend route exists; original React workspace does not yet expose this explicit action |

## State and response contracts

The important state fields shared by the Streamlit and API workflows are:

```text
teacher_request
teacher_id
school_id
conversation_id
intent
required_capability
topic
subject
chapter
class_level
student_class_level
section
question_count
marks
generation_mode
source_preference
knowledge_source
requested_source
source_url
classroom_course_id
uploaded_file_name
uploaded_file_type
source_candidates
source_approved
questions
answer_key
marking_scheme
assessment_review_status
approval_status
workflow_id
form_id
responder_url
assessment_id
student_email_sent
student_email_failed
evaluation_results
result_email_summary
```

The React adapter must preserve `workflow_id` from the backend. It must not use
`request_id` as a substitute when both values are returned.

## Verified React boundary

Previously completed browser/network evidence proves:

1. A complete assessment request first calls `/api/v1/tco/execute` with
   `source_preference=awaiting_source_selection`.
2. Clarification keeps the source popup closed.
3. Complete requirements produce `waiting_for_source_selection`.
4. No generation request occurs before source selection.
5. Each selected source changes the actual generation request.
6. Upload Material uses multipart `FormData`.
7. Review, revision, rejection, and workflow-ID propagation use the registered
   assessment routes.

The real model-backed General Knowledge generation and regeneration were also
verified separately. They are not repeated by this mapping audit.

## Remaining React integration boundary

The legacy `frontend/workspace-preview.tsx` contains a separate preview flow
with buttons for `approve-and-publish`, `send-to-students`, `evaluate`, and
`send-result-emails`. Those controls are not the original React `/workspace`
components and must not be treated as proof that the original workspace is
integrated.

The next implementation stage should add those explicit actions to the
original React workflow using the existing `ITCOApiService`/FastAPI adapter and
workflow state, one action at a time:

1. Preserve the approval response and expose the published state.
2. Add explicit student-delivery action.
3. Add explicit evaluation action.
4. Add explicit result-email action.

Each action must remain teacher-triggered, use the existing endpoint, and be
tested before adding the next one. No automatic publication, student email,
evaluation, or result email is permitted.

## Current external limitations

The configured environment contains a Forms body token but no separate Forms
metadata/response token, no Gmail token, no controlled recipient, and no
isolated authorized test Form. The configured SQLite database has no student
rows. Therefore publication, student delivery, live response retrieval, and
real email delivery remain BLOCKED. Existing temporary-database Evaluation
Agent, ResultStore, and fake-Gmail fixtures are documented as FIXTURE PASS in
[`TCO_ASSESSMENT_E2E_TEST_REPORT.md`](./TCO_ASSESSMENT_E2E_TEST_REPORT.md).

## Lifecycle controls implemented in the original workspace

The original React `/workspace` now uses these typed API methods:

- `sendAssessmentToStudents` → `POST /assessment-workflows/{workflow_id}/send-to-students`
- `evaluateAssessment` → `POST /assessment-workflows/{workflow_id}/evaluate`
- `sendAssessmentResultEmails` → `POST /assessment-workflows/{workflow_id}/send-result-emails`

`ContextPanel` keeps the teacher approval action explicit, reloads the returned
workflow after approval, and displays the actual publication/persistence
metadata. It conditionally exposes delivery, evaluation, and result-email
buttons from backend status and returned saved-result data. The implementation
does not duplicate the Streamlit workflow or automatically trigger side
effects.

Changed React files and backups are listed in the Assessment E2E report.
