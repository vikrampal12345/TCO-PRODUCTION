from typing import Any

from backend.core.task import Task
from backend.core.tool_result import ToolResult
from backend.state import TCOState


class TaskExecutionError(Exception):
    """Raised when task execution fails."""


class TaskExecutor:
    """
    Executes an already-routed TCO task.

    The executor does NOT decide which agent/tool should handle
    the task. That decision has already been made by Master Agent
    + TaskRouter + Registry.

    Responsibilities:
        Agent -> agent.run(state, task)
        Tool  -> tool.execute(**task.input_data)
    """

    def execute(
        self,
        provider: Any,
        task: Task,
        state: TCOState,
    ) -> TCOState:
        """
        Execute the task using the routed provider.

        Args:
            provider:
                Registered agent or tool.

            task:
                Task selected and routed by TaskRouter.

            state:
                Current TCO execution state.

        Returns:
            Updated TCOState.
        """

        if provider is None:
            raise TaskExecutionError(
                "Task provider is missing."
            )

        if task.status.value != "running":
            raise TaskExecutionError(
                f"Task '{task.task_id}' must be running "
                f"before execution. Current status: "
                f"'{task.status.value}'."
            )

        # -----------------------------------------------------
        # Specialist Agent
        # -----------------------------------------------------

        if hasattr(provider, "run"):

            try:
                result_state = provider.run(
                    state=state,
                    task=task,
                )

            except Exception as exc:
                task.fail(str(exc))

                return {
                    **state,
                    "current_task": task,
                    "status": "error",
                    "error_code": "TASK_EXECUTION_FAILED",
                    "error_message": str(exc),
                }

            # ---------------------------------------------
            # Agent returned a valid state
            # ---------------------------------------------

            result_state = {
                **state,
                **result_state,
            }

            # A specialist agent can intentionally return a
            # waiting/clarification state. That is not an
            # execution exception.
            result_status = result_state.get(
                "status"
            )

            if result_status == "error":

                task.fail(
                    result_state.get(
                        "error_message",
                        "Agent execution failed.",
                    )
                )

            else:
                task.complete(
                    result=result_state
                )

            return {
                **result_state,
                "current_task": task,
            }

        # -----------------------------------------------------
        # Deterministic Tool
        # -----------------------------------------------------

        if hasattr(provider, "execute"):

            try:
                tool_result: ToolResult = provider.execute(
                    **task.input_data
                )

            except Exception as exc:
                task.fail(str(exc))

                return {
                    **state,
                    "current_task": task,
                    "status": "error",
                    "error_code": "TASK_EXECUTION_FAILED",
                    "error_message": str(exc),
                }

            if not isinstance(
                tool_result,
                ToolResult,
            ):
                task.fail(
                    "Tool did not return a ToolResult."
                )

                return {
                    **state,
                    "current_task": task,
                    "status": "error",
                    "error_code": "INVALID_TOOL_RESULT",
                    "error_message": (
                        "Tool execution returned an invalid "
                        "result type."
                    ),
                }

            if not tool_result.success:

                task.fail(
                    tool_result.error_message
                    or "Tool execution failed."
                )

                return {
                    **state,
                    "current_task": task,
                    "status": "error",
                    "error_code": (
                        tool_result.error_code
                        or "TOOL_EXECUTION_FAILED"
                    ),
                    "error_message": (
                        tool_result.error_message
                        or "Tool execution failed."
                    ),
                }

            # Tool succeeded.
            task.complete(
                result=tool_result.data
            )

            return {
                **state,
                "current_task": task,
                "status": "task_completed",
                "metadata": {
                    **state.get("metadata", {}),
                    "tool_result_metadata": (
                        tool_result.metadata
                    ),
                },
            }

        raise TaskExecutionError(
            f"Provider '{getattr(provider, 'name', 'unknown')}' "
            f"is neither a valid agent nor a valid tool."
        )


def execute_task(
    provider: Any,
    task: Task,
    state: TCOState,
) -> TCOState:
    """
    Convenience function for task execution.
    """

    return TaskExecutor().execute(
        provider=provider,
        task=task,
        state=state,
    )