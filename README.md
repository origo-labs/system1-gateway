# GLiNER System-1 Gateway

Fast, local, typed decisions for the part of an application that usually gets
called a “tool call”. The gateway turns a message, ticket, alert, or command
into intent, entities, routing, approval, and confidence:

```json
{"intent":"billing_duplicate_charge",
 "entities": {"amount":"€49.00"},
 "route":"billing_queue",
 "status":"accepted",
 "auto_executable":true,
 "confidence":0.95}
```

GLiNER is a model family for extracting entities and making schema-defined
classifications. GLiNER2.5 performs the local semantic step. Typed policy code
handles thresholds, approval, abstention, routing, idempotency, and side effects.

## The proposition

### Credit to Fastino

This project builds on Fastino’s work. The Fastino team created the GLiNER2.5
architecture and released GLiNER2.5-Decide as an open-weight, Apache 2.0
specialist for schema-defined decisions. Their work turns the idea of a small
local decision model into a practical, reusable foundation: typed questions,
constrained answers, confidence scores, span extraction, and related outputs
can be evaluated in one model call. We are grateful to the Fastino researchers
and engineers for making that capability available to the community. See their
[GLiNER2.5-Decide announcement](https://fastino.ai/blog/gliner-2-5-decide-open-weight-decision-model)
and [open model](https://huggingface.co/fastino/GLiNER2.5-Decide).

Jev is a useful reference point: its public description reduces System-1 work
to three primitives—Choice, Score, and Noul. Choice selects one option. Score
orders a state against levels. Noul evaluates a yes/no statement. Jev targets
structured decisions rather than natural-language writing. See the public
[Jev reference](https://en.wikipedia.org/wiki/Jev_(AI_model)).

But a hosted proprietary model is not the only way to implement those
primitives. When the result is a finite choice plus a few arguments, a local
encoder and policy layer can be simpler to deploy and inspect:

- no inference API bill or network dependency;
- no ticket or alert leaving the device;
- explicit abstention instead of confident free-form text;
- typed output tested like ordinary application code.

This is not a claim that a small model replaces frontier models for writing,
research, or open-ended planning. The narrower claim is:

> If the application only needs to choose a route, fill arguments, score a
> state, or decide whether a rule applies, use a small local decision system.

## Why not Needle 3 for everything?

Needle 3 makes a related embedded-device case: a compact quantized model,
structured JSON, tool calls, and extraction. Its public page describes an
8–29 MB model and positions it against larger models on mobile tool calls and
extraction. See the public [Needle 3 page](https://cactuscompute.com/needle).

That is a strong fit when an application needs a compact generative tool-call
model. It is more machinery than necessary for a narrow, known decision
schema. Often the “tool call” is simply:

```text
message → intent + entities → policy check → route/action
```

The gateway makes that boundary explicit: the semantic model proposes a typed
decision and deterministic code validates it.

## Included

- Local GLiNER2.5 classification with explicit label descriptions
- Configurable domain packs for intents, routes, approvals, and per-intent thresholds
- Extraction of amounts, temperatures, email addresses, and ticket IDs
- `accepted`, `abstained`, and `escalated` decision states
- Separate `auto_executable` safety decision for low-risk routes
- Dry-run action adapter with idempotency protection
- CLI, JSONL stream, and local HTTP interfaces
- Warm-up/readiness and source provenance reporting
- Cold-start, warm-latency, throughput, abstention, and calibration metrics
- Deterministic baseline for contract tests without model weights

## Quick start

```bash
uv sync
uv run system1-gateway --text "The warehouse temperature is 9 C"
```

The first command uses the deterministic contract baseline. Run real local
GLiNER2.5 explicitly:

```bash
uv run system1-gateway --model --text "The warehouse temperature is 9 C"
```

Use the operationally fine-tuned Decide checkpoint:

```bash
uv run system1-gateway --model fastino/GLiNER2.5-Decide \
  --text "Please deploy checkout to production"
```

For a long-lived JSONL process:

```bash
printf '%s\n' '{"text":"My card was charged twice","source":"support"}' \
  | uv run system1-stream
```

For HTTP:

```bash
uv run system1-http --model fastino/GLiNER2.5-Decide --warmup
curl -s http://127.0.0.1:8765/decide \
  -H 'content-type: application/json' \\
  -d '{"text":"Please deploy checkout to production","source":"ops"}'
```

Open `http://127.0.0.1:8765/` for the local dashboard. It shows readiness,
intent, route, extracted entities, confidence, policy reason, execution safety,
and the complete JSON envelope for each decision.

Pass `--config path/to/domain.json` to use a validated domain pack. Custom
intent labels do not require Python changes.

The packaged `src/system1_gateway/default_config.json` is the single default
domain pack. A custom pack can override intent descriptions, routes, approval
requirements, and confidence thresholds without changing Python code.

## Safety model

The model never directly executes a privileged action:

1. Low-confidence or unsupported inputs become `abstained`.
2. High-risk inputs become `escalated`.
3. Correct classification does not imply execution permission.
4. Only an explicit low-risk route allowlist can set `auto_executable: true`.
5. The default adapter is dry-run and suppresses duplicate idempotency keys.

External adapters are an explicit integration choice.

## Measurements

The included report measures Choice, Score, and Noul-style tasks for this
repository. On the recorded Apple Silicon run, native small GLiNER reached
100% Choice accuracy, 83.3% Score accuracy, and 31.36 ms p99 latency. p99 is
the latency below which 99% of measured requests completed. Run the report
with:

```bash
uv run system1-report --model
```

These measurements apply to the recorded implementation and fixtures, not to
every workload.

Evaluate a labeled, customer-shaped fixture with per-intent metrics:

```bash
uv run system1-evaluate fixtures/ops_sample.jsonl
uv run system1-evaluate fixtures/ops_sample.jsonl --model
```

The report separates intent accuracy, policy acceptance coverage, and
`auto_route_coverage`. The bundled operations fixture is a regression example,
not a claim of production accuracy.

## Development

```bash
uv sync
uv run pytest -q tests
uv build
```

See [PLAN.md](PLAN.md) and [REFINEMENT_PLAN.md](REFINEMENT_PLAN.md) for the
design and implementation history.
