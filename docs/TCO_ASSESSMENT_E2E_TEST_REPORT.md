# TCO Assessment Agent E2E Test Report

Date: 2026-10-22

## Scope and safety

This verification covered only the Assessment Agent workflow in the existing
React `/workspace` and FastAPI assessment routes. No production Google Form was
published, no Classroom content was mutated, and no student or result emails
were sent. Browser source-routing assertions used mocked responses where live
model latency or external side effects would otherwise be unsafe.

The initial worktree was already dirty and contained unrelated modifications and
tracked Streamlit deletions. Those changes were preserved.

## Request path traced

1. [ChatWindow.tsx](../frontend/src/components/workspace/ChatWindow.tsx) selects
   Assessment Agent and passes the selected agent/source to `useChat`.
2. [useChat.ts](../frontend/src/hooks/useChat.ts) creates or updates the local
   conversation and calls `api.sendMessage`.
3. [fastApiService.ts](../frontend/src/services/fastApiService.ts) sends the
   initial request to `POST /api/v1/tco/execute` with
   `source_preference=awaiting_source_selection`.
4. [master_agent.py](../backend/agents/master_agent.py) validates topic, count
   and marks. Complete requests stop at `waiting_for_source_selection` without
   creating a task.
5. After selection, the adapter calls
   `POST /api/v1/assessment-workflows/generate` with the selected `mode`, or
   `POST /api/v1/assessment-workflows/generate-with-file` with multipart data.
6. The returned `workflow_id` is retained for review retrieval and lifecycle
   actions.

## Verified behavior

| Stage | Status | Evidence |
|---|---|---|
| Assessment Agent selection does not open modal | PASS | Browser snapshot |
| Incomplete request asks clarification | PASS | Browser mock returned `waiting_for_teacher`; clarification rendered |
| Modal hidden during clarification | PASS | Browser dialog count was zero |
| Complete request gates before source selection | PASS | First request was `/tco/execute`; no generation request |
| Backend source gate | PASS | Mocked Master Agent returned `waiting_for_source_selection`, `source_selection`, and no task |
| Source-selection popup gate | PASS | Browser accessibility snapshot; final focused verification moved it above the composer |
| General Knowledge routing | PASS | `/assessment-workflows/generate`, `mode=general_knowledge` |
| Classroom routing | PASS | `/assessment-workflows/generate`, `mode=classroom` |
| Web Search routing | PASS | `/assessment-workflows/generate`, `mode=web_search` |
| Upload Material contract | PASS | Multipart OpenAPI fields verified; frontend sends `FormData` |
| Upload request preservation | PASS | Empty composer content reconstructs the prior teacher request before multipart submission |
| Review ID propagation | PASS | Mapping now prefers response `workflow_id` over `request_id` |
| Revision endpoint | PASS | Frontend calls `/regenerate` with feedback |
| Cancel/reject endpoint | PASS | Frontend calls `/cancel` |
| Approval/publish endpoint | BLOCKED | External Google Form creation was not authorized |
| Student invitations | BLOCKED | Real email delivery was not authorized |
| Evaluation/result persistence | BLOCKED LIVE | Safe lifecycle unit tests exist; no published test Form/response was available |
| Result emails | BLOCKED | No real email delivery was authorized |

## Verified defects fixed

### Generation before source selection

The hidden composer previously defaulted to `general_knowledge`, causing a
complete first request to call assessment generation before the source modal.
The composer now leaves the source undefined until the explicit source choice,
and the Master Agent has a conditional source-selection gate.

### Upload losing the original request

After choosing Upload Material, the teacher may attach a file with no new text.
The service now reconstructs the accumulated teacher request from the current
conversation before extracting fields and sending multipart data.

### Incorrect review identifier

The response mapper previously preferred `request_id`, but the assessment route
returns a distinct `workflow_id`. Review and approval could therefore target a
nonexistent workflow. Mapping now prefers `workflow_id`.

## Assessment lifecycle endpoints verified in OpenAPI

- `POST /api/v1/tco/execute`
- `POST /api/v1/assessment-workflows/generate`
- `POST /api/v1/assessment-workflows/generate-with-file`
- `GET /api/v1/assessment-workflows/{workflow_id}`
- `POST /api/v1/assessment-workflows/{workflow_id}/approve-and-publish`
- `POST /api/v1/assessment-workflows/{workflow_id}/regenerate`
- `POST /api/v1/assessment-workflows/{workflow_id}/cancel`
- `POST /api/v1/assessment-workflows/{workflow_id}/approve-source`
- `POST /api/v1/assessment-workflows/{workflow_id}/send-to-students`
- `POST /api/v1/assessment-workflows/{workflow_id}/evaluate`
- `POST /api/v1/assessment-workflows/{workflow_id}/send-result-emails`

