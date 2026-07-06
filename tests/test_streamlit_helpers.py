import sys

import pytest

from app.ui_streamlit import _load_streamlit, run_agent_for_ui


def test_run_agent_for_ui_calls_agent_pipeline_without_streamlit():
    result = run_agent_for_ui(
        "请用 dplyr 清洗销售数据，删除 price 缺失或小于等于 0 的行，按 store 和 month 汇总 revenue",
        execute=False,
        top_k=3,
    )

    assert result["task_type"] == "dplyr"
    assert "sales_clean" in result["r_code"]
    assert result["execution"]["status"] == "skipped"
    assert result["retrieved_chunk_ids"]
    assert "# RStats-Agent-RAG Analysis Report" in result["markdown_report"]


def test_run_agent_for_ui_passes_request_options():
    captured = {}

    class FakeResponseAgent:
        def run(self, request):
            from rstats_agent.schemas import AgentResponse, ExecutionResult

            captured["request"] = request
            return AgentResponse(
                question=request.question,
                task_type="demo",
                rewritten_queries={},
                retrieved=[],
                context=[],
                r_code="print('ok')",
                explanation="demo",
                assumptions=[],
                failure_modes=[],
                citations=[],
                execution=ExecutionResult(status="skipped", reason="R execution is disabled."),
            )

    result = run_agent_for_ui(
        "demo question",
        retriever="hybrid",
        execute=True,
        repair=True,
        max_repairs=2,
        top_k=4,
        agent_builder=lambda retriever: FakeResponseAgent(),
    )

    assert result["task_type"] == "demo"
    assert captured["request"].retriever == "hybrid"
    assert captured["request"].execute is True
    assert captured["request"].repair is True
    assert captured["request"].max_repairs == 2
    assert captured["request"].top_k == 4


def test_streamlit_missing_error_is_clear(monkeypatch):
    monkeypatch.setitem(sys.modules, "streamlit", None)

    with pytest.raises(RuntimeError, match="Streamlit is not installed"):
        _load_streamlit()
