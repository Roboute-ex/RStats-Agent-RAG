from pathlib import Path

from rstats_agent.cli import build_parser


def test_cli_defaults_to_no_execute():
    args = build_parser().parse_args(["请用 dplyr 清洗销售数据"])

    assert args.execute is False


def test_cli_accepts_no_execute_compat_flag():
    args = build_parser().parse_args(["请用 ggplot2 画散点图", "--no-execute"])

    assert args.execute is False


def test_cli_execute_sets_execute_true():
    args = build_parser().parse_args(["请用 lme4 拟合模型", "--execute"])

    assert args.execute is True


def test_cli_report_and_report_path_share_dest():
    parser = build_parser()

    report_args = parser.parse_args(["请用 ggplot2 画散点图", "--report", "reports/a.md"])
    report_path_args = parser.parse_args(["请用 ggplot2 画散点图", "--report-path", "reports/b.md"])

    assert report_args.report_path == Path("reports/a.md")
    assert report_path_args.report_path == Path("reports/b.md")
    assert not hasattr(report_args, "report")
