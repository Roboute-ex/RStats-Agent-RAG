"""Optional Docker-backed R execution with deterministic skip fallback."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from rstats_agent.execution.safety import check_r_code_safety
from rstats_agent.schemas import ExecutionResult


@dataclass
class DockerRExecutor:
    image: str = "rocker/r-ver:4.3.3"
    timeout_seconds: int = 20
    allow_pull: bool = False

    def is_docker_available(self) -> bool:
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

    def is_image_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def execute(self, r_code: str, enabled: bool = False) -> ExecutionResult:
        safety = check_r_code_safety(r_code)
        if not safety.allowed:
            return ExecutionResult(status="blocked", diagnostics=safety.diagnostics)

        if not enabled:
            return ExecutionResult(
                status="skipped",
                diagnostics=["未启用 R 执行；已完成静态安全检查。"],
            )

        if not self.is_docker_available():
            return ExecutionResult(
                status="skipped",
                diagnostics=["未检测到可用 Docker；跳过 R 执行，不影响核心流程。"],
            )

        if not self.allow_pull and not self.is_image_available():
            return ExecutionResult(
                status="skipped",
                diagnostics=[
                    f"Docker 可用，但本地没有镜像 {self.image}；为避免测试或演示时隐式联网，已跳过执行。"
                ],
            )

        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "-i", self.image, "Rscript", "-"],
                input=r_code,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                status="failed",
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                diagnostics=[f"R 执行超时：{self.timeout_seconds} 秒。"],
            )
        except OSError as exc:
            return ExecutionResult(status="failed", stderr=str(exc), diagnostics=["启动 Docker 执行失败。"])

        return ExecutionResult(
            status="success" if result.returncode == 0 else "failed",
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            diagnostics=["Docker R 执行完成。"],
        )
