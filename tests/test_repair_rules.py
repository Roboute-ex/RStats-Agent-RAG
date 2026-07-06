from rstats_agent.execution.repair import apply_one_shot_repair, suggest_repairs
from rstats_agent.schemas import ExecutionDiagnostic


def _diag(error_type: str) -> ExecutionDiagnostic:
    return ExecutionDiagnostic(
        error_type=error_type,
        severity="error",
        message="message",
        evidence="evidence",
        likely_cause="likely cause",
        suggested_fix="suggested fix",
    )


def test_missing_dplyr_library_gets_patch():
    code = "sales %>% filter(price > 0) %>% summarise(total = sum(price))"

    suggestions = suggest_repairs(code, [_diag("missing_function")])

    assert suggestions[0].repair_type == "add_library_dplyr"
    assert suggestions[0].patched_code.startswith("library(dplyr)")
    assert apply_one_shot_repair(code, [_diag("missing_function")]).startswith("library(dplyr)")


def test_missing_ggplot2_library_gets_patch():
    code = "ggplot(mpg, aes(displ, hwy)) + geom_point()"

    suggestions = suggest_repairs(code, [_diag("missing_function")])

    assert suggestions[0].repair_type == "add_library_ggplot2"
    assert suggestions[0].patched_code.startswith("library(ggplot2)")


def test_missing_lme4_library_gets_patch():
    code = "fit <- lmer(Reaction ~ Days + (Days | Subject), sleepstudy)"

    suggestions = suggest_repairs(code, [_diag("missing_function")])

    assert suggestions[0].repair_type == "add_library_lme4"
    assert suggestions[0].patched_code.startswith("library(lme4)")


def test_missing_package_never_installs_automatically():
    code = "library(dplyr)"

    suggestions = suggest_repairs(code, [_diag("missing_package")])

    assert suggestions[0].patched_code is None
    assert "install.packages" not in suggestions[0].message
    assert "manually" in suggestions[0].message


def test_singular_fit_can_suggest_simplified_random_effect():
    code = "fit <- lmer(Reaction ~ Days + (Days | Subject), data = sleepstudy)"

    suggestions = suggest_repairs(code, [_diag("lme4_singular_fit")])

    assert suggestions[0].repair_type == "simplify_lme4_random_effects"
    assert "(1 | Subject)" in suggestions[0].patched_code
    assert suggestions[0].confidence == "medium"


def test_column_not_found_does_not_blindly_rename():
    code = "sales %>% filter(price > 0)"

    suggestions = suggest_repairs(code, [_diag("column_not_found")])

    assert suggestions[0].patched_code is None
    assert "names(data)" in suggestions[0].message


def test_lme4_convergence_does_not_patch_blindly():
    suggestions = suggest_repairs("fit <- lmer(y ~ x + (x | g), data = df)", [_diag("lme4_convergence")])

    assert suggestions[0].patched_code is None
    assert "scale" in suggestions[0].message
