"""Screen a bounded slice of documents against a query with a System One
judge. A configurable cascade examines progressively richer metadata and then
the body, retaining the evidence used to rank every document not ruled out.

The cascade the ``outrage-search`` agent follows, moved out of an agent's
context and into the library: every document in the slice is judged at the
first level -- its ``!title``, as shipped -- and only the ones that level
leaves unsure go on to the next, through richer metadata to the body. What
comes back is every document not ruled out, best first. The calling agent
reads none of it.

**The judging is not done here.** A :class:`Judge` answers questions about a
piece of state -- the protocol System One models speak -- and this module
decides what to ask, of which documents, and what the answers add up to. So the
suite runs against a fake, and a second model or a local server is a different
judge rather than a different cascade.

What is expected to change as the cascade is measured is not in this module
at all. The levels and their order, the question asked at each, **which way
round** each is asked (the query as the state and many documents as the
questions, or each document as the state and the query as its one question),
the scoring constants and the request sizes are a :class:`Tuning`, read from
a JSON file shipped in the package, :data:`TUNING_PATH`, beside a readme
saying what each part means and how to tune it. What stays here is the rules:
what each :data:`Kind` of level reads, and how :class:`Scoring` turns the
per-level answers into a decision -- one object over the evidence, which the
result keeps whole so that a tuning run can re-score without asking the
model again.

Two rules carry over from the agent unchanged. **Missing metadata is unsure,
never no**: a document without a summary has told the cascade nothing, so it
goes on to the next level as it was. And **a partial value cannot justify a
no**: a truncated title, or a body judged in fewer chunks than it has, can
count for a document but never against it.

A third rule, from measuring, is that **a supporting level can count only
for a document**. A title or keywords label a document rather than describe
it, so a generic one gets a low answer rather than an unsure one; counted
against, a single such answer ruled out the best document for a query. The
tuning says which levels are supporting, and :attr:`Scoring.supporting`
applies it.

Content leaves the machine whenever the judge is a remote service, which is
the front ends' to say; this module cannot tell one judge from another.
"""

from __future__ import annotations

import functools
import json
import math
import re
import string
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Protocol

from . import keys, shipped
from .errors import OutrageError, Refusal
from .store import BoundedSubtree, KeyRange, Store

#: A level's name, as the tuning defines it: a metadata name for a level that
#: reads metadata, or whatever the tuning calls the level reading the body.
Level = str

#: Which way round a level is asked.
#:
#: ``"questions"`` puts the query in the state and one document in each question,
#: so one request judges many documents. ``"state"`` puts the document in the
#: state and the query in its one question, a request per document. Both are
#: measured; if one wins everywhere the other goes.
Shape = Literal["questions", "state"]

#: Where a level leaves a document: ruled in, ruled out, or carried to the next.
Decision = Literal["yes", "no", "unsure"]


@dataclass(frozen=True, slots=True)
class Question:
    """One question put to a judge, in terms that do not depend on the wire.

    ``text`` may name ``{query}``, which is filled in when the query is not the
    state. ``instructions`` are the facts the question is about -- for the
    ``"questions"`` shape, the document's key and the value being judged. They
    travel beside the text rather than inside it, so the text names them in
    backticks, the way System One expects a question to point at its data.
    """

    kind: Literal["noul", "score"]
    """``"noul"`` answers one probability of yes; ``"score"`` picks one of
    ``criteria`` and answers a probability for each."""
    text: str
    criteria: tuple[str, ...] = ()
    """For a score, what each level means, lowest first. Two to ten of them."""
    instructions: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Answer:
    """What a judge said about one question.

    A Noul answer sets ``probability``. A Score answer sets ``score``, the
    probability-weighted level counted from zero -- it can land between two --
    and usually ``probabilities`` across every level and a ``confidence``.
    """

    probability: float | None = None
    score: float | None = None
    probabilities: tuple[float, ...] = ()
    confidence: float | None = None

    def as_probability(self, levels: int | None = None) -> float:
        """This answer as one probability of a match, from 0 to 1.

        A Noul answer already is one. A score becomes its expected level scaled
        to 0-1, which uses the whole distribution where there is one: a
        document the model put evenly between *related* and *relevant* sits
        between them rather than at whichever won.
        """
        if self.probability is not None:
            return self.probability
        count = len(self.probabilities) or levels
        if not count or count < 2:
            raise ValueError("a score answer needs its number of levels")
        if self.probabilities:
            mass = sum(self.probabilities)
            expected = sum(i * p for i, p in enumerate(self.probabilities)) / (mass or 1)
        elif self.score is not None:
            expected = self.score
        else:
            raise ValueError("an answer carries neither a probability nor a score")
        return expected / (count - 1)


@dataclass(frozen=True, slots=True)
class Judgement:
    """A judge's answers to one request, by the ids the questions were sent under."""

    answers: Mapping[str, Answer]
    input_tokens: int = 0