The multipart schema exposes `teacher_request`, `teacher_id`, `school_id`,
`topic`, `question_count`, `marks`, `conversation_id`, and `file`, plus optional
subject/class/section fields.

## Tests and actual outcomes

PASS:

- `Set-Location frontend; npm run build`
- `python -m compileall -q backend`
- OpenAPI route and multipart-field assertions
- Mocked source-gate assertion
- Browser request-order and source-mode assertions
- `python test_assessment_approval.py`
- Focused pytest run: 4 tests passed before collection errors
- Previous focused assessment/copy-checking run: 23 passed

PRE-EXISTING FAILURES/BLOCKERS:

- `test/test_result_email_service.py`: three tests fail collection because the
  `result_store` fixture is not defined.
- `test_assessment_cycle.py`: the script reached `assessment_review_failed`
  after three review attempts for a model-generated incorrect SQL answer key,
  then failed printing its warning under Windows CP1252 due to an existing
  Unicode encoding issue.
- `tests/test_workspace.py`: cannot collect because `frontend.workspace_core`
  is missing.
- Live Google Forms, Classroom, Gmail, and response retrieval remain blocked by
  authorization/test-fixture constraints.

## Changed files and backups

Changed for this focused verification:

- [fastApiService.ts](../frontend/src/services/fastApiService.ts)
- [TCO_INTEGRATION_TEST_PLAN.md](./TCO_INTEGRATION_TEST_PLAN.md)
- [TCO_IMPLEMENTATION_REPORT.md](./TCO_IMPLEMENTATION_REPORT.md)
- this report

Backups created before changes:

- `frontend/src/services/fastApiService.ts.bak-20261022-054700`
- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-054700`
- `docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-054700`

Earlier assessment-gate backups remain documented in the implementation report.

## Final acceptance status

The safe request-ordering and source-routing portion is **PASS**. The full
external lifecycle is **BLOCKED**, not complete, because publication, student
delivery, live responses, persistence verification through a published Form, and
result email delivery were not authorized or available with controlled fixtures.

## Continuation verification — 2026-10-22 16:52 +05:30

The previously documented ordering and source-routing checks were not repeated.
This continuation tested the next safe Assessment-only stages with the local
FastAPI service and the configured model provider. No approval, Google Form
publication, student invitation, evaluation, or result email action was
invoked.

| Stage | Status | Evidence |
|---|---|---|
| Provider configuration presence | PASS | `.env` contains configured provider variable names; values were not displayed |
| FastAPI health | PASS | `GET http://127.0.0.1:8000/health` returned `{"status":"ok","service":"tco-unified-backend","version":"0.2.0"}` |
| Live OpenAPI assessment routes | PASS | OpenAPI listed generate, multipart generate, retrieve, regenerate, approve/publish, cancel, delivery, evaluation, and result-email routes |
| Actual General Knowledge generation | PASS | `POST /api/v1/assessment-workflows/generate` returned workflow `tco_8a96592cab714f0c9d978aef9b1b7985`, status `assessment_ready_for_teacher`, 5 questions, 20 marks, answer key, and marking scheme |
| Generated assessment content | PASS | Returned questions were on Booth Algorithm and included four answer options and selected correct options |
| Actual review state | PASS | Generation response returned `assessment_review_status=passed` and `approval_status=pending` |
| Actual revision | PASS | `POST /api/v1/assessment-workflows/{workflow_id}/regenerate` accepted teacher feedback and returned the same workflow with 5 revised questions and status `assessment_ready_for_teacher` |
| Workflow retrieval | PASS | `GET /api/v1/assessment-workflows/{workflow_id}` returned the revised assessment with no `form_id` or `assessment_id` before approval |
| Multipart contract | PASS | Live OpenAPI required `teacher_request`, `teacher_id`, `school_id`, `topic`, `question_count`, `marks`, and `file`; optional context fields were also present |
| Approval and Google Form publication | BLOCKED | Not called because configured credentials do not prove an isolated test Form or safe publication target |
| Assessment database persistence | BLOCKED | Approval/publication was not executed, so no new approved assessment record could be verified |
| Student invitation delivery | BLOCKED | No authorized controlled recipient was configured; no email was sent |
| Form response retrieval and Evaluation Agent | BLOCKED LIVE | No isolated published test Form and controlled submission were available |
| Result persistence read-back | FIXTURE PASS | Existing local lifecycle/result-store tests passed; no new live result was created |
| Result emails | BLOCKED | No authorized controlled recipient was configured; no email was sent |

