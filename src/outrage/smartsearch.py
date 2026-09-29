"""Screen a slice of documents against a query with a System One model.

The cascade the ``outrage-search`` agent follows, moved out of an agent's
context and into the library: every document in the slice is judged on its
``!title`` first, and only the ones that level leaves unsure go on to its
``!keywords``, its ``!summary``, then its ``!contents``, then its body. What comes back is every
document not ruled out, best first. The calling agent reads none of it.

**The judging is not done here.** A :class:`Judge` answers questions about a
piece of state -- the protocol System One models speak -- and this module
decides what to ask, of which documents, and what the answers add up to. So the
suite runs against a fake, and a second model or a local server is a different
judge rather than a different cascade.

Three things here are expected to change as the cascade is measured, and each
is kept in one place so that tuning it touches nothing else:

* **the question asked at each level** is data, :data:`SCORE_QUESTIONS` by
  default and :data:`NOUL_QUESTIONS` as the alternative, since what a title can
  show is not what a body can;
* **which way round** a level is asked -- the query as the state and many
  documents as the questions, or each document as the state and the query as
  its one question -- is a :data:`Shape` per level, and the body is always the
  second, being too long to sit in a question;
* **how the per-level answers become a decision** is :class:`Scoring`, one
  object over the evidence, which the result keeps whole so that a tuning run
  can re-score without asking the model again.

Two rules carry over from the agent unchanged. **Missing metadata is unsure,
never no**: a document without a summary has told the cascade nothing, so it
goes on to the next level as it was. And **a partial value cannot justify a
no**: a truncated title, or a body judged in fewer chunks than it has, can
count for a document but never against it.

A third rule, from measuring: **a title or keywords can count only for a
document**. Both are written to label a document rather than to describe it,
so a short or generic one -- an API page titled by its module name, a README
titled with the project's -- is uninformative, and a yes-or-no question has no
answer for that but a low one. Counted against, a single such answer ruled out
the best document for a query. :attr:`Scoring.supporting` holds the rule.

Content leaves the machine whenever the judge is a remote service, which is
the front ends' to say; this module cannot tell one judge from another.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol

from . import keys
from .errors import OutrageError, Refusal
from .store import BoundedSubtree, KeyRange, Store

#: What a level judges: a metadata value by its name, or the document itself.
Level = Literal["title", "keywords", "summary", "contents", "body"]

#: The default cascade, cheapest and most telling first.
#:
#: Keywords beside the title, being as short and written for the same purpose.
#: Summary before contents because a summary is the shorter of the two and says
#: more about what a document is for; a contents index is headings, which name
#: what is in a document without saying what it concludes.
LEVELS: tuple[Level, ...] = ("title", "keywords", "summary", "contents", "body")

#: Which way round a level is asked.
#:
#: ``"questions"`` puts the query in the state and one document in each question,
#: so one request judges many documents. ``"state"`` puts the document in the
#: state and the query in its one question, a request per document. Both are
#: measured; if one wins everywhere the other goes.
Shape = Literal["questions", "state"]

#: Where a level leaves a document: ruled in, ruled out, or carried to the next.
Decision = Literal["yes", "no", "unsure"]

#: A starting point: many short values to a request, and a body on its own.
DEFAULT_SHAPES: Mapping[Level, Shape] = {
    "title": "questions",
    "keywords": "questions",
    "summary": "questions",
    "contents": "questions",
    "body": "state",
}

#: Documents in one slice, which is what bounds a result: the server keeps no
#: state, so a result for its slice cannot itself be paged.
DEFAULT_LIMIT = 100

#: Documents judged in one ``"questions"`` request. Each question is evaluated
#: in isolation, so this bounds the request rather than what the model weighs.
DEFAULT_BATCH_SIZE = 50

#: Longest metadata value read for judging. A longer one is judged on its
#: first part and marked partial, so it cannot rule a document out.
DEFAULT_VALUE_CHARS = 8000

#: Characters of body in one state. Jev takes 32k tokens for the state and the
#: longest question together, and English runs near four characters a token, so
#: this leaves room for the question and for text that tokenises badly. A chunk
#: the model still refuses as too large is halved and asked again.
DEFAULT_CHUNK_CHARS = 60000

#: Body chunks judged per document before the rest is left unread. A document
#: cut short this way is partial, so it can be kept but not ruled out.
DEFAULT_MAX_CHUNKS = 16

#: Below this, halving a chunk the model refuses as too large stops, and the
#: document is reported unjudged rather than split into fragments.
MIN_CHUNK_CHARS = 1000


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


def _noul(level: str, what: str) -> LevelQuestions:
    return LevelQuestions(
        questions=Question(
            "noul",
            f"The state is a search query. `{level}` is the {what} of the stored "
            f"document at `key`. Is that document likely to be relevant to the query?",
        ),
        state=Question(
            "noul",
            f"The state is the {what} of one stored document. Is that document "
            f"likely to be relevant to this search query: {{query}}",
        ),
    )


_WHAT: Mapping[Level, str] = {
    "title": "title",
    "keywords": "keywords",
    "summary": "summary",
    "contents": "table of contents (its headings)",
    "body": "text, or one part of it,",
}

#: The alternative question at each level: a single probability of relevance.
NOUL_QUESTIONS: Mapping[Level, LevelQuestions] = {
    level: _noul(level, what) for level, what in _WHAT.items()
}

_CRITERIA = (
    "no relevance to the query topic",
    "relevant to a related topic",
    "relevant to the query topic",
    "directly addresses the query",
)


def _score(level: str, what: str) -> LevelQuestions:
    noul = _noul(level, what)
    return LevelQuestions(
        questions=replace(noul.questions, kind="score", criteria=_CRITERIA),
        state=replace(noul.state, kind="score", criteria=_CRITERIA),
    )


#: The default question at each level: four ordered levels of relevance.
#:
#: Better than Noul at most levels in the first measurement, and in John's own
#: testing: the tiers say what kind of match to look for, where a single
#: probability leaves the model to decide what "relevant" means. The same
#: criteria everywhere for now; tuning is what says whether a level wants its own.
SCORE_QUESTIONS: Mapping[Level, LevelQuestions] = {
    level: _score(level, what) for level, what in _WHAT.items()
}


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

    The weights and thresholds here are a starting point and not a result:
    measuring the cascade against labelled queries is what sets them. Other
    rules the measuring may prefer -- the strongest level rather than the sum,
    a small fitted model over the per-level answers, or the last level alone
    with the earlier ones only pruning -- are each a different :meth:`combine`.
    """

    weights: Mapping[Level, float] = field(
        default_factory=lambda: {
            "title": 0.6,
            "keywords": 0.6,
            "summary": 0.8,
            "contents": 0.6,
            "body": 1.0,
        }
    )
    supporting: frozenset[Level] = frozenset({"title", "keywords"})
    """Levels whose evidence can count for a document and never against it, as
    partial evidence cannot. A label too generic to say anything gets a low
    answer, not an unsure one, and must not rule the document out."""
    yes: float = 0.8
    """At or above this, a document is decided a match and stops cascading."""
    no: float = 0.2
    """At or below this, a document is ruled out."""

    def combine(self, evidence: Sequence[Evidence]) -> float:
        """The probability that a document matches, on everything seen so far."""
        total = 0.0
        for item in evidence:
            weight = self.weights.get(item.level, 1.0)
            if item.answer.confidence is not None:
                weight *= item.answer.confidence
            contribution = weight * _logit(item.probability)
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


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


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


