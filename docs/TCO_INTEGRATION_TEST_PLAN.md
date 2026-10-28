# TCO Integration Test Plan

Audit date: 2026-10-22

## Safe automated scenarios

| Scenario | Status | Evidence |
|---|---|---|
| Assessment request with complete details | PASS | Browser assertion: first request was `/tco/execute` with `awaiting_source_selection`; mocked gate returned `waiting_for_source_selection` |
| Assessment request with missing details | PASS | Browser mock returned `waiting_for_teacher`; clarification rendered |
| Source popup closed before request | PASS | Browser snapshot and request assertion |
| Source popup hidden while clarification is pending | PASS | Browser assertion: dialog count 0 while missing-marks clarification was visible |
| Source popup after required details | PASS | Browser mock gate response produced the source-selection panel |
| Source selector not permanently in composer | PASS | Browser snapshot showed no composer source selector |
| No generation before source selection | PASS | Browser network assertion: only `/tco/execute` before selection; no `/generate` request |
| Four source labels and source-selection panel | PASS | Browser accessibility snapshot and source choices immediately above the composer |
| AI General Knowledge route | PASS | Browser request assertion: `/assessment-workflows/generate` with `mode=general_knowledge` |
| Upload Material multipart route | PASS | `generate-with-file` route registered; frontend sends `FormData` |
| Upload preserves prior request when composer text is empty | PASS | Service reconstructs teacher request from conversation history |
| Google Classroom route | BLOCKED | Browser request shape is correct (`mode=classroom`), but backend requires `classroom_course_id` and no authorized course fixture/UI selection was available |
| Web Search approval/retrieval | BLOCKED | Browser request shape is correct (`mode=web_search`), but live source discovery/approval was not authorized |
| Assessment review and revision | PASS | Assessment lifecycle tests; frontend now uses dedicated workflow endpoints |
| Approval and publish | BLOCKED | Would create an external Google Form; no authorization |
| Explicit student-send | BLOCKED | Requires real student database/Gmail integration; no send authorized |
| Evaluation and persistence | BLOCKED | Lifecycle unit coverage exists, but no safe published test Form/response was available |
| Explicit result-email action | BLOCKED | Real Gmail send not authorized |
| Analytics Agent | PASS | Existing analytics routing/service tests |
| Copy Checking Agent | PASS | `tests/test_copy_checker_integration.py`: 23 tests passed with assessment lifecycle |
| Backend unavailable/error messaging | PASS | `apiRequest` preserves HTTP detail and distinguishes network errors |
| Invalid input | PASS | FastAPI/Pydantic validation and upload extension/size checks |
| Authentication regression | BLOCKED | Supabase credentials/browser session not available for automated live test |
| Streamlit backup preservation | BLOCKED | Existing tracked deletions were pre-existing and intentionally not reverted |

## Commands executed

```powershell
Set-Location frontend
npm run build

Set-Location ..
python -m compileall -q backend
python -c "from fastapi.testclient import TestClient; from backend.api.main import app; c=TestClient(app); print(c.get('/health').json())"
python -m pytest test_routing.py test_master_routing.py test_assessment_cycle.py -q
python -m pytest test\test_assessment_result_lifecycle.py tests\test_copy_checker_integration.py -q
```

The focused assessment/copy-checking run completed with 23 passed tests.
The legacy `tests/test_workspace.py` collection is blocked because
`frontend.workspace_core` is not present. No real Google Form, email, Classroom
mutation or external publication was performed.

Browser request assertions used mocked backend responses to avoid model latency
and external side effects. They demonstrated the exact request ordering and
source-mode payloads for general knowledge, Classroom and Web Search.

The later assessment-only run had 4 passed tests and 3 pre-existing collection
errors because `test_result_email_service.py` requires an undefined
`result_store` fixture. The standalone assessment cycle script reached its
expected review-failure path but then hit a Windows CP1252 Unicode print error.

## Source workflow verification — 2026-10-22

| Scenario | Status | Evidence |
|---|---|---|
| Web Search bounded grounded context | PASS | RAG and Assessment Agent now enforce a 12,000-character context budget while retaining source labels. |
| Web Search browser candidate discovery and approval | PASS | Real Tavily candidates appeared in the browser and explicit approval reached the teacher review panel. |
| Classroom course discovery and selection | PASS | One authorized course was listed and its ID was sent in the generation request. |
| Classroom material retrieval and generation | PASS | 15 materials were listed; a supported Booth Algorithm PDF was retrieved and the browser reached the teacher review panel in about 95 seconds. |
| Classroom timeout diagnosis | PASS | Timings isolated healthy course/material listing and a long but successful retrieval/generation path; no timeout increase was used. |

