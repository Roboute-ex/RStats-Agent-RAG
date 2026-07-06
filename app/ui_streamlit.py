"""Optional Streamlit UI for the local RStats-Agent-RAG demo."""

from __future__ import annotations

from typing import Any, Callable

from app.demo_cases import get_demo_case, list_demo_cases
from rstats_agent.cli import _build_agent
from rstats_agent.execution.r_executor import DEFAULT_R_DOCKER_IMAGE
from rstats_agent.reporting.markdown import render_markdown_report
from rstats_agent.schemas import AgentRequest, AgentResponse


STREAMLIT_INSTALL_HINT = 'Streamlit is not installed. Install web extras with: py -3 -m pip install -e ".[web]"'


def _load_streamlit():
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError(STREAMLIT_INSTALL_HINT) from exc
    return st


def _execution_payload(response: AgentResponse) -> dict[str, Any]:
    execution = response.execution
    return {
        "status": execution.status,
        "ok": execution.ok,
        "skipped": execution.skipped,
        "returncode": execution.returncode,
        "stdout": execution.stdout,
        "stderr": execution.stderr,
        "reason": execution.reason,
        "timed_out": execution.timed_out,
        "duration_sec": execution.duration_sec,
        "command_preview": execution.command_preview,
        "diagnostics": list(execution.diagnostics),
    }


def agent_response_to_web_payload(response: AgentResponse) -> dict[str, Any]:
    """Convert an AgentResponse into a JSON-safe web/API payload."""

    markdown_report = render_markdown_report(response)
    return {
        "task_type": response.task_type,
        "r_code": response.r_code,
        "explanation": response.explanation,
        "assumptions": list(response.assumptions),
        "failure_modes": list(response.failure_modes),
        "citations": list(response.citations),
        "retrieved_chunk_ids": [item.chunk_id for item in response.context],
        "execution": _execution_payload(response),
        "diagnostics": [
            {
                "error_type": item.error_type,
                "severity": item.severity,
                "message": item.message,
                "evidence": item.evidence,
                "likely_cause": item.likely_cause,
                "suggested_fix": item.suggested_fix,
            }
            for item in response.execution_diagnostics
        ],
        "repair_suggestions": [
            {
                "repair_type": item.repair_type,
                "message": item.message,
                "patched_code": item.patched_code,
                "confidence": item.confidence,
                "applied": item.applied,
            }
            for item in response.repair_suggestions
        ],
        "pipeline_diagnostics": list(response.diagnostics),
        "markdown_report": markdown_report,
    }


def run_agent_for_ui(
    question: str,
    *,
    retriever: str = "tfidf",
    execute: bool = False,
    repair: bool = False,
    max_repairs: int = 1,
    top_k: int = 6,
    timeout_sec: int = 20,
    docker_image: str = DEFAULT_R_DOCKER_IMAGE,
    agent_builder: Callable[[str], Any] = _build_agent,
) -> dict[str, Any]:
    """Run the existing Agent pipeline for Streamlit or FastAPI callers."""

    agent = agent_builder(retriever)
    response = agent.run(
        AgentRequest(
            question=question,
            retriever=retriever,
            execute=execute,
            repair=repair,
            max_repairs=max_repairs,
            top_k=top_k,
            timeout_sec=timeout_sec,
            docker_image=docker_image,
        )
    )
    return agent_response_to_web_payload(response)


def _write_list(st, title: str, items: list[str]) -> None:
    st.subheader(title)
    if not items:
        st.write("无")
        return
    for item in items:
        st.markdown(f"- {item}")


def main() -> None:
    st = _load_streamlit()

    st.set_page_config(page_title="RStats-Agent-RAG Demo", layout="wide")
    st.title("RStats-Agent-RAG Demo")

    demo_cases = list_demo_cases()
    case_ids = [case["id"] for case in demo_cases]
    case_titles = {case["id"]: case["title"] for case in demo_cases}

    selected_case_id = st.sidebar.selectbox(
        "Demo case",
        options=case_ids,
        format_func=lambda case_id: case_titles[case_id],
    )
    selected_case = get_demo_case(selected_case_id)
    retriever = st.sidebar.selectbox("Retriever", options=["tfidf", "hybrid"])
    execute = st.sidebar.checkbox("Execute", value=False)
    repair = st.sidebar.checkbox("Repair", value=False)
    max_repairs = st.sidebar.number_input("Max repairs", min_value=0, max_value=3, value=1, step=1)
    top_k = st.sidebar.number_input("Top K", min_value=1, max_value=20, value=6, step=1)

    question = st.text_area("User question", value=selected_case["query"], height=150)
    run_clicked = st.button("Run", type="primary")

    if not run_clicked:
        return

    with st.spinner("Running local Agent pipeline..."):
        payload = run_agent_for_ui(
            question,
            retriever=retriever,
            execute=execute,
            repair=repair,
            max_repairs=int(max_repairs),
            top_k=int(top_k),
        )

    st.subheader("Generated R code")
    st.code(payload["r_code"], language="r")

    st.subheader("Explanation")
    st.write(payload["explanation"])

    _write_list(st, "Assumptions", payload["assumptions"])
    _write_list(st, "Failure modes", payload["failure_modes"])
    _write_list(st, "Citations", payload["citations"])
    _write_list(st, "Retrieved chunk ids", payload["retrieved_chunk_ids"])

    st.subheader("Execution status")
    st.json(payload["execution"])

    if payload["diagnostics"]:
        st.subheader("Execution diagnostics")
        st.json(payload["diagnostics"])

    if payload["repair_suggestions"]:
        st.subheader("Repair suggestions")
        st.json(payload["repair_suggestions"])

    st.download_button(
        "Download Markdown report",
        data=payload["markdown_report"],
        file_name="rstats_agent_report.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
