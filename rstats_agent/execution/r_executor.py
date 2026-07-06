"""Optional Docker-backed R execution with deterministic skip fallback."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from rstats_agent.execution.safety import check_r_code_safety
from rstats_agent.schemas import ExecutionResult


DEFAULT_R_DOCKER_IMAGE = "rocker/r-ver:4.3.3"


def is_docker_available() -> bool:
    """Return whether the Docker CLI is available and responsive."""

    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def is_image_available(image: str) -> bool:
    """Return whether an image already exists locally."""

    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def build_docker_command(work_dir: Path, image: str = DEFAULT_R_DOCKER_IMAGE) -> list[str]:
    """Build the restricted Docker command used by the optional R executor."""

    return [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--cpus",
        "1.0",
        "--memory",
        "1g",
        "--pids-limit",
        "256",
        "--network",
        "none",
        "--mount",
        f"type=bind,source={work_dir},target=/work",
        "-w",
        "/work",
        image,
        "Rscript",
        "task.R",
    ]


def _text_or_empty(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run_docker_script(
    r_code: str,
    *,
    image: str,
    timeout_sec: int,
) -> ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="rstats-agent-r-") as temp_dir:
        work_dir = Path(temp_dir).resolve()
        script_path = work_dir / "task.R"
        script_path.write_text(r_code, encoding="utf-8")
        command = build_docker_command(work_dir, image=image)
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                status="timeout",
                stdout=_text_or_empty(exc.stdout),
                stderr=_text_or_empty(exc.stderr),
                reason=f"R execution timed out after {timeout_sec} seconds.",
                timed_out=True,
                duration_sec=time.monotonic() - started,
                command_preview=command,
                diagnostics=[f"R execution timed out after {timeout_sec} seconds."],
            )
        except OSError as exc:
            return ExecutionResult(
                status="failed",
                stderr=str(exc),
                reason="Failed to start Docker R execution.",
                duration_sec=time.monotonic() - started,
                command_preview=command,
                diagnostics=["Failed to start Docker R execution."],
            )

    status = "ok" if result.returncode == 0 else "failed"
    return ExecutionResult(
        status=status,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        reason=None if status == "ok" else "Rscript returned a non-zero exit code.",
        duration_sec=time.monotonic() - started,
        command_preview=command,
        diagnostics=["Docker R execution completed."],
    )


def run_r_script(
    r_code: str,
    *,
    image: str = DEFAULT_R_DOCKER_IMAGE,
    timeout_sec: int = 20,
    allow_pull: bool = False,
) -> ExecutionResult:
    """Run R code through Docker when available, otherwise return a skipped result."""

    safety = check_r_code_safety(r_code)
    if not safety.allowed:
        return ExecutionResult(
            status="unsafe",
            reason="Static safety check failed; Docker execution was not attempted.",
            diagnostics=safety.diagnostics,
        )

    if not is_docker_available():
        return ExecutionResult(
            status="skipped",
            reason="Docker is not available.",
            diagnostics=["Docker is not available; skipped optional R execution."],
        )

    if not allow_pull and not is_image_available(image):
        return ExecutionResult(
            status="skipped",
            reason=f"Docker image {image} is not available locally.",
            diagnostics=[
                f"Docker is available, but image {image} is not local; skipped to avoid implicit network pull."
            ],
        )

    return _run_docker_script(r_code, image=image, timeout_sec=timeout_sec)


@dataclass
class DockerRExecutor:
    image: str = DEFAULT_R_DOCKER_IMAGE
    timeout_seconds: int = 20
    allow_pull: bool = False

    def is_docker_available(self) -> bool:
        return is_docker_available()

    def is_image_available(self) -> bool:
        return is_image_available(self.image)

    def build_docker_command(self, work_dir: Path) -> list[str]:
        return build_docker_command(work_dir, image=self.image)

    def execute(
        self,
        r_code: str,
        enabled: bool = False,
        timeout_sec: int | None = None,
    ) -> ExecutionResult:
        safety = check_r_code_safety(r_code)
        if not safety.allowed:
            return ExecutionResult(
                status="unsafe",
                reason="Static safety check failed; Docker execution was not attempted.",
                diagnostics=safety.diagnostics,
            )

        if not enabled:
            return ExecutionResult(
                status="skipped",
                reason="R execution is disabled.",
                diagnostics=["R execution is disabled; static safety check completed."],
            )

        if not self.is_docker_available():
            return ExecutionResult(
                status="skipped",
                reason="Docker is not available.",
                diagnostics=["Docker is not available; skipped optional R execution."],
            )

        if not self.allow_pull and not self.is_image_available():
            return ExecutionResult(
                status="skipped",
                reason=f"Docker image {self.image} is not available locally.",
                diagnostics=[
                    f"Docker is available, but image {self.image} is not local; skipped to avoid implicit network pull."
                ],
            )

        return _run_docker_script(
            r_code,
            image=self.image,
            timeout_sec=timeout_sec or self.timeout_seconds,
        )
