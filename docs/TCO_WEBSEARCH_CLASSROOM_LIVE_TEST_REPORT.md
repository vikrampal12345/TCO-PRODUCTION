# TCO Web Search and Google Classroom Assessment Test Report

Date: 2026-10-22

## Scope and safety

This test covered only the original React `/workspace` Assessment Agent
source-selection and retrieval paths. No Google Form was published, no student
invitation was sent, and no result email was sent.

## Initial defects reproduced

| Area | Status | Evidence and root cause |
|---|---|---|
| Clarification to source selection | PASS | Browser request `Create an assessment on Booth Algorithm.` followed by `10 questions, total 20 marks.` preserved the request and displayed the source chooser above the composer. |
| Web Search source contract | FAIL before fix | The backend returned five real Tavily candidates and paused for approval, but the original React UI rendered only the generic clarification; it had no candidate approval control or `/approve-source` call. |
| Google Classroom source contract | FAIL before fix | Browser/API generation returned HTTP 422: `classroom_course_id is required for Classroom mode`. The React payload had no course ID and no course-discovery UI. |
| Source-selected browser retry | BLOCKED/FAIL | After selecting Web Search in the browser, the current configured model provider returned `Error code: 400 - {'error': 'Context size has been exceeded.'}`. This prevented the browser run from reaching candidate approval. The backend source flow itself was verified separately with a direct API call. |

## Changes made

- [ChatWindow.tsx](../frontend/src/components/workspace/ChatWindow.tsx)
  now loads authorized Classroom courses, requires a selected course, stores the
  selected course for the conversation, and avoids concatenating every
  clarification message again during source selection.
- [fastApiService.ts](../frontend/src/services/fastApiService.ts) now sends
  `classroom_course_id`, maps Web Search candidates, approves a selected
  candidate through the existing `approve-source` endpoint, and lists courses.
- [api.ts](../frontend/src/services/api.ts) adds typed Classroom course and
  Web-source approval contracts.
- [ChatMessageItem.tsx](../frontend/src/components/workspace/ChatMessageItem.tsx)
  renders real source candidates with explicit teacher approval actions.
- [useChat.ts](../frontend/src/hooks/useChat.ts) connects source approval to the
  existing conversation and review state.
- [chat.ts](../frontend/src/types/chat.ts) adds typed source candidates.
- [assessment_workflow_routes.py](../backend/api/assessment_workflow_routes.py)
  exposes a read-only `/assessment-workflows/classroom/courses` route using the
  existing `ClassroomTool`.
- [mockApi.ts](../frontend/src/services/mockApi.ts) preserves the same typed
  interface for local demo mode.

## Live provider evidence

### Web Search

**PASS — backend provider and generation path.** A live
`POST /api/v1/assessment-workflows/generate` request with Web Search mode
returned five real Tavily candidates, all marked unapproved. Approving the
first returned candidate through the existing
`/{workflow_id}/approve-source` route fetched/indexed the source and returned:

- status: `assessment_ready_for_teacher`
- source status: `source_ready`
- topic: `Booth Algorithm`
- question count: 10
- total marks: 20

No publication or distribution action was invoked.

**BLOCKED/FAIL — final browser retry.** The browser reached the source chooser,
but the source-selection request ended with the configured model provider's
context-size error before the candidate list could be rendered. This is not
claimed as a browser PASS.

### Google Classroom

**PASS — OAuth/course discovery.** The new read-only route returned one active
course from the authorized Classroom account. Course IDs were not included in
this report.

**BLOCKED — material retrieval/generation.** Sending the selected real course
ID through the backend contract reached Classroom retrieval, but the
read-only material discovery/ingestion request timed out. No Classroom content
was modified. The final assessment draft was therefore not claimed as a live
Classroom PASS.

## Automated verification

```text
Set-Location frontend; npm run build
```

**PASS** — TypeScript and Vite production build completed. Vite emitted the
existing chunk-size warning for the main JavaScript bundle.

```text
python -m compileall -q backend
```

**PASS**.

