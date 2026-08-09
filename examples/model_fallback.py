"""
Resilient model call: health-aware fallback with a time-to-first-token watchdog.

A representative excerpt of the layer that wraps every model call. The production
version adds per-provider error mapping, cost metering against the budget router,
and full tracing; this is trimmed to the parts worth discussing: how one call
survives a provider failing, stays cheap, and never silently hangs.

Design decisions worth defending:

  - Three failure classes, handled differently:
      * RETRYABLE   (429 / 5xx / timeout) - transient; fall through the chain
                    (5xx gets one brief same-model retry first).
      * TERMINAL    (400 / 401 / 403 / 422 - bad request, bad credential, or
                    content rejected) - no other model will accept it either;
                    ABORT the whole call instead of burning the chain.
      * PER-MODEL   (404 model-not-found, or tool definitions the model can't
                    accept) - a property of that one model, not the request;
                    skip to the next model. Getting this class wrong is easy
                    and expensive: early versions treated 404 as TERMINAL,
                    which meant one retired model ID aborted the exact chain
                    that existed to route around it.
      Anything unrecognized re-raises: unknown errors should be loud, not
      silently retried.
  - A rate-limited model is put in an escalating cooldown and PREEMPTIVELY
    skipped on later calls, so we don't keep re-hitting a wall. Strikes are
    cleared by a SUCCESS, not by the cooldown expiring; a model that fails
    every time it's readmitted keeps climbing the ladder.
  - A time-to-first-token watchdog bounds only the FIRST token of each attempt.
    A model that stalls and emits nothing trips it and we fall over. Safe,
    because nothing was yielded yet (no duplicate output). Once a real stream
    starts it runs unbounded; OUTER_TIMEOUT_S backstops a mid-stream stall
    (the two are ordered on purpose: TTFT 90s < outer 240s).
  - If the whole chain is exhausted on recoverable errors, degrade gracefully
    (a usable message) rather than crash the wider run. Chains end on
    deliberately DIFFERENT terminal models per role, so no two roles share a
    last resort; and any workload can instead be pinned to a locally-served
    model when no external provider should be in the path.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

RETRYABLE = {429, 500, 502, 503, 504}          # transient: fall through the chain
TERMINAL = {400, 401, 403, 422}                # no model will accept this call: abort
PER_MODEL = {404}                              # this model is the problem: skip it
TTFT_TIMEOUT_S = 90.0                          # bound ONLY the first token
OUTER_TIMEOUT_S = 240.0                        # backstop for a mid-stream stall
CLOSE_TIMEOUT_S = 5.0                          # bound generator cleanup, too
COOLDOWN_BASE_S = 60.0                          # escalates 60 -> 120 -> 180 ...
COOLDOWN_CAP_S = 300.0                          # ... capped at 300


class ProviderError(Exception):
    def __init__(self, status: int, message: str = ""):
        super().__init__(f"{status} {message}".strip())
        self.status = status


class ToolsUnsupported(Exception):
    """Model can't accept the request's tool definitions: skip it, don't fail."""


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
    Escalating cooldown: 60s -> 120s -> 180s -> ... capped at 300s.

    State lifetimes are deliberate: cooldown expiry readmits a model but KEEPS
    its strike count (repeat offenders climb the ladder); only a successful
    call clears history. An earlier version cleared strikes on expiry, which
    quietly capped the ladder at one step under steady traffic."""

    def __init__(self) -> None:
        self._cooldown_until: dict[str, float] = {}
        self._strikes: dict[str, int] = {}

    def is_healthy(self, model: str) -> bool:
        until = self._cooldown_until.get(model)
        if until is None:
            return True
        if time.monotonic() >= until:               # cooled off: readmit, keep strikes
            self._cooldown_until.pop(model, None)
            return True
        return False

    def mark_rate_limited(self, model: str) -> float:
        n = self._strikes.get(model, 0) + 1
        self._strikes[model] = n
        cooldown = min(COOLDOWN_BASE_S * n, COOLDOWN_CAP_S)
        self._cooldown_until[model] = time.monotonic() + cooldown
        return cooldown

    def mark_success(self, model: str) -> None:
        self._cooldown_until.pop(model, None)
        self._strikes.pop(model, None)


health = HealthTracker()


def _backoff(attempt: int) -> float:
    return min(0.5 * (2 ** attempt), 4.0)           # 0.5s, 1s, 2s, ... capped at 4s


async def _stream_once(model, prompt, stream):
    """One attempt. The TTFT watchdog bounds ONLY the first chunk; once tokens
    flow, the caller's outer timeout (OUTER_TIMEOUT_S) backstops the stream.
    Raises asyncio.TimeoutError if no first token arrives in time; an empty
    stream (a 200 that closes with zero chunks) is treated the same way, since
    from the caller's seat both are "this model produced nothing." The
    generator is closed on every exit, with the close itself bounded so a
    half-dead connection can't turn a detected stall into a new hang."""
    agen = stream(model, prompt).__aiter__()
    try:
        try:
            first = await asyncio.wait_for(agen.__anext__(), timeout=TTFT_TIMEOUT_S)
        except StopAsyncIteration:
            raise asyncio.TimeoutError(f"{model}: stream closed with zero chunks")
        chunks = [first]
        async for chunk in agen:                      # unbounded after first token
            chunks.append(chunk)
    finally:
        try:
            await asyncio.wait_for(agen.aclose(), timeout=CLOSE_TIMEOUT_S)
        except (asyncio.TimeoutError, RuntimeError):
            pass                                      # cleanup must never mask the result
    text = "".join(c.text for c in chunks)
    last = chunks[-1]
    return text, getattr(last, "input_tokens", 0), getattr(last, "output_tokens", 0)


