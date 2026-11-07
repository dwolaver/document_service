import json

import pytest
import requests

import answer_generator
from answer_generator import (
    NOT_FOUND_ANSWER,
    ModelResponseError,
    ModelSettings,
    ModelUnavailableError,
    build_messages,
    generate_answer,
)
from chunker import Chunk

SETTINGS = ModelSettings("llama3.2", "http://localhost:11434", 8192, 512, 120)
CHUNKS = [
    Chunk("rfc9110-s15.5.5-p0", 9110, "HTTP Semantics", "http", "15.5.5", "404 Not Found", "Not found text."),
    Chunk("rfc7231-s6.5.4-p0", 7231, "HTTP/1.1 Semantics", "http", "6.5.4", "404 Not Found", "Older text."),
    Chunk("rfc2616-s10.4.5-p0", 2616, "HTTP/1.1", "http", "10.4.5", "404 Not Found", "Oldest text."),
]


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload


def _ollama(output, **extra):
    payload = {
        "message": {"role": "assistant", "content": output if isinstance(output, str) else json.dumps(output)},
        "load_duration": 2_000_000,
        "prompt_eval_duration": 6_000_000,
        "eval_duration": 42_000_000,
        "prompt_eval_count": 1200,
        "eval_count": 49,
    }
    payload.update(extra)
    return payload


@pytest.fixture
def model(monkeypatch):
    """Replace the network call, recording each request and returning ``model.response``."""

    class Model:
        requests = []
        response = FakeResponse(200, _ollama({"found": True, "answer": "Gone.", "citations": ["P1"]}))

    def fake_post(url, body, timeout):
        Model.requests.append({"url": url, "body": body, "timeout": timeout})
        if isinstance(Model.response, Exception):
            raise Model.response
        return Model.response

    Model.requests = []
    monkeypatch.setattr(answer_generator, "_post_chat", fake_post)
    return Model


def _answer_with(model, output, **extra):
    model.response = FakeResponse(200, _ollama(output, **extra))
    return generate_answer("What does 404 mean?", CHUNKS, SETTINGS)


# --- Prompt (task 2.1) ---

def test_messages_label_passages_in_order_then_ask_the_question():
    system, user = build_messages("What does 404 mean?", CHUNKS)
    assert system["role"] == "system" and "only the passages" in system["content"]
    content = user["content"]
    positions = [content.index(label) for label in ("Passage P1", "Passage P2", "Passage P3")]
    assert positions == sorted(positions)
    assert "Passage P1 (RFC 9110 section 15.5.5: 404 Not Found)\nNot found text." in content
    assert content.rstrip().endswith("Question: What does 404 mean?")


def test_messages_do_not_show_chunk_ids():
    assert "rfc9110-s15.5.5-p0" not in build_messages("q", CHUNKS)[1]["content"]


# --- Model call (task 2.2) ---

