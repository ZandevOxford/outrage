"""The smart search cascade, against a judge that reads for marker words.

The fake stands in for a System One model and answers by what the text it is
shown contains: ``MATCH`` is a confident yes, ``NEAR`` a near miss, ``HUGE`` is
refused as too large, ``BROKEN`` fails the request, and anything else is a
confident no. So each test says what a document holds at each level and
asserts on where the cascade stopped.

A Score question, the default, is answered with its mass split between the
bottom and top tiers, which reduces to exactly the Noul probability: the
cascade tests then mean the same whichever question set is asked.
"""

from __future__ import annotations

import json

import pytest

from outrage import messages, shipped, smartsearch
from outrage.errors import OutrageError, Refusal
from outrage.mounts import MountedStore
from outrage.smartsearch import (
    Answer,
    Evidence,
    JudgeError,
    Judgement,
    Requests,
    Scoring,
    StateTooLarge,
    Tuning,
    smart_search,
)
from outrage.store_sqlite import SqliteStore


class FakeJudge:
    def __init__(self, *, score: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.score = score

    def judge(self, state, questions):
        self.calls.append((state, dict(questions)))
        answers = {}
        for qid, question in questions.items():
            text = state + " " + " ".join(question.instructions.values())
            if "HUGE" in text:
                raise StateTooLarge("smart-search-test-too-large")
            if "BROKEN" in text:
                raise JudgeError("smart-search-test-broken", status=529)
            p = 0.97 if "MATCH" in text else 0.8 if "NEAR" in text else 0.03
            if self.score:
                answers[qid] = Answer(score=round(p * 3), probabilities=_spread(p), confidence=1.0)
            elif question.kind == "score":
                answers[qid] = Answer(score=3 * p, probabilities=(1 - p, 0.0, 0.0, p))
            else:
                answers[qid] = Answer(probability=p)
        return Judgement(answers, input_tokens=len(state) + len(questions))

    def judged(self, level):
        """The keys that were judged at a metadata level in the questions shape."""
        return [
            question.instructions["key"]
            for _, questions in self.calls
            for question in questions.values()
            if level in question.instructions
        ]


def _spread(p):
    top = round(p * 3)
    return tuple(1.0 if i == top else 0.0 for i in range(4))


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as opened:
        yield opened


def _put(store, key, body="nothing here", **meta):
    store.store_document(key, body)
    for name, value in meta.items():
        store.store_document(f"{key}/!{name}", value)


def test_a_title_decides_a_match_and_the_rest_cascade(store):
    _put(store, "d/yes", title="MATCH")
    _put(store, "d/no", title="unrelated", summary="unrelated")
    _put(store, "d/later", title="NEAR", summary="NEAR", body="MATCH in the body")
    judge = FakeJudge()

    result = smart_search(store, "d", "anything", judge)

    by_key = {m.key: m for m in result.matches}
    assert set(by_key) == {"d/yes", "d/later"}
    assert by_key["d/yes"].decided_at == "title"
    assert by_key["d/later"].decided_at in ("summary", "body")
    assert result.levels["title"].asked == 3
    assert result.levels["title"].yes == 1 and result.levels["title"].no == 0
    assert result.levels["summary"].no == 1
    assert judge.judged("summary") == ["d/later", "d/no"]


@pytest.mark.parametrize("level", ["title", "keywords"])
def test_a_label_can_count_for_a_document_but_never_against_it(store, level):
    _put(store, "d/generic", body="MATCH", **{level: "unrelated"})
    _put(store, "d/named", **{level: "MATCH"})

    result = smart_search(store, "d", "q", FakeJudge())

    by_key = {m.key: m for m in result.matches}
    assert by_key["d/generic"].decided_at == "body"
    assert by_key["d/named"].decided_at == level
    assert result.levels[level].no == 0


def test_a_label_can_rule_out_when_the_scoring_says_so(store):
    _put(store, "d/generic", title="unrelated", body="MATCH")

    result = smart_search(store, "d", "q", FakeJudge(), scoring=Scoring(supporting=frozenset()))

    assert result.matches == ()
    assert result.levels["title"].no == 1


def test_keywords_are_read_from_their_own_metadata(store):
    _put(store, "d/a", title="unrelated", keywords="NEAR", summary="NEAR")
    judge = FakeJudge()

    result = smart_search(store, "d", "q", judge)

    assert judge.judged("keywords") == ["d/a"]
    [match] = result.matches
    assert [e.level for e in match.evidence] == ["title", "keywords", "summary"]


def test_two_near_misses_add_up_to_a_match(store):
    _put(store, "d/a", title="NEAR", summary="NEAR", body="nothing")

    result = smart_search(store, "d", "q", FakeJudge())

    [match] = result.matches
    assert match.decision == "yes" and match.decided_at == "summary"
    assert [e.level for e in match.evidence] == ["title", "summary"]


def test_missing_metadata_is_unsure_and_goes_on_unchanged(store):
    _put(store, "d/bare", body="MATCH")

    result = smart_search(store, "d", "q", FakeJudge())

    assert result.levels["title"].missing == 1
    assert result.levels["summary"].missing == 1
    assert result.levels["contents"].missing == 1
    [match] = result.matches
    assert match.decided_at == "body"
    assert [e.level for e in match.evidence] == ["body"]


def test_a_level_reads_only_the_documents_still_pending(store):
    _put(store, "d/a", title="MATCH", summary="MATCH")
    _put(store, "d/b", title="NEAR", summary="unrelated")
    _put(store, "d/b/child", title="MATCH", summary="unrelated")

    judge = FakeJudge()
    smart_search(store, "d", "q", judge)

    assert judge.judged("summary") == ["d/b"]


def test_a_truncated_value_cannot_rule_a_document_out(store):
    _put(store, "d/long", title="unrelated " * 20, body="unrelated")

    result = smart_search(store, "d", "q", FakeJudge(), levels=["title"], value_chars=10)

    [match] = result.matches
    assert match.decision == "unsure"
    assert match.evidence[0].partial


def test_a_body_is_judged_by_its_best_chunk(store):
    body = "filler. " * 50 + "MATCH"
    _put(store, "d/a", body=body)
    judge = FakeJudge()

    result = smart_search(store, "d", "q", judge, levels=["body"], chunk_chars=100)

    [match] = result.matches
    assert match.decided_at == "body"
    assert match.evidence[0].chunks == len(judge.calls) > 1
    assert "".join(state for state, _ in judge.calls) == body


def test_a_body_cut_short_is_partial_and_kept(store):
    _put(store, "d/a", body="filler. " * 50)

    result = smart_search(
        store, "d", "q", FakeJudge(), levels=["body"], chunk_chars=100, max_chunks=2
    )

    [match] = result.matches
    assert match.decision == "unsure" and match.evidence[0].partial


def test_body_chunks_follow_the_contents_sections(store):
    body = "# One\n" + "a" * 40 + "\n# Two\n" + "b" * 40 + "\n# Three\n" + "c" * 40 + "\n"
    two, three = body.index("# Two"), body.index("# Three")
    contents = f"# One\n0 0 1\n\n# Two\n{two} {two} 3\n\n# Three\n{three} {three} 5\n"
    _put(store, "d/a", body=body, contents=contents)
    judge = FakeJudge()

    carry_on = Scoring(yes=1.0, no=0.0)
    smart_search(
        store, "d", "q", judge, levels=["contents", "body"], chunk_chars=60, scoring=carry_on
    )

    contents_state = judge.calls[0][1]["d0"].instructions["contents"]
    assert contents_state == "# One\n# Two\n# Three"
    assert [state for state, _ in judge.calls[1:]] == [
        body[:two],
        body[two:three],
        body[three:],
    ]


def test_windows_split_a_section_too_long_for_one_chunk():
    assert list(smartsearch._windows(250, [], 100)) == [(0, 100), (100, 200), (200, 250)]
    assert list(smartsearch._windows(100, [10, 20, 90], 50)) == [(0, 20), (20, 70), (70, 100)]
    assert list(smartsearch._windows(0, [], 100)) == [(0, 0)]


def test_a_chunk_refused_as_too_large_is_halved(store):
    body = "a" * 3000 + "HUGE" + "b" * 3000 + "MATCH"
    _put(store, "d/a", body=body)
    judge = FakeJudge()

    result = smart_search(store, "d", "q", judge, levels=["body"])

    # Halving isolates the marker in a chunk the fake refuses whatever its
    # size, so the document ends unjudged -- after the halving was tried.
    [failure] = result.unjudged
    assert failure.code == "smart-search-test-too-large"
    assert len(judge.calls) > 2


def test_a_failed_request_reports_its_documents_unjudged(store):
    _put(store, "d/a", title="NEAR", summary="BROKEN")
    _put(store, "d/b", title="NEAR", summary="NEAR")

    result = smart_search(store, "d", "q", FakeJudge(), batch_size=1)

    [failure] = result.unjudged
    assert failure.key == "d/a" and failure.level == "summary"
    assert failure.details == {"status": 529}
    assert [e.level for e in failure.evidence] == ["title"]
    assert [m.key for m in result.matches] == ["d/b"]
    assert result.levels["summary"].unjudged == 1


def test_a_batch_that_fails_takes_every_document_in_it(store):
    _put(store, "d/a", title="BROKEN")
    _put(store, "d/b", title="MATCH")

    result = smart_search(store, "d", "q", FakeJudge())

    assert sorted(u.key for u in result.unjudged) == ["d/a", "d/b"]
    assert result.matches == ()


def test_the_state_shape_puts_the_value_in_the_state(store):
    _put(store, "d/a", title="MATCH")
    judge = FakeJudge()

    smart_search(store, "d", "cats", judge, levels=["title"], shapes={"title": "state"})

    [(state, questions)] = judge.calls
    assert state == "MATCH"
    assert questions["q"].text.endswith("cats")


def test_the_questions_shape_puts_the_query_in_the_state(store):
    _put(store, "d/a", title="MATCH")
    _put(store, "d/b", title="MATCH")
    judge = FakeJudge()

    smart_search(store, "d", "cats", judge, levels=["title"])

    [(state, questions)] = judge.calls
    assert state == "cats"
    assert [q.instructions for q in questions.values()] == [
        {"key": "d/a", "title": "MATCH"},
        {"key": "d/b", "title": "MATCH"},
    ]


def test_score_questions_reduce_to_a_probability(store):
    _put(store, "d/a", title="MATCH")
    _put(store, "d/b", title="unrelated")

    result = smart_search(
        store, "d", "q", FakeJudge(score=True), questions=smartsearch.SCORE_QUESTIONS
    )

    assert [m.key for m in result.matches] == ["d/a"]
    assert result.matches[0].evidence[0].probability == 1.0


def test_an_answer_scales_its_expected_level():
    assert Answer(probabilities=(0.0, 0.5, 0.5, 0.0)).as_probability() == pytest.approx(0.5)
    assert Answer(score=2).as_probability(3) == 1.0
    assert Answer(probability=0.3).as_probability() == 0.3


def test_partial_evidence_counts_for_but_never_against():
    scoring = Scoring()
    against = Evidence("title", Answer(probability=0.01), 0.01, partial=True)
    in_favour = Evidence("title", Answer(probability=0.99), 0.99, partial=True)
    assert scoring.combine([against]) == 0.5
    assert scoring.combine([in_favour]) > 0.5


def test_matches_are_best_first_and_the_slice_pages(store):
    for name, summary in [("a", "NEAR"), ("b", "MATCH"), ("c", "unrelated"), ("d", "MATCH")]:
        _put(store, f"s/{name}", summary=summary)

    first = smart_search(store, "s", "q", FakeJudge(), levels=["summary"], limit=2)
    assert (first.documents, first.total, first.next_cursor) == (2, 4, "s/b")
    assert [m.key for m in first.matches] == ["s/b", "s/a"]

    second = smart_search(store, "s", "q", FakeJudge(), levels=["summary"], after="s/b")
    assert [m.key for m in second.matches] == ["s/d"]
    assert second.next_cursor is None


def test_every_refusal_is_reported(store):
    found = smartsearch.refusals(
        " ", ["title", "nope", "title", "body"], {"body": "questions", "title": "sideways"}
    )
    assert [r.code for r in found] == [
        "smart-search-query-empty",
        "smart-search-level-unknown",
        "smart-search-level-repeated",
        "smart-search-body-shape",
        "smart-search-shape-unknown",
    ]
    for refusal in found:
        assert messages.render(refusal.as_error())

    with pytest.raises(OutrageError) as raised:
        smart_search(store, None, "", FakeJudge())
    assert raised.value.code == "smart-search-query-empty"


def test_a_search_crosses_mounts(tmp_path):
    with SqliteStore(tmp_path / "inner") as inner, SqliteStore(tmp_path / "ref") as ref:
        _put(inner, "notes/a", title="MATCH")
        _put(ref, "b", title="MATCH")
        table = MountedStore({"": inner, "ref": ref})

        result = smart_search(table, None, "q", FakeJudge(), levels=["title"])

        assert [m.key for m in result.matches] == ["notes/a", "ref/b"]


def test_score_questions_are_asked_by_default(store):
    _put(store, "d/a", title="MATCH")
    judge = FakeJudge()

    smart_search(store, "d", "q", judge)

    assert {q.kind for _, questions in judge.calls for q in questions.values()} == {"score"}


# -- The tuning file ---------------------------------------------------------


def _tuning_data():
    return json.loads(shipped.tree().joinpath(*smartsearch.TUNING_PATH).read_text())


def test_the_packaged_tuning_loads():
    tuning, found = Tuning.read_file()

    assert found == []
    assert tuning.names == smartsearch.LEVELS
    assert tuning.source.endswith("tuning.json")


def test_the_packaged_tuning_is_todays_constants():
    # Scaffolding for the move onto the file, and removed with the constants.
    tuning = Tuning.load()

    for level in tuning.levels:
        assert level.questions == smartsearch.SCORE_QUESTIONS[level.name]
        assert level.shape == smartsearch.DEFAULT_SHAPES[level.name]
    assert tuning.scoring == Scoring()
    assert tuning.requests == Requests(
        limit=smartsearch.DEFAULT_LIMIT,
        batch_size=smartsearch.DEFAULT_BATCH_SIZE,
        value_chars=smartsearch.DEFAULT_VALUE_CHARS,
        chunk_chars=smartsearch.DEFAULT_CHUNK_CHARS,
        max_chunks=smartsearch.DEFAULT_MAX_CHUNKS,
        min_chunk_chars=smartsearch.MIN_CHUNK_CHARS,
    )


def test_the_readme_describes_every_name_the_tuning_accepts():
    readme = shipped.document_text("smart-search", "readme")

    assert [name for name in smartsearch.TUNING_NAMES if f"`{name}`" not in readme] == []


def test_every_tuning_refusal_is_reported_at_once():
    data = _tuning_data()
    data["format"] = 2
    data["question"]["criteria"] = ["only one"]
    data["levels"][0]["weigth"] = 1
    del data["levels"][1]["what"]
    data["levels"][2]["name"] = "title"
    data["levels"][3]["kind"] = "body"
    data["levels"][4]["shape"] = "questions"
    data["levels"][4]["question"] = {"state": "no query here"}
    data["scoring"]["no"] = 0.9
    data["requests"]["min_chunk_chars"] = 10**6

    tuning, found = Tuning.read(data, "edited.json")

    assert tuning is None
    assert [(r.code, r.details.get("where")) for r in found] == [
        ("smart-search-tuning-value", "format"),
        ("smart-search-tuning-name-unknown", "levels[0]"),
        ("smart-search-tuning-value", "question.criteria"),
        ("smart-search-tuning-name-missing", "levels[1]"),
        ("smart-search-tuning-value", "levels[2].name"),
        ("smart-search-tuning-value", "levels[3].shape"),
        ("smart-search-tuning-value", "levels[4].kind"),
        ("smart-search-tuning-value", "levels[4].shape"),
        ("smart-search-tuning-value", "levels[4].question.state"),
        ("smart-search-tuning-value", "scoring.no"),
        ("smart-search-tuning-value", "requests.min_chunk_chars"),
    ]
    for refusal in found:
        assert refusal.details["source"] == "edited.json"
        assert messages.render(refusal.as_error())


def test_a_missing_section_is_one_refusal():
    data = _tuning_data()
    del data["scoring"]

    _, found = Tuning.read(data, "t")

    assert [(r.code, r.details["name"]) for r in found] == [
        ("smart-search-tuning-name-missing", "scoring")
    ]


@pytest.mark.parametrize("section", ["question", "levels", "scoring", "requests"])
def test_a_null_section_is_refused_rather_than_taken_as_missing(section):
    data = _tuning_data()
    data[section] = None

    tuning, found = Tuning.read(data, "t")

    assert tuning is None
    assert [(r.code, r.details["where"]) for r in found][:1] == [
        ("smart-search-tuning-value", section)
    ]


def test_a_template_placeholder_must_be_a_plain_name():
    data = _tuning_data()
    data["question"]["state"] = "{what!r} for {query:>5}"

    _, found = Tuning.read(data, "t")

    assert [(r.code, r.details["where"]) for r in found] == [
        ("smart-search-tuning-value", "question.state")
    ]


def test_a_file_that_cannot_be_read_or_parsed_is_refused(tmp_path):
    missing = tmp_path / "absent.json"
    broken = tmp_path / "broken.json"
    broken.write_text("{")

    assert [r.code for r in Tuning.read_file(missing)[1]] == ["smart-search-tuning-unreadable"]
    assert [r.code for r in Tuning.read_file(broken)[1]] == ["smart-search-tuning-not-json"]
    with pytest.raises(OutrageError) as raised:
        Tuning.load(broken)
    assert str(broken) in messages.render(raised.value)


def test_a_level_may_override_the_question_and_read_other_metadata():
    data = _tuning_data()
    data["levels"].insert(
        1,
        {
            "name": "tags",
            "meta": "labels",
            "kind": "value",
            "what": "tags {braced}",
            "shape": "state",
            "weight": 0.5,
            "question": {"kind": "noul", "state": "Tags {{x}}: {what}. Relevant to {query}?"},
            "note": "ignored",
        },
    )

    tuning, found = Tuning.read(data, "t")

    assert found == []
    tags = tuning.level("tags")
    assert (tags.meta, tags.shape, tags.supporting) == ("labels", "state", False)
    assert tags.questions.state.kind == "noul"
    assert tags.questions.state.criteria == ()
    assert tags.questions.state.text.format(query="Q") == "Tags {x}: tags {braced}. Relevant to Q?"
    assert tags.questions.questions.kind == "noul"
    assert tuning.level("title").questions.state.kind == "score"
    assert tuning.scoring.weights["tags"] == 0.5
    assert tuning.level("body").meta is None


def _broken_packaged_tuning(monkeypatch):
    refusal = Refusal(
        "smart-search-tuning-value",
        overridable=False,
        source="tuning.json",
        where="scoring.no",
        expected="below scoring.yes, 0.8",
    )
    monkeypatch.setattr(smartsearch, "packaged_tuning", lambda: (None, (refusal,)))


def test_a_broken_packaged_tuning_is_among_the_refusals(monkeypatch, store):
    _broken_packaged_tuning(monkeypatch)

    found = smartsearch.refusals("", ["title"])

    assert [r.code for r in found] == ["smart-search-tuning-value", "smart-search-query-empty"]
    with pytest.raises(OutrageError) as raised:
        smart_search(store, None, "q", FakeJudge())
    assert "scoring.no" in messages.render(raised.value)


def test_the_cascade_follows_the_tuning_it_is_given(store):
    data = _tuning_data()
    data["levels"] = [
        {
            "name": "tags",
            "meta": "labels",
            "kind": "value",
            "what": "tags",
            "shape": "questions",
            "weight": 1.0,
        },
        {"name": "text", "kind": "body", "what": "text", "shape": "state", "weight": 1.0},
    ]
    data["requests"]["limit"] = 2
    tuning, found = Tuning.read(data, "t")
    assert found == []
    _put(store, "s/a", "nothing", labels="MATCH")
    _put(store, "s/b", "a MATCH in the body", labels="unrelated", title="MATCH")
    _put(store, "s/c", "MATCH")

    result = smart_search(store, "s", "q", FakeJudge(), tuning=tuning)

    assert (result.documents, result.next_cursor) == (2, "s/b"), "the tuning's limit"
    assert list(result.levels) == ["tags", "text"]
    assert [(m.key, m.decided_at) for m in result.matches] == [("s/a", "tags")]
    assert result.levels["tags"].no == 1, "s/b's title is not a level of this tuning"
    assert smartsearch.refusals("q", ["title"], tuning=tuning)[0].code == (
        "smart-search-level-unknown"
    )


def test_a_missing_field_is_reported_once_as_missing():
    data = _tuning_data()
    del data["levels"][0]["weight"]
    del data["scoring"]["clamp"]
    del data["requests"]["limit"]

    _, found = Tuning.read(data, "t")

    assert [(r.code, r.details["where"], r.details["name"]) for r in found] == [
        ("smart-search-tuning-name-missing", "levels[0]", "weight"),
        ("smart-search-tuning-name-missing", "scoring", "clamp"),
        ("smart-search-tuning-name-missing", "requests", "limit"),
    ]
