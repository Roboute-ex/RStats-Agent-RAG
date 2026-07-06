import pytest

from app.demo_cases import get_demo_case, list_demo_cases


def test_demo_cases_have_required_fields():
    cases = list_demo_cases()

    assert len(cases) == 4
    for case in cases:
        assert {"id", "title", "query", "category"} <= set(case)
        assert case["id"]
        assert case["title"]
        assert case["query"]
        assert case["category"]


def test_get_demo_case_returns_matching_case():
    case = get_demo_case("ggplot2-scatter-facet")

    assert case["id"] == "ggplot2-scatter-facet"
    assert case["category"] == "ggplot2"
    assert "ggplot2" in case["query"]


def test_get_demo_case_unknown_id_has_clear_error():
    with pytest.raises(ValueError, match="Unknown demo case id: missing-case"):
        get_demo_case("missing-case")


def test_list_demo_cases_returns_copies():
    cases = list_demo_cases()
    cases[0]["title"] = "changed"

    assert get_demo_case("dplyr-clean-summary")["title"] == "dplyr 数据清洗与汇总"

