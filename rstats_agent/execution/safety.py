"""Static safety checks for generated R code."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SafetyFinding:
    rule_id: str
    message: str
    pattern: str


@dataclass
class SafetyReport:
    allowed: bool
    findings: list[SafetyFinding] = field(default_factory=list)

    @property
    def diagnostics(self) -> list[str]:
        if self.allowed:
            return ["静态安全检查通过。"]
        return [finding.message for finding in self.findings]


DANGEROUS_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("dangerous-system", r"\bsystem\s*\(", "检测到 system()，可能执行任意 shell 命令。"),
    ("dangerous-system2", r"\bsystem2\s*\(", "检测到 system2()，可能执行任意 shell 命令。"),
    ("dangerous-shell", r"\bshell\s*\(", "检测到 shell()，可能执行任意 shell 命令。"),
    ("dangerous-unlink", r"\bunlink\s*\(", "检测到 unlink()，可能删除文件。"),
    ("dangerous-file-remove", r"\bfile\.remove\s*\(", "检测到 file.remove()，可能删除文件。"),
    ("dangerous-url", r"\burl\s*\(", "检测到 url()，可能打开网络或文件连接。"),
    ("dangerous-file-create", r"\bfile\.create\s*\(", "检测到 file.create()，可能写入文件系统。"),
    ("dangerous-write-lines", r"\bwriteLines\s*\(", "检测到 writeLines()，可能写入文件或连接。"),
    ("dangerous-sink", r"\bsink\s*\(", "检测到 sink()，可能重定向输出到文件或连接。"),
    ("dangerous-setwd", r"\bsetwd\s*\(", "检测到 setwd()，可能改变执行工作目录。"),
    ("dangerous-download", r"\bdownload\.file\s*\(", "检测到 download.file()，会访问网络。"),
    ("dangerous-install", r"\binstall\.packages\s*\(", "检测到 install.packages()，会访问外部包仓库。"),
    ("dangerous-source-url", r"\bsource\s*\(\s*[\"']https?://", "检测到 source(URL)，会执行远程代码。"),
)


def _strip_r_comments(code: str) -> str:
    lines = []
    for line in code.splitlines():
        quote: str | None = None
        escaped = False
        kept = []
        for char in line:
            if escaped:
                kept.append(char)
                escaped = False
                continue
            if char == "\\":
                kept.append(char)
                escaped = True
                continue
            if char in {"'", '"'}:
                if quote == char:
                    quote = None
                elif quote is None:
                    quote = char
                kept.append(char)
                continue
            if char == "#" and quote is None:
                break
            kept.append(char)
        lines.append("".join(kept))
    return "\n".join(lines)


def check_r_code_safety(code: str) -> SafetyReport:
    """Return a static safety report for R code."""

    searchable = _strip_r_comments(code)
    findings: list[SafetyFinding] = []
    for rule_id, pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, searchable, flags=re.IGNORECASE):
            findings.append(SafetyFinding(rule_id=rule_id, message=message, pattern=pattern))
    return SafetyReport(allowed=not findings, findings=findings)
