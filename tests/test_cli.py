from pathlib import Path

from rstats_agent.cli import build_parser, main
from rstats_agent.schemas import AgentResponse, ExecutionResult


def test_cli_defaults_to_no_execute():
    args = build_parser().parse_args(["use dplyr to clean sales data"])

    assert args.execute is False


def test_cli_accepts_no_execute_compat_flag():
    args = build_parser().parse_args(["use ggplot2 to draw a scatter plot", "--no-execute"])

    assert args.execute is False


def test_cli_execute_sets_execute_true():
    args = build_parser().parse_args(["use lme4 to fit a model", "--execute"])

    assert args.execute is True


def test_cli_report_and_report_path_share_dest():
    parser = build_parser()

    report_args = parser.parse_args(["use ggplot2 to draw a scatter plot", "--report", "reports/a.md"])
    report_path_args = parser.parse_args(
        ["use ggplot2 to draw a scatter plot", "--report-path", "reports/b.md"]
    )

    assert report_args.report_path == Path("reports/a.md")
    assert report_path_args.report_path == Path("reports/b.md")
    assert not hasattr(report_args, "report")


def test_cli_accepts_repair_arguments():
    args = build_parser().parse_args(
        [
            "use dplyr to clean sales data",
            "--execute",
            "--repair",
            "--max-repairs",
            "1",
            "--timeout-sec",
            "7",
            "--docker-image",
            "rocker/r-ver:4.3.3",
        ]
    )

    assert args.execute is True
    assert args.repair is True
    assert args.max_repairs == 1
    assert args.timeout_sec == 7
    assert args.docker_image == "rocker/r-ver:4.3.3"


def test_cli_execute_repair_main_does_not_break_output(monkeypatch, capsys):
    captured = {}

    class FakeAgent:
        def run(self, request):
            captured["request"] = request
            return AgentResponse(
                question=request.question,
                task_type="dplyr",
                rewritten_queries={},
                retrieved=[],
                context=[],
                r_code="print('ok')",
                explanation="demo",
                assumptions=[],
                failure_modes=[],
                citations=[],
                execution=ExecutionResult(status="skipped", reason="Docker is not available."),
                diagnostics=["knowledge_source=fixture_fallback"],
            )

    monkeypatch.setattr("rstats_agent.cli._build_agent", lambda retriever_mode: FakeAgent())

    exit_code = main(["demo", "--execute", "--repair", "--max-repairs", "1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "# RStats-Agent-RAG Analysis Report" in output
    assert captured["request"].execute is True
    assert captured["request"].repair is True
    assert captured["request"].max_repairs == 1
