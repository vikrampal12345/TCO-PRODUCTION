from backend.state import TCOState
from backend.rag.retriever import retrieve_context


def retrieve_source(state: TCOState) -> TCOState:
    """
    Retrieve approved source material for the assessment topic.

    This node:
    - uses the existing RAG retriever
    - does not generate content
    - does not ask the LLM to decide
    - only retrieves relevant educational material
    """

    topic = state.get("topic")

    if not topic:
        return {
            **state,
            "status": "waiting_for_teacher",
            "next_action": "ask_teacher",
            "clarification_message": (
                "Please provide the exact chapter name or topic "
                "for the assessment."
            ),
        }

    context, source_references = retrieve_context(
        query=topic,
        top_k=5,
        similarity_threshold=0.30,
    )

    if not context:
        return {
            **state,
            "source_available": False,
            "retrieved_context": "",
            "source_references": [],
            "source_status": "no_relevant_source",
            "status": "source_not_found",
            "next_action": "ask_teacher",
            "clarification_message": (
                f"I couldn't find approved material for {topic}. "
                "Please provide notes/reference material, provide "
                "a source URL, or explicitly allow AI-generated "
                "questions."
            ),
        }

    return {
        **state,
        "source_available": True,
        "retrieved_context": context,
        "source_references": source_references,
        "source_status": "source_ready",
        "status": "source_retrieved",
        "next_action": "assessment",
    }