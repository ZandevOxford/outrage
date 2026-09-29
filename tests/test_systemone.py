"""The System One client, against a transport that answers as the service does.

The request and response bodies here are the shapes TypeSafe's API reference
documents, so a test failing here means the client stopped speaking the
protocol, not that a fake drifted from it.
"""

from __future__ import annotations

import json
import os

import httpx2
import pytest

from outrage import messages
from outrage.errors import OutrageError
from outrage.smartsearch import JudgeError, Question, StateTooLarge
from outrage.systemone import (
    BASE_URL_VARIABLE,
    KEY_VARIABLE,
    MODEL_VARIABLE,
    RetryPolicy,
    Settings,
    SystemOne,
)

NOUL = Question("noul", "Is it relevant?")
SCORE = Question("score", "How relevant?", criteria=("none", "some", "much"))


def _client(handler, *, key="k", retry=None):
    sleeps: list[float] = []
    client = SystemOne(
        Settings(key=key),
        retry=retry or RetryPolicy(backoff_jitter=0.0),
        transport=httpx2.MockTransport(handler),
        sleep=sleeps.append,
    )
    return client, sleeps


def _ok(answers, input_tokens=10):
    return httpx2.Response(
        200,
        json={
            "model": "jev-1.13.0",
            "answers": answers,
            "usage": {"input_tokens": input_tokens, "output_tokens": 5},
        },
    )


def test_a_request_is_the_documented_body():
    sent = []

    def handler(request):
        sent.append((request, json.loads(request.content)))
        return _ok({"a": {"type": "noul", "noul": 0.9}})

    client, _ = _client(handler)
    question = Question("noul", "Is `title` relevant?", instructions={"key": "k", "title": "T"})
    client.judge("the query", {"a": question, "b": SCORE})

    [(request, body)] = sent
    assert request.url == "https://api.typesafe.ai/v1/systemone"
    assert request.headers["authorization"] == "Bearer k"
    assert body == {
        "model": "jev-latest",
        "state": "the query",
        "questions": {
            "a": {
                "type": "noul",
                "instructions": {"question": "Is `title` relevant?", "key": "k", "title": "T"},
            },
            "b": {
                "type": "score",
                "instructions": "How relevant?",
                "criteria": list(SCORE.criteria),
            },
        },
    }


def test_answers_are_read_in_both_types():
    def handler(request):
        return _ok(
            {
                "n": {"type": "noul", "noul": 0.25},
                "s": {
                    "type": "score",
                    "score": 1.05,
                    "legend": {"0": "none", "1": "some", "2": "much"},
                    "probabilities": {"0": 0.0, "1": 0.95, "2": 0.05},
                    "confidence": 0.92,
                },
            },
            input_tokens=304,
        )

    client, _ = _client(handler)
    judgement = client.judge("s", {"n": NOUL, "s": SCORE})

    assert judgement.answers["n"].probability == 0.25
    score = judgement.answers["s"]
    assert (score.score, score.probabilities, score.confidence) == (1.05, (0.0, 0.95, 0.05), 0.92)
    assert score.as_probability() == pytest.approx(0.525)
    assert judgement.input_tokens == 304


def test_no_key_sends_no_authorisation():
    seen = []

    def handler(request):
        seen.append(request.headers.get("authorization"))
        return _ok({})

    client, _ = _client(handler, key=None)
    client.judge("s", {})
    assert seen == [None]


def test_a_busy_service_is_retried_with_backoff():
    statuses = iter([529, 429, 200])

    def handler(request):
        status = next(statuses)
        return (
            _ok({"q": {"type": "noul", "noul": 1.0}}) if status == 200 else httpx2.Response(status)
        )

    client, sleeps = _client(handler)
    assert client.judge("s", {"q": NOUL}).answers["q"].probability == 1.0
    assert sleeps == [0.5, 1.0]


def test_retry_after_is_honoured():
    statuses = iter([429, 200])

    def handler(request):
        if next(statuses) == 429:
            return httpx2.Response(429, headers={"Retry-After": "2"})
        return _ok({})

    client, sleeps = _client(handler)
    client.judge("s", {})
    assert sleeps == [2.0]


def test_retries_run_out():
    client, sleeps = _client(lambda request: httpx2.Response(503, text="down for maintenance"))

    with pytest.raises(JudgeError) as raised:
        client.judge("s", {"q": NOUL})
    assert raised.value.code == "smart-search-service-failed"
    assert raised.value.details["detail"] == "down for maintenance"
    assert len(sleeps) == 2
    assert "HTTP 503" in messages.render(raised.value)


def test_an_unreachable_service_is_retried_then_reported():
    def handler(request):
        raise httpx2.ConnectError("refused", request=request)

    client, sleeps = _client(handler)
    with pytest.raises(JudgeError) as raised:
        client.judge("s", {})
    assert raised.value.code == "smart-search-unreachable"
    assert len(sleeps) == 2


@pytest.mark.parametrize(
    ("status", "text", "error", "code"),
    [
        (401, "", JudgeError, "smart-search-unauthorised"),
        (422, "state exceeds 32768 tokens", StateTooLarge, "smart-search-state-too-large"),
        (422, "questions.q.type: invalid", JudgeError, "smart-search-request-rejected"),
        (400, "bad", JudgeError, "smart-search-service-failed"),
    ],
)
def test_a_refusal_is_final(status, text, error, code):
    client, sleeps = _client(lambda request: httpx2.Response(status, text=text))
    with pytest.raises(error) as raised:
        client.judge("s", {"q": NOUL})
    assert raised.value.code == code
    assert sleeps == []
    assert messages.render(raised.value)


