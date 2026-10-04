from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass
class ToolResult(Generic[T]):
    """
    Standard result returned by TCO tools.

    Every tool should clearly tell the system:
    - whether it succeeded
    - what data it produced
    - what went wrong, if anything
    """

    success: bool

    data: T | None = None

    error_code: str | None = None
    error_message: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: T | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult[T]":
        return cls(
            success=True,
            data=data,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        error_code: str,
        error_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult[T]":
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {},
        )