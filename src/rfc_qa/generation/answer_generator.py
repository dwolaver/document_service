"""Ask the local model to answer a question from retrieved RFC passages, and check its citations.

Passages are labeled ``P1``, ``P2`` and so on in the prompt, and cited labels are mapped back to
chunks here. A citation check proves that a cited passage was retrieved. It can't prove that the
passage supports the answer, which the golden question set measures separately.
"""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import requests

from rfc_qa.chunk import Chunk
from rfc_qa.errors import ModelResponseError, ModelUnavailableError

logger = logging.getLogger(__name__)

NOT_FOUND_ANSWER = "The indexed RFCs don't answer this question."

SYSTEM_PROMPT = """You answer questions about IETF RFCs using only the passages provided.
Rules:
- Use only facts stated in the passages. Do not use outside knowledge.
- If the passages do not answer the question, set found to false, and leave answer and citations empty.
- Otherwise set found to true, answer briefly, and list the label of every passage you used in \
citations, such as "P1"."""

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["found", "answer", "citations"],
}

_NANOSECONDS_PER_MS = 1_000_000


@dataclass(frozen=True)
class ModelSettings:
    model: str
    base_url: str
    num_ctx: int
    max_answer_tokens: int
    timeout_seconds: float


@dataclass(frozen=True)
class GenerationResult:
    """The checked outcome of one model call. ``cited`` holds the retrieved chunks that were cited."""

    found: bool
    answer: str | None
    cited: list[Chunk] = field(default_factory=list)
    model_load_ms: int | None = None
    generation_ms: int | None = None
    prompt_tokens: int | None = None
    answer_tokens: int | None = None


def _label(position: int) -> str:
    return f"P{position + 1}"


def build_messages(question: str, chunks: Sequence[Chunk]) -> list[dict[str, str]]:
    """Return the chat messages for ``question``, with ``chunks`` labeled in retrieval order."""
    passages = "\n\n".join(
        f"Passage {_label(position)} (RFC {chunk.rfc_number} section {chunk.section_number}: "
        f"{chunk.section_title})\n{chunk.text}"
        for position, chunk in enumerate(chunks)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Passages:\n\n{passages}\n\nQuestion: {question}"},
    ]


def _request_body(question: str, chunks: Sequence[Chunk], settings: ModelSettings) -> dict[str, Any]:
    return {
        "model": settings.model,
        "messages": build_messages(question, chunks),
        "format": _ANSWER_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": settings.num_ctx,
            "num_predict": settings.max_answer_tokens,
        },
    }


def _post_chat(url: str, body: dict[str, Any], timeout: float) -> requests.Response:
    """Send one chat request to Ollama. This is the only network call, so tests replace it."""
    return requests.post(url, json=body, timeout=timeout)


def _ollama_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text
    error = body.get("error", "") if isinstance(body, dict) else ""
    return error if isinstance(error, str) else str(error)


def _call_model(question: str, chunks: Sequence[Chunk], settings: ModelSettings) -> dict[str, Any]:
    url = settings.base_url.rstrip("/") + "/api/chat"
    logger.debug("Asking model %r at %s with %d passages", settings.model, url, len(chunks))
    try:
        response = _post_chat(url, _request_body(question, chunks, settings), settings.timeout_seconds)
    except requests.Timeout as exc:
        raise ModelUnavailableError(
            f"Ollama didn't respond within {settings.timeout_seconds} seconds."
        ) from exc
    except requests.RequestException as exc:
        raise ModelUnavailableError(
            f"Can't reach Ollama at {settings.base_url}. Start Ollama, for example with `ollama serve`."
        ) from exc

    if response.status_code == 404 and "not found" in _ollama_error(response):
        raise ModelUnavailableError(
            f"Model {settings.model!r} isn't installed in Ollama. Run `ollama pull {settings.model}`."
        )
    if response.status_code != 200:
        raise ModelUnavailableError(f"Ollama returned HTTP {response.status_code}: {_ollama_error(response)}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ModelResponseError("Ollama returned a response that isn't JSON.") from exc
    if not isinstance(payload, dict):
        raise ModelResponseError("Ollama returned a response that isn't a JSON object.")
    return payload


def _parse_answer(payload: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """Return (found, answer, labels) from the model's structured output, or raise."""
    message = payload.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ModelResponseError("The model's output isn't valid JSON.")
    try:
        output = json.loads(content)
    except ValueError as exc:
        raise ModelResponseError("The model's output isn't valid JSON.") from exc
    found, answer, labels = (
        (output.get("found"), output.get("answer"), output.get("citations"))
        if isinstance(output, dict)
        else (None, None, None)
    )
    if (
        not isinstance(found, bool)
        or not isinstance(answer, str)
        or not isinstance(labels, list)
        or not all(isinstance(label, str) for label in labels)
    ):
        raise ModelResponseError("The model's output doesn't have the expected fields.")
    return found, answer, labels


def _cited_chunks(labels: list[str], chunks: Sequence[Chunk]) -> list[Chunk]:
    """Map cited labels to retrieved chunks, dropping unknown labels and repeats."""
    by_label = {_label(position): chunk for position, chunk in enumerate(chunks)}
    cited: list[Chunk] = []
    for label in labels:
        chunk = by_label.get(label.strip())
        if chunk is not None and chunk not in cited:
            cited.append(chunk)
    return cited


def _int_or_none(value: object) -> int | None:
    """Return ``value`` if it's an integer, otherwise ``None``. Ollama's counts are optional."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _to_ms(nanoseconds: int | None) -> int | None:
    return None if nanoseconds is None else round(nanoseconds / _NANOSECONDS_PER_MS)


def generate_answer(question: str, chunks: Sequence[Chunk], settings: ModelSettings) -> GenerationResult:
    """Answer ``question`` from ``chunks`` and return a :class:`GenerationResult`.

    Raises :class:`ModelUnavailableError` or :class:`ModelResponseError` when no usable answer comes
    back. An answer with no valid citations is returned as not found, without its text.
    """
    payload = _call_model(question, chunks, settings)
    prompt_tokens = payload.get("prompt_eval_count")
    if isinstance(prompt_tokens, int) and prompt_tokens >= settings.num_ctx:
        raise ModelResponseError(
            f"The prompt used {prompt_tokens} tokens, reaching the {settings.num_ctx}-token context window, "
            "so it may have been cut short."
        )
    found, answer, labels = _parse_answer(payload)
    cited = _cited_chunks(labels, chunks) if found else []
    is_answered = found and bool(cited) and bool(answer.strip())

    generation_ns = [payload.get("prompt_eval_duration"), payload.get("eval_duration")]
    result = GenerationResult(
        found=is_answered,
        answer=answer.strip() if is_answered else None,
        cited=cited if is_answered else [],
        model_load_ms=_to_ms(_int_or_none(payload.get("load_duration"))),
        generation_ms=_to_ms(sum(ns for ns in generation_ns if isinstance(ns, int)))
        if any(isinstance(ns, int) for ns in generation_ns)
        else None,
        prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
        answer_tokens=payload.get("eval_count") if isinstance(payload.get("eval_count"), int) else None,
    )
    logger.debug(
        "Model reported %s prompt tokens and %s answer tokens, loaded in %s ms, generated in %s ms",
        result.prompt_tokens,
        result.answer_tokens,
        result.model_load_ms,
        result.generation_ms,
    )
    return result
