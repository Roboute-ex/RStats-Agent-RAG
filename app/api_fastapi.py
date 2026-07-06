"""Optional FastAPI service for RStats-Agent-RAG."""

from __future__ import annotations

from typing import Literal

from app.demo_cases import list_demo_cases
from app.ui_streamlit import run_agent_for_ui
from rstats_agent import __version__


FASTAPI_INSTALL_HINT = 'FastAPI is not installed. Install web extras with: py -3 -m pip install -e ".[web]"'

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError:
    FastAPI = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment,misc]

    def Field(default=None, **_kwargs):  # type: ignore[no-redef]
        return default


class AnalyzeRequest(BaseModel):  # type: ignore[misc]
    question: str
    retriever: Literal["tfidf", "hybrid"] = "tfidf"
    execute: bool = False
    repair: bool = False
    max_repairs: int = Field(default=1, ge=0)
    top_k: int = Field(default=6, ge=1)


class _MissingFastAPIApp:
    def __call__(self, *_args, **_kwargs):
        raise RuntimeError(FASTAPI_INSTALL_HINT)


def create_app():
    """Create the optional FastAPI application."""

    if FastAPI is None:
        raise RuntimeError(FASTAPI_INSTALL_HINT)

    service = FastAPI(title="RStats-Agent-RAG", version=__version__)

    @service.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "service": "RStats-Agent-RAG",
        }

    @service.get("/demo-cases")
    def demo_cases() -> list[dict[str, str]]:
        return list_demo_cases()

    @service.post("/analyze")
    def analyze(request: AnalyzeRequest) -> dict:
        return run_agent_for_ui(
            request.question,
            retriever=request.retriever,
            execute=request.execute,
            repair=request.repair,
            max_repairs=request.max_repairs,
            top_k=request.top_k,
        )

    return service


try:
    app = create_app()
except RuntimeError:
    app = _MissingFastAPIApp()