### Commands and outputs

```powershell
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
GET http://127.0.0.1:8000/health
python -m pytest test_routing.py test_master_routing.py test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py tests/test_copy_checker_integration.py -q
```

The regression command completed with **23 passed, 12 warnings**. The live
generation and regeneration requests were made with test-only teacher, school,
conversation, and workflow identifiers. The temporary backend was not used for
any external side-effecting lifecycle endpoint.

Backup created before this report update:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-165207`

## Remaining lifecycle verification — 2026-10-22 16:57 +05:30

This pass did not repeat live generation or revision. It inspected the actual
Google Forms, Gmail, database, Evaluation Agent, and result-storage
integrations, then ran only isolated lifecycle fixtures.

### Safe configuration and fixture inspection

- `credentials.json`: present, but its contents were not displayed.
- `forms_token.json`: present with a refresh token and only
  `https://www.googleapis.com/auth/forms.body`.
- `forms_metadata_token.json`: missing.
- `forms_responses_token.json`: missing.
- `gmail_token.json`: missing.
- `data/tco.db`: present with two existing assessment rows and existing form
  identifiers, but no student rows. Existing forms could not be assumed to be
  isolated test forms and were not queried or modified.
- No safe test-recipient configuration was found.

### Remaining-stage result matrix

| Stage | Status | Evidence |
|---|---|---|
| Teacher approval orchestration | FIXTURE PASS | `python test_assessment_approval.py` passed approved and rejected approval branches; no external provider was called |
| Real teacher approval against generated workflow | BLOCKED | Approval immediately invokes Google Form creation; no isolated authorized test Form target was available |
| Google Form creation/publication | BLOCKED | Existing Forms token is creation-scoped, but no isolated test target/authorization was supplied; no form was created |
| Assessment persistence after publication | BLOCKED | No safe publication occurred, so no new approved assessment could be read back |
| Controlled student invitation | BLOCKED | No student rows exist in the configured database and no controlled recipient is configured; Gmail token is absent |
| Google Form response retrieval | BLOCKED | Response-read OAuth token is absent and no isolated test Form/response is available |
| Evaluation Agent with controlled response | FIXTURE PASS | Temporary database plus fake Forms metadata/response tools evaluated one correct and one incorrect answer |
| Result persistence and read-back | FIXTURE PASS | Temporary ResultStore read-back returned the saved result after Evaluation Agent processing |
| Controlled result email success | FIXTURE PASS | Fake Gmail accepted one message and ResultStore read-back reported `result_email_status=sent` |
| Result email failure handling | FIXTURE PASS | Simulated Gmail failure left the result persisted and recorded `result_email_status=failed` |
| Real result email | BLOCKED | `gmail_token.json` and an authorized controlled recipient are absent |

### Fixture outputs

The temporary-database lifecycle harness reported:

```text
success_lifecycle=result_saved_email_sent
result_persisted=True
email_status=sent
fake_email_calls=1

failure_lifecycle=result_saved_email_failed
result_still_persisted=True
email_status=failed
fake_email_calls=1
```

The fixture used only a temporary copy of `data/tco.db`, a synthetic student
record, a synthetic assessment/form identifier, fake Forms metadata/responses,
and fake Gmail. The configured database was not modified.

The existing `test/test_result_email_integration.py` script was also inspected.
When run directly it failed before exercising the service because it expects a
`GMAIL_TEST_001` student but does not seed that student in its temporary
database. This is a test-fixture defect, not a production lifecycle result.

Backup created before this report update:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-165708`

## Streamlit reference mapping — 2026-10-22 17:50 +05:30

The existing Streamlit implementation was inspected as the behavioral
reference. Its direct calls are mapped to the React/API boundary in
[`TCO_REACT_ASSESSMENT_INTEGRATION.md`](./TCO_REACT_ASSESSMENT_INTEGRATION.md).
No generation or revision tests were repeated.

The audit found no need to modify Python assessment business logic. The main
React workspace already maps clarification, source selection, generation,
multipart upload, review, revision, rejection, and approval to the existing
FastAPI routes. The legacy `frontend/workspace-preview.tsx` has additional
post-publication buttons, but that preview is not the original `/workspace`
component tree and is not counted as completed integration.

The next React implementation boundary is to expose the existing explicit
`send-to-students`, `evaluate`, and `send-result-emails` actions in the
original workspace while preserving teacher control. Live execution remains
blocked by the external test-fixture limitations already documented.

Backup created before this mapping update:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-175054`

## Original React lifecycle controls — 2026-10-22 17:59 +05:30

