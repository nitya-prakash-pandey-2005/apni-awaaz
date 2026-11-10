"""GnaniGate unit tests: it serialises calls and retries only a rate limit (429), a bounded number of times."""

import asyncio

import pytest
from voice_core.gnani import GnaniError

from awaaz import gate as gate_mod
from awaaz.gate import GnaniGate


@pytest.fixture
def sleeps(monkeypatch):
    """Record backoff delays instead of waiting them out."""
    seen: list[float] = []

    async def no_wait(s):
        seen.append(s)

    monkeypatch.setattr(gate_mod.asyncio, "sleep", no_wait)
    return seen


async def test_a_non_429_error_is_raised_at_once(sleeps):
    calls = []

    async def server_error():
        calls.append(1)
        raise GnaniError(500, "internal error")

    with pytest.raises(GnaniError) as e:
        await GnaniGate().wrap(server_error)()
    assert e.value.status == 500 and len(calls) == 1 and sleeps == []


async def test_a_429_that_never_clears_gives_up_after_the_retries(sleeps):
    calls = []

    async def busy():
        calls.append(1)
        raise GnaniError(429, "RATE_LIMITED")

    with pytest.raises(GnaniError) as e:
        await GnaniGate(retries=2, backoff=(0.5, 1.5)).wrap(busy)()
    assert e.value.status == 429 and len(calls) == 3 and sleeps == [0.5, 1.5]


async def test_backoff_repeats_its_last_delay(sleeps):
    n = 0

    async def flaky():
        nonlocal n
        n += 1
        if n < 4:
            raise GnaniError(429, "RATE_LIMITED")
        return "ok"

    assert await GnaniGate(retries=3, backoff=(0.5, 1.5)).wrap(flaky)() == "ok"
    assert sleeps == [0.5, 1.5, 1.5]


async def test_other_exceptions_pass_through_without_retry(sleeps):
    calls = []

    async def broken():
        calls.append(1)
        raise ValueError("bad audio")

    with pytest.raises(ValueError):
        await GnaniGate().wrap(broken)()
    assert len(calls) == 1 and sleeps == []


async def test_wrapped_calls_never_overlap_and_keep_their_arguments():
    active = peak = 0

    async def call(x, *, y):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return x + y

    gated = GnaniGate().wrap(call)
    assert await asyncio.gather(*(gated(i, y=1) for i in range(4))) == [1, 2, 3, 4]
    assert peak == 1 and gated.__name__ == "call"


async def test_one_gate_serialises_different_functions():
    order = []

    def make(name):
        async def fn():
            order.append(f"{name}-start")
            await asyncio.sleep(0.01)
            order.append(f"{name}-end")
        return fn

    g = GnaniGate()
    await asyncio.gather(g.wrap(make("clone"))(), g.wrap(make("timbre"))())
    assert order in (["clone-start", "clone-end", "timbre-start", "timbre-end"],
                     ["timbre-start", "timbre-end", "clone-start", "clone-end"])
