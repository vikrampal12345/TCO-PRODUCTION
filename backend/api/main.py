from __future__ import annotations

import os
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.api.copy_checking_routes import router as copy_checking_router
from backend.api.assessment_workflow_routes import router as assessment_workflow_router


class TCOExecuteRequest(BaseModel):
    """Text-based request contract for the TCO Master Agent."""

    teacher_request: str = Field(min_length=1, max_length=10000)
    request_id: str | None = None
    teacher_id: str | None = None
    school_id: str | None = None
    conversation_id: str | None = None
    intent: str | None = None
    class_level: str | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    question_count: int | None = Field(default=None, ge=1)
    marks: int | None = Field(default=None, ge=1)
    student_name: str | None = None
    generation_mode: str | None = None
    requested_source: str | None = None
    source_preference: str | None = None
    source_url: str | None = None


app = FastAPI(
    title="TCO Unified Backend API",
    version="0.2.0",
    description=(
        "Unified FastAPI entry point for the TCO Master Agent and registered "
        "specialist agents, including the local-LLM Copy Checking Agent."
    ),
)

origins = [
    item.strip()
    for item in os.getenv(
        "TCO_CORS_ORIGINS",
        (
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5181,http://127.0.0.1:5181,"
            "http://localhost:5182,http://127.0.0.1:5182,"
            "http://localhost:5184,http://127.0.0.1:5184,"
            "http://localhost:3000"
        ),
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(copy_checking_router)
app.include_router(assessment_workflow_router)


@app.get("/")
def home() -> dict[str, str]:
    return {
        "service": "TCO Unified Backend API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tco-unified-backend", "version": app.version}


@app.post("/api/v1/tco/execute")
def execute_tco_request(request: TCOExecuteRequest) -> Any:
    """Run a text request through the existing LangGraph Master Agent."""
    from backend.graph import workflow

    initial_state: dict[str, Any] = {
        "teacher_request": request.teacher_request.strip(),
        "request_id": request.request_id or f"REQ-{uuid4().hex[:12]}",
        "metadata": {"api": "tco-fastapi"},
    }
    for key in (
        "teacher_id", "school_id", "conversation_id", "intent", "class_level",
        "subject", "chapter", "topic", "question_count", "marks", "student_name",
        "generation_mode", "requested_source", "source_preference", "source_url",
    ):
        value = getattr(request, key)
        if value is not None:
            initial_state[key] = value

    try:
        result = workflow.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="TCO workflow failed to execute.") from exc
    return jsonable_encoder(result)
