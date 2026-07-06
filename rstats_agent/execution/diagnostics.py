"""Rule-based diagnostics for R execution errors."""

from __future__ import annotations

import re

from rstats_agent.schemas import ExecutionDiagnostic


def _first_evidence(text: str, patterns: list[str]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for pattern in patterns:
        regex = re.compile(pattern, flags=re.IGNORECASE)
        for line in lines:
            if regex.search(line):
                return line[:300]
    return (lines[0] if lines else text.strip())[:300]


def _diagnostic(
    error_type: str,
    severity: str,
    message: str,
    evidence: str,
    likely_cause: str,
    suggested_fix: str,
) -> ExecutionDiagnostic:
    return ExecutionDiagnostic(
        error_type=error_type,
        severity=severity,
        message=message,
        evidence=evidence,
        likely_cause=likely_cause,
        suggested_fix=suggested_fix,
    )


def classify_r_error(stderr: str, stdout: str = "") -> list[ExecutionDiagnostic]:
    """Classify common R errors without calling R or an LLM."""

    combined = "\n".join(part for part in [stderr, stdout] if part).strip()
    if not combined:
        return []

    lower = combined.lower()
    diagnostics: list[ExecutionDiagnostic] = []

    missing_package_patterns = [
        r"there is no package called",
        r"package\s+['\"].+?['\"]\s+is not installed",
    ]
    if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in missing_package_patterns):
        diagnostics.append(
            _diagnostic(
                "missing_package",
                "error",
                "R package is missing from the execution environment.",
                _first_evidence(combined, missing_package_patterns),
                "The generated code loads a package that is not installed in the current R library.",
                "Install the package manually in a reproducible environment, update renv.lock, or rerun with --no-execute.",
            )
        )

    if re.search(r"could not find function", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "missing_function",
                "error",
                "R could not resolve a function name.",
                _first_evidence(combined, [r"could not find function"]),
                "A required library() call may be missing, the function name may be misspelled, or package::function may be needed.",
                "Load the right package with library(pkg), fix the function name, or call the function with package::function.",
            )
        )

    explicit_column = re.search(r"Column\s+.+?doesn['’]t exist", combined, flags=re.IGNORECASE)
    object_not_found = re.search(r"object\s+['\"]?.+?['\"]?\s+not found", combined, flags=re.IGNORECASE)
    column_context_terms = ("dplyr", "ggplot", "aes", "select", "filter")
    has_column_context = any(term in lower for term in column_context_terms)
    if explicit_column or (object_not_found and has_column_context):
        diagnostics.append(
            _diagnostic(
                "column_not_found",
                "error",
                "A referenced data column was not found.",
                _first_evidence(combined, [r"Column\s+.+?doesn['’]t exist", r"object\s+.+?\s+not found"]),
                "The input data may use different column names than the generated template expects.",
                "Inspect names(data), confirm the input object, and replace placeholder columns with real field names.",
            )
        )
    elif object_not_found:
        diagnostics.append(
            _diagnostic(
                "object_not_found",
                "error",
                "R could not find a referenced object.",
                _first_evidence(combined, [r"object\s+.+?\s+not found"]),
                "The input data object may not exist, or a column/object name may be misspelled.",
                "Create or load the required object, check names(data), and align the generated code with the real data.",
            )
        )

    if re.search(r"unexpected end of input|parse", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "parse_error",
                "error",
                "R could not parse the code.",
                _first_evidence(combined, [r"unexpected end of input", r"parse"]),
                "The code may have an incomplete expression, missing closing delimiter, or truncated pipeline.",
                "Check parentheses, braces, quotes, commas, and pipe operators before executing again.",
            )
        )
    elif re.search(r"Error:\s*unexpected|unexpected", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "syntax_error",
                "error",
                "R reported an unexpected token.",
                _first_evidence(combined, [r"Error:\s*unexpected", r"unexpected"]),
                "The code likely contains a syntax issue around brackets, commas, quotes, or pipes.",
                "Review the indicated line and repair unmatched delimiters, misplaced commas, quotes, or pipe operators.",
            )
        )

    if re.search(r"boundary\s*\(singular\)\s*fit|singular fit", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "lme4_singular_fit",
                "warning",
                "lme4 reported a singular random-effects fit.",
                _first_evidence(combined, [r"boundary\s*\(singular\)\s*fit", r"singular fit"]),
                "The random-effects structure may be too complex for the available grouping levels or repeated observations.",
                "Consider simplifying the random-effects structure, for example using (1 | Subject), and inspect the study design.",
            )
        )

    if re.search(r"failed to converge|convergence", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "lme4_convergence",
                "warning",
                "lme4 reported a model convergence issue.",
                _first_evidence(combined, [r"failed to converge", r"convergence"]),
                "The model may be over-complex, poorly scaled, affected by outliers, or using a difficult optimizer path.",
                "Check variable scaling and outliers, simplify the model if justified, or try an optimizer deliberately.",
            )
        )

    if re.search(r"namespace|loaded namespace", combined, flags=re.IGNORECASE):
        diagnostics.append(
            _diagnostic(
                "package_namespace_error",
                "error",
                "R reported a package namespace conflict or version issue.",
                _first_evidence(combined, [r"loaded namespace", r"namespace"]),
                "A loaded package namespace may be incompatible with the requested package or version.",
                "Restart the R session, align package versions, and update the reproducible environment metadata.",
            )
        )

    if not diagnostics:
        diagnostics.append(
            _diagnostic(
                "unknown_error",
                "error",
                "R execution failed with an unclassified error.",
                combined[:300],
                "The error does not match the v0.4 deterministic diagnostic rules.",
                "Inspect stderr/stdout, reproduce locally if needed, and add a targeted rule if this failure is common.",
            )
        )

    return diagnostics
