"""Evaluate recorded responses against an explicit, limited rule-based rubric."""
import argparse
import html
import json
import re
from pathlib import Path


def load_jsonl(path):
    rows = []
    seen = set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON") from exc
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError(f"{path}:{number}: nonempty string id required")
        if row["id"] in seen:
            raise ValueError(f"{path}:{number}: duplicate id {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no records")
    return rows


def normalized(text):
    return re.sub(r"\s+", " ", text.casefold()).strip()


def string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def validate_cases(cases):
    for case in cases:
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            raise ValueError(f"{case['id']}: prompt required")
        for name in ("allowed_citations", "required_citations", "forbidden"):
            if not string_list(case.get(name, [])):
                raise ValueError(f"{case['id']}: {name} must be a list of nonempty strings")
        if not set(case.get("required_citations", [])).issubset(case.get("allowed_citations", [])):
            raise ValueError(f"{case['id']}: required citations must be allowed")
        groups = case.get("required_any", [])
        if not isinstance(groups, list) or any(not string_list(group) or not group for group in groups):
            raise ValueError(f"{case['id']}: required_any must contain nonempty lists of phrases")
        if not isinstance(case.get("must_abstain", False), bool):
            raise ValueError(f"{case['id']}: must_abstain must be boolean")
        if not groups and not case.get("forbidden") and not case.get("required_citations") and not case.get("must_abstain"):
            raise ValueError(f"{case['id']}: at least one substantive check required")


def evaluate_case(case, response):
    if response is None:
        return {"id": case["id"], "passed": False, "checks": {"response_present": False}}
    answer = response.get("answer")
    citations = response.get("citations")
    schema_ok = isinstance(answer, str) and bool(answer.strip()) and string_list(citations)
    if not schema_ok:
        return {"id": case["id"], "passed": False, "checks": {"response_schema": False}}
    text = normalized(answer)
    groups = case.get("required_any", [])
    checks = {
        "response_schema": True,
        "required_content": all(any(normalized(phrase) in text for phrase in group) for group in groups),
        "forbidden_content_absent": not any(normalized(phrase) in text for phrase in case.get("forbidden", [])),
        "citation_allowlist": set(citations).issubset(case.get("allowed_citations", [])),
        "required_citations": set(case.get("required_citations", [])).issubset(citations),
    }
    if case.get("must_abstain"):
        markers = ("cannot determine", "not enough information", "not provided", "unable to confirm", "cannot confirm")
        checks["abstention_language"] = any(marker in text for marker in markers)
    return {"id": case["id"], "passed": all(checks.values()), "checks": checks}


def evaluate(cases, responses):
    if not cases:
        raise ValueError("Dataset must not be empty")
    validate_cases(cases)
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate case IDs")
    response_ids = [response["id"] for response in responses]
    if len(response_ids) != len(set(response_ids)):
        raise ValueError("Duplicate response IDs")
    extra = set(response_ids) - set(case_ids)
    if extra:
        raise ValueError("Unknown response IDs: " + ", ".join(sorted(extra)))
    lookup = {row["id"]: row for row in responses}
    results = [evaluate_case(case, lookup.get(case["id"])) for case in cases]
    passed = sum(item["passed"] for item in results)
    return {"rubric": "Deterministic content/citation checks; not a semantic correctness or safety guarantee",
            "total": len(results), "passed": passed, "failed": len(results)-passed,
            "pass_rate": passed/len(results), "results": results}


def save_report(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = []
    for item in report["results"]:
        failures = ", ".join(key for key, value in item["checks"].items() if not value) or "All configured checks passed"
        rows.append(f"<tr><td>{html.escape(item['id'])}</td><td>{'PASS' if item['passed'] else 'FAIL'}</td><td>{html.escape(failures)}</td></tr>")
    page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>AI response evaluation report</title><style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:20px;background:#0a121c;color:#edf4f7}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #365448}}h1{{color:#93efcf}}</style>
    <h1>AI response evaluation</h1><p>{report['passed']} / {report['total']} passed · {report['pass_rate']:.0%} pass rate</p>
    <p>{html.escape(report['rubric'])}</p><table><thead><tr><th>Case</th><th>Result</th><th>Details</th></tr></thead><tbody>{''.join(rows)}</tbody></table></html>"""
    (directory / "report.html").write_text(page, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/cases.jsonl")
    parser.add_argument("--responses", default="data/responses-reference.jsonl")
    parser.add_argument("--output", default="reports/latest")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args(argv)
    if not 0 <= args.min_pass_rate <= 1:
        parser.error("--min-pass-rate must be between 0 and 1")
    try:
        report = evaluate(load_jsonl(args.dataset), load_jsonl(args.responses))
        save_report(report, Path(args.output))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Invalid evaluation input: {exc}\n")
    print(f"{report['passed']}/{report['total']} passed ({report['pass_rate']:.0%}); report: {args.output}")
    return 0 if report["pass_rate"] >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
