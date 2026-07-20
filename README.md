# Pacific Slate: a personal AI system

Pacific Slate is a personal AI system that works over my own knowledge and the sources I follow, and does useful work in the background instead of only answering when asked.

It runs on a private remote server, remembers context across sessions, and is built from specialized agents I route work to. This page is a plain overview: what it is, how it's put together, and how it handles privacy. Technical details are at the end if interested.

Up front: I'm an operator and systems architect, not a career software engineer. I designed the architecture, made the model-routing, reliability, and cost decisions, and built it AI-natively, in partnership with a range of AI platforms, agents, and coding tools.

**What it does for me, day to day.** It keeps itself current on my world. Whatever's wired in electronically (mail, calendar, messages, the feeds and accounts I follow) flows in on its own, so it already knows the state of play when I ask. It puts that awareness to work on ordinary tasks: a heads-up before a meeting, a standing watch on something I care about, the daily admin that usually eats an afternoon. And I reach all of it from a normal Claude client over a standard MCP connection: the same assistant I already use, now backed by my own memory, data, and tools.

---

## ▶ Live demo

**[pacslate.com/demo](https://pacslate.com/demo)** is the real UI, running on fabricated **sample data** with no private backend.

- **Canvas.** Issue a prompt (or watch the autoplay): the operator routes to specialist agents, streams a synthesized answer, and spawns result cards, each tagged with the model that served it and what the call cost. → **[open the canvas](https://pacslate.com/demo)**
- **Monitor.** A world dashboard. In the demo, USGS seismic and a public headline feed (HackerNews) run live, fetched client-side; markets, aircraft, and the personal layer are clearly-labeled sample data. (In production the headline feed is server-side RSS and the market/flight feeds are live.) → **[open the monitor](https://pacslate.com/demo/#monitor)**

*The personal layer is sample data and there's no private backend; the production system is private by design.*

<video src="docs/demo-canvas.mp4" poster="docs/demo-canvas-poster.jpg" autoplay muted loop playsinline preload="metadata" style="width:100%;border:1px solid rgba(255,255,255,0.10);border-radius:10px;display:block;margin:14px 0">
  <img src="docs/demo-canvas-poster.jpg" alt="The Pacific Slate chat canvas: the operator routes a prompt to specialist agents, which return movable result cards. A synthesized response tagged with the model that served it and the call's cost and latency, a structured brief, and suggested follow-up tests. A guided pointer drags a card to rearrange the workspace and switches the color palette.">
</video>

*The canvas (sample data). The agent's answer streams in as movable result cards, each tagged with the model that served it and the call's cost. The pointer is a one-time guided preview: it drags a card and re-themes the workspace, then hands control back the moment you move the mouse or type.*

![The Pacific Slate situational-awareness monitor: a dark world map with live USGS seismic markers and sample aircraft positions, a right rail of live seismic events, sample markets, and a public news feed, and a left rail showing a clearly-labeled sample personal layer.](docs/demo-monitor.png)

*The monitor. USGS seismic and a public headline feed run live (client-side); markets, aircraft, and the personal layer are sample data.*

---

## Why I built it

The frontier chat tools I was using didn't hold context across sessions the way I wanted, filtered at the output layer, and kept my data on their side. I wanted something that was mine end to end: runs continuously, remembers what matters, reasons over my own knowledge, and pushes useful things to me instead of waiting to be asked.

The harder part: take a lot of noisy, scattered input (my own notes and documents, the feeds and sources I care about) and turn it into something **verified and actionable** instead of just another summary.

One design choice shaped the rest: the model is the part I don't own, so I built the system so it's the part I can swap. The durable pieces are mine and stay put: my data, the memory, the tools, the routing and orchestration logic. The model is rented, reached over standard interfaces, so moving to a better one (or another provider) is mostly a config change rather than a rebuild. Day to day I drive it through Claude Code, but the design doesn't depend on that.

## What it's made of

A plain-language tour of the pieces:

- **A multi-agent core.** An operator reads a request and routes it to the right specialist (research, coding, analysis, review, and a few others), each backed by the model best suited and priced for its job, with automatic ranked fallback across vendors so one model going down doesn't stop the run.
- **A tool layer.** About eighteen tool-servers the agents can call over the Model Context Protocol (MCP): memory, knowledge retrieval, code execution, web search and feeds, infrastructure, and more. New capabilities are added by registering a server, not by rewiring the agents. Agents find the right tool by searching an index rather than holding all of them in context.
- **Memory that persists.** A private, indexed knowledge base the system reasons over, plus a layer that links related conversations and decisions over time, so context carries across sessions instead of resetting every chat. It's more than vector lookup: a fast, deterministic relevance pass picks what's relevant before any model runs, and memories decay and reconcile over time so the store stays current.
- **Proactive routines.** Scheduled jobs that pull from many sources, synthesize, and hand me a short brief, so the system works in the background, not only when I ask. Each item is filtered for signal first, and the noise it drops is logged rather than silently discarded.
- **A canvas interface.** Requests spawn live, movable result cards rather than a single scrolling thread. Results stream in as they're generated, each card showing which model answered and what the call cost.
- **Guardrails built in.** Every model call is metered against a budget and traced, so I can see what ran, what it returned, and what it cost. Spend is checked before each call, background work fails closed at the cap, and cost-driven model swaps are surfaced instead of hidden.
- **Self-maintaining.** A watchdog monitors the fleet and flags dependency and CVE updates; the low-risk ones are auto-merged through CI checks, and anything that needs a judgment call escalates to me.

## Privacy

This isn't a classified system and doesn't pretend to be one. The realistic problem with everyday AI tools is that the vendor owns your history, trains on it, and you can't get it back. Pacific Slate inverts that: you own the system of record, and inference is a commodity you rent on your own terms.

- **What's yours, and what stays yours.** Almost everything durable lives on your own server: data at rest, the knowledge base, the continuity layer, the orchestration. Exportable, deletable, and configured not to be used for training. The one deliberate exception is a hosted semantic-memory service for cross-session facts, a swappable dependency rather than the system of record (and it can be self-hosted if you'd rather).
- **What's rented.** Model calls route to providers through a single gateway. A call sends the prompt and the context it needs, gets an answer, and goes only to providers set not to train on or publish your inputs.
- **No external inference dependency, when you want it.** The routing is yours: any workload can be pinned to a model running on the box itself.

It's a pragmatic posture on purpose: serious about control, still using frontier models. The claim isn't "nothing ever leaves." It's that you own the system of record, you control where things go, and your data isn't being fed into someone else's product.

*As shown in the OpenRouter account settings ([screenshot](docs/openrouter-privacy.png), 2026-06-29): the train-on-data toggles (paid and free) are off and prompt-publishing is off, so providers don't train on or publish your inputs. Zero-data-retention is left off globally so the full model roster stays available (enforcing ZDR-only drops every non-ZDR endpoint, some of which host the open-weight models the system runs on), and it can be set per request when a call needs it.*

## What it runs on

This is a recipe you adapt, not a product you install. The point isn't my exact build. You point your own coding agent at this architecture and have it rebuild the parts you want, with whatever you already have: your models, your tools, your box. Go as deep or as shallow as you need.

A workable floor:

- a ~$20/mo coding assistant as the driver,
- a small ~$20/mo VPS for the always-on substrate,
- metered model calls on top, which on a budget-model roster at a normal personal load run on the order of $10-40/mo.

So on the order of $50-80/mo for a sovereign, always-on, multi-agent assistant, and you scale up only where you want depth: a bigger box to self-host models, premium models for the reasoning seats, a video tool for video. The structure doesn't change. The cost discipline that makes that floor real (complexity-scored routing, cheap-model defaults, a hard budget ceiling) is the same machinery described in §4. My own build runs heavier, because I develop it daily and run background automations; the architecture is what keeps it cheap when you don't.

## How it fits together

The short version of a request's life:

A request comes in → the **operator** decides which specialist should own it → that agent pulls what it needs from memory and the knowledge base and calls any tools it needs over MCP → the **model router** picks the right model (and fails over if one is down) → the answer is synthesized, returned to the canvas, and the agent can write anything worth keeping back to memory. Cost is metered on every call; the whole path is traced.

![Pacific Slate architecture](docs/architecture.svg)

*Click the diagram to enlarge.*

---

# For the technically curious

Everything below expands. Each line is one part of the system; open the ones you care about and skip the rest. One note on specifics before you do: any model named on this page or in the example config is illustrative. The architecture is model-agnostic by design, the roster rotates as better options ship, and the structure is the durable part.

<details markdown="1">
<summary><strong>Model-agnostic by design</strong> · swap the engine, keep the substrate</summary>

The model is the one rented part, so the system treats it as swappable behind two standard interfaces: an **MCP gateway** (the substrate's tools and memory exposed over the Model Context Protocol, mountable by any MCP-capable client) and an **OpenAI-compatible endpoint** (any client that speaks the standard chat format can drive the pipeline). Today the day-to-day client is Claude Code, extended through the same standard surfaces it already exposes: MCP for tools and memory, and lifecycle hooks that inject the right context on every turn.

The point: the work that's mine (memory, data, tools, routing, verification) doesn't move when the model does. Moving to a better model, or another provider, is a config change, not a rebuild.

</details>

<details markdown="1">
<summary><strong>1. How a request flows</strong> · one visible stream from prompt to answer</summary>

The operator reads each request and either answers inline (one model call) or hands it to a specialist, which pulls context from memory and the knowledge base, calls tools over MCP, and streams its answer back as a card tagged with the model that served it and what the call cost. Everything is visible as it happens: tokens, tool invocations, and which model is running, not a black-box pause.

**The mechanics.**

1. The canvas (a Next.js single-page app) opens a streaming connection and posts the prompt. Streaming uses the **AG-UI protocol over Server-Sent Events**, proxied to the backend so tokens, tool calls, and model-resolution events all arrive on one stream.
2. The backend is a **Starlette** service exposing two surfaces: the AG-UI SSE endpoint for the canvas, and an OpenAI-compatible endpoint so other clients can talk to the same pipeline.
3. The **operator** agent classifies the request: direct answer, or hand off to a specialist, and routes accordingly.
4. The chosen specialist pulls context (memory, knowledge base) and calls whatever tools it needs over MCP.
5. The **resilient model layer** resolves the actual model for that call (with cost-aware downgrades and health-aware fallback, see §4), streams the completion, and meters the cost.
6. The answer streams back to the canvas as a card, tagged with the model that served it and the cost, and the agent can write anything worth keeping back to memory.

Two speed tiers fall out of this: the operator answers simple things inline in a single model call, and anything that needs a specialist becomes a delegated run, where the specialist works its own tool loop.

</details>

<details markdown="1">
<summary><strong>2. Agent orchestration</strong> · eight agents, and nothing grades its own homework</summary>

The core is a multi-agent tree built on **Google's Agent Development Kit (ADK)**: one operator (the root) plus seven specialists (coder, researcher, analyst, productivity, reviewer, evaluator, and a research sub-agent scoped to the coder). Specialization is what keeps it cheap and contained: each role gets the model suited and priced for its work, a failure or rate-limit stays inside one specialist, and the evaluator deliberately runs on a *different model family* than the agents whose output it scores.

**The mechanics.**

- **Cost and quality.** A heavy reasoning job and a one-line lookup shouldn't pay the same price or wait on the same model. Each role is mapped to the model that's best and most cost-effective for its work.
- **Honest review.** Cross-family evaluation is imperfect independence (different weights, not necessarily different biases), but better than none. The reviewer is a separate instance kept off the write path by policy.
- **Least privilege.** Tools are scoped per role through explicit allow-lists. The researcher can't touch infrastructure, the reviewer is kept read-only by policy (no commit/push/write in its charter), and the productivity agent's credentials are isolated so an OAuth failure there can't crash the operator.
- ADK enforces a single-parent constraint on sub-agents, which is why the coder's research arm is a separate instance from the standalone researcher even though they share a model and tools.
- Specialists publish discoveries to a **Redis event stream** that peers read as ambient context, a lightweight awareness mesh. Longer async jobs hand off to a separate background orchestrator, so not everything funnels through one synchronous call path.

</details>

<details markdown="1">
<summary><strong>3. The tool layer (MCP)</strong> · ~18 servers behind one gateway, found by search</summary>

About eighteen tool-servers (memory, knowledge retrieval, code execution, git, feeds, infrastructure, and more) sit behind a single token-authenticated gateway (FastMCP over streamable HTTP; each tool-server is its own process). Adding a capability means registering a server, not rewiring agents.

**The mechanics.** Two decisions worth explaining:

- **Register, don't rewire.** New tools compose in. The cost of that flexibility is an extra network hop and a single failure domain at the gateway, which is why the gateway gets its own health check and the whole fleet is health-polled.
- **Search, don't dump context.** Carrying every tool's schema in every agent's context is expensive and dilutes attention. So the gateway exposes a **custom BM25 search over the tool catalog**: an agent describes what it needs and gets the right tool back. MCP's spec only lists tools; this search is my own addition. Same instinct as the memory design (§5): use a cheap deterministic index to decide what to load before spending model tokens on it.

</details>

<details markdown="1">
<summary><strong>4. Model routing and resilience</strong> · the budget router, the health tracker, and a silent failure</summary>

The part that took the most iteration: the first LLM call is easy; keeping calls reliable and cheap under real conditions is where the bugs lived. Role-to-model assignment is declarative config. A deterministic scorer rates each prompt's complexity before any model runs, and that score plus budget state picks the tier: under budget pressure, work degrades to progressively cheaper models instead of failing, and only background work can be blocked outright. A health tracker cools down rate-limited models so calls skip known walls, a first-token watchdog catches models that stall without emitting anything, and an exhausted chain degrades to a usable message instead of crashing the run.

**Cost-aware selection, decided before the call.** The scorer rates complexity 1-5 (word count, keyword classes, code markers, the agent's role weight, conversation depth) with no model in the loop. Under ~80% of the monthly budget, everyone runs on their assigned model; 80-95% downgrades only trivial tasks; 95-100% downgrades everything except essential high-complexity work; at 100% it fails closed on non-essential calls. Spend is tracked per request against a hard monthly ceiling, with crash-safe atomic writes so the ledger survives a restart.

**Health-aware fallback.** In the ADK version I built on, the model wrapper called the provider directly and didn't consult the underlying library's fallback config, so that global setting did nothing. I found that gap and wrapped the model layer with one that actually implements it:

- A singleton **health tracker** records any model that returns a rate-limit (429) and puts it in an **escalating cooldown** that grows with repeat offenses, up to a cap. Future calls preemptively skip a cooling-down model instead of re-hitting a wall.
- A **time-to-first-token watchdog** bounds only the *first* response of each attempt. A model that stalls and emits nothing trips it and the call falls over to the next model; because nothing was yielded yet, there's no duplicate output. Once a real stream starts it runs unbounded, with a longer outer timeout as backstop.
- A fallback model that can't accept the tool definitions is detected and skipped as a compatibility miss, not surfaced as a failure.
- If the *entire* chain is exhausted, the layer yields a graceful "this specialist is temporarily unavailable, others are still available" message rather than crashing the run group.

The chains deliberately end on *different* terminal models, so no two roles share a last resort, and any workload can be pinned to a model running on the box itself as the escape hatch when every hosted provider is unhappy.

**The failure that taught me the most was silent.** Agents would intermittently get worse (more hedging, the occasional refusal) with nothing in the error logs. It wasn't the prompts: under budget pressure the cost router was quietly swapping an agent's model for a cheaper one that returned `200 OK` while behaving differently. Silent degradation is worse than a hard failure, because you debug the wrong layer for an hour first. The fix was observability on the swap itself: every cost-router substitution now shows up on the result card's model badge and in tracing, so the first question on any behavioral regression is "which model actually served this call?" before anyone touches the prompt.

</details>

<details markdown="1">
<summary><strong>5. Memory</strong> · four layers, and memory is a lead, not a fact</summary>

Memory is layered: a private knowledge corpus (roughly **27,000 documents / ~294,000 chunks**, full-text retrieval by default), a continuity graph linking related conversations and decisions over time, a semantic memory service for durable facts with a nightly reconciliation job, and tiered context so the always-loaded core stays small.

**The mechanics.**

- **A private knowledge base.** Retrieval over my own indexed corpus (a large archived reference set plus my own working notes and feeds). Keyword (full-text) retrieval is the default. It's a deliberate tradeoff: semantic (vector) search is wired but turned off because, at this corpus size, the keyword path was fast enough and simpler to operate, and the recall hit was acceptable for my own curated material.
- **A continuity layer.** A standalone graph that links related conversations, decisions, and topics over time, so a new request can be connected to what came before instead of starting cold.
- **Semantic memory + reconciliation.** A cloud semantic-memory service captures durable facts (decisions, commitments, context worth keeping) for cross-session recall, with a nightly job that reconciles and de-duplicates it so it doesn't rot.
- **Hierarchical context tiering.** Always-on core vs. retrieved-on-demand, so the expensive always-loaded set stays small.

Two rules run through all of it. First, **a deterministic relevance pass runs before any model**: what context to load is decided by a cheap deterministic scan (no model call, no vector round-trip), the same instinct as the tool search. Second, **memory is a lead, not a fact**: recalled memory is a pointer to verify, so if memory says a vendor renews in July, the agent pulls the source email or contract and acts on *that*. This is the single most important discipline for keeping a long-lived memory system from confidently acting on something that was true three weeks ago.

</details>

<details markdown="1">
<summary><strong>6. The proactive layer</strong> · signal over noise, with the dropped noise logged</summary>

A lot of the value is that it runs when I'm not looking at it. Scheduled routines pull from many sources, filter for signal (noise is the default every candidate item has to beat), and deliver a short brief.

**The mechanics.** Candidate items run through an explicit relevance filter before they're allowed into a brief: is it actually relevant to what I'm working on, is it material, is it genuinely new, or is it noise. What gets dropped is logged rather than silently discarded, so the filter can be inspected instead of trusted blind. A separate consolidation stage de-duplicates and normalizes before anything is persisted, with a credential/PII screen in that path, which is also part of the privacy story: sensitive strings get caught at ingestion rather than after they're in the store.

</details>

<details markdown="1">
<summary><strong>7. Infrastructure and operations</strong> · segmented, sandboxed, health-gated deploys</summary>

Docker services across four segmented network tiers behind a Cloudflare Tunnel, agent code execution in an isolated sandbox, health-gated continuous deployment with a build-provenance check, and tracing on every model call and every model swap.

**The mechanics.**

- **Containerized, network-segmented.** Four core tiers (public-facing, internal backend, outbound-capable, and an isolated sandbox), plus a couple of purpose-built nets like the code-execution broker, so the blast radius of any one service is bounded. Public ingress is through a Cloudflare Tunnel; the origin isn't directly exposed.
- **Sandboxed code execution.** Agent-run code executes in an isolated sandbox (ephemeral tmpfs workspace, a hardened runtime) on its own network tier.
- **Health-gated CD.** A push to main triggers pull, smart rebuild, health check, and a **build-provenance gate that asserts the running build actually matches what was deployed** before it's considered green, so a "successful" deploy that didn't actually swap the image gets caught. A drift-check job reconciles config (ports, versions) automatically.
- **Self-healing.** A watchdog flags dependency and CVE updates; low-risk ones are auto-merged through CI checks, and the decisions that genuinely need me escalate.
- **Observability.** Spend attributed per request and per model; every call and every swap traced.

</details>

<details markdown="1">
<summary><strong>8. Engineering principles I kept coming back to</strong> · algorithm-first, failure made visible</summary>

- **Algorithm-first, LLM on the edges.** Default every data-access and classification problem to something deterministic: regex, an index, SQL, set membership, the standard library. Reach for a model only on the genuinely irreducible part (semantics, multi-hop synthesis, judgment). The complexity scorer, the tool search, and the memory relevance pass are all this principle. It's what keeps the thing fast and affordable at scale.
- **Make failure visible, then make it cheap.** Most of the reliability work followed the same arc: a real outage or silent regression, surfaced by debugging, then closed with a guardrail *and a trace* so the same class of problem can't hide again.
- **Resilience over peak capability.** Ordered fallbacks, escalating cooldowns, graceful degradation, and the option to pin any workload to a local model that needs no external provider. A system that's slightly slower but stays up beats a faster one that falls over.
- **Cost as a first-class constraint.** Designing under a real ceiling forces honest trade-offs: model choice, context size, when to retrieve, when to use a model at all.

</details>

<details markdown="1">
<summary><strong>Known limits</strong> · the trade-offs, stated plainly</summary>

- **One router in the path.** All hosted models are reached through a single gateway today, so a router outage is the shared dependency. Mitigated by pinning a workload to the local model, not eliminated.
- **The demo is representative, not connected.** The real UI on sample data; it doesn't touch the production system.
- **The semantic-memory layer is a hosted service.** The one cloud dependency in an otherwise local stack (swappable, and not the system of record).
- **Keyword retrieval can miss paraphrases.** The default full-text path trades some recall for speed; semantic search is wired for when that matters.
- **Not a high-security or classified design.** It's serious about data control, not a threat model against a determined adversary.

</details>

<details markdown="1">
<summary><strong>Stack at a glance</strong> · the whole system in one table</summary>

*(The roles and structure are the durable part; every model seat is illustrative and rotates as better options ship.)*

| Layer | Choice |
|---|---|
| Agent framework | Google ADK (multi-agent tree: operator + specialists) |
| Backend | Starlette. AG-UI over SSE + OpenAI-compatible endpoint |
| Interop | MCP gateway + OpenAI-compatible endpoint, engine-agnostic by design |
| Frontend | Next.js (chat front door + spatial canvas view, streaming result cards) |
| Inter-agent bus | Redis event streams |
| Tooling | ~18 MCP servers behind one gateway; BM25 tool search |
| Operator / routing | a long-context, native-tool-calling model |
| Coder | a purpose-built code model (large context) |
| Researcher | a fast long-context model, single-pass (1 model call + a few tool calls) |
| Analyst | a large mixture-of-experts reasoning model |
| Reviewer / evaluator | independent of the code-writers; evaluator scores on a different model family; local-first, paid fallback |
| Memory | full-text knowledge corpus + continuity graph + semantic memory + tiered context |
| Infra | Docker, four core segmented tiers, Cloudflare Tunnel, sandboxed exec |
| Reliability | per-role fallback chains, health tracker with escalating cooldown, TTFT watchdog, graceful degrade |
| Cost / observability | per-request metering to a monthly ceiling, full call + model-swap tracing |

</details>

---

## Selected artifacts

- [`examples/model-routing.example.yaml`](examples/model-routing.example.yaml) is the real config structure (role → model routing, cost router, fallback chains) with illustrative model IDs and numbers, since the roster rotates by design.
- [`examples/model_fallback.py`](examples/model_fallback.py) is the resilient-call fallback pattern (simplified), with the design decisions worth defending in the comments.

---

The goal: take agentic AI from an architecture to a system that actually runs every day, under real cost, reliability, and privacy constraints, and keep it honest.

*The live system is private by design; this page describes its architecture and decisions, not the running deployment.*
