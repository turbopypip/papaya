from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
import json
import logging

import joblib
import numpy as np
import polars as pl

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "stackexchange_titles.jsonl"
CONTENT_INDEX_FILENAME = "content_index.joblib"


@dataclass(frozen=True)
class ThreadContentFixture:
    title: str
    tags: list[str]
    topic: str
    content: str
    source_url: str
    source: str
    license: str
    attribution: str
    question_id: str = ""
    owner_source_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    score: int = 0
    posts: list[dict[str, Any]] | None = None
    comments: list[dict[str, Any]] | None = None


@dataclass
class ContentIndex:
    thread_ids: list[str]
    content_hashes: dict[str, str]
    embeddings: np.ndarray
    backend: str
    search_backend: str
    model_name: str
    build_seconds: float
    metadata: dict[str, Any]


def load_stackexchange_fixture(path: Path | None = None, limit: int | None = None) -> list[ThreadContentFixture]:
    fixture_path = path or DEFAULT_FIXTURE_PATH
    if not fixture_path.exists():
        logger.warning("Stack Exchange fixture is missing: %s", fixture_path)
        return []
    rows: list[ThreadContentFixture] = []
    with fixture_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                ThreadContentFixture(
                    title=str(raw.get("title", "")).strip(),
                    tags=[str(tag) for tag in raw.get("tags", [])],
                    topic=str(raw.get("topic", "mixed") or "mixed"),
                    content=str(raw.get("content", "") or ""),
                    source_url=str(raw.get("source_url", "") or ""),
                    source=str(raw.get("source", "Stack Exchange Data Dump") or "Stack Exchange Data Dump"),
                    license=str(raw.get("license", "CC BY-SA 4.0") or "CC BY-SA 4.0"),
                    attribution=str(raw.get("attribution", "") or ""),
                    question_id=str(raw.get("question_id", "") or ""),
                    owner_source_id=str(raw.get("owner_source_id", "") or ""),
                    created_at=str(raw.get("created_at", "") or ""),
                    updated_at=str(raw.get("updated_at", "") or ""),
                    score=int(raw.get("score", 0) or 0),
                    posts=list(raw.get("posts", []) or []),
                    comments=list(raw.get("comments", []) or []),
                )
            )
            if limit is not None and len(rows) >= limit:
                break
    return [row for row in rows if row.title]


def import_stackexchange_posts_xml(
    posts_xml: Path,
    output_jsonl: Path,
    limit: int = 1000,
    topic_tags: dict[str, set[str]] | None = None,
    comments_xml: Path | None = None,
    answers_per_thread: int = 5,
    comments_per_post: int = 5,
) -> int:
    """Build a compact real-content fixture from Stack Exchange Data Dump XML files."""
    import html
    import xml.etree.ElementTree as ET

    topic_tags = topic_tags or {
        "backend": {"go", "postgresql", "database", "sql", "backend"},
        "frontend": {"reactjs", "react", "next.js", "typescript", "javascript", "frontend"},
        "devops": {"docker", "linux", "docker-compose", "nginx", "kubernetes", "devops"},
        "mixed": {"api", "authentication", "architecture", "microservices"},
        "noise": {"developer-tools", "career", "editor"},
    }
    questions: dict[str, dict[str, Any]] = {}
    for _event, elem in ET.iterparse(posts_xml, events=("end",)):
        if elem.tag != "row" or elem.attrib.get("PostTypeId") != "1":
            elem.clear()
            continue
        title = html.unescape(elem.attrib.get("Title", "")).strip()
        tags = _parse_stackexchange_tags(elem.attrib.get("Tags", ""))
        topic = topic_for_tags(tags, topic_tags)
        body = _html_to_text(elem.attrib.get("Body", ""))
        if not title or not body or topic == "noise":
            elem.clear()
            continue
        question_id = elem.attrib.get("Id", "")
        questions[question_id] = {
            "source": "Stack Exchange Data Dump",
            "source_url": f"https://stackoverflow.com/questions/{question_id}" if question_id else "",
            "license": "CC BY-SA 4.0",
            "attribution": f"Stack Overflow question {question_id}",
            "question_id": question_id,
            "owner_source_id": elem.attrib.get("OwnerUserId", ""),
            "topic": topic,
            "title": title,
            "tags": tags,
            "score": _safe_int(elem.attrib.get("Score")),
            "created_at": elem.attrib.get("CreationDate", ""),
            "updated_at": elem.attrib.get("LastActivityDate") or elem.attrib.get("LastEditDate") or elem.attrib.get("CreationDate", ""),
            "content": body,
            "posts": [
                _stackexchange_post_payload(
                    elem.attrib,
                    role="question",
                    thread_question_id=question_id,
                    source_url=f"https://stackoverflow.com/questions/{question_id}" if question_id else "",
                )
            ],
            "comments": [],
        }
        elem.clear()
        if len(questions) >= limit:
            break

    if not questions:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        output_jsonl.write_text("", encoding="utf-8")
        return 0

    question_ids = set(questions)
    answer_counts = {question_id: 0 for question_id in question_ids}
    post_to_question = {question_id: question_id for question_id in question_ids}
    for _event, elem in ET.iterparse(posts_xml, events=("end",)):
        if elem.tag != "row" or elem.attrib.get("PostTypeId") != "2":
            elem.clear()
            continue
        parent_id = elem.attrib.get("ParentId", "")
        if parent_id not in questions or answer_counts[parent_id] >= answers_per_thread:
            elem.clear()
            continue
        body = _html_to_text(elem.attrib.get("Body", ""))
        if not body:
            elem.clear()
            continue
        answer_id = elem.attrib.get("Id", "")
        questions[parent_id]["posts"].append(
            _stackexchange_post_payload(
                elem.attrib,
                role="answer",
                thread_question_id=parent_id,
                source_url=f"https://stackoverflow.com/a/{answer_id}" if answer_id else questions[parent_id]["source_url"],
            )
        )
        answer_counts[parent_id] += 1
        post_to_question[answer_id] = parent_id
        elem.clear()

    if comments_xml is not None and comments_xml.exists():
        comment_counts: dict[str, int] = {}
        for _event, elem in ET.iterparse(comments_xml, events=("end",)):
            if elem.tag != "row":
                elem.clear()
                continue
            post_id = elem.attrib.get("PostId", "")
            question_id = post_to_question.get(post_id)
            if question_id is None:
                elem.clear()
                continue
            if comment_counts.get(post_id, 0) >= comments_per_post:
                elem.clear()
                continue
            text = _html_to_text(elem.attrib.get("Text", ""))
            if not text:
                elem.clear()
                continue
            questions[question_id]["comments"].append(
                {
                    "source_comment_id": elem.attrib.get("Id", ""),
                    "source_post_id": post_id,
                    "owner_source_id": elem.attrib.get("UserId", ""),
                    "content": text,
                    "score": _safe_int(elem.attrib.get("Score")),
                    "created_at": elem.attrib.get("CreationDate", ""),
                    "source_url": questions[question_id]["source_url"],
                    "license": "CC BY-SA 4.0",
                    "attribution": f"Stack Overflow comment {elem.attrib.get('Id', '')}",
                }
            )
            comment_counts[post_id] = comment_counts.get(post_id, 0) + 1
            elem.clear()

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as out:
        for row in questions.values():
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(questions)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "li", "pre", "code"}:
            self.parts.append(" ")

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _html_to_text(value: str) -> str:
    import html

    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    return parser.text()


