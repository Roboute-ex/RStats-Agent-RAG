from rstats_agent.agents.repair_loop import run_repair_loop
from rstats_agent.execution.r_executor import DockerRExecutor
from rstats_agent.execution.safety import SafetyFinding, SafetyReport
from rstats_agent.schemas import ExecutionResult


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, code: str, enabled: bool = False, timeout_sec: int | None = None) -> ExecutionResult:
        self.calls.append(code)
        if len(self.calls) == 1:
            return ExecutionResult(
                status="failed",
                stderr='Error in filter(sales, price > 0) : could not find function "filter"',
                returncode=1,
            )
        return ExecutionResult(status="ok", stdout="repaired", returncode=0)


def test_repair_loop_generates_diagnostics_and_suggestions_after_failure():
    executor = FakeExecutor()

    result = run_repair_loop(
        "sales %>% filter(price > 0)",
        execute=True,
        repair=True,
        max_repairs=1,
        executor=executor,
    )

    assert result.original_execution.status == "failed"
    assert [item.error_type for item in result.diagnostics] == ["missing_function"]
    assert result.suggestions[0].repair_type == "add_library_dplyr"
    assert result.suggestions[0].applied is True
    assert result.repaired_code.startswith("library(dplyr)")
    assert result.repaired_execution.status == "ok"
    assert result.attempts == 1
    assert len(executor.calls) == 2


def test_repair_loop_respects_max_repairs_zero():
    executor = FakeExecutor()

    result = run_repair_loop(
        "sales %>% filter(price > 0)",
        execute=True,
        repair=True,
        max_repairs=0,
        executor=executor,
    )

    assert result.suggestions
    assert result.repaired_code is None
    assert result.repaired_execution is None
    assert result.attempts == 0
    assert len(executor.calls) == 1


def test_repair_loop_safety_checks_repaired_code(monkeypatch):
    calls = {"count": 0}

    def fake_safety(code: str) -> SafetyReport:
        calls["count"] += 1
        if calls["count"] == 1:
            return SafetyReport(allowed=True)
        return SafetyReport(
            allowed=False,
            findings=[
                SafetyFinding(
                    rule_id="test-unsafe",
                    message="patched code is unsafe",
                    pattern="test",
                )
            ],
        )

    monkeypatch.setattr("rstats_agent.agents.repair_loop.check_r_code_safety", fake_safety)

    result = run_repair_loop(
        "sales %>% filter(price > 0)",
        execute=True,
        repair=True,
        max_repairs=1,
        executor=FakeExecutor(),
    )

    assert result.repaired_code.startswith("library(dplyr)")
    assert result.repaired_execution.status == "unsafe"
    assert result.repaired_execution.diagnostics == ["patched code is unsafe"]
    assert result.attempts == 1
    assert calls["count"] == 2


def test_repair_loop_docker_unavailable_gracefully_skips(monkeypatch):
    executor = DockerRExecutor()
    monkeypatch.setattr(executor, "is_docker_available", lambda: False)

    result = run_repair_loop(
        "print('safe')",
        execute=True,
        repair=True,
        max_repairs=1,
        executor=executor,
    )

    assert result.original_execution.status == "skipped"
    assert result.original_execution.reason == "Docker is not available."
    assert result.diagnostics == []
    assert result.suggestions == []