class Judge(Protocol):
    """Anything that answers questions about a piece of state.

    The System One protocol, reduced to what the cascade needs. A client
    retries what is worth retrying before it raises, so a :class:`JudgeError`
    reaching the cascade is final for the documents that request carried.
    """

    def judge(self, state: str, questions: Mapping[str, Question]) -> Judgement: ...


class JudgeError(OutrageError, RuntimeError):
    """A request to the judge failed, after whatever retrying the client does."""


class StateTooLarge(JudgeError):
    """The judge refused a request as too long. The cascade halves and retries."""


@dataclass(frozen=True, slots=True)
class LevelQuestions:
    """The question for one level, in each of the two shapes."""

    questions: Question
    """Asked with the query as the state; the document is in its instructions."""
    state: Question
    """Asked with the document's value as the state; names ``{query}``."""


@dataclass(frozen=True, slots=True)
class Evidence:
    """What one level said about one document, kept whole for re-scoring."""

    level: Level
    answer: Answer
    probability: float
    """``answer`` reduced to one probability of a match."""
    chunks: int = 1
    """How many requests the level took for this document: one, or a body's
    chunks. For a body, ``answer`` is the best chunk's."""
    partial: bool = False
    """Whether the level judged less than all there was -- a truncated value,
    or a body with chunks left unread. Partial evidence cannot count against."""


@dataclass(frozen=True, slots=True)
class Scoring:
    """How evidence from the levels becomes a probability and a decision.

    **Weighted log-odds, summed**: each level adds ``weight * logit(p)``,
    scaled by the answer's confidence where it has one, and the combined
    probability is the sigmoid of the total. Two near misses therefore add up
    to more than either, where per-level thresholds would carry both as unsure
    and forget them. The levels are not independent -- a title and a summary
    written together say much the same thing -- and weights below one are the
    damping for that.

    The numbers come from the tuning file, :data:`TUNING_PATH`, and are a
    starting point rather than a result: measuring the cascade against
    labelled queries is what sets them. Other
    rules the measuring may prefer -- the strongest level rather than the sum,
    a small fitted model over the per-level answers, or the last level alone
    with the earlier ones only pruning -- are each a different :meth:`combine`.
    """

    weights: Mapping[Level, float]
    """How much each level's answer counts, by level name."""
    supporting: frozenset[Level]
    """Levels whose evidence can count for a document and never against it, as
    partial evidence cannot. A label too generic to say anything gets a low
    answer, not an unsure one, and must not rule the document out."""
    yes: float
    """At or above this, a document is decided a match and stops cascading."""
    no: float
    """At or below this, a document is ruled out."""
    clamp: float
    """How close to 0 or 1 a probability is taken to be, so that a certain
    answer adds a large finite amount rather than an infinite one."""

    def combine(self, evidence: Sequence[Evidence]) -> float:
        """The probability that a document matches, on everything seen so far."""
        total = 0.0
        for item in evidence:
            weight = self.weights.get(item.level, 1.0)
            if item.answer.confidence is not None:
                weight *= item.answer.confidence
            contribution = weight * _logit(item.probability, self.clamp)
            if item.partial or item.level in self.supporting:
                contribution = max(contribution, 0.0)
            total += contribution
        return 1 / (1 + math.exp(-total))

    def decide(self, probability: float) -> Decision:
        """Yes, no, or carry on to the next level."""
        if probability >= self.yes:
            return "yes"
        if probability <= self.no:
            return "no"
        return "unsure"


def _logit(p: float, clamp: float) -> float:
    p = min(max(p, clamp), 1 - clamp)
    return math.log(p / (1 - p))


#: What a level reads: a plain metadata value, a ``!contents`` index (judged on
#: its headings, its offsets kept for chunking the body), or the body itself.
#: Behaviour rather than a number, so the tuning picks one per level but cannot
#: invent another.
Kind = Literal["value", "contents", "body"]

#: The tuning file's layout version; a file naming another is refused.
TUNING_FORMAT = 1

#: Where the tuning lives in the shipped documents tree, which is what serves it
#: as ``outrage/smart-search/tuning`` beside the readme describing it.
TUNING_PATH = ("smart-search", "tuning.json")

#: How each combination rule is named in the tuning. The rule is code, so a
#: second one is a new name here and a new :meth:`Scoring.combine`.
RULES = ("log-odds-sum",)

#: Accepted anywhere an object is, and ignored: the short reason beside a
#: number, where the readme holds the longer account.
_NOTE = "note"
_TOP = ("format", "question", "levels", "scoring", "requests")
_QUESTION = ("kind", "criteria", "questions", "state")
_LEVEL = ("name", "kind", "meta", "what", "shape", "weight", "supporting", "question")
_LEVEL_REQUIRED = ("name", "kind", "what", "shape", "weight")
_SCORING = ("rule", "yes", "no", "clamp")
_REQUESTS = ("limit", "batch_size", "value_chars", "chunk_chars", "max_chunks", "min_chunk_chars")
_KINDS = ("value", "contents", "body")
_SHAPES = ("questions", "state")
_QUESTION_KINDS = ("score", "noul")
_CRITERIA_RANGE = (2, 10)