def _parse_stackexchange_tags(value: str) -> list[str]:
    return [tag for tag in value.replace("><", "|").strip("<>").split("|") if tag]


def _stackexchange_post_payload(
    attrs: dict[str, str],
    role: str,
    thread_question_id: str,
    source_url: str,
) -> dict[str, Any]:
    post_id = attrs.get("Id", "")
    return {
        "source_post_id": post_id,
        "source_parent_id": attrs.get("ParentId", thread_question_id),
        "role": role,
        "owner_source_id": attrs.get("OwnerUserId", ""),
        "content": _html_to_text(attrs.get("Body", "")),
        "score": _safe_int(attrs.get("Score")),
        "created_at": attrs.get("CreationDate", ""),
        "updated_at": attrs.get("LastActivityDate") or attrs.get("LastEditDate") or attrs.get("CreationDate", ""),
        "source_url": source_url,
        "license": "CC BY-SA 4.0",
        "attribution": f"Stack Overflow {role} {post_id}",
    }


def _safe_int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def topic_for_tags(tags: list[str], topic_tags: dict[str, set[str]] | None = None) -> str:
    topic_tags = topic_tags or {
        "backend": {"go", "postgresql", "database", "sql", "backend"},
        "frontend": {"reactjs", "react", "next.js", "typescript", "javascript", "frontend"},
        "devops": {"docker", "linux", "docker-compose", "nginx", "kubernetes", "devops"},
        "mixed": {"api", "authentication", "architecture", "microservices"},
        "noise": {"developer-tools", "career", "editor"},
    }
    normalized = {tag.lower() for tag in tags}
    scores = {topic: len(normalized & values) for topic, values in topic_tags.items()}
    return max(scores, key=lambda topic: (scores[topic], topic != "noise")) if any(scores.values()) else "mixed"


def thread_documents(threads: pl.DataFrame) -> tuple[list[str], list[str], dict[str, str]]:
    if threads.is_empty():
        return [], [], {}
    thread_ids: list[str] = []
    documents: list[str] = []
    hashes: dict[str, str] = {}
    for row in threads.iter_rows(named=True):
        thread_id = str(row["thread_id"])
        categories = " ".join(str(value) for value in (row.get("categories") or []))
        content = str(row.get("content") or "")
        document = f"{row.get('title', '')}\n{categories}\n{content}".strip()
        digest = sha256(document.encode("utf-8")).hexdigest()
        thread_ids.append(thread_id)
        documents.append(document)
        hashes[thread_id] = digest
    return thread_ids, documents, hashes