Focused source regression command:

```powershell
python -m pytest test/test_web_search.py test/test_web_source_retrieval.py test/test_classroom_discovery.py test/test_classroom_ingestion.py -q
```

Result: **2 passed, 1 warning**. Frontend production build, backend
compilation, and `git diff --check` also passed. No external publication,
student invitation, or email was performed.

## Manual smoke test

1. Start the backend from the repository root with `python -m uvicorn backend.api.main:app --reload --port 8000`.
2. In a second terminal, run `Set-Location frontend; npm run dev -- --host 127.0.0.1 --port 5181`.
3. Set `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`.
4. Open `/workspace`, select an agent, and verify that selecting Assessment Agent
   does not open a source modal.
5. Submit a complete assessment request. Verify that the modal appears only after
   the assistant response and that it is centered.
6. For Upload Material, include question count and total marks, attach one
   supported file, and verify the network request is multipart to
   `/assessment-workflows/generate-with-file`.
7. Stop the backend and verify the user sees the actionable network error.

## Continuation evidence — 2026-10-22 16:52 +05:30

The remaining safe live generation path was exercised without repeating the
already-passed source-selection ordering checks.

| Scenario | Status | Evidence |
|---|---|---|
| Provider configuration presence | PASS | Required provider variable names were present; secret values were not printed |
| Running backend health | PASS | `/health` returned service `tco-unified-backend`, version `0.2.0` |
| Actual General Knowledge assessment generation | PASS | Live `/api/v1/assessment-workflows/generate` returned 5 Booth Algorithm MCQs for 20 marks |
| Review output mapped to teacher workflow | PASS | Returned state was `assessment_ready_for_teacher`, review passed, approval remained pending |
| Actual review revision | PASS | Live `/regenerate` returned revised questions in the same workflow |
| Review retrieval | PASS | Live `GET /{workflow_id}` returned the revised assessment |
| Approval/Form/database lifecycle | BLOCKED | No isolated authorized test Form target was available; endpoint was intentionally not invoked |
| Student invitation | BLOCKED | No controlled recipient was authorized |
| Evaluation/result read-back | FIXTURE PASS / BLOCKED LIVE | Local lifecycle and result-store tests passed; no safe published Form response existed |
| Result email | BLOCKED | No controlled recipient was authorized |

Exact regression command:

```powershell
python -m pytest test_routing.py test_master_routing.py test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py tests/test_copy_checker_integration.py -q
```

Result: **23 passed, 12 warnings**. The temporary backend was started only for
health, OpenAPI, generation, regeneration, and retrieval checks. No external
publication or email route was called.

Backup created before this update:
`docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-165207`

## Final focused React verification — 2026-10-22 18:15 +05:30

| Scenario | Status | Evidence |
|---|---|---|
| Source popup immediately above composer | PASS | Fixed full-screen centered rendering was replaced by an input-area panel in `ChatWindow.tsx` |
| Popup hidden during clarification | PASS | Panel remains conditional on `waiting_for_source_selection` |
| Attachment selects Upload Material automatically | PASS | `fastApiService.ts` derives `teacher_file` for Assessment attachments |
| Attachment survives clarification/retry | PASS | Composer state is retained on send failure and the service keeps the pending file while the backend is waiting for teacher clarification |
| Supported upload extensions | PASS | Composer accept list is aligned to backend-supported `.pdf,.pptx,.txt,.md` |
| Multipart field contract | PASS | Existing FormData request uses the registered `generate-with-file` field names |
| Frontend production build | PASS | `npm run build` |
| Backend compilation | PASS | `python -m compileall -q backend` |
| Focused routing/cycle command | FAIL | `python -m pytest test_routing.py test_master_routing.py test_assessment_cycle.py -q` exited 5 after 128.81s; output contained 26 deprecation warnings but no passing-test summary |
| Result-email integration fixture | BLOCKED | Collection returned “no tests ran” and exit code 5 |

The earlier request-ordering, source-specific routing, live generation, review,
revision, lifecycle fixture, and external-provider blocker results remain as
recorded above. No production external integration was invoked.

## Real incomplete-query browser verification — 2026-10-22 18:31 +05:30