Implemented the remaining explicit Assessment lifecycle actions in the
original `/workspace` component tree. No Streamlit or backend business logic
was changed.

| Control | Status | Implementation/evidence |
|---|---|---|
| Teacher approval and publish | MOCK PASS | Existing `ContextPanel` approval calls the real `approve-and-publish` adapter; returned workflow is reloaded so Form URL/ID and saved assessment ID are displayed |
| Saved Form details | MOCK PASS | Review panel now displays `responder_url` and `assessment_id` from the backend response |
| Send to Students | MOCK PASS | Explicit button is rendered only for `assessment_form_published` and calls `/send-to-students`; delivery counts are displayed from the response |
| Evaluation | MOCK PASS | Explicit button is rendered only for published/unsent/sent states and calls `/evaluate`; returned evaluation results and marks are displayed |
| Result review | MOCK PASS | Evaluation results are shown only from returned `evaluation_results` and `saved_result` data; no fabricated rows are created |
| Result emails | MOCK PASS | Explicit button is rendered only for `evaluation_completed` with saved result IDs and calls `/send-result-emails`; returned summary/status is displayed |
| Real Google Form publication | BLOCKED | No isolated authorized test Form was available; no publication request was triggered |
| Real student email delivery | BLOCKED | No controlled recipient or Gmail token was available; no email request was triggered |
| Real response evaluation | BLOCKED LIVE | No isolated published Form and controlled response were available |

### React files changed

- `frontend/src/types/workflow.ts`
- `frontend/src/services/api.ts`
- `frontend/src/services/fastApiService.ts`
- `frontend/src/services/mockApi.ts`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/pages/Workspace.tsx`
- `frontend/src/components/workspace/ContextPanel.tsx`

Timestamped backups created before code edits:

- `frontend/src/types/workflow.ts.bak-20261022-175625`
- `frontend/src/services/api.ts.bak-20261022-175625`
- `frontend/src/services/fastApiService.ts.bak-20261022-175625`
- `frontend/src/hooks/useChat.ts.bak-20261022-175625`
- `frontend/src/pages/Workspace.tsx.bak-20261022-175625`
- `frontend/src/components/workspace/ContextPanel.tsx.bak-20261022-175625`

The mock service was extended in the same change so the existing demo mode
continues to satisfy the typed API contract.

### Validation

```powershell
Set-Location frontend
npm run build

Set-Location ..
python -m pytest test_routing.py test_master_routing.py `
  test/test_assessment_result_lifecycle.py `
  test/test_assessment_result_service.py `
  test/test_result_store.py `
  tests/test_copy_checker_integration.py -q
```

Results:

- Frontend production build: **PASS**
- Backend/routing/lifecycle regression suite: **23 passed, 12 warnings**
- `git diff --check`: **PASS**
- No frontend test runner was configured in `frontend/package.json`; browser
  lifecycle controls were therefore validated by TypeScript/build and real
  endpoint contract inspection, not claimed as live external success.

Report backups created before this documentation update:

- `docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-175919`
- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-175919`
- `docs/TCO_REACT_ASSESSMENT_INTEGRATION.md.bak-20261022-175919`

## Final focused React verification — 2026-10-22 18:15 +05:30

This continuation implemented the remaining source-selection/upload UX fixes
without repeating the already-passed live generation and revision tests.

| Stage | Status | Evidence |
|---|---|---|
| Source popup placement | PASS | `ChatWindow.tsx` now renders the selector in the composer-area flow immediately above `MessageComposer`; the prior fixed full-screen centered modal was removed |
| Popup hidden before request | PASS | Existing `waiting_for_source_selection` gate remains the only open condition |
| Popup hidden during clarification | PASS | Clarification state does not satisfy the source-selection gate |
| No generation before source selection | PASS | Existing request-order evidence remains valid: `/tco/execute` precedes any generation route |
| Attachment automatically selects Upload Material | PASS | `fastApiService.sendMessage` derives `effectiveSourceMode=teacher_file` whenever Assessment has an attachment |
| Attachment survives clarification/retry | PASS | The composer clears content and attachments only after a successful send; the service retains a pending attachment for `waiting_for_teacher` and resubmits it with the accumulated clarification request |
| Upload file filter | PASS | `MessageComposer` now accepts only `.pdf,.pptx,.txt,.md`, matching the backend multipart contract |
| Multipart request fields | PASS | Existing FormData path remains unchanged and sends the OpenAPI field names including `file` |
| Frontend production build | PASS | `Set-Location frontend; npm run build` |
| Backend compilation | PASS | `python -m compileall -q backend` |
| Focused routing/cycle command | FAIL | `python -m pytest test_routing.py test_master_routing.py test_assessment_cycle.py -q` exited 5 after 128.81s with 26 deprecation warnings and no passing-test summary; this is recorded as a baseline command failure, not a claimed pass |
| Result-email fixture collection | BLOCKED | `python -m pytest test/test_result_email_integration.py -q` collected no tests and exited 5 |

