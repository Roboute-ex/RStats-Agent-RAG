"""End-to-end local R Agent and RAG pipeline."""

from __future__ import annotations

from rstats_agent.agents.fusion import fuse_context
from rstats_agent.agents.generator import generate_answer
from rstats_agent.agents.prompts import LOCAL_PIPELINE_NOTE
from rstats_agent.agents.repair_loop import run_repair_loop
from rstats_agent.execution.r_executor import DockerRExecutor
from rstats_agent.knowledge.query_rewriter import detect_task_types, rewrite_query
from rstats_agent.knowledge.retriever import LocalTfidfRetriever, build_default_retriever
from rstats_agent.schemas import AgentRequest, AgentResponse


class RStatsAgent:
    """Local deterministic Agent for the R statistics MVP."""

    def __init__(
        self,
        retriever: LocalTfidfRetriever | None = None,
        executor: DockerRExecutor | None = None,
    ) -> None:
        self.retriever = retriever or build_default_retriever()
        self.executor = executor or DockerRExecutor()

    def run(self, request: AgentRequest | str) -> AgentResponse:
        if isinstance(request, str):
            request = AgentRequest(question=request)

        rewritten = rewrite_query(request.question)
        retrieved = self.retriever.search(rewritten, top_k=request.top_k)
        task_hints = [task for task in detect_task_types(request.question) if task != "general_r"]
        context = fuse_context(retrieved, max_chunks=request.top_k, preferred_packages=task_hints)
        generated = generate_answer(request.question, context)

        self.executor.image = request.docker_image
        self.executor.timeout_seconds = request.timeout_sec
        repair_loop = run_repair_loop(
            generated.r_code,
            execute=request.execute,
            repair=request.repair,
            max_repairs=request.max_repairs,
            executor=self.executor,
            timeout_sec=request.timeout_sec,
        )
        execution = repair_loop.original_execution

        citations = [item.as_citation() for item in context]
        diagnostics = [
            LOCAL_PIPELINE_NOTE,
            f"knowledge_source={self.retriever.knowledge_source}",
            f"retriever={request.retriever}",
            f"repair_enabled={request.repair}",
            f"max_repairs={request.max_repairs}",
            f"retrieval_top_k={request.top_k}",
            f"context_chunks={len(context)}",
        ]
        diagnostics.extend(getattr(self.retriever, "diagnostics", []))
        diagnostics.extend(execution.diagnostics)
        diagnostics.extend(f"execution_diagnostic={item.error_type}" for item in repair_loop.diagnostics)
        diagnostics.extend(f"repair_suggestion={item.repair_type}" for item in repair_loop.suggestions)
        diagnostics.append(f"repair_loop_attempts={repair_loop.attempts}")

        return AgentResponse(
            question=request.question,
            task_type=generated.task_type,
            rewritten_queries=rewritten,
            retrieved=retrieved,
            context=context,
            r_code=generated.r_code,
            explanation=generated.explanation,
            assumptions=generated.assumptions,
            failure_modes=generated.failure_modes,
            citations=citations,
            execution=execution,
            knowledge_source=self.retriever.knowledge_source,
            diagnostics=diagnostics,
            execution_diagnostics=repair_loop.diagnostics,
            repair_suggestions=repair_loop.suggestions,
            repair_loop=repair_loop,
        )
