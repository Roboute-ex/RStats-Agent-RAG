"""Deterministic repair suggestions for common R execution diagnostics."""

from __future__ import annotations

import re

from rstats_agent.schemas import ExecutionDiagnostic, RepairSuggestion


PACKAGE_FUNCTIONS: dict[str, tuple[str, ...]] = {
    "dplyr": ("filter", "mutate", "group_by", "summarise", "summarize", "arrange"),
    "ggplot2": ("ggplot", "aes", "geom_point", "facet_wrap", "labs"),
    "lme4": ("lmer", "fixef", "ranef"),
}


def _has_library(code: str, package: str) -> bool:
    pattern = rf"\b(?:library|require)\s*\(\s*['\"]?{re.escape(package)}['\"]?\s*\)"
    return re.search(pattern, code, flags=re.IGNORECASE) is not None


def _uses_package_functions(code: str, package: str) -> bool:
    for function_name in PACKAGE_FUNCTIONS[package]:
        if re.search(rf"\b{re.escape(function_name)}\s*\(", code):
            return True
    return False


def _prepend_library(code: str, package: str) -> str:
    if _has_library(code, package):
        return code
    return f"library({package})\n\n{code.lstrip()}"


def _missing_library_suggestions(code: str) -> list[RepairSuggestion]:
    suggestions: list[RepairSuggestion] = []
    for package in ("dplyr", "ggplot2", "lme4"):
        if _uses_package_functions(code, package) and not _has_library(code, package):
            suggestions.append(
                RepairSuggestion(
                    repair_type=f"add_library_{package}",
                    message=f"Add library({package}) because generated code uses {package} functions without loading the package.",
                    patched_code=_prepend_library(code, package),
                    confidence="high",
                )
            )
    return suggestions


def suggest_repairs(code: str, diagnostics: list[ExecutionDiagnostic]) -> list[RepairSuggestion]:
    """Return rule-based repair suggestions without calling an LLM."""

    suggestions: list[RepairSuggestion] = []
    seen_types: set[str] = set()
    for diagnostic in diagnostics:
        if diagnostic.error_type in seen_types:
            continue
        seen_types.add(diagnostic.error_type)

        if diagnostic.error_type == "missing_package":
            suggestions.append(
                RepairSuggestion(
                    repair_type="missing_package_manual_install",
                    message=(
                        "The R package is missing. Install it manually in a reproducible environment, "
                        "update renv.lock later, or rerun with --no-execute. The agent will not install packages automatically."
                    ),
                    confidence="high",
                )
            )
        elif diagnostic.error_type == "missing_function":
            suggestions.extend(_missing_library_suggestions(code))
            if not suggestions:
                suggestions.append(
                    RepairSuggestion(
                        repair_type="check_function_or_namespace",
                        message="Check for a misspelled function name or call it with package::function.",
                        confidence="medium",
                    )
                )
        elif diagnostic.error_type in {"object_not_found", "column_not_found"}:
            suggestions.append(
                RepairSuggestion(
                    repair_type="check_input_objects_and_columns",
                    message=(
                        "Do not rename columns blindly. Check names(data), replace template columns with real names, "
                        "and ensure the input data object exists."
                    ),
                    confidence="high",
                )
            )
        elif diagnostic.error_type in {"syntax_error", "parse_error"}:
            suggestions.append(
                RepairSuggestion(
                    repair_type="inspect_r_syntax",
                    message="Check parentheses, braces, commas, quotes, and pipe operators near the reported parse location.",
                    confidence="medium",
                )
            )
        elif diagnostic.error_type == "lme4_singular_fit":
            patched_code = None
            if "(Days | Subject)" in code:
                patched_code = code.replace("(Days | Subject)", "(1 | Subject)", 1)
            suggestions.append(
                RepairSuggestion(
                    repair_type="simplify_lme4_random_effects",
                    message=(
                        "A singular fit can mean the random-effects structure is too complex. "
                        "A one-shot patch can simplify (Days | Subject) to (1 | Subject), but this is not guaranteed to be statistically optimal."
                    ),
                    patched_code=patched_code,
                    confidence="medium",
                )
            )
        elif diagnostic.error_type == "lme4_convergence":
            suggestions.append(
                RepairSuggestion(
                    repair_type="review_lme4_convergence",
                    message=(
                        "Check scaling, outliers, grouping structure, and model complexity. Consider scale(Days) or an optimizer only after reviewing diagnostics."
                    ),
                    confidence="medium",
                )
            )
        else:
            suggestions.append(
                RepairSuggestion(
                    repair_type="manual_debug",
                    message="Inspect stderr/stdout and reproduce the error locally; no deterministic patch is available.",
                    confidence="low",
                )
            )

    return suggestions


def apply_one_shot_repair(code: str, diagnostics: list[ExecutionDiagnostic]) -> str | None:
    """Return the first deterministic patched code candidate, if any."""

    for suggestion in suggest_repairs(code, diagnostics):
        if suggestion.patched_code and suggestion.patched_code != code:
            return suggestion.patched_code
    return None
