from rstats_agent.execution.safety import check_r_code_safety


def test_allows_generated_style_r_code():
    report = check_r_code_safety("library(dplyr)\nprint(head(mtcars))")

    assert report.allowed
    assert report.diagnostics == ["静态安全检查通过。"]


def test_blocks_dangerous_system_call():
    report = check_r_code_safety("system('rm -rf /')")

    assert not report.allowed
    assert any("system()" in message for message in report.diagnostics)


def test_blocks_additional_dangerous_v01_calls():
    dangerous_calls = {
        "url('https://example.test')": "dangerous-url",
        "file.create('out.txt')": "dangerous-file-create",
        "writeLines('x', 'out.txt')": "dangerous-write-lines",
        "sink('out.txt')": "dangerous-sink",
        "setwd('/tmp')": "dangerous-setwd",
    }

    for code, expected_rule_id in dangerous_calls.items():
        report = check_r_code_safety(code)

        assert not report.allowed
        assert any(finding.rule_id == expected_rule_id for finding in report.findings)


def test_ignores_commented_dangerous_call():
    report = check_r_code_safety("# system('echo no')\nprint('safe')")

    assert report.allowed
