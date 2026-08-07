# Pacific Slate

Most AI assistants begin from nothing every time you open one. You explain your situation, get a useful answer, close the tab, and next week you explain the whole thing over again. Whatever you told it lives on a company's server, and none of what it learned is really yours to keep.

Pacific Slate is the other version of that. It remembers. It keeps up with the things I care about while I'm not watching. And it runs on a computer I own, so the part that accumulates, everything it has picked up about my work and my world, stays with me.

I designed it, built it, and I run it every day. The first part of this page is plain English: what it does, and why it's put together the way it is. The technical detail is folded up at the bottom for anyone who wants to check the engineering.

## What it's actually like

The useful part isn't that it can answer questions. Everything can answer questions now. It's that it has already caught up by the time I get there, and that it keeps working while I'm not looking.

![An illustrative day: early, a short unprompted brief on what changed and what needs attention. Midday, a question answered without re-explaining the background. Afternoon, a single clear flag when something being watched actually moves. Evening, a written record of everything it decided was not worth mentioning.](docs/a-day-with-it.svg)

That last one matters more than it looks. Anything trying to filter the world for you is making judgment calls about what you don't need to see, and those calls are usually invisible. Here they're written down, so I can go back and check whether it was right.

## What happens when I ask it something

There isn't one assistant behind this. There's a small group of specialists, and something in front deciding who should take the question. A quick lookup and a piece of hard analysis shouldn't cost the same or wait on the same machinery.

![What happens when a question comes in: it is sized up and handed to whichever specialist suits it; that specialist gathers what it needs from memory and from my own material; it picks a model to do the work and moves to another if one is unavailable; the answer returns with its sources and what the work cost; anything worth keeping is remembered for next time.](docs/what-happens-when-i-ask.svg)

Two things in there are deliberate. It tells me where an answer came from, because an assistant that can't show its sources is just a confident stranger. And it tells me what the work cost, because I'd rather know than find out at the end of the month.

## Seeing it

![The Pacific Slate workspace, captured from the public demo. A question has been answered into movable cards on a dark canvas: the response is labeled with the model that produced it, what the call cost, and how long it took, alongside a short brief and some suggested follow-ups. The header reads: Pacific Slate, demo, sample data, no backend.](docs/demo-canvas-still.png)

*The workspace, captured from the public demo. Answers arrive as cards you can move around rather than as one long scroll, each labeled with which model produced it, what it cost, and how long it took. Everything here is made-up sample data: the demo has no connection to the real system.*

