import pytest

from clip_pipeline.highlights import (
    build_windows,
    parse_moments,
    select_heuristic,
    select_with_llm,
)
from clip_pipeline.models import Moment, Segment


def segs(*items):
    return [Segment(start=a, end=b, text=t) for a, b, t in items]


def test_build_windows_respects_duration_bounds():
    segments = segs((0, 5, "a"), (5, 10, "b"), (10, 15, "c"), (15, 20, "d"))
    windows = build_windows(segments, min_len=8, max_len=12)
    assert windows
    for w in windows:
        assert 8 <= w.end - w.start <= 12


def test_heuristic_prefers_keyword_window():
    segments = segs(
        (0, 10, "fala comum do dia a dia sem nada demais aqui"),
        (10, 20, "uau isso e inacreditavel! olha so que incrivel!"),
        (20, 30, "mais uma fala comum seguindo o assunto normal"),
    )
    chosen = select_heuristic(segments, count=1, min_len=8, max_len=12)
    assert len(chosen) == 1
    assert 10 <= chosen[0].start < 20


def test_heuristic_windows_do_not_overlap():
    segments = segs(*[(i * 5, i * 5 + 5, f"uau incrivel {i}!") for i in range(12)])
    chosen = select_heuristic(segments, count=3, min_len=10, max_len=15)
    assert len(chosen) == 3
    for a in chosen:
        for b in chosen:
            if a is b:
                continue
            assert a.end <= b.start or b.end <= a.start


def test_parse_moments_accepts_json_with_surrounding_text():
    text = 'Aqui esta:\n```json\n[{"start": 5, "end": 18, "reason": "gancho forte"}]\n```'
    moments = parse_moments(text)
    assert moments == [Moment(start=5.0, end=18.0, reason="gancho forte")]


def test_parse_moments_rejects_invalid():
    with pytest.raises(ValueError):
        parse_moments("sem json aqui")
    with pytest.raises(ValueError):
        parse_moments('[{"start": 10, "end": 5}]')


def test_parse_moments_truncates_overlong_window():
    moments = parse_moments('[{"start": 0, "end": 60, "reason": "x"}]', max_len=20)
    assert moments[0].end == 20.0


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessages:
    def create(self, **kwargs):
        assert kwargs["messages"][0]["role"] == "user"
        assert "[0.0 -> 5.0]" in kwargs["messages"][0]["content"]

        class Resp:
            content = [_FakeBlock('[{"start": 0, "end": 15, "reason": "melhor trecho"}]')]

        return Resp()


class _FakeClient:
    messages = _FakeMessages()


def test_select_with_llm_uses_client_and_parses():
    segments = segs((0, 5, "ola"), (5, 10, "mundo"))
    moments = select_with_llm(segments, count=1, client=_FakeClient(), model="qualquer")
    assert len(moments) == 1
    assert moments[0].reason == "melhor trecho"
