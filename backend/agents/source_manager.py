from backend.state import TCOState


def source_manager(state: TCOState) -> TCOState:
    """
    Decide whether the assessment workflow can continue
    using approved source material.

    This is a deterministic decision node.

    It does NOT:
    - generate questions
    - search the web
    - perform RAG retrieval
    """

    generation_mode = state.get(
        "generation_mode",
        "source_grounded",
    )

    retrieved_context = state.get(
        "retrieved_context",
        "",
    )

    reference_questions = state.get(
        "reference_questions",
        [],
    )

    # ========================================================
    # Case 1: Teacher explicitly allowed AI generation
    # ========================================================

    if generation_mode == "llm_generated":

        return {
            **state,
            "source_available": False,
            "source_status": "llm_generation_allowed",
            "status": "source_check_complete",
            "next_action": "assessment",
        }

    # ========================================================
    # Case 2: RAG retrieved approved material
    # ========================================================

    if retrieved_context.strip():

        return {
            **state,
            "source_available": True,
            "source_status": "source_ready",
            "status": "source_check_complete",
            "next_action": "assessment",
        }

    # ========================================================
    # Case 3: Reference questions are available
    # ========================================================

    if reference_questions:

        return {
            **state,
            "source_available": True,
            "source_status": "reference_questions_available",
            "status": "source_check_complete",
            "next_action": "assessment",
        }

    # ========================================================
    # Case 4: No approved source
    # ========================================================

    return {
        **state,
        "source_available": False,
        "source_status": "no_source_found",
        "status": "waiting_for_teacher",
        "next_action": "ask_teacher",
        "clarification_message": (
            "I couldn't find approved material for this assessment. "
            "Please provide notes/reference material, provide a "
            "source URL, or explicitly allow AI-generated questions."
        ),
    }