**You can try it: [pacslate.com/demo](https://pacslate.com/demo).** It's the real interface running on invented data.

- **The canvas.** Ask it something, or just watch it run, and see the answer arrive as cards. [Open the canvas](https://pacslate.com/demo)
- **The monitor.** A world dashboard. The earthquake data and headlines are genuinely live, pulled in your browser; markets, aircraft, and anything personal are labeled sample data. [Open the monitor](https://pacslate.com/demo/#monitor)

## What's mine, and what's rented

The realistic problem with everyday AI tools isn't that they're dangerous. It's that the company owns your history, learns from it, and you can't take it with you. This is arranged the other way around: I keep the part that accumulates, and I rent the thinking.

![Who owns what. On my own server and staying there: my own material, the memory that carries between conversations, the tools it can use, and the judgment about what to use and when. Rented and swappable: the AI model itself, reached through a standard connection, so a better one can take its place without rebuilding anything around it. If nothing should leave at all, a model can run on the same server instead.](docs/who-owns-what.svg)

One choice shaped everything else. The AI model is the piece I don't own and can't control, so I built the system to treat it as replaceable. The durable parts, my own material and the memory and the tools and the judgment, sit on my side and stay put. When a better model arrives, swapping it in is a settings change rather than a rebuild.

A few specifics, since this is the part people are right to be skeptical about. What's stored is exportable and deletable, and it isn't training anyone's product. Questions that do go out to a model provider go only to providers configured not to train on them or publish them ([the account settings](docs/openrouter-privacy.png), June 2026). And if I'd rather nothing left the building at all, any of the work can be pointed at a model running on the same server.

This isn't a classified system and doesn't pretend to be one. The claim isn't that nothing ever leaves. It's that I own the thing that accumulates, I decide where anything goes, and none of it is quietly becoming someone else's product.

## My part in it

I wanted something that was mine end to end: that runs continuously, holds on to what matters, works from my own material, and brings me things instead of waiting to be asked. The harder half was never getting an answer out of a model. It was taking a lot of scattered, noisy input and turning it into something I'd actually trust enough to act on.

A note on what I am and what I'm not. I'm an operator and a systems architect by background, not a career software engineer. The architecture here is mine: what the pieces are, how they fit, what each one runs on, what happens when something fails, and what it's allowed to spend. I built it AI-natively, specifying and reviewing while coding agents wrote most of the code, in partnership with a range of AI platforms and tools. Directing AI systems to build an AI system was the method, and it's part of what this project demonstrates.

---

# For the technically curious

Four sections, each one expandable. Every one follows the same shape: the claim, then how it actually works, then something you can go look at.

One note before you open them. Any model named on this page or in the example config is illustrative. The design is deliberately model-agnostic, the lineup rotates as better options ship, and the structure is the durable part. Counts are current as of August 2026 and were checked against the running system.

<details markdown="1">
<summary><strong>1 · AI development</strong> · designed, not assembled: agents, memory, and the routing between them</summary>

**The claim: this is a designed multi-agent system, not a chat model with plugins.**

The core is a multi-agent tree built on **Google's Agent Development Kit (ADK)**: one operator (the root) plus seven specialists (coder, researcher, analyst, productivity, reviewer, evaluator, and a research sub-agent scoped to the coder). Specialization is what keeps it cheap and contained: each role gets the model suited and priced for its work, a failure or rate-limit stays inside one specialist, and the evaluator deliberately runs on a *different model family* than the agents whose output it scores.

- **Cost and quality.** A heavy reasoning job and a one-line lookup shouldn't pay the same price or wait on the same model. Each role is mapped to the model that's best and most cost-effective for its work.
- **Honest review.** Cross-family evaluation is imperfect independence (different weights, not necessarily different biases), but better than none. The reviewer is a separate instance kept off the write path by policy.
- **Least privilege.** Tools are scoped per role through explicit allow-lists. The researcher can't touch infrastructure, the reviewer is kept read-only by policy (no commit, push, or write in its charter), and the productivity agent's credentials are isolated so a failure there can't crash the operator.
- ADK enforces a single-parent constraint on sub-agents, which is why the coder's research arm is a separate instance from the standalone researcher even though they share a model and tools.
- Specialists publish discoveries to a **Redis event stream** that peers read as ambient context, a lightweight awareness mesh. Longer async jobs hand off to a separate background orchestrator, so not everything funnels through one synchronous call path.

**Model-agnostic by design.** The model is the one rented part, so the system treats it as swappable behind two standard interfaces: an **MCP gateway** (the tools and memory exposed over the Model Context Protocol, mountable by any MCP-capable client) and an **OpenAI-compatible endpoint** (any client that speaks the standard chat format can drive the pipeline). The work that's mine, meaning memory, data, tools, routing, and verification, doesn't move when the model does.

**Memory is layered, and memory is a lead rather than a fact.** A private knowledge corpus (roughly **14,000 documents and ~196,000 passages** as of August 2026), a continuity graph linking related conversations and decisions over time, a semantic memory service for durable facts with a nightly reconciliation job, and tiered context so the always-loaded core stays small.

- **A private knowledge base.** Retrieval over my own indexed material: a large archived reference set plus my own working notes and the sources I follow. Retrieval is hybrid, combining keyword matching with semantic (vector) similarity, so a passage can be found either by the words in it or by what it means.
- **A continuity layer.** A standalone graph that links related conversations, decisions, and topics over time, so a new request can be connected to what came before instead of starting cold.
- **Semantic memory and reconciliation.** A hosted semantic-memory service captures durable facts (decisions, commitments, context worth keeping) for cross-session recall, with a nightly job that reconciles and de-duplicates so it doesn't rot.
- **Hierarchical context tiering.** Always-on core versus retrieved-on-demand, so the expensive always-loaded set stays small.

Two rules run through all of it. First, **a deterministic relevance pass runs before any model**: what context to load is decided by a cheap deterministic scan, no model call required. Second, **memory is a lead rather than a fact**: recalled memory is a pointer to verify, so if memory says a vendor renews in July, the agent pulls the source document and acts on *that*. This is the single most important discipline for keeping a long-lived memory system from confidently acting on something that was true three weeks ago.

**The proactive layer filters for signal, and logs the noise.** Scheduled routines pull from many sources and run every candidate item through an explicit relevance filter before it's allowed into a brief: is it actually relevant, is it material, is it genuinely new, or is it noise. What gets dropped is logged rather than silently discarded, so the filter can be inspected instead of trusted blind. A separate consolidation stage de-duplicates and normalizes before anything is persisted, with a credential and PII screen in that path, so sensitive strings get caught on the way in rather than after they're in the store.

**The principles behind these choices.**

- **Algorithm first, models on the edges.** Default every data-access and classification problem to something deterministic: regex, an index, SQL, set membership, the standard library. Reach for a model only on the genuinely irreducible part (semantics, multi-hop synthesis, judgment). The complexity scorer, the tool search, and the memory relevance pass are all this principle.
- **Make failure visible, then make it cheap.** Most of the reliability work followed the same arc: a real outage or silent regression, surfaced by debugging, then closed with a guardrail *and a trace* so the same class of problem can't hide again.
- **Resilience over peak capability.** A system that's slightly slower but stays up beats a faster one that falls over.
- **Cost as a first-class constraint.** Designing under a real ceiling forces honest trade-offs: model choice, context size, when to retrieve, and when to use a model at all.

**Go look at:** the role-to-model routing structure in [`examples/model-routing.example.yaml`](examples/model-routing.example.yaml) · the model and cost label on every card in the [live demo](https://pacslate.com/demo) · the architecture diagram in the next section.

</details>

<details markdown="1">
<summary><strong>2 · System integration</strong> · models, tools, data, and a streaming interface joined into one environment</summary>

**The claim: many layers, meaning model providers, tools, data, memory, and a frontend, are integrated into one working environment reachable over standard interfaces.**

**How a request actually flows.**

1. The canvas (a Next.js single-page app) opens a streaming connection and posts the prompt. Streaming uses the **AG-UI protocol over Server-Sent Events**, proxied to the backend so tokens, tool calls, and model-resolution events all arrive on one stream.
2. The backend is a **Starlette** service exposing two surfaces: the AG-UI endpoint for the canvas, and an OpenAI-compatible endpoint so other clients can talk to the same pipeline.
3. The **operator** agent classifies the request, either answering inline or handing off to a specialist, and routes accordingly.
4. The chosen specialist pulls context (memory, knowledge base) and calls whatever tools it needs over MCP.
5. The **resilient model layer** resolves the actual model for that call (with cost-aware downgrades and health-aware fallback, covered in section 3), streams the completion, and meters the cost.
6. The answer streams back to the canvas as a card, labeled with the model that served it and the cost, and the agent can write anything worth keeping back to memory.

Two speed tiers fall out of this: the operator answers simple things inline in a single model call, and anything needing a specialist becomes a delegated run where the specialist works its own tool loop.

![Pacific Slate architecture](docs/architecture.svg)

*The whole system in one picture. Click to enlarge.*

**The tool layer: about two dozen servers behind one gateway, found by search.** Tool-servers (memory, knowledge retrieval, code execution, git, feeds, infrastructure, and more) sit behind a single token-authenticated gateway (FastMCP over streamable HTTP; each tool-server is its own process). Two decisions worth explaining:

- **Register, don't rewire.** Adding a capability means registering a server, not rewiring agents. The cost of that flexibility is an extra network hop and a single failure domain at the gateway, which is why the gateway gets its own health check and the whole fleet is health-polled.
- **Search, don't dump context.** Carrying every tool's schema in every agent's context is expensive and dilutes attention, so the gateway exposes a **custom BM25 search over the tool catalog**: an agent describes what it needs and gets the right tool back. The MCP spec only lists tools; this search is my own addition. Same instinct as the memory design in section 1: use a cheap deterministic index to decide what to load before spending model tokens on it.

**The stack at a glance.** *(The roles and structure are the durable part; every model seat is illustrative and rotates as better options ship.)*

| Layer | Choice |
|---|---|
| Agent framework | Google ADK (multi-agent tree: operator plus specialists) |
| Backend | Starlette. AG-UI over SSE plus an OpenAI-compatible endpoint |
| Interop | MCP gateway plus OpenAI-compatible endpoint, engine-agnostic by design |
| Frontend | Next.js (chat front door and spatial canvas view, streaming result cards) |
| Inter-agent bus | Redis event streams |
| Tooling | ~24 MCP servers behind one gateway; BM25 tool search |
| Operator and routing | a long-context, native-tool-calling model |
| Coder | a purpose-built code model (large context) |
| Researcher | a fast long-context model, single-pass |
| Analyst | a large mixture-of-experts reasoning model |
| Reviewer and evaluator | independent of the code-writers; evaluator scores on a different model family; local-first, paid fallback |
| Memory | hybrid-retrieval knowledge corpus, continuity graph, semantic memory, tiered context |
| Infra | Docker, four core segmented tiers, Cloudflare Tunnel, sandboxed execution |
| Reliability | per-role fallback chains, health tracker with escalating cooldown, first-token watchdog, graceful degrade |
| Cost and observability | per-request metering to a monthly ceiling, full call and model-swap tracing |

**Go look at:** the architecture diagram above · the [live demo](https://pacslate.com/demo), which is the real Next.js canvas speaking the same protocol against scripted sample events.

</details>

<details markdown="1">
<summary><strong>3 · Reliability, cost, and evaluation</strong> · what makes it production rather than a prototype</summary>

**The claim: it stays up, stays on budget, and checks its own output, and every one of those mechanisms is observable.**

This took the most iteration. The first model call is easy; keeping calls reliable and cheap under real conditions is where the bugs lived. Role-to-model assignment is declarative config. A deterministic scorer rates each prompt's complexity before any model runs, and that score plus budget state picks the tier: under budget pressure work degrades to progressively cheaper models instead of failing, and only background work can be blocked outright. A health tracker cools down rate-limited models so calls skip known walls, a first-token watchdog catches models that stall without emitting anything, and an exhausted chain degrades to a usable message instead of crashing the run.

**Cost-aware selection, decided before the call.** The scorer rates complexity 1-5 (word count, keyword classes, code markers, the agent's role weight, conversation depth) with no model in the loop. Under ~80% of the monthly budget everyone runs on their assigned model; 80-95% downgrades only trivial tasks; 95-100% downgrades everything except essential high-complexity work; at 100% it fails closed on non-essential calls. Spend is tracked per request against a hard monthly ceiling, with crash-safe atomic writes so the ledger survives a restart.

**Health-aware fallback.** In the ADK version I built on, the model wrapper called the provider directly and didn't consult the underlying library's fallback config, so that global setting did nothing. I found that gap and wrapped the model layer with one that actually implements it:

- A singleton **health tracker** records any model that returns a rate-limit and puts it in an **escalating cooldown** that grows with repeat offenses, up to a cap. Future calls preemptively skip a cooling-down model instead of re-hitting a wall.
- A **time-to-first-token watchdog** bounds only the *first* response of each attempt. A model that stalls and emits nothing trips it and the call falls over to the next model; because nothing was yielded yet, there's no duplicate output. Once a real stream starts it runs unbounded, with a longer outer timeout as backstop.
- A fallback model that can't accept the tool definitions is detected and skipped as a compatibility miss, not surfaced as a failure.
- If the *entire* chain is exhausted, the layer yields a graceful "this specialist is temporarily unavailable, others are still available" message rather than crashing the run group.

The chains deliberately end on *different* terminal models, so no two roles share a last resort, and any workload can be pinned to a model running on the box itself as the escape hatch when every hosted provider is unhappy.

**Evaluation is separated by design.** The evaluator scores output on a different model family than the agents that produced it, and the reviewer is a separate instance kept off the write path by policy. Nothing grades its own homework.

**The failure that taught me the most was silent.** Agents would intermittently get worse, more hedging and the occasional refusal, with nothing in the error logs. It wasn't the prompts. Under budget pressure the cost router was quietly swapping an agent's model for a cheaper one that returned a success code while behaving differently. Silent degradation is worse than a hard failure, because you debug the wrong layer for an hour first. The fix was observability on the swap itself: every cost-router substitution now shows up on the result card's model label and in tracing, so the first question on any behavioral regression is "which model actually served this call?" before anyone touches the prompt.

**Go look at:** the resilient-call pattern in [`examples/model_fallback.py`](examples/model_fallback.py), with the design decisions defended in the comments · the budget and threshold structure in [`examples/model-routing.example.yaml`](examples/model-routing.example.yaml) · the cost and model label on every card in the [live demo](https://pacslate.com/demo).

</details>

<details markdown="1">
<summary><strong>4 · Operations, limits, and rebuilding it yourself</strong> · versioned, deployed, honest about scope</summary>

**The claim: this runs as versioned, monitored infrastructure with a gated deployment path, and its limits are stated rather than implied.**

**Operations.**

- **Containerized and network-segmented.** Docker services across four core network tiers (public-facing, internal backend, outbound-capable, and an isolated sandbox), plus a couple of purpose-built networks, so the blast radius of any one service is bounded. Public ingress is through a Cloudflare Tunnel; the origin isn't directly exposed.
- **Sandboxed code execution.** Agent-run code executes in an isolated sandbox (ephemeral workspace, hardened runtime) on its own network tier.
- **Health-gated deployment.** A push triggers pull, smart rebuild, health check, and a **build-provenance gate that asserts the running build actually matches what was deployed** before it's considered green, so a "successful" deploy that didn't actually swap the image gets caught. A drift-check job reconciles configuration automatically.
- **Self-maintaining.** A watchdog flags dependency and security updates; low-risk ones are auto-merged through CI checks, and the decisions that genuinely need me escalate.
- **Observability.** Spend attributed per request and per model; every call and every model swap traced.

**Known limits, stated plainly.**

- **Built for one.** Single operator, single user, by design. The reliability and privilege patterns here are real mechanisms, but they operate at personal scale; nothing on this page claims enterprise load, multi-tenancy, or an adversarial threat model.
- **One router in the path.** Hosted models are reached through a single gateway today, so a router outage is the shared dependency. Mitigated by pinning a workload to the local model, not eliminated.
- **The demo is representative, not connected.** The real interface on sample data; it doesn't touch the running system.
- **The semantic-memory layer is a hosted service.** The one cloud dependency in an otherwise local stack, swappable, and not the system of record.
- **Retrieval quality is a moving target.** Hybrid retrieval covers more ground than keyword alone, but tuning what surfaces first is ongoing work rather than a solved problem.
- **Not a high-security or classified design.** It's serious about data control, not a threat model against a determined adversary.

**Rebuilding it yourself.** This is a recipe you adapt, not a product you install. The point isn't my exact build: you point your own coding agent at this architecture and have it rebuild the parts you want, with whatever you already have. A workable floor is a ~$20/mo coding assistant as the driver, a small ~$20/mo server for the always-on part, and metered model calls that run on the order of $10-40/mo at a normal personal load. So roughly $50-80/mo, and you scale up only where you want depth: a bigger box to host models yourself, premium models for the reasoning seats. The structure doesn't change. The cost discipline that makes that floor real (complexity-scored routing, cheap-model defaults, a hard ceiling) is the same machinery in section 3. My own build runs heavier because I develop it daily; the architecture is what keeps it cheap when you don't.

**Selected artifacts.**

- [`examples/model-routing.example.yaml`](examples/model-routing.example.yaml) is the real config structure (role-to-model routing, cost router, fallback chains) with illustrative model IDs and numbers, since the lineup rotates by design.
- [`examples/model_fallback.py`](examples/model_fallback.py) is the resilient-call fallback pattern, simplified, with the design decisions worth defending in the comments.

**Labels and dates.** Everything demonstrated publicly on this page is sample or redacted data, labeled where it appears. Counts were verified against the running system in August 2026.

</details>

---

The goal was to take agentic AI from an architecture diagram to something that actually runs every day, under real cost, reliability, and privacy constraints, and to keep it honest about what it is.

*The running system is private by design. This page describes its architecture and the decisions behind it, not the live deployment.*