def refusals(
    query: str,
    levels: Sequence[str] = LEVELS,
    shapes: Mapping[str, str] | None = None,
) -> list[Refusal]:
    """Every reason these arguments cannot be searched with, at once."""
    found: list[Refusal] = []
    if not query.strip():
        found.append(Refusal("smart-search-query-empty", overridable=False))
    if not levels:
        found.append(Refusal("smart-search-levels-empty", overridable=False))
    for level in levels:
        if level not in LEVELS:
            found.append(
                Refusal("smart-search-level-unknown", overridable=False, level=level, known=LEVELS)
            )
    repeated = sorted({level for level in levels if list(levels).count(level) > 1})
    for level in repeated:
        found.append(Refusal("smart-search-level-repeated", overridable=False, level=level))
    for level, shape in (shapes or {}).items():
        if shape not in ("questions", "state"):
            found.append(
                Refusal("smart-search-shape-unknown", overridable=False, level=level, shape=shape)
            )
        elif level == "body" and shape != "state":
            found.append(Refusal("smart-search-body-shape", overridable=False, shape=shape))
    return found


def smart_search(
    store: Store,
    key: str | None,
    query: str,
    judge: Judge,
    *,
    depth: int | None = None,
    limit: int = DEFAULT_LIMIT,
    after: str | None = None,
    levels: Sequence[Level] = LEVELS,
    shapes: Mapping[Level, Shape] | None = None,
    questions: Mapping[Level, LevelQuestions] = SCORE_QUESTIONS,
    scoring: Scoring | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    value_chars: int = DEFAULT_VALUE_CHARS,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> SmartSearchResult:
    """Screen one slice of the documents under ``key`` against ``query``.

    The slice is a page of the subtree's documents, ``limit`` of them after
    ``after``, exactly as ``get_documents`` would page it. Each is judged at
    the first of ``levels`` and carried to the next only while the combined
    evidence leaves it unsure.

    Raises the first of :func:`refusals` as an error; a front end wanting
    every reason calls that first. A failed request never
    raises: its documents are reported in :attr:`SmartSearchResult.unjudged`.
    """
    problems = refusals(query, levels, shapes)
    if problems:
        raise problems[0].as_error()
    shapes = {**DEFAULT_SHAPES, **(shapes or {})}
    scoring = scoring or Scoring()
    subtree = BoundedSubtree(key, depth)

    page = store.get_documents(subtree, cursor=after, limit=limit, max_chars=1)
    candidates = [_Candidate(excerpt.key) for excerpt in page.items]
    unavailable = set(page.unavailable)
    counts: dict[Level, LevelCounts] = {level: LevelCounts() for level in levels}
    tokens = 0

    for level in levels:
        pending = [c for c in candidates if c.decision == "unsure" and c.failure is None]
        if not pending:
            break
        tally = counts[level]
        if level == "body":
            judged, spent = _judge_bodies(
                store, pending, query, judge, questions[level].state, chunk_chars, max_chunks
            )
        else:
            values, missed = _values(store, subtree, level, pending, value_chars)
            unavailable.update(missed)
            if level == "contents":
                for candidate in pending:
                    if candidate.key in values:
                        candidate.contents = values[candidate.key][0]
                values = {k: (_headings_only(v), partial) for k, (v, partial) in values.items()}
            tally.missing += sum(1 for c in pending if c.key not in values)
            present = [c for c in pending if c.key in values]
            judged, spent = _judge_values(
                present, values, level, query, judge, questions[level], shapes[level], batch_size
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
    level: Level,
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
    suffix = keys.META_PREFIX + level
    stretch = KeyRange(after_inclusive=pending[0].key, final_subtree=pending[-1].key)
    values: dict[str, tuple[str, bool]] = {}
    missed: set[str] = set()
    cursor: str | None = None
    while True:
        page = store.get_documents(
            subtree, key_range=stretch, meta_name=level, cursor=cursor, max_chars=value_chars
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
    query: str,
    judge: Judge,
    asked: Question,
    chunk_chars: int,
    max_chunks: int,
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
                if end - start < 2 * MIN_CHUNK_CHARS:
                    candidate.failure = _failed(candidate, "body", error)
                    break
                middle = start + (end - start) // 2
                windows[:0] = [(start, middle), (middle, end)]
                continue
            except JudgeError as error:
                candidate.failure = _failed(candidate, "body", error)
                break
            asked_count += 1
            p = answer.as_probability(levels)
            if p > best_p:
                best, best_p = answer, p
        if candidate.failure is not None or best is None:
            continue
        judged[candidate.key] = Evidence(
            "body", best, best_p, chunks=asked_count, partial=bool(windows)
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
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_CHUNK_CHARS",
    "DEFAULT_LIMIT",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_SHAPES",
    "DEFAULT_VALUE_CHARS",
    "LEVELS",
    "MIN_CHUNK_CHARS",
    "NOUL_QUESTIONS",
    "SCORE_QUESTIONS",
    "Answer",
    "Decision",
    "Evidence",
    "Judge",
    "JudgeError",
    "Judgement",
    "Level",
    "LevelCounts",
    "LevelQuestions",
    "Match",
    "Question",
    "Scoring",
    "Shape",
    "SmartSearchResult",
    "StateTooLarge",
    "Unjudged",
    "refusals",
    "smart_search",
]