Files changed in this continuation:

- [ChatWindow.tsx](../frontend/src/components/workspace/ChatWindow.tsx)
- [MessageComposer.tsx](../frontend/src/components/workspace/MessageComposer.tsx)
- [fastApiService.ts](../frontend/src/services/fastApiService.ts)

Timestamped backups created before these edits:

- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-181559`
- `frontend/src/components/workspace/MessageComposer.tsx.bak-20261022-181559`
- `frontend/src/services/fastApiService.ts.bak-20261022-181559`
- `docs/TCO_REACT_ASSESSMENT_INTEGRATION.md.bak-20261022-181559`
- `docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-181559`
- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-181559`
- `docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-181559`

The existing live generation/revision PASS results and all external lifecycle
BLOCKED results remain unchanged. No Google Form, student invitation, or email
was triggered.

## Real incomplete-query browser verification — 2026-10-22 18:31 +05:30

The original React `/workspace` was run against the local FastAPI service with
an isolated development workspace bypass. No Supabase account, Google Form, or
email integration was used.

| Stage | Status | Evidence |
|---|---|---|
| Exact incomplete query | PASS | Submitted `Create an assessment on Booth Algorithm.` |
| Mandatory-field clarification | PASS | FastAPI response displayed `Please provide number of questions, total marks.` |
| No source popup during clarification | PASS | Browser dialog count was 0 while the clarification was displayed |
| Accumulated clarification context | PASS | The follow-up path now sends the prior teacher request plus the clarification answer; generation payload contained `Create an assessment on Booth Algorithm.`, `10 questions worth 20 marks`, and `Booth Algorithm` |
| Source popup after clarification | PASS | Browser dialog appeared only after the backend returned `waiting_for_source_selection` and was rendered immediately above the composer |
| AI General Knowledge selection | PASS | Browser request sent `POST /api/v1/assessment-workflows/generate` with `mode=general_knowledge`, `topic=Booth Algorithm`, `question_count=10`, and `marks=20` |
| Actual assessment generation | PASS | Live backend returned generated Booth Algorithm questions and `assessment_ready_for_teacher` |
| Review presentation | PASS | Existing teacher review controls displayed `Open Review Panel`, `Approve Outcome`, and `Ask for Changes` |

The clarification defect was fixed in [useChat.ts](../frontend/src/hooks/useChat.ts):
when the latest Assessment workflow is `waiting_for_teacher`, a normal composer
reply now uses `respondToClarification`, preserving the accumulated teacher
request instead of sending only the latest sentence.

## Corrected test discovery and results — 2026-10-22 18:31 +05:30

The earlier command exited 5 because `test_routing.py`,
`test_master_routing.py`, and `test_assessment_cycle.py` are executable
diagnostic scripts with no pytest test functions. The result-email integration
file likewise contains no `test_*` functions; it only runs under its
`if __name__ == "__main__"` block, so pytest correctly reported no tests.

| Command | Status | Actual result |
|---|---|---|
| `python -m pytest test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py test/test_evaluation_result_integration.py test/test_evaluation_result_integration_identity.py -q` | PASS | 4 passed |
| `python -m pytest tests/test_copy_checker_integration.py -q` | PASS | 19 passed, 4 warnings |
| `python -m pytest test/test_result_email_service.py -q` | FAIL | 3 setup errors: required `result_store` fixture is undefined |
| `python -m pytest test/test_google_forms_metadata.py test/test_google_forms_responses.py -q` | BLOCKED | Script-only files; no pytest tests collected |
| `Set-Location frontend; npm run build` | PASS | TypeScript and Vite production build succeeded |
| `python -m compileall -q backend` | PASS | No compilation errors |
| `git diff --check` | PASS | No whitespace errors |

No publication, student invitation, evaluation against a live Form, or email
send was started.

## Assessment lifecycle completion verification — 2026-10-22 18:35 +05:30

### Result-email test setup repair

The pytest result-email tests had declared `result_store`, `result_id`,
`student_id`, and `assessment_id` as parameters without defining fixtures.
The test file now uses an isolated temporary copy of `data/tco.db`, seeds only
the controlled fixture student and assessment, and creates result records
through the real `ResultStore` API. The duplicate-protection test explicitly
marks its own isolated result as sent instead of depending on test order.

