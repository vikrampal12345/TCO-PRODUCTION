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
4. Decide which CAPABILITY is required.
5. Prepare the information needed by that capability.

You DO NOT perform the specialist work yourself.

You DO NOT generate assessment questions.
You DO NOT directly analyze student performance.
You DO NOT directly access the database.
You DO NOT directly send emails.
You DO NOT perform RAG.
You DO NOT perform web search.

Those responsibilities belong to specialist agents or tools.

==================================================
CAPABILITY ROUTING
==================================================

You will receive a list of capabilities currently registered
in TCO.

You MUST select required_capability from that list.

Never invent a capability.

Examples:

assessment.create
    -> create an assessment

evaluation.check
    -> evaluate student submissions

analytics.performance
    -> analyze performance

attendance.read
    -> retrieve attendance records

email.send
    -> send an email

==================================================
AGENT VS TOOL
==================================================

Use a specialist-agent capability when the request requires
reasoning, planning, generation or domain-specific analysis.

Use a tool capability when the request is a concrete,
deterministic action.

Example:

"Create a 20-mark Science test"
    -> assessment.create

"Show Rahul's attendance"
    -> attendance.read

==================================================
ASSESSMENT
==================================================

For an assessment request, these are mandatory:

1. Exact topic/chapter
2. Number of questions
3. Total marks

If any are missing:
- Add the canonical field name to missing_information.
- Do not create a task.
- Do not guess the missing value.

Canonical names:

topic
question_count
marks

==================================================
SOURCE POLICY
==================================================

Default generation_mode:
source_grounded

Use llm_generated ONLY when the teacher explicitly allows
general AI knowledge.

Examples:

"use general knowledge"
"use your general knowledge"
"no source required"
"generate without reference"

If the teacher specifies a source such as NCERT:
- preserve it in requested_source
- do not invent a source
- pass the source requirement to the assigned task

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