| Scenario | Status | Evidence |
|---|---|---|
| `Create an assessment on Booth Algorithm.` | PASS | Submitted in the original `/workspace` |
| Missing mandatory details | PASS | Master Agent asked for number of questions and total marks |
| Popup hidden during clarification | PASS | No dialog was present while clarification was pending |
| Follow-up preserves original request | PASS | Fixed hook routes pending Assessment clarification through `respondToClarification`; subsequent generation payload included the original request and accumulated answer |
| Popup appears after clarification | PASS | `waiting_for_source_selection` response opened the panel above the composer |
| AI General Knowledge generation | PASS | Real request used `/assessment-workflows/generate` with `mode=general_knowledge` |
| Generated assessment/review | PASS | Live Booth Algorithm questions returned and teacher review controls displayed |

The corrected pytest discovery findings are:

- Root `test_routing.py`, `test_master_routing.py`, and `test_assessment_cycle.py`
  are executable scripts, not pytest suites; this caused the previous exit 5.
- `test/test_result_email_integration.py`,
  `test/test_google_forms_metadata.py`, and
  `test/test_google_forms_responses.py` have no pytest test functions and are
  script-only.
- Actual Assessment lifecycle tests: **4 passed**.
- Copy Checking regression: **19 passed, 4 warnings**.
- Result-email service tests: **3 setup errors** because `result_store` is not
  defined as a pytest fixture.

## Remaining lifecycle evidence — 2026-10-22 16:57 +05:30

| Scenario | Status | Evidence |
|---|---|---|
| Approval accepted/rejected orchestration | FIXTURE PASS | `python test_assessment_approval.py` passed both branches |
| Real approval and Google Form publication | BLOCKED | No isolated authorized test Form; approval is intentionally not invoked |
| Assessment database read-back after publication | BLOCKED | No safe publication occurred |
| Student invitation | BLOCKED | Configured database has no student rows; no controlled recipient or Gmail token |
| Google Forms metadata/response retrieval | BLOCKED | Separate metadata/response tokens are missing; no safe Form ID was available |
| Evaluation Agent | FIXTURE PASS | Fake Forms metadata and one controlled synthetic response exercised the real Evaluation Agent |
| Result persistence/read-back | FIXTURE PASS | Temporary ResultStore persisted and retrieved the evaluated result |
| Result email success | FIXTURE PASS | Fake Gmail path updated stored email status to `sent` |
| Result email failure | FIXTURE PASS | Saved result remained available and stored status `failed` after simulated provider failure |
| Real result email | BLOCKED | No Gmail OAuth token or authorized test recipient |

The configured `forms_token.json` is scoped for form-body access only. Existing
assessment rows contain form identifiers but are not known to be isolated test
forms, so they were not queried or changed. The configured database contains no
student records. No real external side effects were performed.

Backup created before this update:
`docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-165708`

## React/Streamlit integration mapping

The detailed stage-by-stage mapping is now recorded in
[`TCO_REACT_ASSESSMENT_INTEGRATION.md`](./TCO_REACT_ASSESSMENT_INTEGRATION.md).
It confirms that the original React workspace has verified clarification,
source selection, source-specific generation, upload multipart handling,
review, revision, rejection, and approval endpoint wiring. The legacy
`frontend/workspace-preview.tsx` lifecycle buttons are not counted as original
React `/workspace` integration.

The remaining React boundary is explicit post-publication actions:
student delivery, evaluation, and result emails. Their backend routes and
Streamlit references are mapped, but the original React workspace does not yet
expose those controls. These stages remain BLOCKED live by the missing isolated
Form, Forms read tokens, student records, Gmail token, and controlled recipient.

## Assessment lifecycle fixture completion — 2026-10-22 18:35 +05:30

The result-email tests were corrected without changing production code:

- `test/test_result_email_service.py` now defines isolated pytest fixtures for
  `ResultStore`, student, assessment, and result records.
- `test/test_result_email_integration.py` now seeds its copied temporary
  database with the controlled student and assessment expected by the fake
  Forms/Email flow.

Actual results:

| Command | Result |
|---|---|
| `python -m pytest test/test_result_email_service.py test/test_result_email_integration.py test/test_assessment_result_lifecycle.py test/test_assessment_result_service.py test/test_result_store.py test/test_evaluation_result_integration.py test/test_evaluation_result_integration_identity.py -q` | **7 passed** |
| `python test/test_result_email_integration.py` | **PASS**; success and simulated Gmail failure both persisted/read back status |
| `python test_assessment_approval.py` | **PASS** |
| `python test_routing.py` | **PASS** |
| `python test_master_routing.py` | **PASS** |
| `python -m pytest tests/test_copy_checker_integration.py -q` | **19 passed, 4 warnings** |
| Frontend build | **PASS** |
| Backend compileall | **PASS** |

