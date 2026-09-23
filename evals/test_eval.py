"""grader와 regression 검출 경로의 자체 검증."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from run_eval import ROOT, grade, structural_errors


class TestGrader(unittest.TestCase):
    def test_code_literals_are_not_scanned_as_markup(self):
        self.assertEqual([], structural_errors('{code}\n{info}\n```\n{code}\n'))

    def test_unclosed_code_is_rejected(self):
        self.assertIn('닫히지 않은 code 블록', structural_errors('{code:language=sql}\nSELECT 1;\n'))

    def test_unclosed_box_is_rejected(self):
        self.assertTrue(structural_errors('{note:title=참고}\n본문\n'))

    def test_forbidden_language_is_rejected(self):
        self.assertTrue(structural_errors('{code:language=json}\n{}\n{code}\n'))

    def test_extra_text_is_rejected(self):
        self.assertTrue(grade('h1. 제목\n', 'h1. 제목\n추가 설명\n'))

    def test_balanced_nested_code_is_accepted(self):
        value = '{info:title=Info}\n{code}\n{x}\n{code}\n{info}\n'
        self.assertEqual([], grade(value, value))

    def test_cli_report_baseline_and_injected_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            skill = work / 'skill'
            shutil.copytree(ROOT, skill, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            runner = skill / 'evals/run_eval.py'
            baseline = work / 'baseline.json'
            current = work / 'current.json'
            def run(*args):
                return subprocess.run([sys.executable, '-B', str(runner), *map(str, args)],
                                      capture_output=True, text=True, timeout=60)
            result = run('--report', baseline)
            before = json.loads(baseline.read_text())
            self.assertEqual(result.returncode, int(before['summary']['failed'] > 0))
            result = run('--baseline', baseline, '--report', current)
            self.assertEqual([], json.loads(current.read_text())['comparison']['regressions'])
            artifacts = work / 'artifacts'
            artifacts.mkdir()
            cases = json.loads((skill / 'evals/cases.json').read_text())['cases']
            for case in cases:
                (artifacts / (case['id'] + '.wiki')).write_text(case['expected'])
            result = run('--artifacts-dir', artifacts, '--report', current)
            self.assertEqual(0, result.returncode, result.stderr)
            (artifacts / 'headings.wiki').unlink()
            result = run('--artifacts-dir', artifacts, '--report', current)
            self.assertEqual(1, result.returncode)
            missing = next(row for row in json.loads(current.read_text())['cases']
                           if row['id'] == 'dataset:headings')
            self.assertIn('FileNotFoundError', missing['reasons'][0])
            converter = skill / 'scripts/md_to_confluence.py'
            text = converter.read_text()
            old = "output.append(f'h{level}. {text}')"
            self.assertIn(old, text)
            converter.write_text(text.replace(old, "output.append(f'BROKEN{level}. {text}')"))
            result = run('--baseline', baseline, '--report', current)
            self.assertEqual(1, result.returncode)
            report = json.loads(current.read_text())
            self.assertIn('dataset:headings', report['comparison']['regressions'])
            self.assertLess(report['comparison']['pass_rate_delta'], 0)
            dataset = skill / 'evals/cases.json'
            data = json.loads(dataset.read_text())
            data['cases'][0]['expected'] += 'changed\n'
            dataset.write_text(json.dumps(data))
            result = run('--baseline', baseline, '--report', work / 'invalid.json')
            self.assertEqual(2, result.returncode)
            self.assertFalse((work / 'invalid.json').exists())


if __name__ == '__main__':
    unittest.main()
