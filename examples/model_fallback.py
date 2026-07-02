"""
Resilient model call — health-aware fallback with a time-to-first-token watchdog.

A representative excerpt of the layer that wraps every model call. The production
version adds per-provider error mapping, cost metering against the budget router,
and full tracing; this is trimmed to the parts worth discussing — how one call
survives a provider failing, stays cheap, and never silently hangs.

Design decisions worth defending:

  - Three failure classes, handled differently:
      * RETRYABLE   (429 / 5xx / timeout) — brief same-model retry with backoff,
                    then fall through the chain.
      * TERMINAL    (400 / 401 / 403 / 422 — bad request / content rejected) — the
                    prompt is the problem, so every model rejects it identically;
                    ABORT the whole call instead of burning the chain.
      * INCOMPATIBLE (model can't accept the request's tool definitions) — skip to
                    the next model; it's a routing miss, not a failure.
  - A rate-limited model is put in an escalating cooldown and PREEMPTIVELY skipped
    on later calls, so we don't keep re-hitting a wall.
  - A time-to-first-token watchdog bounds only the FIRST token of each attempt. A
    model that stalls and emits nothing trips it and we fall over — safe, because
    nothing was yielded yet (no duplicate output). Once a real stream starts it
    runs unbounded (a longer outer timeout backstops a rare mid-stream stall).
  - If the whole chain is exhausted on recoverable errors, degrade gracefully (a
    usable message) rather than crash the run group. The configured chain ends
    on a self-hosted model (a config invariant, not enforced here), so "every
    hosted provider is unhappy" degrades to "slower but up," not "down."
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

RETRYABLE = {429, 500, 502, 503, 504}          # transient — retry, then fall through
TERMINAL = {400, 401, 403, 404, 422}           # the request is the problem — abort
TTFT_TIMEOUT_S = 90.0                          # bound ONLY the first token
COOLDOWN_BASE_S = 60.0                          # escalates 60 -> 120 -> 180 ...
COOLDOWN_CAP_S = 300.0                          # ... capped at 300


class ProviderError(Exception):
    def __init__(self, status: int, message: str = ""):
        super().__init__(f"{status} {message}".strip())
        self.status = status


class ToolsUnsupported(Exception):
    """Model can't accept the request's tool definitions — skip, don't fail."""


@dataclass
class Result:
    text: str
    model: str                 # which model actually served the request
    fell_back: bool            # did we leave the primary?
    degraded: bool = False     # whole chain exhausted -> graceful message
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: list[str] = field(default_factory=list)   # ["model:429", "model:ttft", ...]


class HealthTracker:
    """Records rate-limited models and cools them down so future calls skip them.
    Escalating cooldown: 60s -> 120s -> 180s -> ... capped at 300s."""

    def __init__(self) -> None:
        self._cooldown_until: dict[str, float] = {}
        self._strikes: dict[str, int] = {}

    def is_healthy(self, model: str) -> bool:
        until = self._cooldown_until.get(model)
        if until is None:
            return True
        if time.monotonic() >= until:               # cooled off — clear it
            self._cooldown_until.pop(model, None)
            self._strikes.pop(model, None)
            return True
        return False

    def mark_rate_limited(self, model: str) -> float:
        n = self._strikes.get(model, 0) + 1
        self._strikes[model] = n
        cooldown = min(COOLDOWN_BASE_S * n, COOLDOWN_CAP_S)
        self._cooldown_until[model] = time.monotonic() + cooldown
        return cooldown


health = HealthTracker()


def _backoff(attempt: int) -> float:
    return min(0.5 * (2 ** attempt), 4.0)           # 0.5s, 1s, 2s, ... capped at 4s


async def _stream_once(model, prompt, stream):
    """One attempt. The TTFT watchdog bounds ONLY the first chunk; once tokens
    flow it runs unbounded (the outer pipeline timeout backstops a mid-stream stall).
    Raises asyncio.TimeoutError if no first token arrives in time. The generator is
    closed on every exit — including the timeout — so a stalled stream's underlying
    connection is released deterministically rather than left to GC."""
    agen = stream(model, prompt).__aiter__()
    try:
        first = await asyncio.wait_for(agen.__anext__(), timeout=TTFT_TIMEOUT_S)
        chunks = [first]
        async for chunk in agen:                      # unbounded after first token
            chunks.append(chunk)
    finally:
        await agen.aclose()
    text = "".join(c.text for c in chunks)
    last = chunks[-1]
    return text, getattr(last, "input_tokens", 0), getattr(last, "output_tokens", 0)


async def call_with_fallback(prompt, primary, fallback_chain, *, stream, trace,
                             retries_per_model=2, health=health):
    """Try `primary`, then each model in `fallback_chain`, in order.

    `stream(model, prompt)` -> async iterator of token chunks (raises ProviderError
        or ToolsUnsupported). `trace(event, **fields)` records an observability event.

    Returns a Result; never raises on a *recoverable* failure (degrades instead).
    Re-raises a TERMINAL ProviderError, because no other model will accept it.
    """
    chain = [primary, *fallback_chain]
    # Preemptively skip models still cooling down (keep at least one to try).
    live = [m for m in chain if health.is_healthy(m)] or [chain[-1]]
    attempts: list[str] = []

    for model in live:
        for attempt in range(retries_per_model):
            try:
                text, in_tok, out_tok = await _stream_once(model, prompt, stream)
                trace("model_call_ok", model=model, attempt=attempt, fell_back=model != primary)
                return Result(text, model, fell_back=model != primary,
                              input_tokens=in_tok, output_tokens=out_tok, attempts=attempts)

            except ToolsUnsupported:                  # routing miss -> next model
                attempts.append(f"{model}:tools_unsupported")
                trace("model_skipped_incompatible", model=model)
                break

            except asyncio.TimeoutError:              # stalled before first token
                cd = health.mark_rate_limited(model)  # treat a stall like a wall
                attempts.append(f"{model}:ttft_timeout")
                trace("model_stalled", model=model, cooldown_s=cd)
                break                                 # nothing yielded -> next model, no dupes

            except ProviderError as e:
                attempts.append(f"{model}:{e.status}")
                if e.status in TERMINAL:               # the prompt is the problem
                    trace("model_call_terminal", model=model, status=e.status)
                    raise                              # abort the chain — don't re-fail on every model
                if e.status == 429:
                    health.mark_rate_limited(model)
                trace("model_call_retry", model=model, status=e.status, attempt=attempt)
                if attempt + 1 < retries_per_model:
                    await asyncio.sleep(_backoff(attempt))   # don't re-hit the provider hot
                    continue                           # retry the same model
                break                                  # retries spent -> next model

    # Whole chain exhausted on recoverable errors: degrade, don't crash the group.
    trace("chain_exhausted", attempts=attempts)
    return Result(
        text=("This specialist is temporarily rate-limited; other specialists are "
              "still available and the affected models recover shortly."),
        model="none", fell_back=True, degraded=True, attempts=attempts,
    )
