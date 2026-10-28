# TCO Copy Checking Integration

## What changed

- Added `backend.copy_checker` as an internal package containing the Copy Checker schemas and services. Imports were namespaced so it cannot collide with the legacy `backend/app` package.
- Added `backend.agents.copy_checking_agent.CopyCheckingAgent` and registered the capability `copy_checking.grade` in TCO's component registry.
- Registered the existing `EvaluationAgent` in the same registry; its capability remains `evaluation.check`.
- Updated the Master Agent's capability guidance so handwritten/scanned answer-copy checking is distinguished from evaluation of normalized submissions.
- Added the unified TCO FastAPI entry point at `backend/api/main.py`. The prior `backend/app/main.py` is left untouched because it is a separate Resume Recommendation API in the provided archive.
- Added `POST /api/v1/copy-checking/grade` and `GET /api/v1/copy-checking/jobs/{job_id}/checked-copy`.
- Added `POST /api/v1/tco/execute` for text requests through the existing LangGraph workflow.
- Added `.env.example`; copy the `COPY_CHECKER_*` values into your existing root `.env` if needed. Do not overwrite existing credentials or commit your real `.env`.

## Run from the repository root

```powershell
# Activate the existing TCO virtual environment first. These are the new direct dependencies.
python -m pip install langgraph langchain-openai pydantic-settings

# Start LM Studio's local OpenAI-compatible server and load the configured vision and text models.
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs` to inspect the API. `/health` should return an `ok` status.

## Two-page copy-checking demo

Call `POST /api/v1/copy-checking/grade` as multipart form data with:

- `question_paper`: UTF-8 `.txt`
- `marking_scheme`: locked TCO `.txt` format
- `answer_copy`: student `.pdf`
- `pages`: query parameter 1 or 2 (defaults to 2)

Example PowerShell request (adjust file paths):

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/copy-checking/grade?pages=2" `
  -F "question_paper=@data\demo\question_paper.txt" `
  -F "marking_scheme=@data\demo\marking_scheme.txt" `
  -F "answer_copy=@data\demo\STU023.pdf"
```

The response contains marks, question-wise feedback, and `checked_copy_url`. Fetch the URL to download the generated PDF. The output is stored under `data/copy_checker/outputs/CC-.../`; temporary input uploads are deleted when the request completes.

## Demo scope and known limitations

- This endpoint intentionally processes only the first one or two pages for the demo.
- The marking scheme must already be locked. This import format supports MCQ and short-answer rows. For short answers, `Correct_Answer` acts as evaluation guidance.
- The question paper is checked for file type and non-empty content, but the current grading model evaluates against the locked marking scheme; the question-paper text is not yet passed into the grading prompt.
- The current whole-page extractor and aggregation flow is run with `expected_question_numbers=[]` to match the successful live two-page test. Therefore this demo does **not** claim to verify full-document question coverage. Extraction uncertainty still stops grading and requires review.
- The verifier and independent grading-review model remain disabled for demo mode.
- The checked-copy renderer places a grading panel to the right of the scanned page; marking directly beside answer bounding boxes is not implemented because extraction does not currently return reliable coordinates.
- The uploaded TCO archive also contained a separate Resume Recommendation API and local resume model/data files. This source overlay preserves its code where present but excludes `.env`, local uploads, caches, and model/data artifacts from the distributable. Extract this overlay into your existing repository; do not use it as a replacement for your data-bearing working copy.

## Endpoints

- `GET /` — API landing metadata
- `GET /health` — health check
- `POST /api/v1/tco/execute` — natural-language requests through the TCO Master Agent / LangGraph
- `POST /api/v1/copy-checking/grade` — execute the integrated Copy Checking Agent against uploaded demo files
- `GET /api/v1/copy-checking/jobs/{job_id}/checked-copy` — download the checked PDF

Recommended additions to the existing root `.gitignore` (merge these lines rather than replacing that file):

```gitignore
.env
.env.*
!.env.example
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
data/copy_checker/work/
data/copy_checker/outputs/
```

Frontend integration is intentionally deferred until the backend API shape has been reviewed and tested.