#: A top-level section the file leaves out, which is refused once as missing,
#: as against one written as ``null``, which is refused as not an object.
_ABSENT = object()

#: The placeholders each template may name. ``{query}`` only where the query is
#: not already the state, and there it is required.
_PLACEHOLDERS = {"questions": ("level", "what"), "state": ("level", "what", "query")}

#: Every name the tuning file accepts, as field names and as the values of its
#: enumerated fields, so that the readme can be held to describing all of them.
TUNING_NAMES = tuple(
    dict.fromkeys(
        (
            *_TOP,
            *_QUESTION,
            *_LEVEL,
            *_SCORING,
            *_REQUESTS,
            _NOTE,
            *_KINDS,
            *_SHAPES,
            *_QUESTION_KINDS,
            *RULES,
        )
    )
)


@dataclass(frozen=True, slots=True)
class LevelTuning:
    """One level of the cascade, as the tuning defines it."""

    name: str
    """What the level is called, in a result and in a request's ``levels``."""
    kind: Kind
    meta: str | None
    """The metadata name read, without its ``!``; None for the body."""
    shape: Shape
    weight: float
    supporting: bool
    questions: LevelQuestions
    """The question in both shapes, with the level's placeholders filled in."""


@dataclass(frozen=True, slots=True)
class Requests:
    """How much is read and sent at once. See :data:`TUNING_PATH`'s readme."""

    limit: int
    batch_size: int
    value_chars: int
    chunk_chars: int
    max_chunks: int
    min_chunk_chars: int


@dataclass(frozen=True, slots=True)
class Tuning:
    """Everything about the cascade that is a number or a sentence, not a rule.

    Read from a JSON file -- the packaged one, :data:`TUNING_PATH`, unless a
    caller names another -- so that the levels, the questions, the scoring
    constants and the request sizes can be tuned without touching the code.
    """

    levels: tuple[LevelTuning, ...]
    """In cascade order."""
    scoring: Scoring
    requests: Requests
    source: str
    """Where it was read from, as a refusal names it."""

    @property
    def names(self) -> tuple[str, ...]:
        """The level names, in cascade order."""
        return tuple(level.name for level in self.levels)

    def level(self, name: str) -> LevelTuning:
        """The level called ``name``; a :class:`KeyError` for one it lacks."""
        for level in self.levels:
            if level.name == name:
                return level
        raise KeyError(name)

    @classmethod
    def read(cls, data: object, source: str) -> tuple[Tuning | None, list[Refusal]]:
        """``data`` as a tuning, and every problem with it at once.

        ``data`` is the parsed JSON, from wherever it came: ``source`` is
        only what a refusal names, so that a second file's problems can be
        told from the packaged one's. The tuning is None whenever there is a
        refusal, since there is no sensible part of a cascade to run.
        """
        return _TuningReader(source).read(data)

    @classmethod
    def read_file(cls, path: Path | None = None) -> tuple[Tuning | None, list[Refusal]]:
        """:meth:`read` over a file, the packaged tuning by default."""
        path = shipped.tree().joinpath(*TUNING_PATH) if path is None else path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            reason = error.strerror or str(error)
            return None, [
                Refusal(
                    "smart-search-tuning-unreadable",
                    overridable=False,
                    source=str(path),
                    reason=reason,
                )
            ]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            return None, [
                Refusal(
                    "smart-search-tuning-not-json",
                    overridable=False,
                    source=str(path),
                    reason=str(error),
                )
            ]
        return cls.read(data, str(path))

    @classmethod
    def load(cls, path: Path | None = None) -> Tuning:
        """:meth:`read_file`, raising the first refusal as its error."""
        tuning, found = cls.read_file(path)
        if found or tuning is None:
            raise found[0].as_error()
        return tuning


