---
description: Find the runs that misbehaved, encode the rule they broke, replay the fix against them, and prove the safe cases still hold.
icon: arrows-rotate
---

# Replay and improve

Replay is why the recording exists. Ten real runs of `returns-resolver` are sitting on your server from the [record stage](01-durable-agent.md). This page finds the ones that misbehaved, turns the support lead's judgment into an evaluator, replays an improved agent version against exactly those runs — and against the runs that must *not* change — and reads the evidence. What arrives as a failing run leaves as a regression check.

This is the part other tooling can't do. An eval re-grades outputs after the fact. Replay re-executes the actual run against your real code with one thing changed, so you find out what *would have happened* if you'd shipped the change.

## Find useful starting points

The built-in evaluators make no model calls — they're cheap signals for where to look:

```bash
uv run kitaru session evaluate \
  --tag returns-baseline \
  --evaluator cost@latest \
  --evaluator latency@latest \
  --evaluator tool-call-patterns@latest \
  --wait

uv run kitaru evaluation list --size 100
```

Cost and latency show resource variation across the ten runs; tool-call patterns expose repeated lookups and diverging investigation paths. But broad evaluators describe sessions — they can't decide what *good* means for your business. That takes a human look.

## Record the human judgment

Ticket 004 issued a $280 refund — above the automatic approval threshold. Instead of a vibe in a meeting, record the review as an [investigation](https://docs.zenml.io/kitaru/concepts/investigations): fixed questions, the session under review, and a curated view pointing at the exact node that needs eyes. (The shell variables here — the session and node ids — are captured with `kitaru --output json session list ... | jq`; the example README shows the exact plumbing.)

```bash
uv run kitaru investigation create refund-policy-review \
  --agent returns-resolver \
  --description "Review whether risky refunds require human approval." \
  --question 'outcome=Is this outcome acceptable, problematic, or uncertain, and why?' \
  --question 'expected=What should the agent have done in this case?' \
  --session "$TICKET_004_SESSION_ID"
```

The support lead's answers land as **annotations**, anchored to the refund node itself:

```bash
uv run kitaru annotation create \
  --investigation-session "$INVESTIGATION_SESSION_ID" \
  --question-key outcome \
  --selector "{\"node_id\":\"$TICKET_004_REFUND_NODE_ID\",\"part\":\"output\"}" \
  --value '{"judgment":"problematic","reason":"The amount exceeds the automatic approval threshold."}'
```

The verdict: refunds above the approval threshold, and refunds on risk-flagged orders, must escalate to a human. Valid refunds must stay refunds. That's a rule — and a rule can be code.

## Encode the rule as an evaluator

An [evaluator](https://docs.zenml.io/kitaru/concepts/evaluators) is a Python function that applies the same check to every recorded or replayed session. `returns-policy` reads each session's final action and accepted tool calls and writes one Boolean result, `policy_correct`:

```bash
uv run kitaru evaluator scaffold returns-policy --path evaluator.py
# implement the rubric — the full evaluator is in the example README
uv run kitaru evaluator register returns-policy \
  --script evaluator.py --entrypoint evaluate
```

Run it over the whole baseline:

```bash
uv run kitaru session evaluate \
  --tag returns-baseline \
  --evaluator returns-policy@1 \
  --wait
```

**Eight passes, two failures.** Tickets 004 and 007 issued refunds where the reviewed policy requires escalation. The human judgment is now a versioned check that will apply identically to every replay — which is what makes the comparison ahead trustworthy.

## Freeze the populations

Two [cohorts](https://docs.zenml.io/kitaru/concepts/cohorts), each an immutable snapshot: the behavior that must change, and the nearby behavior that must not regress.

```bash
uv run kitaru cohort create unsafe-refund-baseline \
  --agent returns-resolver \
  --description "Baseline sessions that refunded despite an approval or risk rule requiring escalation." \
  --session TICKET_004_SESSION_ID \
  --session TICKET_007_SESSION_ID

uv run kitaru cohort create safe-refund-control \
  --agent returns-resolver \
  --description "Valid refund sessions that must remain correct after the policy change." \
  --session TICKET_001_SESSION_ID \
  --session TICKET_009_SESSION_ID \
  --session TICKET_010_SESSION_ID
```

Immutability is the point: version 1 of each cohort is always the same sessions, so "both risky cases became correct and no control case regressed" stays checkable forever.

## Register the candidate

The baseline agent assumed its action tools enforce approval limits. The candidate removes that assumption — it must inspect risk flags, thresholds, and return windows *before* calling `issue_refund`. Same entrypoint, one environment switch:

```bash
uv run kitaru agent version register \
  returns-resolver \
  --command "python -m examples.canonical_example.agent" \
  --display-version strict-policy-v2 \
  --working-dir ../.. \
  --env RETURNS_POLICY_MODE=strict \
  --timeout-seconds 180 \
  --tool lookup_order --tool get_return_policy --tool check_shipping \
  --tool issue_refund --tool create_replacement --tool escalate_to_human
```

That's `returns-resolver@2`. The imported sessions stay attached to version 1 — the change is a new version, never a rewrite of history.

## Run the experiment

An [experiment](https://docs.zenml.io/kitaru/concepts/experiments) names the change once — evaluators and tool policy resolved to immutable versions — and each run replays one cohort through it:

```bash
uv run kitaru experiment create improve-returns-policy \
  --description "Replay policy-risk and valid-refund cohorts with strict refund approval rules." \
  --tool-policy '{"default":{"type":"passthrough"},"tools":{}}' \
  --evaluator returns-policy@1 \
  --evaluator cost@latest --evaluator latency@latest \
  --evaluator tool-call-patterns@latest

uv run kitaru experiment run start improve-returns-policy \
  --cohort-version "$TARGET_COHORT_VERSION_ID" \
  --agent returns-resolver@2 \
  --evaluate-baselines --wait --timeout 1800

uv run kitaru experiment run start improve-returns-policy \
  --cohort-version "$CONTROL_COHORT_VERSION_ID" \
  --agent returns-resolver@2 \
  --evaluate-baselines --wait --timeout 1800
```

Two things here are load-bearing:

* **`--evaluate-baselines`** applies the same resolved evaluator versions to the imported originals and the replays, so both sides of the diff were judged by identical code.
* **The [tool policy](https://docs.zenml.io/kitaru/guides/tool-policies)** decides what a replayed tool call touches. This example sets `passthrough` explicitly because its commerce tools are mocks against a fresh in-memory store — safe to call again. For an agent with real side effects, the posture flips: `{"type": "history", "scope": "cohort_version", "on_miss": "fail"}` answers tool calls from the recordings and guarantees nothing unrecorded executes. No card gets refunded twice by a replay.

## Read the evidence

```bash
uv run kitaru experiment run list --size 20
uv run kitaru session list --agent returns-resolver --origin replay --size 20
uv run kitaru evaluation list \
  --filter '{"field":"name","op":"eq","value":"policy_correct"}' \
  --size 100
```

The candidate succeeds when tickets 004 and 007 flip from policy failure to pass, tickets 001, 009, and 010 remain passes, and every replay completes. The dashboard at `http://localhost:8000` puts each imported session next to its replay — the changed tool path, policy correctness, latency, and tool-call patterns side by side. A failed replay is still evidence: inspect it, change the agent again, register version 3, and rerun the same immutable experiment and cohort versions. And because `--wait` exits nonzero when a run fails, the exact command you just ran doubles as a CI gate.

## Let an agent drive it

Every step above is scriptable — the CLI takes `--output json` everywhere, and an [MCP server](https://docs.zenml.io/kitaru/agent-native/mcp-server) exposes the same loop as capability-gated tools. The example ships an [agent-guided path](https://github.com/zenml-io/kitaru/tree/develop/examples/canonical_example) where a coding agent inspects the traces, interviews you for the behavior rubric, proposes evidence-backed cohort membership, and authors the evaluator — the same steps this page walked, driven by Claude Code or Codex while you review. Give it the discipline you just practiced: judge with versioned evaluators, freeze cohorts before comparing, change one variable per experiment.
