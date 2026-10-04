from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """
    Standard unit of work in TCO.

    Master Agent creates/assigns a Task.
    A specialist agent or tool executes it.
    """

    capability: str
    input_data: dict[str, Any] = field(default_factory=dict)

    task_id: str = field(
        default_factory=lambda: f"task_{uuid4().hex[:12]}"
    )

    status: TaskStatus = TaskStatus.PENDING

    assigned_to: str | None = None

    result: Any = None

    error: str | None = None

    created_at: datetime = field(
        default_factory=datetime.utcnow
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self, assigned_to: str) -> None:
        self.assigned_to = assigned_to
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result: Any = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()