class _TuningReader:
    """One pass over a tuning file, collecting every refusal as it goes."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.found: list[Refusal] = []

    def read(self, data: object) -> tuple[Tuning | None, list[Refusal]]:
        top = self._object(data, "the tuning", _TOP, _TOP)
        if top is None:
            return None, self.found
        found = top.get("format", TUNING_FORMAT)
        if type(found) is not int or found != TUNING_FORMAT:
            self._value("format", f"{TUNING_FORMAT}, the only format this version reads")
        default = self._object(top.get("question", _ABSENT), "question", _QUESTION, _QUESTION)
        levels = self._levels(top.get("levels", _ABSENT), default)
        scoring = self._scoring(top.get("scoring", _ABSENT), levels)
        requests = self._requests(top.get("requests", _ABSENT))
        if self.found or levels is None or scoring is None or requests is None:
            assert self.found, "a tuning that could not be built says why"
            return None, self.found
        return Tuning(levels, scoring, requests, self.source), []

    def _levels(
        self, data: object, default: Mapping[str, Any] | None
    ) -> tuple[LevelTuning, ...] | None:
        if data is _ABSENT:
            return None
        if not isinstance(data, list) or not data:
            self._value("levels", "a list of at least one level")
            return None
        levels: list[LevelTuning] = []
        seen: set[str] = set()
        kinds: set[str] = set()
        for index, item in enumerate(data):
            where = f"levels[{index}]"
            level = self._object(item, where, _LEVEL, _LEVEL_REQUIRED)
            if level is None:
                continue
            name = level.get("name")
            if "name" not in level:
                pass
            elif not _meta_name(name):
                self._value(f"{where}.name", "a metadata name: not empty, without '!' or '/'")
            elif name in seen:
                self._value(f"{where}.name", "a name no other level has")
            else:
                seen.add(name)
            kind = level.get("kind")
            if "kind" not in level:
                pass
            elif kind not in _KINDS:
                self._value(f"{where}.kind", _one_of(_KINDS))
            elif kind != "value" and kind in kinds:
                self._value(f"{where}.kind", f"not {kind!r} again: only one level reads it")
            else:
                kinds.add(kind)
            meta = level.get("meta", name if kind != "body" else None)
            if "meta" in level:
                if kind == "body":
                    self._value(f"{where}.meta", "left out, since the body is not metadata")
                elif not _meta_name(meta):
                    self._value(f"{where}.meta", "a metadata name: not empty, without '!' or '/'")
            what = level.get("what")
            if "what" in level and (not isinstance(what, str) or not what):
                self._value(f"{where}.what", "a non-empty string")
            shape = level.get("shape")
            if "shape" not in level:
                pass
            elif shape not in _SHAPES:
                self._value(f"{where}.shape", _one_of(_SHAPES))
            elif kind == "body" and shape != "state":
                self._value(f"{where}.shape", "'state', since a body is too long for a question")
            weight = level.get("weight")
            if "weight" in level and (not _number(weight) or weight < 0):
                self._value(f"{where}.weight", "a number, zero or more")
            supporting = level.get("supporting", False)
            if not isinstance(supporting, bool):
                self._value(f"{where}.supporting", "true or false")
            own = self._object(level.get("question", {}), f"{where}.question", _QUESTION, ())
            asked = None
            if default is not None and own is not None and isinstance(name, str):
                asked = self._questions(default, own, where, name, what)
            if asked is not None and not self.found:
                levels.append(
                    LevelTuning(name, kind, meta, shape, float(weight), supporting, asked)
                )
        return tuple(levels) if not self.found else None

    def _questions(
        self,
        default: Mapping[str, Any],
        own: Mapping[str, Any],
        where: str,
        name: str,
        what: object,
    ) -> LevelQuestions | None:
        """The level's question: the default's fields, overridden by its own."""
        merged = {**default, **own}

        def at(field_name: str) -> str:
            owner = f"{where}.question" if field_name in own else "question"
            return f"{owner}.{field_name}"

        kind = merged.get("kind")
        if kind not in _QUESTION_KINDS:
            self._once(at("kind"), _one_of(_QUESTION_KINDS))
            kind = None
        criteria = merged.get("criteria", [])
        low, high = _CRITERIA_RANGE
        if not isinstance(criteria, list) or not all(isinstance(c, str) and c for c in criteria):
            self._once(at("criteria"), "a list of non-empty strings")
            criteria = None
        elif kind == "score" and not low <= len(criteria) <= high:
            self._once(at("criteria"), f"{low} to {high} of them, lowest first, for a score")
            criteria = None
        texts: dict[str, str] = {}
        for shape in _SHAPES:
            template = merged.get(shape)
            text = self._template(template, at(shape), shape)
            if text is not None and isinstance(what, str):
                texts[shape] = _fill(text, shape, name, what)
        if kind is None or criteria is None or len(texts) != len(_SHAPES):
            return None
        kept = tuple(criteria) if kind == "score" else ()
        return LevelQuestions(
            questions=Question(kind, texts["questions"], kept),
            state=Question(kind, texts["state"], kept),
        )

    def _template(self, template: object, where: str, shape: str) -> str | None:
        allowed = _PLACEHOLDERS[shape]
        if not isinstance(template, str) or not template:
            self._once(where, "a non-empty string")
            return None
        try:
            named = [
                placeholder
                for _, placeholder, _, _ in string.Formatter().parse(template)
                if placeholder is not None
            ]
            plain = all(
                not spec and conversion is None
                for _, placeholder, spec, conversion in string.Formatter().parse(template)
                if placeholder is not None
            )
        except ValueError:
            self._once(where, "a template whose braces balance; write a literal one as {{ or }}")
            return None
        if not plain:
            self._once(where, "a template whose placeholders are plain names, such as {what}")
            return None
        unknown = [name for name in named if name not in allowed]
        if unknown:
            self._once(where, f"a template naming only {_braced(allowed)}, not {_braced(unknown)}")
            return None
        if shape == "state" and "query" not in named:
            self._once(where, "a template naming {query}, where the query goes")
            return None
        return template

    def _scoring(self, data: object, levels: Sequence[LevelTuning] | None) -> Scoring | None:
        table = self._object(data, "scoring", _SCORING, _SCORING)
        if table is None:
            return None
        if table.get("rule", RULES[0]) not in RULES:
            self._value("scoring.rule", _one_of(RULES))
        valid = "yes" in table and "no" in table
        for name in ("yes", "no"):
            value = table.get(name)
            if name in table and (not _number(value) or not 0 < value < 1):
                self._value(f"scoring.{name}", "a number between 0 and 1")
                valid = False
        if valid and table["no"] >= table["yes"]:
            self._value("scoring.no", f"below scoring.yes, {table['yes']}")
        clamp = table.get("clamp")
        if "clamp" in table and (not _number(clamp) or not 0 < clamp < 0.5):
            self._value("scoring.clamp", "a number between 0 and 0.5")
        if self.found or levels is None:
            return None
        return Scoring(
            weights={level.name: level.weight for level in levels},
            supporting=frozenset(level.name for level in levels if level.supporting),
            yes=float(table["yes"]),
            no=float(table["no"]),
            clamp=float(clamp),
        )

    def _requests(self, data: object) -> Requests | None:
        table = self._object(data, "requests", _REQUESTS, _REQUESTS)
        if table is None:
            return None
        valid = True
        for name in _REQUESTS:
            value = table.get(name)
            if name in table and (
                not isinstance(value, int) or isinstance(value, bool) or value < 1
            ):
                self._value(f"requests.{name}", "a whole number, one or more")
                valid = False
        sizes = [table.get(name) for name in ("min_chunk_chars", "chunk_chars")]
        if valid and None not in sizes and sizes[0] > sizes[1]:
            self._value("requests.min_chunk_chars", "at most requests.chunk_chars")
        if self.found or len(table) - (_NOTE in table) < len(_REQUESTS):
            return None
        return Requests(**{name: table[name] for name in _REQUESTS})

    def _object(
        self, data: object, where: str, known: Sequence[str], required: Sequence[str]
    ) -> Mapping[str, Any] | None:
        """``data`` if it is an object, refusing its unknown and missing names."""
        if data is _ABSENT:
            return None
        if not isinstance(data, dict):
            self._value(where, "an object")
            return None
        for name in data:
            if name == _NOTE:
                if not isinstance(data[name], str):
                    self._value(f"{where}.{_NOTE}", "a string")
            elif name not in known:
                self.found.append(
                    Refusal(
                        "smart-search-tuning-name-unknown",
                        overridable=False,
                        source=self.source,
                        where=where,
                        name=name,
                        known=tuple(known),
                    )
                )
        for name in required:
            if name not in data:
                self.found.append(
                    Refusal(
                        "smart-search-tuning-name-missing",
                        overridable=False,
                        source=self.source,
                        where=where,
                        name=name,
                    )
                )
        return data

    def _value(self, where: str, expected: str) -> None:
        self.found.append(
            Refusal(
                "smart-search-tuning-value",
                overridable=False,
                source=self.source,
                where=where,
                expected=expected,
            )
        )

    def _once(self, where: str, expected: str) -> None:
        """:meth:`_value`, but a default question's fault is reported once, not per level."""
        for refusal in self.found:
            if refusal.code == "smart-search-tuning-value" and refusal.details["where"] == where:
                return
        self._value(where, expected)


