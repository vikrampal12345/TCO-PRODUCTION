# TCO Implementation Report

Date: 2026-10-22

## Summary

The original React workspace remains the active `/workspace` route. The targeted
integration fixes address port-5181 CORS, delayed source-mode modal behavior,
composer source-selector visibility, and real multipart upload handling. Existing
uncommitted work was preserved; no files were deleted by this implementation.

## Files changed

- [backend/api/main.py](../backend/api/main.py): added localhost and loopback
  port 5181 to the safe default CORS origins.
- [frontend/src/components/workspace/ChatWindow.tsx](../frontend/src/components/workspace/ChatWindow.tsx):
  stopped source popup activation on agent selection, opened the centered modal
  only after the explicit source-selection gate, and hid the permanent composer
  selector.
- [frontend/src/components/workspace/MessageComposer.tsx](../frontend/src/components/workspace/MessageComposer.tsx):
  removed the hidden composer default that was sending `general_knowledge`
  before source selection.
- [frontend/src/types/workflow.ts](../frontend/src/types/workflow.ts):
  added the explicit `waiting_for_source_selection` UI state.
- [backend/agents/master_agent.py](../backend/agents/master_agent.py) and
  [backend/graph.py](../backend/graph.py): prevent `assessment.create` from
  being scheduled until the source-selection sentinel is replaced by a chosen
  source mode.
- [frontend/src/services/fastApiService.ts](../frontend/src/services/fastApiService.ts):
  routed a valid single teacher-file upload through multipart
  `/assessment-workflows/generate-with-file`; unsupported upload combinations
  return an explicit error.
- [docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md](./TCO_ASSESSMENT_E2E_TEST_REPORT.md):
  records the assessment-only end-to-end trace, verified defects, blockers, and
  actual test results.

Timestamped backups were created before editing:

- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-051900`
- `frontend/src/services/fastApiService.ts.bak-20261022-051900`
- `frontend/src/services/http.ts.bak-20261022-051900`
- `backend/api/main.py.bak-20261022-051900`
- `backend/agents/master_agent.py.bak-20261022-052700`
- `backend/graph.py.bak-20261022-052700`
- `frontend/src/services/fastApiService.ts.bak-20261022-052700`
- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-052700`
- `frontend/src/hooks/useChat.ts.bak-20261022-052700`
- `frontend/src/components/workspace/MessageComposer.tsx.bak-20261022-053300`
- `frontend/src/types/workflow.ts.bak-20261022-052900`

## Verified results

- FastAPI imports, route registration and `/health`: PASS.
- CORS preflight from `http://localhost:5181`: PASS.
- Backend `compileall`: PASS.
- Frontend TypeScript/Vite production build: PASS.
- Focused assessment and copy-checking tests: 23 passed.
- Existing routing/assessment cycle tests: passed.
- Assessment-only regression subset: 4 passed; result-email subset had 3
  pre-existing fixture collection errors.
- Assessment cycle script: reached `assessment_review_failed` after three
  attempts, then hit a pre-existing Windows CP1252 Unicode print error.
- No real Google Form publication, bulk email, Classroom mutation or external
  result-email operation was run.

### End-to-end ordering evidence

Browser network interception against the original `/workspace` proved:

1. A complete assessment request first calls `POST /api/v1/tco/execute` with
   `source_preference: "awaiting_source_selection"`.
2. No assessment generation request is sent before source selection.
3. A mocked `waiting_for_teacher` response renders clarification and keeps the
   source dialog hidden.
4. A mocked `waiting_for_source_selection` response opens the source-selection
   panel immediately above the composer.
5. Selecting source modes sends the dedicated generation request with
   `mode: "general_knowledge"`, `mode: "classroom"`, or `mode: "web_search"`.
6. A mocked ready response renders the existing teacher approval bar and opens
   the review panel path. Review fetches use
   `/api/v1/assessment-workflows/{workflow_id}`.

The Upload Material path remains multipart and uses the backend field names
`teacher_request`, `teacher_id`, `school_id`, `topic`, `question_count`, `marks`,
`conversation_id`, and `file`.

## Remaining limitations

