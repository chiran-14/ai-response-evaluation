# AI Response Evaluation

A runnable AI testing learning project by Chiranjeevi Neerukattu. Evaluate recorded responses against versioned cases, detect known regressions, generate HTML/JSON reports, and fail CI when the pass-rate threshold is missed.

This is an evaluation harness, not a trained model or an LLM chatbot. Included responses are hand-authored synthetic fixtures, not measurements from a real model. No paid API, credentials, network service, or third-party package is required.

## Run it

Requires Python 3.11 or newer. Run commands from this repository root.

```bash
python -m unittest discover -s tests -v
python -m ai_eval.runner
```

Open `reports/latest/report.html` for a readable report. The reference fixture passes 12/12 configured cases. Try the deliberately regressed fixture:

```bash
python -m ai_eval.runner --responses data/responses-regression.jsonl --output reports/regression
```

This returns exit code **1**, with 8/12 passing, detecting an incorrect toll rate, a prompt-injection sentinel, an unsupported booking confirmation, and a fabricated citation. These are fixture outcomes, not a model benchmark.

## Evaluate actual AI outputs

1. Choose a model or assistant you have access to. Supply the prompt/context from each record in `data/cases.jsonl`.
2. Save its unedited response as one JSON line with the matching `id`, an `answer` string, and a `citations` list. If citations are absent, use an empty list; do not invent them to make a check pass.
3. Record model/version, generation settings, collection date, and relevant system instructions in your own experiment notes. Collect multiple runs to study variability.
4. Run the evaluator against the saved file:

```bash
python -m ai_eval.runner --responses my-responses.jsonl --output reports/my-run
```

Example response record:

```json
{"id":"car-rate","answer":"The toll is 250 cents.","citations":["rates-v1"]}
```

The harness never sends prompts to a model by itself. You control response collection, cost, and data sharing. Missing response IDs fail their cases. Unknown or duplicate IDs are configuration errors; they do not silently improve the score.

## Rubric and output

| Check | What it actually verifies |
| --- | --- |
| Required content | At least one phrase in every configured alternative group appears |
| Forbidden content | None of the case-specific prohibited phrases appears |
| Citation allowlist | Every citation ID is explicitly allowed for the case |
| Required citations | Required IDs are present |
| Abstention language | A configured uncertainty phrase is present |
| Response schema | Nonempty answer plus list of nonempty citation strings |

A case passes only if all of its configured checks pass. Pass rate = passing cases / all dataset cases. The default threshold is 1.0; set `--min-pass-rate 0.9` to require at least 90%. Exit codes: 0 threshold met, 1 threshold missed, 2 invalid input/configuration.

Reports contain case IDs and pass/fail details, not full response text. Input fixtures are synthetic; do not commit private data or credentials when adding experiments.

## Important limits

Phrase matching is a regression signal, not semantic truth, groundedness, or a safety guarantee. A response can include a required phrase and still be wrong. Allowed citation IDs do not prove that a claim is supported by a source. Abstention words can be present in a misleading answer. Prompt injection has only a small sentinel-based example here. Human review and broader, domain-specific evaluation are still needed. See [rubric notes](docs/rubric.md).

## Layout

- `ai_eval/runner.py`: CLI, validation, scoring, HTML/JSON reporting.
- `data/cases.jsonl`: 12 synthetic tolling/support cases and explicit expectations.
- `data/responses-reference.jsonl`: hand-authored passing reference fixture.
- `data/responses-regression.jsonl`: four controlled regressions.
- `tests/test_evaluation.py`: scoring and input-validation tests.
- `.github/workflows/tests.yml`: CI and report artifact configuration.

## Next learning steps

Collect real model outputs, add paraphrase and adversarial examples, review false positives/negatives, and compare repeated runs. Add an optional model adapter only after deciding how keys and costs should be handled.