def build_or_load_content_index(
    threads: pl.DataFrame,
    artifacts_dir: Path,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    force_rebuild: bool = False,
) -> ContentIndex:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / CONTENT_INDEX_FILENAME
    thread_ids, documents, hashes = thread_documents(threads)
    if not force_rebuild and path.exists():
        loaded = joblib.load(path)
        if loaded.get("content_hashes") == hashes:
            return ContentIndex(**loaded)

    started = perf_counter()
    embeddings, backend = encode_documents(documents, model_name=model_name)
    embeddings = _normalize_rows(embeddings.astype(np.float32, copy=False))
    search_backend = "faiss" if _faiss_available() else "numpy"
    index = ContentIndex(
        thread_ids=thread_ids,
        content_hashes=hashes,
        embeddings=embeddings,
        backend=backend,
        search_backend=search_backend,
        model_name=model_name,
        build_seconds=perf_counter() - started,
        metadata={
            "threads": len(thread_ids),
            "embedding_dimension": int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.size else 0,
            "memory_bytes": int(embeddings.nbytes),
        },
    )
    joblib.dump(index.__dict__, path)
    return index


def load_content_index(artifacts_dir: Path) -> ContentIndex | None:
    path = artifacts_dir / CONTENT_INDEX_FILENAME
    if not path.exists():
        return None
    return ContentIndex(**joblib.load(path))


def encode_documents(documents: list[str], model_name: str) -> tuple[np.ndarray, str]:
    if not documents:
        return np.zeros((0, 0), dtype=np.float32), "empty"
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        return np.asarray(
            model.encode(documents, batch_size=64, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        ), "sentence_transformers"
    except Exception as exc:
        logger.info("Using sklearn hashing content embeddings because sentence-transformers is unavailable: %s", exc)

    from sklearn.feature_extraction.text import HashingVectorizer

    vectorizer = HashingVectorizer(n_features=384, alternate_sign=False, norm="l2")
    return vectorizer.transform(documents).astype(np.float32).toarray(), "sklearn_hashing"


def content_recommendations_for_user(
    user_id: str,
    interactions: pl.DataFrame,
    index: ContentIndex,
    limit: int,
    exclude: set[str] | None = None,
) -> list[tuple[str, float]]:
    exclude = exclude or set()
    if interactions.is_empty() or index.embeddings.size == 0:
        return []
    user_rows = interactions.filter(pl.col("user_id") == user_id)
    if user_rows.is_empty():
        return []
    vectors: list[np.ndarray] = []
    weights: list[float] = []
    position_by_thread = {thread_id: idx for idx, thread_id in enumerate(index.thread_ids)}
    for row in user_rows.sort("score", descending=True).head(25).iter_rows(named=True):
        position = position_by_thread.get(row["thread_id"])
        if position is None:
            continue
        vectors.append(index.embeddings[position])
        weights.append(max(float(row["score"]), 0.01))
    if not vectors:
        return []
    profile = np.average(np.vstack(vectors), axis=0, weights=np.asarray(weights, dtype=np.float32))
    profile = _normalize_rows(profile.reshape(1, -1))[0]
    return _search(index, profile, limit=limit, exclude=exclude)


def performance_guardrails(index: ContentIndex, generation_seconds: float, max_generation_seconds: float = 120.0) -> dict[str, Any]:
    failures: list[str] = []
    if generation_seconds > max_generation_seconds:
        failures.append("generation_time_exceeded")
    memory_mb = index.metadata.get("memory_bytes", 0) / 1024 / 1024
    return {
        "passed": not failures,
        "failures": failures,
        "embedding_backend": index.backend,
        "search_backend": index.search_backend,
        "embedding_dimension": index.metadata.get("embedding_dimension", 0),
        "index_memory_mb": round(memory_mb, 3),
        "content_index_build_seconds": index.build_seconds,
        "generation_seconds": generation_seconds,
    }


def _search(index: ContentIndex, vector: np.ndarray, limit: int, exclude: set[str]) -> list[tuple[str, float]]:
    if index.embeddings.size == 0:
        return []
    candidate_count = min(len(index.thread_ids), max(limit + len(exclude), limit * 3, 1))
    if _faiss_available():
        import faiss

        faiss_index = faiss.IndexFlatIP(index.embeddings.shape[1])
        faiss_index.add(index.embeddings)
        scores, positions = faiss_index.search(vector.reshape(1, -1).astype(np.float32), candidate_count)
        pairs = zip(positions[0].tolist(), scores[0].tolist(), strict=False)
    else:
        scores = index.embeddings @ vector
        positions = np.argpartition(-scores, range(candidate_count))[:candidate_count]
        ordered = positions[np.argsort(-scores[positions])]
        pairs = ((int(position), float(scores[position])) for position in ordered)
    output: list[tuple[str, float]] = []
    for position, score in pairs:
        if position < 0:
            continue
        thread_id = index.thread_ids[int(position)]
        if thread_id in exclude:
            continue
        output.append((thread_id, float(score)))
        if len(output) >= limit:
            break
    return output


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return values / norms


def _faiss_available() -> bool:
    try:
        import faiss  # noqa: F401
    except Exception:
        return False
    return True