def _meta_name(name: object) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and not name.startswith(keys.META_PREFIX)
        and keys.DELIMITER not in name
    )


def _number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _one_of(names: Sequence[str]) -> str:
    return "one of " + ", ".join(repr(name) for name in names)


def _braced(names: Sequence[str]) -> str:
    return ", ".join("{" + name + "}" for name in names)


def _fill(template: str, shape: str, level: str, what: str) -> str:
    """A template with the level's placeholders filled in.

    A ``"state"`` text still names ``{query}``, filled per search with
    :meth:`str.format`, so everything else in it is left escaped for that.
    """
    if shape == "questions":
        return template.format(level=level, what=what)
    escape = {"level": level, "what": what}
    text = []
    for literal, placeholder, _, _ in string.Formatter().parse(template):
        text.append(literal.replace("{", "{{").replace("}", "}}"))
        if placeholder is not None:
            text.append(
                "{query}"
                if placeholder == "query"
                else escape[placeholder].replace("{", "{{").replace("}", "}}")
            )
    return "".join(text)


@dataclass(frozen=True, slots=True)
class Match:
    """One document not ruled out."""

    key: str
    probability: float
    decision: Literal["yes", "unsure"]
    decided_at: Level | None
    """The level at which it was decided a match, or None when no level did
    and it is here as still unsure."""
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class Unjudged:
    """A document the cascade could not finish, and why."""

    key: str
    level: Level
    code: str
    """The failure's code, which :mod:`outrage.messages` renders."""
    details: Mapping[str, object]
    evidence: tuple[Evidence, ...]
    """Whatever the levels before this one said."""


