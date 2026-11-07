import query
from query import QueryErrorCode, QueryResponse, main
from query import query as run_query


# --- QueryResponse / QueryErrorCode (task 1.1) ---

def test_response_fields_and_defaults():
    resp = QueryResponse(success=True, answer="hi")
    assert resp.success is True
    assert resp.answer == "hi"
    assert resp.error_string is None
    assert resp.error_code is None


def test_error_code_is_integer_enum():
    assert int(QueryErrorCode.INVALID_QUERY) == 1
    assert int(QueryErrorCode.NOT_IMPLEMENTED) == 2


# --- Input validation (task 2.1) ---

def test_invalid_queries_rejected():
    for bad in [None, 123, "", "   ", "\t\n"]:
        resp = run_query(bad)
        assert resp.success is False
        assert resp.error_code is QueryErrorCode.INVALID_QUERY
        assert resp.error_string
        assert resp.answer is None


# --- Stub answer path (task 2.2) ---

def test_valid_query_returns_not_implemented():
    resp = run_query("What is RFC 2616 about?")
    assert resp.success is False
    assert resp.error_code is QueryErrorCode.NOT_IMPLEMENTED
    assert resp.answer is None
    assert "RAG" in resp.error_string


# --- Console entry point (tasks 3.1, 3.2) ---

def test_main_failure_routes_to_stderr_nonzero(capsys):
    code = main(["What is RFC 2616 about?"])
    captured = capsys.readouterr()
    assert code != 0
    assert captured.out == ""
    assert captured.err.strip()


def test_main_invalid_query_argument(capsys):
    code = main([""])
    captured = capsys.readouterr()
    assert code != 0
    assert captured.err.strip()
    assert captured.out == ""


def test_main_success_routes_to_stdout_zero(monkeypatch, capsys):
    monkeypatch.setattr(query, "query", lambda q: QueryResponse(success=True, answer="the answer"))
    code = main(["anything"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "the answer"
    assert captured.err == ""
