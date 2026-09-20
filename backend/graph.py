from langgraph.graph import StateGraph, START, END

from backend.state import TCOState

from backend.agents.master_agent import master_agent
from backend.agents.source_manager import source_manager
from backend.agents.assessment_agent import assessment_agent

from backend.rag.source_retrieval import retrieve_source


# ============================================================
# Ask Teacher Node
# ============================================================

def ask_teacher(state: TCOState) -> TCOState:
    """
    Ask the teacher for missing information or required approval.
    """

    message = state.get(
        "clarification_message",
        "Please provide the required information.",
    )

    print("\nTCO:")
    print(message)

    return {
        **state,
        "status": "waiting_for_teacher",
    }


# ============================================================
# Evaluation Placeholder
# ============================================================

def evaluation_placeholder(
    state: TCOState,
) -> TCOState:

    print("\nRouting to Evaluation Agent...")

    return {
        **state,
        "status": "evaluation_agent_called",
    }


# ============================================================
# Master Agent Router
# ============================================================

def route_after_master(state: TCOState) -> str:

    next_action = state.get("next_action")

    # --------------------------------------------------------
    # Missing information
    # --------------------------------------------------------

    if next_action == "ask_teacher":
        return "ask_teacher"

    # --------------------------------------------------------
    # Assessment
    # --------------------------------------------------------

    if next_action == "assessment":

        generation_mode = state.get(
            "generation_mode",
            "source_grounded",
        )

        # Teacher explicitly allowed AI generation.
        if generation_mode == "llm_generated":
            return "assessment"

        # Otherwise retrieve approved material first.
        return "retrieve_source"

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    if next_action == "evaluation":
        return "evaluation"

    # --------------------------------------------------------
    # Other intents
    # --------------------------------------------------------

    return "end"


# ============================================================
# Source Manager Router
# ============================================================

def route_after_source_check(
    state: TCOState,
) -> str:

    source_status = state.get(
        "source_status"
    )

    # Approved source found
    if source_status == "source_ready":
        return "assessment"

    # Reference questions available
    if source_status == "reference_questions_available":
        return "assessment"

    # Teacher explicitly allowed AI generation
    if source_status == "llm_generation_allowed":
        return "assessment"

    # No source
    return "ask_teacher"


# ============================================================
# Build Graph
# ============================================================

graph = StateGraph(TCOState)


# ============================================================
# Add Nodes
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
    "assessment",
    assessment_agent,
)

graph.add_node(
    "ask_teacher",
    ask_teacher,
)

graph.add_node(
    "evaluation",
    evaluation_placeholder,
)


# ============================================================
# START
# ============================================================

graph.add_edge(
    START,
    "master_agent",
)


# ============================================================
# Master Agent Routing
# ============================================================

graph.add_conditional_edges(
    "master_agent",
    route_after_master,
    {
        "ask_teacher": "ask_teacher",
        "retrieve_source": "retrieve_source",
        "assessment": "assessment",
        "evaluation": "evaluation",
        "end": END,
    },
)


# ============================================================
# RAG Retrieval → Source Manager
# ============================================================

graph.add_edge(
    "retrieve_source",
    "source_check",
)


# ============================================================
# Source Manager Routing
# ============================================================

graph.add_conditional_edges(
    "source_check",
    route_after_source_check,
    {
        "assessment": "assessment",
        "ask_teacher": "ask_teacher",
    },
)


# ============================================================
# Temporary Endpoints
# ============================================================

graph.add_edge(
    "assessment",
    END,
)

graph.add_edge(
    "ask_teacher",
    END,
)

graph.add_edge(
    "evaluation",
    END,
)


# ============================================================
# Compile
# ============================================================

workflow = graph.compile()