@dataclass(slots=True)
class LevelCounts:
    """What happened at one level, across the slice."""

    asked: int = 0
    """Documents judged at this level."""
    yes: int = 0
    no: int = 0
    missing: int = 0
    """Documents that reached this level without the metadata it reads, and
    so went on unchanged."""
    unjudged: int = 0


@dataclass(frozen=True, slots=True)
class SmartSearchResult:
    """The whole answer for one slice.

    ``total`` and ``next_cursor`` are over the *input* -- the documents of the
    subtree -- since the matches cannot be paged: the next slice is asked for
    with ``after=next_cursor``.
    """

    key: str | None
    query: str
    matches: tuple[Match, ...]
    """Every document not ruled out, best first."""
    unjudged: tuple[Unjudged, ...]
    levels: Mapping[Level, LevelCounts]
    documents: int
    """Documents in this slice."""
    total: int
    """Documents in the whole subtree."""
    next_cursor: str | None
    unavailable: tuple[str, ...]
    """Mount points the slice had to leave out."""
    input_tokens: int


@dataclass(slots=True)
class _Candidate:
    key: str
    evidence: list[Evidence] = field(default_factory=list)
    decision: Decision = "unsure"
    decided_at: Level | None = None
    probability: float = 0.5
    failure: Unjudged | None = None
    contents: str | None = None
    """The raw ``!contents`` value, kept from that level for chunking a body."""


@functools.cache
def packaged_tuning() -> tuple[Tuning | None, tuple[Refusal, ...]]:
    """The tuning shipped in the package, and every problem with it.

    Read once per process, so an edit to the file reaches the next process
    rather than one already running -- the same as an edit to the code.
    """
    tuning, found = Tuning.read_file()
    return tuning, tuple(found)


def refusals(
    query: str,
    levels: Sequence[str] | None = None,
    *,
    tuning: Tuning | None = None,
) -> list[Refusal]:
    """Every reason these arguments cannot be searched with, at once.

    ``tuning`` is the packaged one by default, and its own problems are
    among the reasons, so a front end asking this hears of a broken file too.
    """
    found: list[Refusal] = []
    if tuning is None:
        tuning, broken = packaged_tuning()
        found.extend(broken)
    known = tuning.names if tuning is not None else ()
    if not query.strip():
        found.append(Refusal("smart-search-query-empty", overridable=False))
    if tuning is None:
        return found
    if levels is not None and not levels:
        found.append(Refusal("smart-search-levels-empty", overridable=False, known=known))
    for level in levels or ():
        if level not in known:
            found.append(
                Refusal("smart-search-level-unknown", overridable=False, level=level, known=known)
            )
    repeated = sorted({level for level in levels or () if list(levels or ()).count(level) > 1})
    for level in repeated:
        found.append(Refusal("smart-search-level-repeated", overridable=False, level=level))
    return found


