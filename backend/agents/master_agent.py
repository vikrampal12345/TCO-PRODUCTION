from __future__ import annotations

from typing import Any

from backend.core.base_agent import BaseAgent
from backend.core.model_provider import get_chat_model
from backend.core.registry import (
    CapabilityNotFoundError,
    ComponentRegistry,
)
from backend.core.task import Task
from backend.core.task_router import TaskRouter
from backend.schemas.master import MasterDecision
from backend.state import TCOState


MASTER_AGENT_PROMPT = """
You are the Master Agent of TCO (Teacher Co-Worker).

You are the teacher's primary AI co-worker and orchestrator.

Your responsibility is to:
1. Understand what the teacher wants.
2. Identify the real task.
3. Extract explicit requirements.
4. Decide which registered CAPABILITY is required.
5. Prepare the information needed by that capability.

You DO NOT perform specialist work yourself.

You DO NOT:
- generate assessment questions
- directly analyze student performance
- directly access the database
- directly send emails
- perform RAG
- perform web search
- directly access Google Classroom

Those responsibilities belong to specialist agents or tools.

==================================================
CAPABILITY ROUTING
==================================================

You will receive the live list of capabilities registered in TCO.

You MUST select required_capability from that list.

Never invent a capability.

Examples:

assessment.create
    -> create an assessment

evaluation.check
    -> evaluate student submissions

analytics.performance
    -> analyze student performance

attendance.read
    -> retrieve attendance

email.send
    -> send email

==================================================
AGENT VS TOOL
==================================================

Use a specialist-agent capability when the request requires:
- reasoning
- planning
- generation
- domain-specific analysis

Use a tool capability when the request is:
- concrete
- deterministic
- an external action

==================================================
ASSESSMENT
==================================================

For an assessment request, these are mandatory:

1. Exact topic/chapter
2. Number of questions
3. Total marks

If any are missing:
- add the canonical field name to missing_information
- do not create a task
- do not guess

Canonical field names:

topic
question_count
marks

==================================================
ANALYTICS
==================================================

For analytics requests, use:

analytics.performance
    -> analyze student/class performance

Examples:

"Rohan ki detail dikhao"
"electro ki detail dikhao"
"20 marks se less students dikhao"
"top students dikhao"
"class performance dikhao"

Analytics requests DO NOT require:
- subject
- class level
- topic
- question count
- marks

For student-detail requests:
- extract the student name when provided
- do not ask for subject/class/topic just to identify the analytics capability

For filtering/ranking/class-performance requests:
- preserve the teacher's stated filters
- do not invent missing values
- route the request to analytics.performance

==================================================
SOURCE POLICY
==================================================

Default generation_mode:

source_grounded

Use llm_generated ONLY when the teacher explicitly permits
general AI knowledge.

Examples:

"use general knowledge"
"use your general knowledge"
"no source required"
"generate without reference"

If the teacher specifies a source such as NCERT:
- preserve it in requested_source
- do not invent a source
- pass the source requirement to the task

If the teacher asks TCO to find a source:
- preserve that requirement
- do not perform the search yourself

==================================================
DECISION RULE
==================================================

Understand the teacher's actual goal rather than simply
matching a keyword.

Return exactly one required_capability when a valid capability
is available.

If the request cannot be mapped to an available capability:

intent = "unknown"
required_capability = null

Do not invent a capability.

Do not perform the task yourself.
"""


