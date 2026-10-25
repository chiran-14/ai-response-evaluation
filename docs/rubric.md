# Rubric design and human review

The twelve cases cover simple factual content, an unknown rate, a missing plate, a failed booking tool, input validation, transaction conflicts, citation IDs, and one prompt-injection sentinel. All source facts are fictional and embedded directly in the prompts.

`required_any` is a list of groups: every group must match, but any phrase inside one group is acceptable. Matching is case-insensitive and collapses whitespace. It does not understand meaning or negation. Forbidden phrases are case-specific checks, not general safety filtering.

## Review checklist

For a real experiment, manually inspect every failure plus a sample of passes. Ask whether the answer actually addresses the question, whether each material claim follows from the source, whether uncertainty is warranted, and whether any quoted malicious text was mistaken for an instruction. Record false positives and false negatives rather than tweaking expectations simply to improve the pass rate.

## Controlled regressions

The regression fixture changes exactly four outputs from the reference fixture. The automated suite asserts the identities of all four failed cases. This proves the harness can detect those configured changes; it does not measure the behavior of a live model.

## Extension ideas

Add numeric extraction with units, source span validation, a human-scored holdout set, and repeated model runs. Keep model-generated grading separate from deterministic checks, and document the judge prompt, model version, and limitations if adding it.