def smart_search(
    store: Store,
    key: str | None,
    query: str,
    judge: Judge,
    *,
    tuning: Tuning | None = None,
    depth: int | None = None,
    limit: int | None = None,
    after: str | None = None,
    levels: Sequence[Level] | None = None,
) -> SmartSearchResult:
    """Screen one slice of the documents under ``key`` against ``query``.

    The slice is a page of the subtree's documents, ``limit`` of them after
    ``after``, exactly as ``get_documents`` would page it. Each is judged at
    the first of ``levels`` -- every level of ``tuning`` by default, in its
    order -- and carried to the next only while the combined evidence leaves
    it unsure.

    ``tuning`` is :func:`packaged_tuning` by default: everything about the
    cascade that is a number or a sentence rather than a rule.

    Raises the first of :func:`refusals` as an error; a front end wanting
    every reason calls that first. A failed request never
    raises: its documents are reported in :attr:`SmartSearchResult.unjudged`.
    """
    problems = refusals(query, levels, tuning=tuning)
    if problems:
        raise problems[0].as_error()
    if tuning is None:
        tuning = packaged_tuning()[0]
        assert tuning is not None, "refusals() reports a broken packaged tuning"
    sizes = tuning.requests
    levels = tuple(levels) if levels is not None else tuning.names
    plans = {name: tuning.level(name) for name in levels}
    scoring = tuning.scoring
    subtree = BoundedSubtree(key, depth)

    page = store.get_documents(
        subtree, cursor=after, limit=sizes.limit if limit is None else limit, max_chars=1
    )
    candidates = [_Candidate(excerpt.key) for excerpt in page.items]
    unavailable = set(page.unavailable)
    counts: dict[Level, LevelCounts] = {level: LevelCounts() for level in levels}
    tokens = 0

    for level in levels:
        pending = [c for c in candidates if c.decision == "unsure" and c.failure is None]
        if not pending:
            break
        plan = plans[level]
        tally = counts[level]
        if plan.kind == "body":
            judged, spent = _judge_bodies(
                store,
                pending,
                level,
                query,
                judge,
                plan.questions.state,
                sizes.chunk_chars,
                sizes.max_chunks,
                sizes.min_chunk_chars,
            )
        else:
            assert plan.meta is not None, "a metadata level names its metadata"
            values, missed = _values(store, subtree, plan.meta, pending, sizes.value_chars)
            unavailable.update(missed)
            if plan.kind == "contents":
                for candidate in pending:
                    if candidate.key in values:
                        candidate.contents = values[candidate.key][0]
                values = {k: (_headings_only(v), partial) for k, (v, partial) in values.items()}
            tally.missing += sum(1 for c in pending if c.key not in values)
            present = [c for c in pending if c.key in values]
            judged, spent = _judge_values(
                present,
                values,
                level,
                query,
                judge,
                plan.questions,
                plan.shape,
                sizes.batch_size,
            )
        tokens += spent
        for candidate in pending:
            if candidate.failure is not None:
                tally.unjudged += 1
                continue
            evidence = judged.get(candidate.key)
            if evidence is None:
                continue
            tally.asked += 1
            candidate.evidence.append(evidence)
            candidate.probability = scoring.combine(candidate.evidence)
            candidate.decision = scoring.decide(candidate.probability)
            if candidate.decision != "unsure":
                candidate.decided_at = level
                if candidate.decision == "yes":
                    tally.yes += 1
                else:
                    tally.no += 1

    matches = sorted(
        (
            Match(
                c.key,
                c.probability,
                "yes" if c.decision == "yes" else "unsure",
                c.decided_at,
                tuple(c.evidence),
            )
            for c in candidates
            if c.failure is None and c.decision != "no"
        ),
        key=lambda match: (-match.probability, keys.sort_form(match.key)),
    )
    return SmartSearchResult(
        key=key,
        query=query,
        matches=tuple(matches),
        unjudged=tuple(c.failure for c in candidates if c.failure is not None),
        levels=counts,
        documents=len(candidates),
        total=page.total,
        next_cursor=page.next_cursor,
        unavailable=tuple(sorted(unavailable)),
        input_tokens=tokens,
    )


def _values(
    store: Store,
    subtree: BoundedSubtree,
    meta: str,
    pending: Sequence[_Candidate],
    value_chars: int,
) -> tuple[dict[str, tuple[str, bool]], tuple[str, ...]]:
    """One metadata name for the pending documents, as ``{key: (value, partial)}``.

    **One name per call**, because a survey asking for two names cannot say
    which a document is missing. The read spans the pending documents' stretch
    of the order and keeps only theirs: a metadata key sorts after its
    document, so the stretch ends at the last one's subtree, and anything else
    in there is dropped rather than asked for key by key.
    """
    wanted = {c.key for c in pending}
    suffix = keys.META_PREFIX + meta
    stretch = KeyRange(after_inclusive=pending[0].key, final_subtree=pending[-1].key)
    values: dict[str, tuple[str, bool]] = {}
    missed: set[str] = set()
    cursor: str | None = None
    while True:
        page = store.get_documents(
            subtree, key_range=stretch, meta_name=meta, cursor=cursor, max_chars=value_chars
        )
        missed.update(page.unavailable)
        for excerpt in page.items:
            document = excerpt.key.removesuffix(suffix).removesuffix(keys.DELIMITER)
            if document in wanted:
                values[document] = (excerpt.content, excerpt.truncated)
        cursor = page.next_cursor
        if cursor is None:
            return values, tuple(missed)


_OFFSETS = re.compile(r"^\d+(?: \d+)*$")


def _headings_only(contents: str) -> str:
    """A ``!contents`` value without its offset lines, which say nothing to a model."""
    return "\n".join(
        line for line in contents.splitlines() if line.strip() and not _OFFSETS.match(line)
    )


def _judge_values(
    present: Sequence[_Candidate],
    values: Mapping[str, tuple[str, bool]],
    level: Level,
    query: str,
    judge: Judge,
    asked: LevelQuestions,
    shape: Shape,
    batch_size: int,
) -> tuple[dict[str, Evidence], int]:
    """Judge one metadata value per document, in whichever shape the level uses."""
    judged: dict[str, Evidence] = {}
    tokens = 0
    if shape == "questions":
        for start in range(0, len(present), batch_size):
            batch = present[start : start + batch_size]
            ids = {f"d{i}": c for i, c in enumerate(batch)}
            sent = {
                qid: replace(
                    asked.questions,
                    instructions={"key": c.key, level: values[c.key][0]},
                )
                for qid, c in ids.items()
            }
            try:
                judgement = judge.judge(query, sent)
            except JudgeError as error:
                for candidate in batch:
                    candidate.failure = _failed(candidate, level, error)
                continue
            tokens += judgement.input_tokens
            for qid, candidate in ids.items():
                try:
                    answer = _answer(judgement, qid)
                except JudgeError as error:
                    candidate.failure = _failed(candidate, level, error)
                    continue
                judged[candidate.key] = _evidence(
                    level, answer, asked.questions, values[candidate.key][1]
                )
    else:
        question = replace(asked.state, text=asked.state.text.format(query=query))
        for candidate in present:
            value, partial = values[candidate.key]
            try:
                judgement = judge.judge(value, {"q": question})
                tokens += judgement.input_tokens
                answer = _answer(judgement, "q")
            except JudgeError as error:
                candidate.failure = _failed(candidate, level, error)
                continue
            judged[candidate.key] = _evidence(level, answer, question, partial)
    return judged, tokens