def test_request_body(model):
    generate_answer("What does 404 mean?", CHUNKS, SETTINGS)
    request = model.requests[0]
    assert request["url"] == "http://localhost:11434/api/chat"
    assert request["timeout"] == 120
    body = request["body"]
    assert body["model"] == "llama3.2"
    assert body["stream"] is False
    assert body["format"]["required"] == ["found", "answer", "citations"]
    assert body["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 512}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_base_url_trailing_slash(model):
    generate_answer("q", CHUNKS, ModelSettings("m", "http://host:1/", 8192, 512, 5))
    assert model.requests[0]["url"] == "http://host:1/api/chat"


def test_connection_error_says_to_start_ollama(model):
    model.response = requests.ConnectionError("refused")
    with pytest.raises(ModelUnavailableError, match="Start Ollama"):
        generate_answer("q", CHUNKS, SETTINGS)


def test_timeout(model):
    model.response = requests.Timeout("slow")
    with pytest.raises(ModelUnavailableError, match="within 120 seconds"):
        generate_answer("q", CHUNKS, SETTINGS)


def test_missing_model_says_to_pull_it(model):
    model.response = FakeResponse(404, {"error": "model 'llama3.2' not found"})
    with pytest.raises(ModelUnavailableError, match=r"ollama pull llama3\.2"):
        generate_answer("q", CHUNKS, SETTINGS)


def test_other_http_error(model):
    model.response = FakeResponse(500, {"error": "out of memory"})
    with pytest.raises(ModelUnavailableError, match="HTTP 500: out of memory"):
        generate_answer("q", CHUNKS, SETTINGS)


def test_only_the_chat_endpoint_is_called(model):
    model.response = FakeResponse(404, {"error": "model 'llama3.2' not found"})
    with pytest.raises(ModelUnavailableError):
        generate_answer("q", CHUNKS, SETTINGS)
    assert [r["url"] for r in model.requests] == ["http://localhost:11434/api/chat"]


def test_module_has_no_way_to_pull_or_start_ollama():
    source = open(answer_generator.__file__, encoding="utf-8").read()
    assert "/api/pull" not in source
    assert "subprocess" not in source


# --- Output and citations (task 2.3) ---

def test_answer_with_valid_citations(model):
    result = _answer_with(model, {"found": True, "answer": " Gone. ", "citations": ["P1", "P3"]})
    assert result.found is True
    assert result.answer == "Gone."
    assert [c.chunk_id for c in result.cited] == ["rfc9110-s15.5.5-p0", "rfc2616-s10.4.5-p0"]


@pytest.mark.parametrize("label", ["P9", "P0", "RFC4271", "rfc9110-s15.5.5-p0", "Passage P1", "p1", ""])
def test_unknown_labels_are_dropped(model, label):
    result = _answer_with(model, {"found": True, "answer": "Gone.", "citations": [label, "P2"]})
    assert [c.chunk_id for c in result.cited] == ["rfc7231-s6.5.4-p0"]


def test_surrounding_whitespace_in_a_label_is_allowed(model):
    result = _answer_with(model, {"found": True, "answer": "Gone.", "citations": [" P2 "]})
    assert [c.chunk_id for c in result.cited] == ["rfc7231-s6.5.4-p0"]


def test_repeated_citation_kept_once_in_first_order(model):
    result = _answer_with(model, {"found": True, "answer": "Gone.", "citations": ["P2", "P1", "P2"]})
    assert [c.chunk_id for c in result.cited] == ["rfc7231-s6.5.4-p0", "rfc9110-s15.5.5-p0"]


def test_no_valid_citations_is_not_found_and_drops_the_answer(model):
    result = _answer_with(model, {"found": True, "answer": "BGP picks paths.", "citations": ["RFC4271"]})
    assert (result.found, result.answer, result.cited) == (False, None, [])


def test_no_citations_at_all_is_not_found(model):
    assert _answer_with(model, {"found": True, "answer": "Gone.", "citations": []}).found is False


def test_model_reports_not_found(model):
    result = _answer_with(model, {"found": False, "answer": "", "citations": []})
    assert (result.found, result.answer, result.cited) == (False, None, [])


def test_not_found_ignores_citations(model):
    assert _answer_with(model, {"found": False, "answer": "x", "citations": ["P1"]}).cited == []


def test_empty_answer_is_not_found(model):
    assert _answer_with(model, {"found": True, "answer": "  ", "citations": ["P1"]}).found is False


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        "[]",
        {"found": "yes", "answer": "a", "citations": []},
        {"found": True, "answer": 3, "citations": []},
        {"found": True, "answer": "a", "citations": "P1"},
        {"found": True, "answer": "a", "citations": [1]},
        {"found": True, "answer": "a"},
    ],
)
def test_invalid_output_is_rejected(model, output):
    with pytest.raises(ModelResponseError):
        _answer_with(model, output)


@pytest.mark.parametrize("payload", [{}, {"message": None}, {"message": {"content": None}}])
def test_missing_message_is_rejected(model, payload):
    model.response = FakeResponse(200, payload)
    with pytest.raises(ModelResponseError):
        generate_answer("q", CHUNKS, SETTINGS)


def test_response_that_is_not_json_is_rejected(model):
    model.response = FakeResponse(200, None, text="<html>")
    with pytest.raises(ModelResponseError, match="isn't JSON"):
        generate_answer("q", CHUNKS, SETTINGS)


@pytest.mark.parametrize("count", [8192, 9000])
def test_prompt_reaching_the_context_window_is_rejected(model, count):
    with pytest.raises(ModelResponseError, match="cut short"):
        _answer_with(model, {"found": True, "answer": "a", "citations": ["P1"]}, prompt_eval_count=count)


def test_prompt_just_under_the_context_window_is_accepted(model):
    assert _answer_with(model, {"found": True, "answer": "a", "citations": ["P1"]}, prompt_eval_count=8191).found


def test_durations_and_counts(model):
    result = _answer_with(model, {"found": True, "answer": "a", "citations": ["P1"]}, load_duration=4_852_400_000)
    assert result.model_load_ms == 4852
    assert result.generation_ms == 48
    assert (result.prompt_tokens, result.answer_tokens) == (1200, 49)


def test_missing_durations_are_none(model):
    model.response = FakeResponse(200, {"message": {"content": json.dumps({"found": False, "answer": "", "citations": []})}})
    result = generate_answer("q", CHUNKS, SETTINGS)
    assert (result.model_load_ms, result.generation_ms, result.prompt_tokens, result.answer_tokens) == (None,) * 4


def test_not_found_answer_text():
    assert NOT_FOUND_ANSWER == "The indexed RFCs don't answer this question."
