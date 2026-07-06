import pytest

from app import api_fastapi


def test_create_app_missing_fastapi_message_is_clear(monkeypatch):
    monkeypatch.setattr(api_fastapi, "FastAPI", None)

    with pytest.raises(RuntimeError, match="FastAPI is not installed"):
        api_fastapi.create_app()


def _test_client():
    pytest.importorskip("fastapi")
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    return fastapi_testclient.TestClient(api_fastapi.create_app())


def test_fastapi_health_and_demo_cases_when_installed():
    client = _test_client()

    health = client.get("/health")
    cases = client.get("/demo-cases")

    assert health.status_code == 200
    assert health.json()["service"] == "RStats-Agent-RAG"
    assert health.json()["status"] == "ok"
    assert cases.status_code == 200
    assert len(cases.json()) == 4


def test_fastapi_analyze_defaults_to_no_execute_when_installed():
    client = _test_client()

    response = client.post(
        "/analyze",
        json={"question": "请用 ggplot2 对 mpg 画 displ 和 hwy 的散点图，颜色映射 class，并按 drv 分面"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_type"] == "ggplot2"
    assert payload["execution"]["status"] == "skipped"
    assert payload["execution"]["reason"] == "R execution is disabled."
    assert "# RStats-Agent-RAG Analysis Report" in payload["markdown_report"]


def test_fastapi_analyze_docker_unavailable_shape_when_installed(monkeypatch):
    client = _test_client()

    def fake_run_agent_for_ui(question, **kwargs):
        return {
            "task_type": "dplyr",
            "r_code": "print('ok')",
            "explanation": "demo",
            "assumptions": [],
            "failure_modes": [],
            "citations": [],
            "retrieved_chunk_ids": [],
            "execution": {
                "status": "skipped",
                "ok": False,
                "skipped": True,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "reason": "Docker is not available.",
                "timed_out": False,
                "duration_sec": None,
                "command_preview": None,
                "diagnostics": ["Docker is not available."],
            },
            "diagnostics": [],
            "repair_suggestions": [],
            "pipeline_diagnostics": [],
            "markdown_report": "# report",
        }

    monkeypatch.setattr(api_fastapi, "run_agent_for_ui", fake_run_agent_for_ui)

    response = client.post(
        "/analyze",
        json={"question": "demo", "execute": True, "repair": True},
    )

    assert response.status_code == 200
    assert response.json()["execution"]["status"] == "skipped"
    assert response.json()["execution"]["reason"] == "Docker is not available."