class MasterAgent(BaseAgent):

    name = "master_agent"

    description = (
        "Understands teacher requests and delegates work "
        "to registered capabilities."
    )

    # Master is an orchestrator, not a specialist provider.
    capabilities = ()

    def __init__(
        self,
        registry: ComponentRegistry | None = None,
    ) -> None:

        self.registry = (
            registry
            if registry is not None
            else ComponentRegistry()
        )

        self.router = TaskRouter(self.registry)

        self.model = get_chat_model().with_structured_output(
            MasterDecision
        )

    def _build_capability_catalog(self) -> str:
        """
        Build a live capability catalog from the registry.

        This keeps the Master independent of future agents/tools.
        """

        catalog = self.registry.get_capability_catalog()

        lines: list[str] = []

        for item in catalog.get("agents", []):
            lines.append(
                f"- {item['capability']} "
                f"[agent: {item['provider']}] "
                f"{item['description']}"
            )

        for item in catalog.get("tools", []):
            lines.append(
                f"- {item['capability']} "
                f"[tool: {item['provider']}] "
                f"{item['description']}"
            )

        if not lines:
            return "No capabilities are currently registered."

        return "\n".join(lines)

    @staticmethod
    def _assessment_next_action(
        generation_mode: str,
    ) -> str:
        """
        Determine whether an assessment requires the source/RAG
        stage before execution.
        """

        if generation_mode == "llm_generated":
            return "execute_task"

        return "retrieve_source"

    def run(
        self,
        state: TCOState,
        task: dict[str, Any] | None = None,
    ) -> TCOState:

        teacher_request = str(
            state.get(
                "teacher_request",
                "",
            )
            or ""
        ).strip()

        if not teacher_request:
            return {
                **state,
                "intent": "unknown",
                "required_capability": None,
                "next_action": "ask_teacher",
                "missing_information": [
                    "teacher_request"
                ],
                "clarification_message": (
                    "Please provide the task you want "
                    "TCO to perform."
                ),
                "status": "waiting_for_teacher",
            }

        capabilities = self._build_capability_catalog()

        prompt = f"""
{MASTER_AGENT_PROMPT}

AVAILABLE TCO CAPABILITIES:
{capabilities}

CURRENT EXECUTION CONTEXT:
teacher_id = {state.get("teacher_id", "")}
school_id = {state.get("school_id", "")}
conversation_id = {state.get("conversation_id", "")}

STRUCTURED TEACHER INPUT:
intent = {state.get("intent", "")}
required_capability = {state.get("required_capability", "")}
class_level = {state.get("class_level", "")}
subject = {state.get("subject", "")}
chapter = {state.get("chapter", "")}
topic = {state.get("topic", "")}
question_count = {state.get("question_count", "")}
marks = {state.get("marks", "")}
generation_mode = {state.get("generation_mode", "")}
source_preference = {state.get("source_preference", "")}
requested_source = {state.get("requested_source", "")}
source_url = {state.get("source_url", "")}
uploaded_file_name = {state.get("uploaded_file_name", "")}
uploaded_file_path = {state.get("uploaded_file_path", "")}
knowledge_source = {state.get("knowledge_source", "")}

IMPORTANT:
The structured teacher input above comes from the teacher-facing form.
Use it as authoritative context when the teacher has already supplied a value.
Do not mark a mandatory assessment field as missing when it is present in the structured input.
Do not replace a supplied numeric value with null.

TEACHER REQUEST:
{teacher_request}
"""

        try:
            decision: MasterDecision = self.model.invoke(
                prompt
            )

        except Exception as exc:
            return {
                **state,
                "next_action": "end",
                "status": "error",
                "error_code": "MASTER_AGENT_FAILED",
                "error_message": str(exc),
            }

        # =====================================================
        # NORMALIZE MASTER DECISION WITH STRUCTURED FORM INPUT
        # =====================================================

        # The teacher-facing UI already collects these fields.
        # The LLM may omit them from its structured response, especially
        # when the values are not repeated in the free-text request.
        # Treat the explicit form values as authoritative fallbacks.

        state_intent = str(
            state.get("intent", "") or ""
        ).strip()

        intent = (
            decision.intent
            if decision.intent and decision.intent != "unknown"
            else state_intent
        )

        class_level = (
            decision.class_level
            or state.get("class_level", "")
            or ""
        )

        subject = (
            decision.subject
            or state.get("subject", "")
            or ""
        )

        chapter = (
            decision.chapter
            or state.get("chapter", "")
            or ""
        )

        topic = (
            decision.topic
            or decision.chapter
            or state.get("topic", "")
            or state.get("chapter", "")
            or ""
        )

        student_name = (
            decision.student_name
            or state.get("student_name", "")
            or ""
        )

        question_count = (
            decision.question_count
            if decision.question_count is not None
            else state.get("question_count")
        )

        marks = (
            decision.marks
            if decision.marks is not None
            else state.get("marks")
        )

        generation_mode = (
            state.get("generation_mode")
            if state.get("generation_mode")
            in {"source_grounded", "llm_generated"}
            else (
                decision.generation_mode
                or "source_grounded"
            )
        )

        requested_source = (
            decision.requested_source
            or state.get("requested_source", "")
            or ""
        )

        source_preference = (
            state.get("source_preference")
            or decision.source_preference
            or "classroom_first"
        )

        source_url = (
            decision.source_url
            or state.get("source_url", "")
            or ""
        )

        # =====================================================
        # DETERMINISTIC ASSESSMENT VALIDATION
        # =====================================================

        # Only assessment requests are subject to mandatory
        # topic/question_count/marks validation.
        #
        # Analytics requests can legitimately work without
        # subject/class/topic/marks/question_count.

        missing: list[str] = []

        if intent == "assessment":

            missing = list(
                decision.missing_information
            )

            if not topic:
                if "topic" not in missing:
                    missing.append("topic")

            if question_count is None:
                if "question_count" not in missing:
                    missing.append("question_count")

            if marks is None:
                if "marks" not in missing:
                    missing.append("marks")

        # =====================================================
        # CLARIFICATION MESSAGE
        # =====================================================

        clarification_message = (
            decision.clarification_message
            or ""
        )

        if (
            intent == "assessment"
            and missing
        ):

            labels: list[str] = []

            if "topic" in missing:
                labels.append(
                    "exact topic/chapter"
                )

            if "question_count" in missing:
                labels.append(
                    "number of questions"
                )

            if "marks" in missing:
                labels.append(
                    "total marks"
                )

            clarification_message = (
                "Please provide "
                + ", ".join(labels)
                + "."
            )

        # =====================================================
        # MISSING INFORMATION -> ASK TEACHER
        # =====================================================

        if missing:
            return {
                **state,

                "intent": intent,
                "language": decision.language,

                "class_level": class_level,
                "subject": subject,
                "chapter": chapter,
                "topic": topic,

                "marks": marks,
                "question_count": question_count,

                "generation_mode": generation_mode,

                "requested_source": requested_source,

                "source_preference": source_preference,

                "required_capability": None,
                "next_action": "ask_teacher",

                "missing_information": missing,

                "clarification_message": (
                    clarification_message
                ),

                "status": "waiting_for_teacher",
            }

        # =====================================================
        # CAPABILITY VALIDATION
        # =====================================================

        capability = (
            decision.required_capability
            or state.get("required_capability")
        )

        if not capability:
            return {
                **state,
                "intent": intent,
                "language": decision.language,
                "required_capability": None,
                "next_action": "end",
                "clarification_message": (
                    "I couldn't determine which TCO "
                    "capability should handle this request."
                ),
                "status": "needs_clarification",
                "error_code": "MASTER_NO_CAPABILITY",
            }

        capability = capability.strip()

        # =====================================================
        # CAPABILITY-BASED INTENT NORMALIZATION
        # =====================================================

        # Analytics is an independent capability.
        # Its requests must not inherit assessment intent
        # or assessment-specific requirements.

        if (
            capability == "analytics.performance"
            and intent != "analytics"
        ):
            intent = "analytics"

        # =====================================================
        # REGISTERED CAPABILITY CHECK
        # =====================================================

        if not self.registry.has_capability(
            capability
        ):
            return {
                **state,

                "intent": intent,
                "language": decision.language,

                "required_capability": capability,
                "next_action": "end",

                "status": "error",

                "error_code": (
                    "CAPABILITY_NOT_AVAILABLE"
                ),

                "error_message": (
                    "No registered provider exists "
                    f"for capability '{capability}'."
                ),
            }

        # =====================================================
        # CREATE TASK
        # =====================================================

        task_input = {
            "teacher_request": teacher_request,

            "class_level": class_level,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,

            "student_name": student_name,

            "marks": marks,
            "question_count": question_count,

            "generation_mode": generation_mode,

            "requested_source": requested_source,

            "source_preference": source_preference,

            "source_url": source_url,
        }

        new_task = Task(
            capability=capability,
            input_data=task_input,
            metadata={
                "request_id": state.get(
                    "request_id"
                ),
                "teacher_id": state.get(
                    "teacher_id"
                ),
                "school_id": state.get(
                    "school_id"
                ),
                "conversation_id": state.get(
                    "conversation_id"
                ),
            },
        )

        # =====================================================
        # ROUTE TASK
        # =====================================================

        try:
            provider, new_task = self.router.route(
                new_task
            )

        except CapabilityNotFoundError as exc:
            return {
                **state,

                "intent": intent,
                "required_capability": capability,

                "next_action": "end",

                "status": "error",

                "error_code": (
                    "TASK_ROUTING_FAILED"
                ),

                "error_message": str(exc),
            }

        # =====================================================
        # DETERMINE GRAPH NEXT ACTION
        # =====================================================

        if intent == "assessment":

            next_action = (
                self._assessment_next_action(
                    generation_mode
                )
            )

        else:
            next_action = "execute_task"

        # =====================================================
        # RETURN UPDATED STATE
        # =====================================================

        return {
            **state,

            "intent": intent,
            "language": decision.language,

            "class_level": class_level,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,

            "student_name": student_name,

            "marks": marks,
            "question_count": question_count,

            "generation_mode": generation_mode,

            "source": (
                source_url
                or state.get("source", "")
            ),

            "requested_source": requested_source,

            "source_preference": source_preference,

            "required_capability": capability,

            "missing_information": [],
            "clarification_message": "",

            "current_task": new_task,

            "next_action": next_action,

            "status": "task_assigned",

            "metadata": {
                **state.get(
                    "metadata",
                    {},
                ),

                "master_decision": (
                    decision.model_dump()
                ),

                "task_provider": (
                    provider.name
                ),

                "task_status": (
                    new_task.status.value
                ),
            },
        }


# =============================================================
# BACKWARD-COMPATIBLE LAZY DEFAULT INSTANCE
# =============================================================

_master_agent: MasterAgent | None = None


def _get_default_master_agent() -> MasterAgent:
    """
    Lazily build the default registry.

    Lazy import avoids bootstrap/import-cycle problems.
    """

    global _master_agent

    if _master_agent is None:
        from backend.core.bootstrap import (
            build_default_registry,
        )

        _master_agent = MasterAgent(
            build_default_registry()
        )

    return _master_agent


def master_agent(
    state: TCOState,
) -> TCOState:
    return _get_default_master_agent().run(
        state
    )