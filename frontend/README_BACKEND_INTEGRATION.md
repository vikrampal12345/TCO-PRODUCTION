# TCO Frontend ↔ FastAPI integration

This frontend has a working demo mode and an opt-in FastAPI mode. It does not contain the TCO backend itself. Match the endpoint paths and response fields in this guide to the backend's actual routers before using real teacher data.

## 1. Choose the mode

This bundle includes `backend/frontend_test_api`, a local FastAPI adapter for frontend integration tests. It is not the production TCO agent backend. Use `VITE_USE_MOCK_API=true` for frontend-only preview, or `false` to connect to the local FastAPI adapter.

### Frontend-only demo mode

```powershell
cd path\to\tco-frontend-mvp
npm install
Copy-Item .env.example .env
npm run dev
```

Demo mode uses `src/services/mockApi.ts` and simulated login. No backend is contacted.

### Connect to FastAPI

Edit `.env`:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_AUTH_LOGIN_PATH=/auth/login
VITE_AUTH_SIGNUP_PATH=/auth/signup
VITE_AUTH_GOOGLE_PATH=/auth/google
```

The base URL must include exactly the prefix your API routers use. For example, with `APIRouter(prefix="/api/v1")`, use `http://127.0.0.1:8000/api/v1`. Restart Vite after changing `.env`.

The Settings page's FastAPI URL is also read by the API client after saving preferences. Environment values are the initial defaults.

## Endpoint contract used by the frontend adapter

| Method | Path relative to `VITE_API_BASE_URL` | Purpose |
|---|---|---|
| POST | `/auth/login` | JSON `{ email, username, password }`; response should contain `user` and `access_token` (or `token`) |
| POST | `/auth/signup` | JSON name/full_name, email, password, role, school/institution |
| POST | `/auth/google` | Optional: OAuth token response or `{ authorization_url }` |
| GET | `/conversations` | List of conversations or `{ items: [...] }` / `{ conversations: [...] }` |
| POST | `/conversations` | Create `{ title, initial_message }` |
| GET | `/conversations/{conversation_id}` | One conversation, including message history |
| PATCH | `/conversations/{conversation_id}` | Rename with `{ title }` |
| DELETE | `/conversations/{conversation_id}` | Delete conversation |
| POST | `/conversations/{conversation_id}/messages` | JSON `{ conversation_id, content, attachments }`; if actual files are attached, multipart fields are `content`, repeated `files`, and JSON text field `attachments` |
| POST | `/conversations/{conversation_id}/clarifications` | `{ option_id, custom_value }` |
| POST | `/conversations/{conversation_id}/archive` | Archive a conversation |
| POST | `/workflows/{workflow_id}/approve` | `{ conversation_id, review_type, notes }` |
| POST | `/workflows/{workflow_id}/reject` | `{ conversation_id, reason }` |
| POST | `/workflows/{workflow_id}/revision` | `{ conversation_id, instructions }` |
| GET | `/reviews/{review_type}/{review_id}` | Load an artifact/review panel payload |

### Message response shape

The message endpoint should preferably return:

```json
{
  "user_message": { "id": "...", "sender": "teacher", "content": "...", "timestamp": "..." },
  "tco_message": {
    "id": "...",
    "sender": "tco",
    "content": "...",
    "workflow_progress": { "workflow_id": "...", "type": "assessment", "state": "review_required", "active_agent": "Assessment Agent", "steps": [] },
    "clarification": null,
    "approval": null,
    "review_type": "assessment",
    "review_data_id": "..."
  }
}
```

The client can also accept camelCase keys (`userMessage`, `tcoMessage`) or a simple `{ reply: "..." }` response. UI-specific workflow/clarification/approval fields should match `src/types/workflow.ts`; normalize them server-side if the agents produce a different internal structure.

## Authentication and security

- Login sends JSON credentials to the configured login route.
- If the response contains `access_token` or `token`, it is stored as `tco_access_token` and sent as `Authorization: Bearer ...` on subsequent API calls.
- The response should include a user object with `id`, `name` (or `full_name`), `email`, `role`, and optionally `school`.
- The frontend route guard is a UX convenience only. Every private endpoint must independently authenticate and authorize the teacher on the backend.
- Never put a database password, service-role secret, provider key, or LLM API key in the Vite `.env`; Vite variables prefixed with `VITE_` are exposed to the browser.
- Google sign-in only works if the backend OAuth flow is configured. A frontend button alone is not Google authentication.

## File upload + CORS

The paperclip button now selects actual local files; it no longer invents demo filenames. The FastAPI message endpoint must accept multipart form data when files are attached and persist/process those bytes. Validate extension, MIME type and file size server-side. Do not trust frontend metadata.

Allow the Vite origin (normally `http://localhost:5173`) via FastAPI `CORSMiddleware`; include authorization and content-type headers. Example:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Adjust origins for deployment; do not use wildcard origins with credentials in production.

## Verify connection

Start the backend first, then from this frontend directory run:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
npm run check:backend
```

This queries FastAPI's `/openapi.json`, verifies the server responds, and flags expected route names that are not registered. Then run:

```powershell
npm run build
npm run dev
```

In real mode test signup/login, refresh, chat persistence, question generation, clarification, artifact review/approval, and file upload. Successful OpenAPI reachability alone does not prove database writes or agent execution work.

## Integration boundary

The bundle provides a separate local adapter at `backend/frontend_test_api/main.py`. It persists test users/conversations and returns labelled placeholder review data, but it does **not** connect to the project's real Master Agent, Assessment Agent, Answer Sheet Checking/Evaluation Agent, OCR, RAG or LLM. Once those actual backend modules are available, wire the orchestration function in this adapter to them (or connect the frontend directly to the production routes) instead of treating test responses as real AI results.