The standalone fake-provider integration fixture had the same missing-record
problem. It now seeds its temporary database with `GMAIL_TEST_001` and
assessment ID 10. It still uses fake Forms and Gmail tools and does not send
real email.

### Lifecycle evidence

| Stage | Status | Evidence |
|---|---|---|
| Teacher review and explicit approval | FIXTURE PASS | `python test_assessment_approval.py`: approved and rejected branches passed |
| Approval/publish route registration | PASS | OpenAPI/application route inspection found all four lifecycle routes |
| Google Form creation/publication | BLOCKED LIVE | No isolated authorized test Form target; `forms_token.json` has only `forms.body` scope and no safe publication was invoked |
| Assessment persistence/Form ID read-back | BLOCKED LIVE | Depends on the blocked publication stage; no production database mutation was made |
| Explicit Send to Students control | MOCK PASS | Original React `ContextPanel` and FastAPI adapter expose the explicit action, gated on published state |
| Student selection and invitation | BLOCKED LIVE | Configured database has no authorized student fixture for delivery; Gmail OAuth token and controlled recipient are unavailable |
| Controlled Form response retrieval | BLOCKED LIVE | No isolated published Form or response-read authorization is available |
| Evaluation Agent and result persistence | FIXTURE PASS | `test/test_assessment_result_lifecycle.py` and related evaluation/persistence tests passed; fake Form metadata/responses exercised real evaluation/result services |
| Result read-back from isolated database | FIXTURE PASS | ResultStore returned the saved result and lifecycle fixture verified saved result IDs |
| Explicit Send Results by Email control | MOCK PASS | React action is separately gated on completed evaluation and saved results |
| Result email provider success | FIXTURE PASS | Standalone fake-provider run returned `result_saved_email_sent`; saved result email status was `sent` |
| Result email provider failure handling | FIXTURE PASS | Standalone fake-provider run returned `result_saved_email_failed`; saved result remained and status was `failed` |
| Real Gmail result email | BLOCKED LIVE | `gmail_token.json` is absent and no controlled recipient authorization exists |

### Commands and actual summaries

- `python -m pytest test/test_result_email_service.py test/test_result_email_integration.py test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py test/test_evaluation_result_integration.py test/test_evaluation_result_integration_identity.py -q`: **7 passed**
- `python test/test_result_email_integration.py`: **PASS**, both fake-provider lifecycle branches passed
- `python test_assessment_approval.py`: **PASS**
- `python test_routing.py`: **PASS**
- `python test_master_routing.py`: **PASS**
- `python -m pytest tests/test_copy_checker_integration.py -q`: **19 passed, 4 warnings**
- `python -m pytest test/test_google_forms_metadata.py test/test_google_forms_responses.py -q`: **BLOCKED**, script-only files, no tests collected
- `python -m compileall -q backend`: **PASS**
- `Set-Location frontend; npm run build`: **PASS**
- `git diff --check`: **PASS**

Changed test fixtures and backups:

- [test_result_email_service.py](../test/test_result_email_service.py)
- [test_result_email_integration.py](../test/test_result_email_integration.py)
- `test/test_result_email_service.py.bak-20261022-183356`
- `test/test_result_email_integration.py.bak-20261022-183517`

The original React lifecycle implementation remains explicit and Assessment-only.
No Google Form, Classroom, student invitation, or real email operation was
started.

## Live provider readiness audit — 2026-10-22 18:38 +05:30

No external side-effect operation was invoked. Provider implementations, token
metadata, configuration names, and local database counts were inspected
without printing secrets.

### Google Forms

- `credentials.json`: **PRESENT**; installed OAuth client metadata is configured.
- `forms_token.json`: **PRESENT** with a refresh token.
- Creation scope: **PRESENT** — `https://www.googleapis.com/auth/forms.body`.
- Creation token metadata expiry: **2026-10-22T01:00:04.964579Z**; expired at
  audit time. Refresh was not attempted because it would be a live provider
  interaction.
- `forms_metadata_token.json`: **ABSENT**. Required by
  `GoogleFormsMetadataTool` for `https://www.googleapis.com/auth/forms.body.readonly`.
- `forms_responses_token.json`: **ABSENT**. Required by
  `GoogleFormsResponsesTool` for `https://www.googleapis.com/auth/forms.responses.readonly`.
- Dedicated test Form ID: **ABSENT**. No configured isolated Form target was
  available.

### Gmail

- `gmail_token.json`: **ABSENT**. `GmailTool` requires a separate token with
  `https://www.googleapis.com/auth/gmail.send`.
- Controlled recipient configuration: **ABSENT**. No approved recipient setting
  was found.
