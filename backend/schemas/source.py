from pydantic import BaseModel, Field


class SourceCandidate(BaseModel):
    """
    A source discovered from the web.

    This is a candidate only.
    It is NOT automatically trusted or approved.
    """

    title: str
    url: str

    snippet: str = ""

    source_type: str = "web"

    relevance_score: float | None = None

    domain: str = ""

    approved: bool = False