The generic conversational `/tco/execute` adapter now explicitly gates complete
assessment requests until source selection. The selected source then uses the
dedicated assessment delivery API. Assessment workflow state is process-local
and is lost on restart.
Live Classroom, Google Forms, Gmail, Supabase and web-search checks are blocked
without authorized credentials and external test fixtures. The legacy workspace
Python test is blocked by its missing `frontend.workspace_core` import.
See [TCO_ASSESSMENT_E2E_TEST_REPORT.md](./TCO_ASSESSMENT_E2E_TEST_REPORT.md) for
the detailed assessment-only PASS/BLOCKED matrix and the pre-existing failures.

## Start commands

```powershell
# Backend, from repository root
python -m uvicorn backend.api.main:app --reload --port 8000

# Frontend
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5181
```

Use `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`
for the live FastAPI adapter. Keep credentials in local environment/configuration
files and do not commit them.

## Continuation verification — 2026-10-22 16:52 +05:30

The existing Assessment ordering/source-selection implementation was preserved.
The configured provider variables were present without exposing secret values.
Because port 8000 was not running, a temporary local FastAPI instance was
started for safe health, OpenAPI, generation, regeneration, and retrieval
checks.

Actual live workflow evidence:

- `GET /health`: PASS.
- OpenAPI route inspection: PASS; all registered Assessment lifecycle routes
  were present.
- `POST /api/v1/assessment-workflows/generate` in
  `general_knowledge` mode: PASS. The configured model returned 5 Booth
  Algorithm questions, 20 total marks, four options per question, answer key,
  and marking scheme.
- `POST /api/v1/assessment-workflows/{workflow_id}/regenerate`: PASS. Teacher
  feedback produced a revised five-question assessment in the same workflow.
- `GET /api/v1/assessment-workflows/{workflow_id}`: PASS. The revised workflow
  was retrievable with `assessment_ready_for_teacher`, `approval_status=pending`,
  and no form or assessment database ID.

The approval/publication route was deliberately not called. Although provider
configuration variables exist, no isolated test Form target, controlled test
student recipient, or authorized email target was available. Therefore
Google Form publication, database save after publication, student invitation,
live Form response retrieval, Evaluation Agent execution against a published
Form, live result read-back, and result emails remain BLOCKED. Local fixture
coverage for lifecycle/result persistence remains PASS.

Regression command:

```powershell
python -m pytest test_routing.py test_master_routing.py test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py tests/test_copy_checker_integration.py -q
```

Result: **23 passed, 12 warnings**.

Backups created before this update:

- `docs/TCO_ASSESSMENT_E2E_TEST_REPORT.md.bak-20261022-165207`
- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-165207`
- `docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-165207`

## Remaining lifecycle verification — 2026-10-22 16:57 +05:30

No production code changes were required in this continuation. The actual
integration inspection found:

- Google Forms creation credentials/token are present, but the token is scoped
  only for `forms.body`.
- Separate metadata and response-read tokens are absent.
- Gmail OAuth token is absent.
- The configured SQLite database has no student rows, and existing assessment
  form identifiers are not known to be isolated test forms.
- No controlled test recipient was configured.

The approval fixture passed accepted and rejected teacher branches. A
temporary-database fixture then exercised the real Evaluation Agent,
AssessmentResultService, ResultStore, and ResultEmailService with fake Forms and
fake Gmail adapters. It verified result persistence/read-back, successful email
status update, and failure status update without deleting the saved result.

Google Form publication, post-publication assessment persistence, controlled
student invitations, live response retrieval, live evaluation against a Form,
and real result emails remain **BLOCKED** for the exact configuration reasons
above. No provider mutation or email was triggered.

Backup created before this update:
`docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-165708`

## Final focused React corrections — 2026-10-22 18:15 +05:30

The original Assessment workspace now places the source choices immediately
above the composer instead of using a centered full-screen modal. The panel
still opens only after the backend returns `waiting_for_source_selection` and
therefore remains hidden while clarification is pending.

Assessment attachments now automatically use `teacher_file`, so selecting
Upload Material is not a second required action. The browser accept list was
also aligned with the backend-supported multipart extensions:
`.pdf`, `.pptx`, `.txt`, and `.md`.
The composer now clears its content and attachment only after a successful
request. When multipart generation returns `waiting_for_teacher`, the service
retains the file in the current session and includes it with the accumulated
clarification reply.

Changed files:

- `frontend/src/components/workspace/ChatWindow.tsx`
- `frontend/src/components/workspace/MessageComposer.tsx`
- `frontend/src/services/fastApiService.ts`

Backups:

- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-181559`
- `frontend/src/components/workspace/MessageComposer.tsx.bak-20261022-181559`
- `frontend/src/services/fastApiService.ts.bak-20261022-181559`

