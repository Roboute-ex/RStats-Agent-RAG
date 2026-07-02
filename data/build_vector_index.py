"""Build local vector index artifacts from the selected knowledge corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rstats_agent.config import DEFAULT_VECTOR_ARTIFACTS_DIR
from rstats_agent.embeddings.base import EmbeddingBackend
from rstats_agent.embeddings.local_hash import LocalHashEmbeddingBackend
from rstats_agent.embeddings.sentence_transformer import SentenceTransformerEmbeddingBackend
from rstats_agent.knowledge.corpus_loader import load_corpus, load_corpus_with_metadata
from rstats_agent.knowledge.vector_index import FaissVectorIndex, NumpyVectorIndex
from rstats_agent.schemas import KnowledgeChunk


def _chunk_text(chunk: KnowledgeChunk) -> str:
    return " ".join(
        [
            chunk.chunk_id,
            chunk.package,
            chunk.function,
            chunk.source_type,
            chunk.title,
            chunk.text,
            chunk.priority,
        ]
    )


def _build_embedding_backend(args: argparse.Namespace) -> EmbeddingBackend:
    if args.backend == "local-hash":
        return LocalHashEmbeddingBackend()
    if args.backend == "sentence-transformer":
        return SentenceTransformerEmbeddingBackend(model_name=args.model_name)
    raise ValueError(f"Unsupported embedding backend: {args.backend}")


def _load_chunks(corpus_path: Path | None) -> tuple[list[KnowledgeChunk], str]:
    if corpus_path is not None:
        return load_corpus(corpus_path), str(corpus_path)
    chunks, source, path = load_corpus_with_metadata()
    return chunks, f"{source}:{path}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build local vector index artifacts.")
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument("--backend", choices=["local-hash", "sentence-transformer"], default="local-hash")
    parser.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name; ignored by local-hash.",
    )
    parser.add_argument("--index-backend", choices=["numpy", "faiss"], default="numpy")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_VECTOR_ARTIFACTS_DIR)
    parser.add_argument("--query", default=None, help="Optional smoke search query.")
    parser.add_argument("--top-k", type=int, default=6, help="Optional smoke search top_k.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    chunks, source_label = _load_chunks(args.corpus)
    try:
        backend = _build_embedding_backend(args)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    texts = [_chunk_text(chunk) for chunk in chunks]
    embeddings = backend.embed_texts(texts)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output_dir / "metadata.jsonl"
    embeddings_path = args.output_dir / "embeddings.npy"

    if args.index_backend == "numpy":
        index = NumpyVectorIndex.build(chunks, embeddings)
        index.save(embeddings_path, metadata_path)
        index_path = embeddings_path
    else:
        try:
            index = FaissVectorIndex.build(chunks, embeddings)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        embeddings_path.unlink(missing_ok=True)
        np.save(embeddings_path, np.asarray(embeddings, dtype="float32"))
        index_path = args.output_dir / "faiss.index"
        index.save(index_path, metadata_path)

    print(f"Built {args.index_backend} vector index with {len(chunks)} chunks")
    print(f"corpus={source_label}")
    print(f"embedding_backend={backend.name}")
    print(f"index_path={index_path}")
    print(f"metadata_path={metadata_path}")

    if args.query:
        results = index.search(backend.embed_query(args.query), top_k=args.top_k)
        for result in results:
            print(f"{result.chunk_id}\t{result.score:.6f}\t{result.package}::{result.function}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