def test_a_response_in_the_wrong_shape_is_reported():
    client, _ = _client(lambda request: _ok({"q": {"type": "noul"}}))
    with pytest.raises(JudgeError) as raised:
        client.judge("s", {"q": NOUL})
    assert raised.value.code == "smart-search-response-malformed"


def _config(tmp_path, text, mode=0o600):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


def _read(tmp_path, environ=None, text=None):
    path = _config(tmp_path, text) if text is not None else tmp_path / "config.toml"
    return Settings.read(environ or {}, path)


def test_with_nothing_configured_the_defaults_are_unconfigured(tmp_path):
    settings, found = _read(tmp_path)
    assert found == []
    assert settings == Settings()
    assert settings.url == "https://api.typesafe.ai/v1/systemone"
    assert settings.configured is False


def test_settings_come_from_the_file(tmp_path):
    settings, found = _read(
        tmp_path,
        text='[smart_search]\nkey = "secret"\nbase_url = "http://localhost:8000/"\n'
        'model = "jev-1"\n',
    )
    assert found == []
    assert settings.key == "secret"
    assert settings.key_source == str(tmp_path / "config.toml")
    assert settings.url == "http://localhost:8000/v1/systemone"
    assert settings.model == "jev-1"


def test_the_environment_wins_over_the_file_setting_by_setting(tmp_path):
    settings, found = _read(
        tmp_path,
        {KEY_VARIABLE: "from-env", MODEL_VARIABLE: "jev-2", BASE_URL_VARIABLE: ""},
        '[smart_search]\nkey = "from-file"\nbase_url = "https://gateway.example/typesafe"\n'
        'model = "jev-1"\n',
    )
    assert found == []
    assert (settings.key, settings.key_source) == ("from-env", KEY_VARIABLE)
    assert settings.model == "jev-2"
    # An empty variable is unset, so the file's base URL stands.
    assert settings.url == "https://gateway.example/typesafe/v1/systemone"


def test_the_base_url_is_the_root_as_the_sdk_means_it(tmp_path):
    settings, _ = _read(tmp_path, {BASE_URL_VARIABLE: "https://openrouter.ai/api"})
    assert settings.url == "https://openrouter.ai/api/v1/systemone"
    assert settings.configured, "a server of its own may want no key"


def test_the_key_is_kept_out_of_the_repr():
    assert "secret" not in repr(Settings(key="secret"))


def test_every_problem_with_the_file_is_reported_at_once(tmp_path):
    settings, found = _read(
        tmp_path,
        {BASE_URL_VARIABLE: "api.typesafe.ai"},
        '[smart_search]\nkey = ""\nmodel = 3\nurl = "x"\nmodle = "y"\n',
    )
    assert [refusal.code for refusal in found] == [
        "smart-search-config-name-unknown",
        "smart-search-config-name-unknown",
        "smart-search-config-value",
        "smart-search-config-value",
        "smart-search-base-url",
    ]
    assert [refusal.details.get("name") for refusal in found[:4]] == [
        "modle",
        "url",
        "key",
        "model",
    ]
    for refusal in found:
        assert messages.render(refusal.as_error())
    assert settings == Settings()


def test_a_table_that_is_not_a_table_is_refused(tmp_path):
    _, found = _read(tmp_path, text='smart_search = "on"\n')
    assert [refusal.code for refusal in found] == ["smart-search-config-not-a-table"]


def test_other_tables_in_the_file_are_left_to_their_own_readers(tmp_path):
    _, found = _read(tmp_path, text="[something_else]\nanything = 1\n")
    assert found == []


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX")
def test_an_exposed_file_refuses_even_when_the_environment_has_the_key(tmp_path):
    path = _config(tmp_path, '[smart_search]\nkey = "secret"\n')
    path.chmod(0o644)
    settings, found = Settings.read({KEY_VARIABLE: "from-env"}, path)
    assert [refusal.code for refusal in found] == ["user-config-exposed"]
    assert settings.key == "from-env"
    with pytest.raises(OutrageError) as raised:
        Settings.load({KEY_VARIABLE: "from-env"}, path)
    assert raised.value.code == "user-config-exposed"


def test_load_gives_the_settings_when_nothing_is_refused(tmp_path):
    settings = Settings.load({KEY_VARIABLE: "k"}, tmp_path / "config.toml")
    assert settings.key == "k"


@pytest.mark.parametrize(
    ("source", "expected"),
    [(KEY_VARIABLE, "check the key from TYPESAFE_API_KEY"), (None, "none is configured")],
)
def test_a_refused_key_names_where_it_came_from(source, expected):
    client = SystemOne(
        Settings(key="k" if source else None, key_source=source),
        transport=httpx2.MockTransport(lambda request: httpx2.Response(401)),
        sleep=lambda _: None,
    )
    with pytest.raises(JudgeError) as raised:
        client.judge("s", {"q": NOUL})
    assert expected in messages.render(raised.value)