If the request cannot be mapped to an available capability,
use:
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

    # Master is the orchestrator, not a specialist provider.
    capabilities = ()

    def __init__(
        self,
        registry: ComponentRegistry | None = None,
    ):
        self.registry = registry or ComponentRegistry()

        self.router = TaskRouter(self.registry)

        self.model = get_chat_model().with_structured_output(
            MasterDecision
        )

    def _build_capability_catalog(self) -> str:
        """
        Convert the live registry into a compact prompt section.

        The Master therefore does not need hard-coded knowledge
        of every future agent/tool.
        """

        catalog = self.registry.get_capability_catalog()

        lines = []

        for item in catalog["agents"]:
            lines.append(
                f"- {item['capability']} "
                f"[agent: {item['provider']}] "
                f"{item['description']}"
            )

        for item in catalog["tools"]:
            lines.append(
                f"- {item['capability']} "
                f"[tool: {item['provider']}] "
                f"{item['description']}"
            )

        if not lines:
            return "No capabilities are currently registered."

        return "\n".join(lines)

    def run(
        self,
        state: TCOState,
        task: dict[str, Any] | None = None,
    ) -> TCOState:

        teacher_request = state.get(
            "teacher_request",
            "",
        ).strip()

        if not teacher_request:
            return {
                **state,
                "intent": "unknown",
                "required_capability": None,
                "missing_information": [
                    "teacher_request"
                ],
                "clarification_message": (
                    "Please provide the task you want TCO "
                    "to perform."
                ),
                "status": "waiting_for_teacher",
            }

        capabilities = self._build_capability_catalog()

        prompt = f"""
{MASTER_AGENT_PROMPT}

AVAILABLE TCO CAPABILITIES:
{capabilities}

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
                "status": "error",
                "error_code": "MASTER_AGENT_FAILED",
                "error_message": str(exc),
            }

        # ---------------------------------------------------------
        # Deterministic assessment validation
        # ---------------------------------------------------------

        missing = list(
            decision.missing_information
        )

        if decision.intent == "assessment":

            if not decision.topic and not decision.chapter:
                if "topic" not in missing:
                    missing.append("topic")

            if decision.question_count is None:
                if "question_count" not in missing:
                    missing.append("question_count")

            if decision.marks is None:
                if "marks" not in missing:
                    missing.append("marks")

        # ---------------------------------------------------------
        # Clarification
        # ---------------------------------------------------------

        clarification_message = (
            decision.clarification_message
        )

        if decision.intent == "assessment" and missing:

            labels = []

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

        # ---------------------------------------------------------
        # Missing information means no task
        # ---------------------------------------------------------

        if missing:
            return {
                **state,
                "intent": decision.intent,
                "language": decision.language,
                "class_level": decision.class_level,
                "subject": decision.subject,
                "chapter": decision.chapter,
                "topic": (
                    decision.topic
                    or decision.chapter
                ),
                "marks": decision.marks,
                "question_count": (
                    decision.question_count
                ),
                "generation_mode": (
                    decision.generation_mode
                ),
                "requested_source": (
                    decision.requested_source
                ),
                "required_capability": None,
                "missing_information": missing,
                "clarification_message": (
                    clarification_message
                ),
                "status": "waiting_for_teacher",
            }

        # ---------------------------------------------------------
        # Validate capability decision
        # ---------------------------------------------------------

        capability = decision.required_capability

        if not capability:
            return {
                **state,
                "intent": decision.intent,
                "language": decision.language,
                "required_capability": None,
                "clarification_message": (
                    "I couldn't determine which TCO "
                    "capability should handle this request."
                ),
                "status": "needs_clarification",
                "error_code": "MASTER_NO_CAPABILITY",
            }

        capability = capability.strip()

        # Never allow the LLM to invent a capability.
        if not self.registry.has_capability(
            capability
        ):
            return {
                **state,
                "intent": decision.intent,
                "language": decision.language,
                "required_capability": capability,
                "status": "error",
                "error_code": "CAPABILITY_NOT_AVAILABLE",
                "error_message": (
                    f"No registered provider exists for "
                    f"capability '{capability}'."
                ),
            }

        # ---------------------------------------------------------
        # Normalize topic
        # ---------------------------------------------------------

        topic = (
            decision.topic
            or decision.chapter
        )

        # ---------------------------------------------------------
        # Create Task
        # ---------------------------------------------------------

        task_input = {
            "teacher_request": teacher_request,
            "class_level": decision.class_level,
            "subject": decision.subject,
            "chapter": decision.chapter,
            "topic": topic,
            "student_name": decision.student_name,
            "marks": decision.marks,
            "question_count": decision.question_count,
            "generation_mode": (
                decision.generation_mode
            ),
            "requested_source": (
                decision.requested_source
            ),
            "source_preference": (
                decision.source_preference
            ),
            "source_url": decision.source_url,
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
                "conversation_id": state.get(
                    "conversation_id"
                ),
            },
        )

        # ---------------------------------------------------------
        # Route Task
        # ---------------------------------------------------------

        try:
            provider, new_task = self.router.route(
                new_task
            )

        except CapabilityNotFoundError as exc:
            return {
                **state,
                "intent": decision.intent,
                "required_capability": capability,
                "status": "error",
                "error_code": "TASK_ROUTING_FAILED",
                "error_message": str(exc),
            }

        # ---------------------------------------------------------
        # Save task information in state
        # ---------------------------------------------------------

        return {
            **state,

            "intent": decision.intent,
            "language": decision.language,

            "class_level": decision.class_level,
            "subject": decision.subject,
            "chapter": decision.chapter,
            "topic": topic,

            "student_name": decision.student_name,

            "marks": decision.marks,
            "question_count": (
                decision.question_count
            ),

            "generation_mode": (
                decision.generation_mode
            ),

            "source": (
                decision.source_url
                or state.get("source")
            ),

            "requested_source": (
                decision.requested_source
            ),

            "required_capability": capability,

            "missing_information": [],

            "clarification_message": "",

            "current_task": new_task,

            "status": "task_assigned",

            "metadata": {
                **state.get("metadata", {}),

                "master_decision": (
                    decision.model_dump()
                ),

                "task_provider": provider.name,

                "task_status": (
                    new_task.status.value
                ),
            },
        }


# -------------------------------------------------------------
# Backward-compatible instance/function
# -------------------------------------------------------------

_master_agent = MasterAgent()


def master_agent(state: TCOState) -> TCOState:
    return _master_agent.run(state)