Validation:

- `Set-Location frontend; npm run build`: **PASS**
- `python -m compileall -q backend`: **PASS**
- `git diff --check`: **PASS**
- `python -m pytest test_routing.py test_master_routing.py test_assessment_cycle.py -q`: **FAIL**, exit 5 after 128.81 seconds with 26 warnings and no passing-test summary
- `python -m pytest test/test_result_email_integration.py -q`: **BLOCKED**, no tests collected, exit 5

No external Form publication, student delivery, evaluation against a live
Form, or result email was performed.

## Clarification context correction — 2026-10-22 18:31 +05:30

Browser verification found that a follow-up typed into the normal composer
could bypass `respondToClarification` and send only the newest sentence. This
caused the Master Agent to lose the original topic and ask for it again.

[useChat.ts](../frontend/src/hooks/useChat.ts) now detects an Assessment
conversation whose latest workflow state is `waiting_for_teacher` and routes
an attachment-free clarification reply through `respondToClarification`.
This preserves the accumulated request while leaving other agent flows
unchanged.

Live browser result:

1. `Create an assessment on Booth Algorithm.` returned a real clarification for
   question count and marks.
2. No source popup was visible during clarification.
3. The clarification answer preserved the original request.
4. The source panel appeared immediately above the composer.
5. AI General Knowledge sent the real dedicated generation request with
   `mode=general_knowledge`.
6. Live generation returned Booth Algorithm questions and teacher review
   controls.

Final verification:

- Frontend build: **PASS**
- Backend compilation: **PASS**
- Assessment lifecycle tests: **4 passed**
- Copy Checking regression: **19 passed, 4 warnings**
- Result-email service tests: **FAIL**, 3 undefined `result_store` fixture errors
- Script-only pytest targets: **BLOCKED**, no tests collected

Backup created for the clarification hook:
`frontend/src/hooks/useChat.ts.bak-20261022-183121`

## Web Search and Classroom source-flow correction — 2026-10-22 19:40

The remaining live source-workflow defects were corrected without changing
Analytics Agent or Copy Checking Agent behavior.

### Implementation

- `frontend/src/components/workspace/ChatWindow.tsx` now preserves the
  original assessment request when the latest clarification does not repeat
  the topic, while avoiding duplicate nested request text.
- `backend/rag/retriever.py` bounds assembled grounded context to 12,000
  characters and retains source labels/provenance.
- `backend/agents/assessment_agent.py` applies the same final prompt boundary
  and logs only prompt/context sizes.
- `backend/services/classroom_ingestion.py` records duration and count-only
  timing for each external/material-processing stage.

### Evidence

The real browser Web Search flow displayed five Tavily candidates, invoked the
real source approval action, and reached the existing “Assessment ready for
teacher review” panel. The real browser Classroom flow listed the authorized
course, propagated its course ID, retrieved a supported Booth Algorithm PDF,
and reached the same review panel after approximately 95 seconds.

Live diagnostic timings showed course discovery at 4.94 seconds, material
listing at 0.94 seconds, and a completed selected-material generation at
approximately 89 seconds. This identified the earlier report's timeout as a
long uninstrumented generation path, not a failed Classroom listing.

### Validation

- `Set-Location frontend; npm run build`: **PASS**
- `python -m compileall -q backend`: **PASS**
- `python -m pytest test/test_web_search.py test/test_web_source_retrieval.py test/test_classroom_discovery.py test/test_classroom_ingestion.py -q`: **2 passed, 1 warning**
- `git diff --check`: **PASS**

Backups created before this source-flow edit:

- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-193333`
- `backend/agents/assessment_agent.py.bak-20261022-193333`
- `backend/rag/retriever.py.bak-20261022-193333`
- `backend/services/classroom_ingestion.py.bak-20261022-193333`

Documentation preservation backups:

- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-194217`
- `docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-194217`

## Result-email fixture and lifecycle verification — 2026-10-22 18:35 +05:30

