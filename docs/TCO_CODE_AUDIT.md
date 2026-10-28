# TCO Code Audit

Audit date: 2026-10-22

## Architecture

- `frontend/` is a React 18, TypeScript, Vite and Tailwind application. `/workspace`
  renders the original three-column workspace: conversation sidebar, chat window and
  review/context panel.
- `frontend/src/services/api.ts` selects the local FastAPI adapter when
  `VITE_USE_MOCK_API=false`; otherwise the demo adapter remains the default.
- `frontend/src/services/fastApiService.ts` stores browser conversation history and
  maps FastAPI workflow responses into the existing chat model.
- `backend/api/main.py` is the unified FastAPI entry point. It registers the master
  execution route, assessment workflow routes and copy-checking routes.
- `backend/graph.py`, the master agent and the registry/task executor route requests
  to assessment, analytics, evaluation and copy-checking capabilities.
- Assessment delivery is implemented in `backend/api/assessment_workflow_routes.py`
  and `backend/workflows/assessment_delivery.py`. Copy checking is implemented in
  `backend/api/copy_checking_routes.py` and `backend/copy_checker/`.

## Verified API surface

| Capability | Route | Contract/state |
|---|---|---|
| Health | `GET /health` | Returns service status and version |
| Master routing | `POST /api/v1/tco/execute` | JSON `teacher_request` plus optional teacher, class, source and intent fields |
| Assessment generation | `POST /api/v1/assessment-workflows/generate` | JSON request with teacher/school/topic/count/marks and source mode |
| Assessment file generation | `POST /api/v1/assessment-workflows/generate-with-file` | Multipart `file` plus teacher/school/topic/count/marks |
| Assessment lifecycle | `GET /{id}`, approve/publish, regenerate, cancel, source approval, student send, evaluate, result emails | In-memory workflow state |
| Copy checking | `POST /api/v1/copy-checking/orchestrated-grade` | Multipart `.txt`, `.txt`, `.pdf`; review may be required |
| Copy checking review | `GET/PUT/POST /api/v1/copy-checking/jobs/{id}/...` | Persisted review and explicit teacher approval |

The frontend text adapter uses `/api/v1/tco/execute`. Upload Material now uses
the real multipart assessment endpoint rather than serializing a `File` in JSON.
The generic composer deliberately rejects unsupported multi-file/copy-checking
uploads instead of silently sending them to the wrong endpoint.

## Findings

### Fixed

1. The development frontend origin on port 5181 was absent from the default CORS
   allow-list. Both localhost and loopback 5181 origins are now allowed by default;
   deployments can still override the list with `TCO_CORS_ORIGINS`.
2. The source-mode popup was opened by selecting Assessment Agent and a source
   selector was permanently rendered in the composer. Agent selection now only
   changes the agent. The centered modal opens after a completed assistant response
   when no clarification is pending, and the composer selector is hidden.
3. Upload Material previously raised a placeholder “not connected” error. A single
   uploaded teacher source is sent as multipart form data to
   `/assessment-workflows/generate-with-file`, with client-side validation that the
   request contains question count and total marks.
4. The frontend build was verified after these changes.

### Partial or blocked

- The unified text route and assessment lifecycle are separate contracts. The
  generic chat adapter does not yet automatically transition an arbitrary natural
  language response into the dedicated generate/approve/publish lifecycle.
- Google Classroom, Google Forms, Gmail, web search, Supabase and live model
  behavior require credentials and external services. No real publication or email
  was attempted.
- Workflow state in the assessment route is process memory (`_states`), so a
  backend restart loses active workflows.
- `tests/test_workspace.py` imports a missing legacy `frontend.workspace_core`
  module and cannot be collected in the current tree.
- The worktree already contained unrelated uncommitted changes, including deleted
  tracked Streamlit files. They were preserved and not reverted.

## Configuration and authentication

Use `VITE_API_BASE_URL` and set `VITE_USE_MOCK_API=false` for the FastAPI adapter.
The frontend reads an optional `tco_access_token` and sends it as a Bearer token.
Supabase configuration remains in the existing auth context. Do not commit
credentials or tokens. Configure exact development origins with
`TCO_CORS_ORIGINS` in environments that do not use the safe defaults.

## Baseline and verification

- `python -m compileall -q backend`: PASS.
- FastAPI route registration and `/health`: PASS.
- CORS preflight from `http://localhost:5181`: PASS.
- Frontend `npm run build` from `frontend/`: PASS.
- Assessment lifecycle and copy-checking integration tests: 23 passed.
- Routing tests: passed in the existing top-level routing test run.
- Legacy workspace Python test: BLOCKED by missing `frontend.workspace_core`.