```text
python -m pytest test/test_web_search.py test/test_web_source_retrieval.py test/test_classroom_discovery.py test/test_classroom_ingestion.py test/test_assessment_result_lifecycle.py test/test_result_email_service.py -q
```

**PASS — 9 passed, 1 warning**.

```text
git diff --check
```

**PASS**.

## Remaining blockers

1. The configured model provider returned a context-size HTTP 400 during the
   final real browser Web Search selection attempt. Provider request/log
   inspection is required to identify whether the limit is caused by the
   provider configuration or an unobserved browser payload expansion.
2. Classroom authentication and course discovery work, but the selected
   course's material retrieval timed out. The course must contain accessible,
   supported material and the provider request must complete before a live
   generated draft can be claimed.

No external student-facing action was performed.

## Final source-workflow verification — 2026-10-22 19:40

### Root causes and fixes

The Web Search browser failure was caused by an unbounded grounded-context
assembly path. Retrieved chunks were interpolated into the Assessment Agent
prompt without a model-request character budget. The RAG formatter and
Assessment Agent now preserve source labels and bound grounded context to
12,000 characters. The frontend also combines the latest clarification with
only earlier requests not already contained in it, preventing duplicated
conversation text while preserving the original topic.

The Classroom delay was not a course-discovery failure. Live timings were:

- authorized course discovery: 4.94 seconds, one course;
- selected-course material listing: 0.94 seconds, 15 materials;
- full selected-material retrieval and generation: 89.0 seconds, completed
  with a real supported PDF and 10 questions.

Classroom ingestion now logs stage timings for course lookup, material lookup,
Drive metadata, Drive download, file loading, vector indexing, and total
ingestion. Logs contain durations and counts only, not credentials or private
content. The workflow was not “fixed” by increasing a timeout.

### Browser evidence

| Stage | Status | Evidence |
|---|---|---|
| Clarification preserves Booth Algorithm request | PASS | Fresh `/workspace` run asked for missing count/marks; the follow-up retained the original topic. |
| Source popup gating and placement | PASS | Popup stayed hidden during clarification and appeared above the composer after `waiting_for_source_selection`. |
| Web Search candidate discovery | PASS | Real browser displayed five Tavily candidates. |
| Web Search explicit source approval | PASS | “Approve and continue” invoked the real approval workflow; no mock success was used. |
| Web Search generated review draft | PASS | Browser reached “Assessment ready for teacher review” with the existing review panel. |
| Classroom course discovery/selection | PASS | Browser loaded one real authorized course and propagated its selected ID. |
| Classroom material retrieval | PASS | Real selected course material was retrieved; the run selected a supported Booth Algorithm PDF. |
| Classroom generated review draft | PASS | Fresh browser run reached “Assessment ready for teacher review” after approximately 95 seconds of UI wait, with no error text. |

### Verification commands

```powershell
Set-Location frontend; npm run build
python -m compileall -q backend
python -m pytest test/test_web_search.py test/test_web_source_retrieval.py test/test_classroom_discovery.py test/test_classroom_ingestion.py -q
git diff --check
```

Results: frontend build **PASS** (existing 730 KB chunk warning), backend
compilation **PASS**, focused source tests **2 passed, 1 warning**, and
`git diff --check` **PASS**.

Files changed in this debugging pass:

- `frontend/src/components/workspace/ChatWindow.tsx`
- `backend/agents/assessment_agent.py`
- `backend/rag/retriever.py`
- `backend/services/classroom_ingestion.py`

Timestamped backups created before editing:

- `frontend/src/components/workspace/ChatWindow.tsx.bak-20261022-193333`
- `backend/agents/assessment_agent.py.bak-20261022-193333`
- `backend/rag/retriever.py.bak-20261022-193333`
- `backend/services/classroom_ingestion.py.bak-20261022-193333`
- `docs/TCO_WEBSEARCH_CLASSROOM_LIVE_TEST_REPORT.md.bak-20261022-193333`

No Form was published, no Classroom content was changed, and no invitation or
email was sent. The Web Search and Classroom source-generation browser stages
are now **PASS**; downstream publication and delivery remain outside this
test's scope.
