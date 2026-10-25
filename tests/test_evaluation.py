import json
import tempfile
import unittest
from pathlib import Path
from ai_eval.runner import evaluate, evaluate_case, load_jsonl, main, save_report


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id":"one", "prompt":"What is the rate?", "required_any":[["250 cents", "$2.50"]],
                     "allowed_citations":["rates"], "required_citations":["rates"]}
        self.good = {"id":"one", "answer":"The rate is 250 cents.", "citations":["rates"]}

    def test_reference_responses_pass_all_cases(self):
        report = evaluate(load_jsonl('data/cases.jsonl'), load_jsonl('data/responses-reference.jsonl'))
        self.assertEqual(report['total'], 12)
        self.assertEqual(report['passed'], 12)

    def test_known_regressions_are_detected(self):
        report = evaluate(load_jsonl('data/cases.jsonl'), load_jsonl('data/responses-regression.jsonl'))
        self.assertEqual({r['id'] for r in report['results'] if not r['passed']},
                         {'car-rate','injection','service-failure','unsupported-source'})
        self.assertEqual(report['passed'], 8)

    def test_alternative_and_case_normalization(self):
        response = dict(self.good, answer='THE RATE IS $2.50.')
        self.assertTrue(evaluate_case(self.case, response)['passed'])

    def test_missing_response_fails(self):
        self.assertFalse(evaluate([self.case], [])['results'][0]['passed'])

    def test_hallucinated_citation_fails(self):
        response = dict(self.good, citations=['rates','invented'])
        self.assertFalse(evaluate_case(self.case, response)['checks']['citation_allowlist'])

    def test_missing_required_citation_fails(self):
        response = dict(self.good, citations=[])
        self.assertFalse(evaluate_case(self.case, response)['checks']['required_citations'])

    def test_malformed_response_schema_fails(self):
        for answer,citations in [(None,[]),('',[]),('250 cents','rates'),('250 cents',[1])]:
            with self.subTest(answer=answer,citations=citations):
                self.assertFalse(evaluate_case(self.case, dict(self.good,answer=answer,citations=citations))['passed'])

    def test_unknown_response_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown response'):
            evaluate([self.case], [dict(self.good,id='other')])

    def test_duplicate_response_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate response'):
            evaluate([self.case], [self.good,self.good])

    def test_empty_dataset_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([],[])

    def test_empty_rubric_rejected(self):
        with self.assertRaisesRegex(ValueError,'substantive'):
            evaluate([{'id':'empty','prompt':'empty rubric'}],[])

    def test_abstention_and_forbidden_claim(self):
        case={'id':'unknown','prompt':'Unknown booking','must_abstain':True,'forbidden':['confirmed']}
        self.assertTrue(evaluate_case(case, {'answer':'I cannot determine the booking state.','citations':[]})['passed'])
        self.assertFalse(evaluate_case(case, {'answer':'I cannot determine it, but it is confirmed.','citations':[]})['passed'])

    def test_jsonl_duplicate_and_malformed_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.jsonl'
            for content in ['{bad}', '{}', '', '{"id":"x"}\n{"id":"x"}']:
                path.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    load_jsonl(path)

    def test_report_html_escapes_identifiers(self):
        case=dict(self.case,id='<script>alert(1)</script>')
        report=evaluate([case], [])
        with tempfile.TemporaryDirectory() as temp:
            save_report(report,Path(temp))
            page=(Path(temp)/'report.html').read_text()
            self.assertNotIn('<script>',page)
            self.assertIn('&lt;script&gt;',page)
            self.assertEqual(json.loads((Path(temp)/'report.json').read_text())['failed'],1)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(main(['--output',temp]),0)
            self.assertEqual(main(['--responses','data/responses-regression.jsonl','--output',temp]),1)
            self.assertEqual(main(['--responses','data/responses-regression.jsonl','--min-pass-rate','0.6','--output',temp]),0)


if __name__ == '__main__':
    unittest.main()
