from rstats_agent.execution.r_executor import DockerRExecutor


def test_executor_skips_when_disabled():
    result = DockerRExecutor().execute("print('hello')", enabled=False)

    assert result.status == "skipped"
    assert result.returncode is None


def test_executor_blocks_unsafe_code_before_docker_check():
    result = DockerRExecutor().execute("unlink('important.csv')", enabled=True)

    assert result.status == "blocked"
    assert any("unlink()" in item for item in result.diagnostics)


def test_executor_skips_when_docker_unavailable(monkeypatch):
    executor = DockerRExecutor()
    monkeypatch.setattr(executor, "is_docker_available", lambda: False)

    result = executor.execute("print('safe')", enabled=True)

    assert result.status == "skipped"
    assert "Docker" in result.diagnostics[0]