- The configured database contains **0 student rows** and **0 student email
  rows**, so student delivery cannot safely resolve a recipient.

| Stage | Status | Exact blocker |
|---|---|---|
| Isolated Google Form creation/publication | BLOCKED | No authorized isolated Form target; creation token expired and was not refreshed |
| Form metadata/answer-key retrieval | BLOCKED | `forms_metadata_token.json` absent and readonly scope unavailable |
| Controlled response retrieval | BLOCKED | `forms_responses_token.json` absent; no Form ID or submitted response |
| Student invitation | BLOCKED | No students, controlled recipient, or Gmail token |
| Live Evaluation Agent flow | BLOCKED | Depends on blocked Form metadata/response stages |
| Real result email | BLOCKED | `gmail_token.json` and controlled recipient absent |

Existing fake-provider execution remains **FIXTURE PASS** only: real
Evaluation Agent, ResultStore, ResultEmailService, and database read-back ran
against fake Forms/Gmail adapters. It is not live provider success.

Safe audit results:

- Provider implementation/token/config inspection: **PASS**
- Local database availability inspection: **PASS** — 0 students, 2 existing
  assessments, and 2 existing form IDs not treated as isolated test Forms
- No Google Forms, Gmail, Classroom, invitation, or result-email side effect
  was performed.

Backup:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-183836`

## Authorization action required — 2026-10-22 18:42 +05:30

The repository has no separate OAuth authorization helper script. The existing
provider tools use Google's local installed-application flow directly:

- Form creation: `https://www.googleapis.com/auth/forms.body`
- Form metadata: `https://www.googleapis.com/auth/forms.body.readonly`
- Form responses: `https://www.googleapis.com/auth/forms.responses.readonly`
- Gmail sending: `https://www.googleapis.com/auth/gmail.send`

The existing creation token is expired, and the separate metadata, response,
and Gmail token files are absent. No authorization flow was started because it
requires explicit browser consent and a user-approved controlled recipient.
No test email address found in repository test code was treated as authorized.

To continue live verification, the user must explicitly provide:

1. Consent to complete the four Google OAuth scopes above in the browser.
2. A dedicated isolated test Form or permission to create one using the
   Assessment approval action.
3. One controlled recipient email address, explicitly authorized for both the
   invitation and result email.
4. Confirmation that a seeded test student may be inserted into an isolated
   test database or that an existing isolated test student record is supplied.

Until those actions are completed, live publication, response retrieval,
student invitation, and real result email remain **BLOCKED**. No provider
operation was invoked.

Backup:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-184201`

## Live isolated lifecycle execution — 2026-10-22 18:48 +05:30

The user explicitly authorized the controlled recipient
`vikrampal12345ram@gmail.com`, creation of a new isolated Form, and a
synthetic test student. Existing OAuth files were preserved before
authorization; the database was backed up before inserting the synthetic
record.

### OAuth authorization

The existing project tools completed local OAuth authorization without exposing
credentials or tokens:

| Tool | Scope | Result |
|---|---|---|
| `GoogleFormsTool` | `forms.body` | PASS |
| `GoogleFormsMetadataTool` | `forms.body.readonly` | PASS |
| `GoogleFormsResponsesTool` | `forms.responses.readonly` | PASS |
| `GmailTool` | `gmail.send` | PASS |

Backup: `forms_token.json.bak-20261022-184439`.

### Isolated test records

- Synthetic student: `TCO_LIVE_TEST_001`
- School: `TCO_LIVE_TEST`
- Class/section: `TCO Live Test` / `LIVE`
- Authorized recipient: `vikrampal12345ram@gmail.com`
- Database backup: `data/tco.db.bak-20261022-184603`
- No existing student rows were used.

### Live evidence

| Stage | Status | Evidence |
|---|---|---|
| Assessment generation | PASS | Live `POST /api/v1/assessment-workflows/generate`; workflow `tco_2c82e919c8994d98b23674b98e3d4197`; 5 questions; `assessment_ready_for_teacher` |
| Explicit teacher approval | PASS | Live `POST /{workflow_id}/approve-and-publish` returned `assessment_form_published` |
| Google Form creation/publication | PASS | Returned Form ID `1-BAXVSPZU7bR6pcU5S7qZARAbjXw-jt8gMFRU8N8mbI` and responder URL; `form_is_published=true` |
| Assessment persistence | PASS | Database row `assessments.id=3` stored topic, status `published`, Form ID/URL, school, class, and section |
| Form metadata/answer-key read-back | PASS | Real Forms API returned title, quiz=true, 5 questions, 3 identity fields, and responder URL |
| Explicit student invitation | PASS | Live send route returned `assessment_sent_to_students`; database workflow state reported `student_email_total=1`, `student_email_sent=1`, `student_email_failed=0` |
| Controlled Form response submission | PASS | Authorized browser submission returned “Your response has been recorded” |
| Form response retrieval | PASS | Real Forms API returned 1 response with response ID `ACYDBNjqFWbnptsxdANHCKoWji26Gkg0wRrBq9lBKMJeH8h0_JvXqeTfyn9L7WUvp_9hy38` and 8 answers |
| Evaluation Agent | PASS | Live evaluate route returned `evaluation_completed` with 1 evaluation result |
| Result persistence/read-back | PASS | Database `assessment_attempts.id=1`: 12/20, 60%, 3 correct, 2 wrong, real Form response ID |
| Explicit result-email action | PASS | Live send-result-emails route returned completed summary, total=1, sent=1, failed=0 |
| Result email provider response | PASS | Gmail provider returned `sent_count=1`, `failed_count=0`, message ID `1a163c32e8358334` |
| Saved delivery status | PASS | Database result row read back with `result_email_status=sent`, sent timestamp, and no error |

### Ordering limitation

The controlled response was submitted immediately before the explicit
Send-to-Students API call in this run. The invitation itself succeeded to the
authorized recipient, and all later retrieval/evaluation/email stages used the
real response. Therefore the individual live stages are **PASS**, but this run
is not claimed as a perfect ordered invitation-before-submission E2E run.

No production student, existing Form, or uncontrolled recipient was used.

Backup created before this evidence update:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-184829`

