from rstats_agent.execution.diagnostics import classify_r_error


def _types(stderr: str, stdout: str = "") -> list[str]:
    return [item.error_type for item in classify_r_error(stderr, stdout)]


def test_classifies_missing_package():
    diagnostics = classify_r_error("Error in library(dplyr) : there is no package called 'dplyr'")

    assert diagnostics[0].error_type == "missing_package"
    assert diagnostics[0].severity == "error"
    assert "renv.lock" in diagnostics[0].suggested_fix
    assert "install.packages" not in diagnostics[0].suggested_fix


def test_classifies_missing_function():
    assert "missing_function" in _types("Error in filter(df, x > 1) : could not find function \"filter\"")


def test_classifies_object_not_found():
    assert "object_not_found" in _types("Error: object 'sales' not found")


def test_classifies_column_not_found_explicit_column_error():
    assert "column_not_found" in _types("Error in `filter()`: Column `price` doesn't exist.")


def test_classifies_column_not_found_from_context():
    stderr = "Error in dplyr::filter(sales, price > 0) : object 'price' not found"

    assert "column_not_found" in _types(stderr)


def test_classifies_syntax_error():
    assert "syntax_error" in _types("Error: unexpected ')' in \"filter(price > )\"")


def test_classifies_parse_error():
    assert "parse_error" in _types("Error in parse(text = x) : unexpected end of input")


def test_classifies_lme4_convergence():
    assert "lme4_convergence" in _types("Model failed to converge with max|grad| = 0.1")


def test_classifies_lme4_singular_fit():
    assert "lme4_singular_fit" in _types("boundary (singular) fit: see help('isSingular')")


def test_classifies_namespace_error():
    assert "package_namespace_error" in _types("namespace 'Matrix' 1.6 is already loaded, but >= 1.7 is required")


def test_classifies_unknown_error():
    diagnostics = classify_r_error("Error: something unusual happened")

    assert diagnostics[0].error_type == "unknown_error"
    assert diagnostics[0].evidence
