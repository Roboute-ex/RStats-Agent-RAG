import subprocess
from pathlib import Path

from rstats_agent.execution.r_executor import DockerRExecutor, build_docker_command


def test_executor_skips_when_disabled():
    result = DockerRExecutor().execute("print('hello')", enabled=False)

    assert result.status == "skipped"
    assert result.returncode is None


def test_executor_blocks_unsafe_code_before_docker_check():
    result = DockerRExecutor().execute("unlink('important.csv')", enabled=True)

    assert result.status == "unsafe"
    assert any("unlink()" in item for item in result.diagnostics)


def test_executor_skips_when_docker_unavailable(monkeypatch):
    executor = DockerRExecutor()
    monkeypatch.setattr(executor, "is_docker_available", lambda: False)

    result = executor.execute("print('safe')", enabled=True)

    assert result.status == "skipped"
    assert "Docker" in result.diagnostics[0]


def test_build_docker_command_uses_restricted_flags():
    command = build_docker_command(Path("C:/tmp/rstats-agent"), image="rocker/r-ver:4.3.3")

    assert "--rm" in command
    assert "--read-only" in command
    assert "--cpus" in command
    assert "1.0" in command
    assert "--memory" in command
    assert "1g" in command
    assert "--pids-limit" in command
    assert "256" in command
    assert "--network" in command
    assert "none" in command
    assert "--mount" in command
    assert "-w" in command
    assert "/work" in command
    assert command[-2:] == ["Rscript", "task.R"]


def test_executor_timeout_is_structured(monkeypatch):
    executor = DockerRExecutor()
    monkeypatch.setattr(executor, "is_docker_available", lambda: True)
    monkeypatch.setattr(executor, "is_image_available", lambda: True)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"], output="partial", stderr="slow")

    monkeypatch.setattr("rstats_agent.execution.r_executor.subprocess.run", fake_run)

    result = executor.execute("print('slow')", enabled=True, timeout_sec=1)

    assert result.status == "timeout"
    assert result.timed_out is True
    assert result.stdout == "partial"
    assert result.stderr == "slow"
    assert result.command_preview is not None


def test_executor_failed_run_is_structured(monkeypatch):
    executor = DockerRExecutor()
    monkeypatch.setattr(executor, "is_docker_available", lambda: True)
    monkeypatch.setattr(executor, "is_image_available", lambda: True)

    completed = subprocess.CompletedProcess(
        args=["docker"],
        returncode=1,
        stdout="",
        stderr="Error: object 'sales' not found",
    )
    monkeypatch.setattr("rstats_agent.execution.r_executor.subprocess.run", lambda *args, **kwargs: completed)

    result = executor.execute("print(sales)", enabled=True)

    assert result.status == "failed"
    assert result.returncode == 1
    assert "sales" in result.stderr
