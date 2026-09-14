"""What an executor hands back. Its own module so executors living in other
apps (`datasources.search`) can import it without importing the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutorResult:
    result: dict
    summary: str
    rows_returned: int | None = None
    # What actually ran (e.g. the compiled IR). Written to
    # `tool_executions.compiled_query`; never sent to the model.
    audit: dict | None = None

    @property
    def successful(self) -> bool:
        """Did this produce something useful? Feeds the barren-turn safety net."""
        return self.rows_returned is None or self.rows_returned > 0
