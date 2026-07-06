"""Rule-based one-shot repair loop for generated R code."""

from __future__ import annotations

from rstats_agent.execution.diagnostics import classify_r_error
from rstats_agent.execution.r_executor import DockerRExecutor
from rstats_agent.execution.repair import suggest_repairs
from rstats_agent.execution.safety import check_r_code_safety
from rstats_agent.schemas import ExecutionResult, RepairLoopResult


def _disabled_execution_result() -> ExecutionResult:
    return ExecutionResult(
        status="skipped",
        reason="R execution is disabled.",
        diagnostics=["R execution is disabled; static safety check completed."],
    )


def run_repair_loop(
    code: str,
    *,
    execute: bool = False,
    repair: bool = False,
    max_repairs: int = 1,
    executor: DockerRExecutor | None = None,
    timeout_sec: int = 20,
) -> RepairLoopResult:
    """Run optional execution, classify errors, and optionally apply one repair."""

    executor = executor or DockerRExecutor(timeout_seconds=timeout_sec)
    safety = check_r_code_safety(code)
    if not safety.allowed:
        original_execution = ExecutionResult(
            status="unsafe",
            reason="Static safety check failed; execution was not attempted.",
            diagnostics=safety.diagnostics,
        )
    elif execute:
        original_execution = executor.execute(code, enabled=True, timeout_sec=timeout_sec)
    else:
        original_execution = _disabled_execution_result()

    diagnostics = []
    if original_execution.status in {"failed", "timeout"}:
        diagnostics = classify_r_error(original_execution.stderr, original_execution.stdout)

    suggestions = suggest_repairs(code, diagnostics) if repair and diagnostics else []
    repaired_code = None
    repaired_execution = None
    attempts = 0

    if repair and max_repairs > 0:
        for suggestion in suggestions:
            if not suggestion.patched_code or suggestion.patched_code == code:
                continue
            repaired_code = suggestion.patched_code
            suggestion.applied = True
            attempts = 1
            repaired_safety = check_r_code_safety(repaired_code)
            if not repaired_safety.allowed:
                repaired_execution = ExecutionResult(
                    status="unsafe",
                    reason="Repaired code failed static safety check; execution was not attempted.",
                    diagnostics=repaired_safety.diagnostics,
                )
            elif execute:
                repaired_execution = executor.execute(repaired_code, enabled=True, timeout_sec=timeout_sec)
            else:
                repaired_execution = ExecutionResult(
                    status="skipped",
                    reason="Repaired code was not executed because R execution is disabled.",
                    diagnostics=["Repaired code passed static safety check but execution is disabled."],
                )
            break

    return RepairLoopResult(
        original_code=code,
        original_execution=original_execution,
        diagnostics=diagnostics,
        suggestions=suggestions,
        repaired_code=repaired_code,
        repaired_execution=repaired_execution,
        attempts=attempts,
    )
