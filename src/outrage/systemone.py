"""A judge for :mod:`outrage.smartsearch` that speaks the System One protocol.

Direct HTTP rather than a vendor SDK, deliberately. The protocol is one POST
with a JSON body, and more than one server speaks it: TypeSafe's hosted Jev
and a local ``laya-serve`` differ in their base URL and nothing else, so a
client written against the wire rather than against one vendor's library is
one client for both.

**The three settings are read in one place**, :meth:`Settings.from_environment`,
because they are expected to change shape once a second provider needs
configuring. Until then a key in ``TYPESAFE_API_KEY`` is the whole of it, with
TypeSafe's URL and ``jev-latest`` as defaults.

Retrying follows the policy TypeSafe's own SDK defaults to -- two retries,
backoff from half a second doubling to five with a quarter jitter, over 408,
429 and every 5xx, honouring ``Retry-After`` -- so a failure that reaches the
cascade has already had the chances an SDK user's would.
"""

from __future__ import annotations

import os
import random
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Self

import httpx2

from .smartsearch import Answer, JudgeError, Judgement, Question, StateTooLarge

#: Where TypeSafe's hosted models answer.
DEFAULT_URL = "https://api.typesafe.ai/v1/systemone"

#: TypeSafe's alias for its current flagship model.
DEFAULT_MODEL = "jev-latest"

#: The environment variable holding the API key.
KEY_VARIABLE = "TYPESAFE_API_KEY"

#: Longest stretch of an error response carried into a message. A validation
#: failure names its field in the first line or two, and a proxy's HTML error
#: page is not worth more.
DETAIL_CHARS = 300

#: What a 422 says when the request was too long rather than malformed. The
#: service documents 422 for both and gives no field that tells them apart, so
#: this reads the body; a too-large refusal it misses is reported as rejected,
#: which leaves the document unjudged rather than wrongly judged.
_TOO_LARGE = re.compile(r"token|too (?:long|large)|context|length|exceed", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Settings:
    """Where to send questions, which model answers them, and the key if any."""

    url: str = DEFAULT_URL
    model: str = DEFAULT_MODEL
    key: str | None = None
    """None sends no ``Authorization`` header, which is what a local server
    wants; TypeSafe's refuses the request."""

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> Self:
        """The settings this process is configured with."""
        environ = os.environ if environ is None else environ
        return cls(key=environ.get(KEY_VARIABLE) or None)

    @property
    def configured(self) -> bool:
        """Whether a search can be sent anywhere with these settings.

        A key, for now: the URL and model always have defaults, and the only
        server that needs no key is a local one, which has no configuration
        of its own yet.
        """
        return self.key is not None


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """When a failed request is sent again, and how long to wait first."""

    max_retries: int = 2
    backoff_initial: float = 0.5
    backoff_max: float = 5.0
    backoff_jitter: float = 0.25
    statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({408, 429, *range(500, 600)})
    )
    timeout: float = 30.0

    def delay(self, attempt: int, retry_after: str | None = None) -> float:
        """Seconds to wait before retry number ``attempt``, counted from zero."""
        if retry_after is not None:
            try:
                return min(max(float(retry_after), 0.0), self.backoff_max)
            except ValueError:
                pass
        base = min(self.backoff_initial * 2**attempt, self.backoff_max)
        return base * (1 + random.uniform(-self.backoff_jitter, self.backoff_jitter))


class SystemOne:
    """A :class:`~outrage.smartsearch.Judge` over HTTP.

    Holds one connection pool for its lifetime, so a search that sends a few
    hundred requests opens a handful of connections rather than a few hundred.
    Close it, or use it as a context manager.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        retry: RetryPolicy | None = None,
        transport: httpx2.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.retry = retry or RetryPolicy()
        self._sleep = sleep
        headers = {"Authorization": f"Bearer {settings.key}"} if settings.key else {}
        self._client = httpx2.Client(
            headers=headers, timeout=self.retry.timeout, transport=transport
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def judge(self, state: str, questions: Mapping[str, Question]) -> Judgement:
        body = {
            "model": self.settings.model,
            "state": state,
            "questions": {qid: _wire(question) for qid, question in questions.items()},
        }
        response = self._send(body)
        try:
            return _judgement(response.json(), questions)
        except (ValueError, KeyError, TypeError) as error:
            raise JudgeError(
                "smart-search-response-malformed", url=self.settings.url, reason=str(error)
            ) from error

    def _send(self, body: dict[str, Any]) -> httpx2.Response:
        url = self.settings.url
        attempt = 0
        while True:
            try:
                response = self._client.post(url, json=body)
            except (httpx2.TimeoutException, httpx2.TransportError) as error:
                if attempt >= self.retry.max_retries:
                    raise JudgeError(
                        "smart-search-unreachable", url=url, reason=str(error)
                    ) from error
                self._sleep(self.retry.delay(attempt))
                attempt += 1
                continue
            status = response.status_code
            if status == 200:
                return response
            if status in self.retry.statuses and attempt < self.retry.max_retries:
                self._sleep(self.retry.delay(attempt, response.headers.get("retry-after")))
                attempt += 1
                continue
            detail = _detail(response)
            if status in (401, 403):
                raise JudgeError("smart-search-unauthorised", url=url, status=status)
            if status == 422 and _TOO_LARGE.search(detail):
                raise StateTooLarge("smart-search-state-too-large", url=url, detail=detail)
            if status == 422:
                raise JudgeError("smart-search-request-rejected", url=url, detail=detail)
            raise JudgeError("smart-search-service-failed", url=url, status=status, detail=detail)


def _wire(question: Question) -> dict[str, Any]:
    """One question as the protocol spells it."""
    instructions: str | dict[str, str] = (
        {"question": question.text, **question.instructions}
        if question.instructions
        else question.text
    )
    wired: dict[str, Any] = {"type": question.kind, "instructions": instructions}
    if question.kind == "score":
        wired["criteria"] = list(question.criteria)
    return wired


def _judgement(payload: Mapping[str, Any], questions: Mapping[str, Question]) -> Judgement:
    """A response body as answers, refusing one that is not the documented shape.

    An answer the response leaves out is left out here too, and the cascade
    reports that document as unjudged; one it gets wrong raises, since a
    response half in the wrong shape says nothing about which half is right.
    """
    answers: dict[str, Answer] = {}
    for qid, raw in payload["answers"].items():
        if qid not in questions:
            continue
        kind = raw["type"]
        if kind == "noul":
            answers[qid] = Answer(probability=float(raw["noul"]))
        elif kind == "score":
            by_level = raw.get("probabilities") or {}
            levels = len(questions[qid].criteria) or len(by_level)
            answers[qid] = Answer(
                score=float(raw["score"]),
                probabilities=tuple(float(by_level.get(str(i), 0.0)) for i in range(levels))
                if by_level
                else (),
                confidence=float(raw["confidence"]) if "confidence" in raw else None,
            )
        else:
            raise ValueError(f"answer {qid!r} has type {kind!r}")
    usage = payload.get("usage") or {}
    return Judgement(answers, input_tokens=int(usage.get("input_tokens", 0)))


def _detail(response: httpx2.Response) -> str:
    """The start of an error response's body, on one line."""
    return " ".join(response.text.split())[:DETAIL_CHARS]


__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_URL",
    "DETAIL_CHARS",
    "KEY_VARIABLE",
    "RetryPolicy",
    "Settings",
    "SystemOne",
]
