from __future__ import annotations

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from backend.agents.master_agent import (
    master_agent,
)
from backend.agents.source_manager import (
    source_manager,
)
from backend.core.bootstrap import (
    build_default_registry,
)
from backend.core.registry import (
    CapabilityNotFoundError,
)
from backend.core.task_router import (
    TaskRouter,
)
from backend.rag.source_retrieval import (
    retrieve_source,
)
from backend.state import TCOState


# ============================================================
# LAZY TASK ROUTER
# ============================================================

_task_router: TaskRouter | None = None


def _get_task_router() -> TaskRouter:
    global _task_router

    if _task_router is None:
        _task_router = TaskRouter(
            build_default_registry()
        )

    return _task_router


# ============================================================
# ASK TEACHER
# ============================================================

def ask_teacher(
    state: TCOState,
) -> TCOState:

    message = state.get(
        "clarification_message",
        "Please provide the required information.",
    )

    print("\nTCO:")
    print(message)

    if state.get("status") == "waiting_for_source_selection":
        return state

    return {
        **state,
        "status": "waiting_for_teacher",
    }


# ============================================================
# GENERIC TASK EXECUTION
# ============================================================

def execute_task(
    state: TCOState,
) -> TCOState:
    """
    Execute the Task previously created by the Master Agent.

    The Graph does not know specialist implementations.
    It simply routes the Task through the registry.
    """

    task = state.get(
        "current_task"
    )

    if task is None:
        return {
            **state,
            "status": "error",
            "error_code": (
                "CURRENT_TASK_MISSING"
            ),
            "error_message": (
                "Master Agent did not create a task."
            ),
            "next_action": "end",
        }

    try:
        provider, routed_task = (
            _get_task_router().route(task)
        )

    except CapabilityNotFoundError as exc:
        return {
            **state,
            "status": "error",
            "error_code": (
                "TASK_EXECUTION_ROUTING_FAILED"
            ),
            "error_message": str(exc),
            "next_action": "end",
        }

    print(
        "\nExecuting task:"
        f" {routed_task.capability}"
    )

    print(
        "Provider:"
        f" {provider.name}"
    )

    updated_state = {
        **state,
        "current_task": routed_task,
        "status": "task_executing",
        "metadata": {
            **state.get(
                "metadata",
                {},
            ),
            "executing_provider": (
                provider.name
            ),
            "executing_capability": (
                routed_task.capability
            ),
        },
    }

    try:
        result_state = provider.run(
            updated_state,
            routed_task,
        )

    except Exception as exc:
        return {
            **updated_state,
            "status": "error",
            "error_code": (
                "TASK_EXECUTION_FAILED"
            ),
            "error_message": str(exc),
            "next_action": "end",
        }

    return result_state


# ============================================================
# EVALUATION PLACEHOLDER
# ============================================================

def evaluation_placeholder(
    state: TCOState,
) -> TCOState:

    print(
        "\nEvaluation capability reached."
    )

    return {
        **state,
        "status": (
            "evaluation_agent_called"
        ),
    }


# ============================================================
# MASTER ROUTER
# ============================================================

def route_after_master(
    state: TCOState,
) -> str:

    next_action = state.get(
        "next_action"
    )

    # --------------------------------------------------------
    # Ask teacher
    # --------------------------------------------------------

    if next_action == "ask_teacher":
        return "ask_teacher"

    if next_action == "source_selection":
        return "ask_teacher"

    # --------------------------------------------------------
    # Knowledge required
    # --------------------------------------------------------

    if next_action == "retrieve_source":
        return "retrieve_source"

    # --------------------------------------------------------
    # Generic specialist/tool task
    # --------------------------------------------------------

    if next_action in {
        "execute_task",
        "assessment",
        "evaluation",
    }:
        return "execute_task"

    # --------------------------------------------------------
    # Errors / unknown
    # --------------------------------------------------------

    return "end"


# ============================================================
# SOURCE MANAGER ROUTER
# ============================================================

def route_after_source_check(
    state: TCOState,
) -> str:

    source_status = state.get(
        "source_status"
    )

    # Source successfully retrieved.
    if source_status == "source_ready":
        return "execute_task"

    # Existing reference questions can also
    # continue directly to the specialist.
    if (
        source_status
        == "reference_questions_available"
    ):
        return "execute_task"

    # Explicit AI-generation permission.
    if (
        source_status
        == "llm_generation_allowed"
    ):
        return "execute_task"

    # Anything else requires teacher intervention.
    return "ask_teacher"


# ============================================================
# BUILD GRAPH
# ============================================================

graph = StateGraph(
    TCOState
)


# ============================================================
# NODES
# ============================================================

graph.add_node(
    "master_agent",
    master_agent,
)

graph.add_node(
    "retrieve_source",
    retrieve_source,
)

graph.add_node(
    "source_check",
    source_manager,
)

graph.add_node(
    "execute_task",
    execute_task,
)

graph.add_node(
    "ask_teacher",
    ask_teacher,
)


# ============================================================
# START
# ============================================================

graph.add_edge(
    START,
    "master_agent",
)


# ============================================================
# MASTER ROUTING
# ============================================================

graph.add_conditional_edges(
    "master_agent",
    route_after_master,
    {
        "ask_teacher": "ask_teacher",
        "retrieve_source": (
            "retrieve_source"
        ),
        "execute_task": "execute_task",
        "end": END,
    },
)


# ============================================================
# CLASSROOM / RAG
# ============================================================

graph.add_edge(
    "retrieve_source",
    "source_check",
)


# ============================================================
# SOURCE MANAGER ROUTING
# ============================================================

graph.add_conditional_edges(
    "source_check",
    route_after_source_check,
    {
        "execute_task": "execute_task",
        "ask_teacher": "ask_teacher",
    },
)


# ============================================================
# ENDPOINTS
# ============================================================

graph.add_edge(
    "execute_task",
    END,
)

graph.add_edge(
    "ask_teacher",
    END,
)


# ============================================================
# COMPILE
# ============================================================

workflow = graph.compile()