def _answer(judgement: Judgement, qid: str) -> Answer:
    """The answer to one question, or a failure for a judge that left it out."""
    answer = judgement.answers.get(qid)
    if answer is None:
        raise JudgeError("smart-search-answer-missing", question=qid)
    return answer


def _evidence(level: Level, answer: Answer, question: Question, partial: bool) -> Evidence:
    probability = answer.as_probability(len(question.criteria) or None)
    return Evidence(level, answer, probability, partial=partial)


def _failed(candidate: _Candidate, level: Level, error: OutrageError) -> Unjudged:
    return Unjudged(
        candidate.key, level, error.code, dict(error.details), tuple(candidate.evidence)
    )


def _judge_bodies(
    store: Store,
    pending: Sequence[_Candidate],
    level: Level,
    query: str,
    judge: Judge,
    asked: Question,
    chunk_chars: int,
    max_chunks: int,
    min_chunk_chars: int,
) -> tuple[dict[str, Evidence], int]:
    """Judge each document's body, a chunk at a time, keeping its best chunk.

    A document is about its most relevant part, so the best chunk is the
    evidence -- and a document whose chunks run out before its end is partial,
    since the part left unread might have been the relevant one.
    """
    question = replace(asked, text=asked.text.format(query=query))
    levels = len(question.criteria) or None
    judged: dict[str, Evidence] = {}
    tokens = 0
    for candidate in pending:
        first = store.retrieve_document(candidate.key, max_chars=1)
        length = first.total if first.total is not None else 0
        windows = list(_windows(length, _section_starts(candidate.contents), chunk_chars))
        best: Answer | None = None
        best_p = -1.0
        asked_count = 0
        while windows and asked_count < max_chunks:
            start, end = windows.pop(0)
            text = (
                store.retrieve_document(candidate.key, offset=start, max_chars=end - start).content
                if end > start
                else ""
            )
            try:
                judgement = judge.judge(text, {"q": question})
                tokens += judgement.input_tokens
                answer = _answer(judgement, "q")
            except StateTooLarge as error:
                if end - start < 2 * min_chunk_chars:
                    candidate.failure = _failed(candidate, level, error)
                    break
                middle = start + (end - start) // 2
                windows[:0] = [(start, middle), (middle, end)]
                continue
            except JudgeError as error:
                candidate.failure = _failed(candidate, level, error)
                break
            asked_count += 1
            p = answer.as_probability(levels)
            if p > best_p:
                best, best_p = answer, p
        if candidate.failure is not None or best is None:
            continue
        judged[candidate.key] = Evidence(
            level, best, best_p, chunks=asked_count, partial=bool(windows)
        )
    return judged, tokens


def _section_starts(contents: str | None) -> list[int]:
    """Character offsets of a document's headings, from its ``!contents``."""
    if not contents:
        return []
    starts = []
    for line in contents.splitlines():
        if _OFFSETS.match(line.strip()):
            starts.append(int(line.split()[0]))
    return starts


def _windows(length: int, starts: Sequence[int], chunk_chars: int) -> Iterator[tuple[int, int]]:
    """Split ``[0, length)`` into chunks of at most ``chunk_chars``.

    On section boundaries where there are any -- consecutive sections share a
    chunk while they fit -- and at fixed widths inside a section too long for
    one, or across a document with no sections at all. An empty document is
    one empty chunk, so that it is still judged rather than silently skipped.
    """
    if length == 0:
        yield (0, 0)
        return
    bounds = sorted({0, length, *(s for s in starts if 0 < s < length)})
    start = end = 0
    for edge in bounds[1:]:
        if edge - start > chunk_chars:
            if end > start:
                yield (start, end)
                start = end
            while edge - start > chunk_chars:
                yield (start, start + chunk_chars)
                start += chunk_chars
        end = edge
    if start < length:
        yield (start, length)


__all__ = [
    "RULES",
    "TUNING_FORMAT",
    "TUNING_NAMES",
    "TUNING_PATH",
    "Answer",
    "Decision",
    "Evidence",
    "Judge",
    "JudgeError",
    "Judgement",
    "Kind",
    "Level",
    "LevelCounts",
    "LevelQuestions",
    "LevelTuning",
    "Match",
    "Question",
    "Requests",
    "Scoring",
    "Shape",
    "SmartSearchResult",
    "StateTooLarge",
    "Tuning",
    "Unjudged",
    "packaged_tuning",
    "refusals",
    "smart_search",
]
