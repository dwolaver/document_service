"""Ask the local model to answer a question from retrieved RFC passages, and check its citations.

Passages are labeled ``P1``, ``P2`` and so on in the prompt, and cited labels are mapped back to
chunks here. A citation check proves that a cited passage was retrieved. It can't prove that the
passage supports the answer, which the golden question set measures separately.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

import requests

NOT_FOUND_ANSWER = "The indexed RFCs don't answer this question."

SYSTEM_PROMPT = """You answer questions about IETF RFCs using only the passages provided.
Rules:
- Use only facts stated in the passages. Do not use outside knowledge.
- If the passages do not answer the question, set found to false, and leave answer and citations empty.
- Otherwise set found to true, answer briefly, and list the label of every passage you used in citations, such as "P1"."""

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


class ModelUnavailableError(Exception):
    """The model service couldn't produce a response, with a message saying how to fix it."""


class ModelResponseError(Exception):
    """The model service responded, but its output can't be used."""


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
    answer: Optional[str]
    cited: List = field(default_factory=list)
    model_load_ms: Optional[int] = None
    generation_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    answer_tokens: Optional[int] = None


def _label(position):
    return "P{n}".format(n=position + 1)


def build_messages(question, chunks):
    """Return the chat messages for ``question``, with ``chunks`` labeled in retrieval order."""
    passages = "\n\n".join(
        "Passage {label} (RFC {rfc} section {section}: {title})\n{text}".format(
            label=_label(position),
            rfc=chunk.rfc_number,
            section=chunk.section_number,
            title=chunk.section_title,
            text=chunk.text,
        )
        for position, chunk in enumerate(chunks)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Passages:\n\n{p}\n\nQuestion: {q}".format(p=passages, q=question)},
    ]


def _request_body(question, chunks, settings):
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


def _post_chat(url, body, timeout):
    """Send one chat request to Ollama. This is the only network call, so tests replace it."""
    return requests.post(url, json=body, timeout=timeout)


def _ollama_error(response):
    try:
        return response.json().get("error", "")
    except ValueError:
        return response.text


def _call_model(question, chunks, settings):
    url = settings.base_url.rstrip("/") + "/api/chat"
    try:
        response = _post_chat(url, _request_body(question, chunks, settings), settings.timeout_seconds)
    except requests.Timeout as exc:
        raise ModelUnavailableError(
            "Ollama didn't respond within {t} seconds.".format(t=settings.timeout_seconds)
        ) from exc
    except requests.RequestException as exc:
        raise ModelUnavailableError(
            "Can't reach Ollama at {u}. Start Ollama, for example with `ollama serve`.".format(
                u=settings.base_url
            )
        ) from exc

    if response.status_code == 404 and "not found" in _ollama_error(response):
        raise ModelUnavailableError(
            "Model {m!r} isn't installed in Ollama. Run `ollama pull {m}`.".format(m=settings.model)
        )
    if response.status_code != 200:
        raise ModelUnavailableError(
            "Ollama returned HTTP {s}: {e}".format(s=response.status_code, e=_ollama_error(response))
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ModelResponseError("Ollama returned a response that isn't JSON.") from exc


def _parse_answer(payload):
    """Return (found, answer, labels) from the model's structured output, or raise."""
    message = payload.get("message") if isinstance(payload, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    try:
        output = json.loads(content)
    except (TypeError, ValueError) as exc:
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


def _cited_chunks(labels, chunks):
    """Map cited labels to retrieved chunks, dropping unknown labels and repeats."""
    by_label = {_label(position): chunk for position, chunk in enumerate(chunks)}
    cited = []
    for label in labels:
        chunk = by_label.get(label.strip())
        if chunk is not None and chunk not in cited:
            cited.append(chunk)
    return cited


def _to_ms(nanoseconds):
    return None if nanoseconds is None else int(round(nanoseconds / _NANOSECONDS_PER_MS))


def generate_answer(question, chunks, settings):
    """Answer ``question`` from ``chunks`` and return a :class:`GenerationResult`.

    Raises :class:`ModelUnavailableError` or :class:`ModelResponseError` when no usable answer comes
    back. An answer with no valid citations is returned as not found, without its text.
    """
    payload = _call_model(question, chunks, settings)
    prompt_tokens = payload.get("prompt_eval_count")
    if isinstance(prompt_tokens, int) and prompt_tokens >= settings.num_ctx:
        raise ModelResponseError(
            "The prompt used {p} tokens, reaching the {n}-token context window, so it may have been "
            "cut short.".format(p=prompt_tokens, n=settings.num_ctx)
        )
    found, answer, labels = _parse_answer(payload)
    cited = _cited_chunks(labels, chunks) if found else []
    is_answered = found and bool(cited) and bool(answer.strip())

    generation_ns = [payload.get("prompt_eval_duration"), payload.get("eval_duration")]
    return GenerationResult(
        found=is_answered,
        answer=answer.strip() if is_answered else None,
        cited=cited if is_answered else [],
        model_load_ms=_to_ms(payload.get("load_duration")),
        generation_ms=_to_ms(sum(ns for ns in generation_ns if isinstance(ns, int)))
        if any(isinstance(ns, int) for ns in generation_ns)
        else None,
        prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
        answer_tokens=payload.get("eval_count") if isinstance(payload.get("eval_count"), int) else None,
    )