## All-eligible-student invitation verification — 2026-10-22 18:55 +05:30

This continuation checked whether the already-published isolated assessment
could safely be sent to all eligible students in the configured database. No
new Form was created, and no delivery call was made because the existing
audience and delivery history did not satisfy the requested no-duplicate
conditions.

### Existing assessment and workflow

| Item | Verified value |
|---|---|
| Workflow ID | `tco_2c82e919c8994d98b23674b98e3d4197` |
| Assessment ID | `3` |
| Workflow state | `evaluation_completed` |
| Form ID | Present in the saved workflow and assessment record |
| Responder URL | Present; existing published Form reused |
| School | `TCO_LIVE_TEST` |
| Class | `TCO Live Test` |
| Section | `LIVE` |
| Prior invitation result | `total=1`, `sent=1`, `failed=0` |

The process-local workflow state remained available. The saved assessment
record remained `published` and matched the same test-only school, class, and
section.

### Recipient eligibility and safety decision

The database-backed delivery selector uses active students filtered by the
assessment's `school_id`, class, and section. The current database contains:

- Total student rows: **1**
- Active student rows: **1**
- Eligible rows for `TCO_LIVE_TEST / TCO Live Test / LIVE`: **1**
- Eligible rows with non-empty email: **1**
- Duplicate eligible email addresses: **0**
- Previously sent eligible recipients: **1**
- New not-already-sent recipients: **0**

The sole eligible record is the synthetic controlled test student used by the
previous live run. Its email address is intentionally omitted from this
report. Because the only eligible recipient was already sent the invitation,
the delivery endpoint was **not called**. No successful invitation was
resent, and no recipient outside the assessment's targeting criteria was
included.

| Stage | Status | Evidence |
|---|---|---|
| Existing API availability | PASS | `GET /openapi.json` returned HTTP 200; existing FastAPI listener reused |
| Workflow/Form verification | PASS | Workflow and database records matched assessment `3`, published Form, and test-only audience |
| Database recipient filtering | PASS | Active, school/class/section-filtered count was 1 |
| Duplicate/history check | PASS | Workflow state recorded one prior sent invitation; no new eligible recipient remained |
| Send invitation to all eligible students | BLOCKED | Sending would resend the sole previously contacted recipient; no authorized retry was requested or supported by the current delivery route |
| Provider response for this continuation | BLOCKED | No provider call was made because the safe recipient set was empty |
| Evaluation/result continuation | BLOCKED | Per instructions, stopped before Form submission and did not evaluate or send result email |

The current published Form is therefore **not appropriate for a broader
database-wide audience**. It is explicitly associated with the isolated
`TCO_LIVE_TEST / TCO Live Test / LIVE` cohort, while the database has no other
student records. A broader invitation requires a separately approved
assessment/Form audience or additional explicitly configured eligible student
records; this run did not alter either.

### Regression tests

Command:

```text
python -m pytest test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_evaluation_result_integration.py test/test_evaluation_result_integration_identity.py test/test_result_email_service.py -q
```

Result: **7 passed in 0.13s**.

Backup created before this update:
`docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-185618`