async def call_with_fallback(prompt, primary, fallback_chain, *, stream, trace,
                             retries_per_model=2, health=health):
    """Try `primary`, then each model in `fallback_chain`, in order.

    `stream(model, prompt)` -> async iterator of token chunks (raises ProviderError
        or ToolsUnsupported). `trace(event, **fields)` records an observability event.

    Returns a Result; never raises on a *recoverable* failure (degrades instead).
    Re-raises a TERMINAL ProviderError (400/401/403/422), because no other model
    will accept the call. A 404 is NOT terminal: model-not-found indicts one
    model ID, so it falls through to the next model in the chain.
    """
    chain = [primary, *fallback_chain]
    # Preemptively skip models still cooling down (keep at least one to try).
    live = [m for m in chain if health.is_healthy(m)] or [chain[-1]]
    attempts: list[str] = []

    for model in live:
        for attempt in range(retries_per_model):
            try:
                text, in_tok, out_tok = await asyncio.wait_for(
                    _stream_once(model, prompt, stream), timeout=OUTER_TIMEOUT_S)
                health.mark_success(model)
                trace("model_call_ok", model=model, attempt=attempt, fell_back=model != primary)
                return Result(text, model, fell_back=model != primary,
                              input_tokens=in_tok, output_tokens=out_tok, attempts=attempts)

            except ToolsUnsupported:                  # per-model miss -> next model
                attempts.append(f"{model}:tools_unsupported")
                trace("model_skipped_incompatible", model=model)
                break

            except asyncio.TimeoutError:              # no first token, or a mid-stream stall
                cd = health.mark_rate_limited(model)  # treat a stall like a wall
                attempts.append(f"{model}:stall_timeout")
                trace("model_stalled", model=model, cooldown_s=cd)
                break                                 # nothing yielded -> next model, no dupes

            except ProviderError as e:
                attempts.append(f"{model}:{e.status}")
                if e.status in TERMINAL:               # no model will accept this call
                    trace("model_call_terminal", model=model, status=e.status)
                    raise                              # abort the chain; don't re-fail on every model
                if e.status in PER_MODEL:              # this model is the problem
                    trace("model_skipped_missing", model=model, status=e.status)
                    break                              # skip it; the chain exists for exactly this
                if e.status == 429:
                    health.mark_rate_limited(model)
                    trace("model_rate_limited", model=model)
                    break                              # marked; retrying the same wall is pointless
                if e.status in RETRYABLE:              # transient 5xx: one brief retry, then move on
                    trace("model_call_retry", model=model, status=e.status, attempt=attempt)
                    if attempt + 1 < retries_per_model:
                        await asyncio.sleep(_backoff(attempt))
                        continue
                    break                              # retries spent -> next model
                raise                                  # unknown status: be loud, not clever

    # Whole chain exhausted on recoverable errors: degrade, don't crash the group.
    trace("chain_exhausted", attempts=attempts)
    return Result(
        text=("This capability is temporarily unavailable (all of its models are "
              "failing or cooling down); other work is unaffected."),
        model="none", fell_back=True, degraded=True, attempts=attempts,
    )