The result-email pytest setup was repaired in
[test_result_email_service.py](../test/test_result_email_service.py) using
temporary-database fixtures and the real `ResultStore` API. The standalone
fake-provider lifecycle fixture was also repaired in
[test_result_email_integration.py](../test/test_result_email_integration.py)
by seeding only its isolated controlled student and assessment.

Backups:

- `test/test_result_email_service.py.bak-20261022-183356`
- `test/test_result_email_integration.py.bak-20261022-183517`

Verification:

- Assessment/result/evaluation/result-email pytest set: **7 passed**
- Standalone `python test/test_result_email_integration.py` fake-provider result→email lifecycle: **PASS**
  - Saved result and provider success status: `sent`
  - Simulated provider failure preserved result and saved status: `failed`
- Approval fixture: **PASS**
- Routing scripts: **PASS**
- Copy Checking regression: **19 passed, 4 warnings**
- Frontend build: **PASS**
- Backend compilation: **PASS**

The original React Assessment lifecycle controls remain explicit:
approval/publish, Send to Students, evaluation, and Send Results by Email are
not chained automatically. Live Google Form publication, database persistence
through a real published Form, student invitation, response retrieval, and
Gmail delivery remain **BLOCKED** because no isolated authorized external
fixture or Gmail token is available. No external side effect was triggered.

## Live isolated lifecycle execution — 2026-10-22 18:48 +05:30

After explicit user authorization, the existing OAuth tools obtained
`forms.body`, `forms.body.readonly`, `forms.responses.readonly`, and
`gmail.send`. The existing Forms token was backed up, and the database was
backed up before adding one synthetic student for the authorized recipient.

Live Assessment lifecycle evidence:

- 5-question Booth Algorithm assessment reached teacher review.
- Explicit approval created and published a new Google Form.
- Returned Form ID and responder URL were persisted in `assessments.id=3`.
- Real Forms metadata and answer key were read back.
- Explicit student delivery sent to exactly one authorized recipient:
  `student_email_total=1`, `student_email_sent=1`, `student_email_failed=0`.
- One controlled response was retrieved from the real Form.
- Existing Evaluation Agent completed and saved a real result: 12/20, 60%.
- Explicit result-email action returned Gmail success with one provider message ID.
- Actual database read-back showed `result_email_status=sent`.

The response submission occurred immediately before the send-to-students call
in this run; that ordering limitation is recorded in the E2E report rather
than hidden. All provider operations used the isolated Form and explicitly
authorized recipient only.

Backups:

- `forms_token.json.bak-20261022-184439`
- `data/tco.db.bak-20261022-184603`
- `docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-184829`

## Live provider readiness audit — 2026-10-22 18:38 +05:30

Provider implementations and token metadata were inspected without exposing
secrets:

- Form creation uses `forms_token.json` and `forms.body`; the token has a
  refresh token but its recorded expiry is past, so it was not refreshed.
- Form metadata uses a separate `forms_metadata_token.json` with
  `forms.body.readonly`; it is absent.
- Form responses use a separate `forms_responses_token.json` with
  `forms.responses.readonly`; it is absent.
- Gmail uses a separate `gmail_token.json` with `gmail.send`; it is absent.
- No dedicated test Form ID or controlled recipient configuration exists.
- `data/tco.db` contains zero students, so real delivery cannot safely select a
  recipient.

Live publication, database persistence through a newly published Form, student
invitation, response retrieval, live evaluation, and Gmail result delivery are
therefore **BLOCKED**. Existing fake-provider coverage remains **FIXTURE PASS**
or **MOCK PASS**, not live provider success. No external provider call was made.

Backup:
`docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-183836`

## Authorization action required — 2026-10-22 18:42 +05:30

The existing Google tools are the only authorization entry points; no separate
OAuth helper script is present. They use local installed-app consent with
`forms.body`, `forms.body.readonly`, `forms.responses.readonly`, and
`gmail.send` in separate token files.

Live completion is **BLOCKED** until the user explicitly consents in the
browser, provides or authorizes an isolated test Form, approves one controlled
recipient for invitation and result email, and permits an isolated test
student record. No provider call was made and no repository test address was
treated as authorized.

Backup:
`docs/TCO_IMPLEMENTATION_REPORT.md.bak-20261022-184201`
