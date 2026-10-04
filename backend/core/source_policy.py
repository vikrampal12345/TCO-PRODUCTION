from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePolicy:
    """
    Defines search preferences for a known educational source.

    IMPORTANT:
    A policy only controls search preference.
    It does NOT mean the source is automatically trusted
    or approved.
    """

    name: str
    preferred_domains: tuple[str, ...]
    description: str


SOURCE_POLICIES: dict[str, SourcePolicy] = {

    "ncert": SourcePolicy(
        name="NCERT",
        preferred_domains=(
            "ncert.nic.in",
        ),
        description=(
            "Official NCERT textbooks and educational material."
        ),
    ),

    "cbse": SourcePolicy(
        name="CBSE",
        preferred_domains=(
            "cbseacademic.nic.in",
            "cbse.gov.in",
        ),
        description=(
            "Official CBSE academic and curriculum material."
        ),
    ),
}


def normalize_source_name(source: str | None) -> str:
    """
    Normalize the source name.

    Examples:
        "NCERT"      -> "ncert"
        " Ncert "    -> "ncert"
        None         -> ""
    """

    if not source:
        return ""

    return source.strip().lower()


def get_source_policy(
    source: str | None,
) -> SourcePolicy | None:
    """
    Return the policy associated with a known source.

    Unknown sources return None.
    """

    normalized = normalize_source_name(source)

    return SOURCE_POLICIES.get(normalized)