Live Form publication, student invitation, response retrieval, and Gmail
delivery remain **BLOCKED**, not mocked-as-live: the environment has no
isolated authorized Form/response fixture, no Gmail OAuth token, and no
authorized controlled recipient. The React controls and route contracts remain
explicit and are covered as **MOCK PASS**.

## Live provider readiness audit — 2026-10-22 18:38 +05:30

No external operation was called. Exact readiness findings:

| Requirement | Status | Evidence/blocker |
|---|---|---|
| Forms creation OAuth client | PASS | `credentials.json` present with configured installed-client metadata |
| Forms creation scope | PASS | Existing token metadata contains `forms.body` |
| Forms creation authorization | BLOCKED | Token metadata expired; refresh intentionally not attempted |
| Form metadata scope/token | BLOCKED | `forms_metadata_token.json` absent; tool requires `forms.body.readonly` |
| Form response scope/token | BLOCKED | `forms_responses_token.json` absent; tool requires `forms.responses.readonly` |
| Dedicated isolated test Form | BLOCKED | No Form ID/configuration supplied; existing IDs not known safe fixtures |
| Gmail send scope/token | BLOCKED | `gmail_token.json` absent; tool requires `gmail.send` |
| Controlled test recipient | BLOCKED | No approved recipient; local database has zero students |

No approval/publication, invitation, response retrieval, or result-email
endpoint was invoked. Existing fake-provider results remain **FIXTURE PASS**,
not live success.

## Live isolated lifecycle execution — 2026-10-22 18:48 +05:30

The user authorized one controlled recipient, a new isolated Form, and a
synthetic test student. OAuth completed through the existing tools with
`forms.body`, `forms.body.readonly`, `forms.responses.readonly`, and
`gmail.send`.

| Scenario | Status | Evidence |
|---|---|---|
| Live Assessment generation | PASS | 5-question Booth Algorithm workflow reached teacher-ready state |
| Explicit approval and publication | PASS | New Form published; real Form ID/URL returned |
| Assessment database persistence | PASS | `assessments.id=3` read back with published Form metadata |
| Form metadata/answer-key retrieval | PASS | Real Forms API returned quiz metadata and 5 questions |
| Controlled student invitation | PASS | 1 recipient sent, 0 failed |
| Controlled response retrieval | PASS | 1 real Form response with 8 answers |
| Evaluation and result persistence | PASS | Real evaluation completed; result read back as 12/20 and 60% |
| Controlled result email | PASS | Gmail reported 1 sent, 0 failed; database status `sent` |

The response was submitted immediately before the invitation route was called
in this run. This ordering limitation is recorded explicitly; no claim of a
perfect ordered invitation-before-submission run is made. No production
student or existing Form was used.

Backups:

- `forms_token.json.bak-20261022-184439`
- `data/tco.db.bak-20261022-184603`
- `docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-184829`

## Authorization action required — 2026-10-22 18:42 +05:30

No standalone authorization script exists; the existing tools invoke
`InstalledAppFlow.run_local_server` directly. Required scopes are:

- Forms creation: `forms.body`
- Forms metadata: `forms.body.readonly`
- Forms responses: `forms.responses.readonly`
- Gmail: `gmail.send`

Live testing is **BLOCKED** pending explicit browser consent for these scopes,
an isolated test Form/create authorization, an explicitly approved controlled
recipient email, and permission to seed or use an isolated test student
record. No repository test address was assumed to be authorized and no
provider operation was attempted.

Backup:
`docs/TCO_INTEGRATION_TEST_PLAN.md.bak-20261022-184201`

## React lifecycle implementation — 2026-10-22 17:59 +05:30

The original `/workspace` now exposes the explicit lifecycle controls in the
existing review panel:

- Approval calls `approve-and-publish`, then reloads the workflow to display
  `responder_url` and `assessment_id`.
- `Send assessment to students` appears only after the backend returns
  `assessment_form_published`.
- `Evaluate student responses` appears only for backend-eligible published
  states and displays returned evaluation summaries.
- `Send saved results by email` appears only when evaluation is completed and
  at least one returned result contains a saved `result_id`.

Each action uses the real FastAPI adapter and preserves the existing
`workflow_id`. No automatic action is chained after generation or source
selection.

Status: **MOCK PASS** for UI/API integration and **BLOCKED LIVE** for external
Forms/Gmail execution. See the Assessment E2E report for exact files, backups,
commands, and blockers.
