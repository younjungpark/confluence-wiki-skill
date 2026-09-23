#!/usr/bin/env python3
"""표준 라이브러리만 사용하는 Confluence 변환 회귀 평가."""
import argparse
import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def digest(data):
    return hashlib.sha256(data).hexdigest()


def summary(rows):
    passed = sum(row['status'] == 'PASS' for row in rows)
    return dict(total=len(rows), passed=passed, failed=len(rows)-passed,
                pass_rate=round(100 * passed / len(rows), 2) if rows else 0.0)


def structural_errors(text):
    """코드 본문을 해석하지 않고 생성된 블록의 닫힘/언어를 검사한다."""
    stack, errors = [], []
    in_code = False
    for number, line in enumerate(text.splitlines(), 1):
        if in_code:
            if line == '{code}':
                in_code = False
            continue
        if re.fullmatch(r'\{code(?::[^}]*)?\}', line):
            if re.search(r'(?:language=|code:)(?:json|yaml)(?:[|}]|$)', line):
                errors.append(f'{number}행: 지원하지 않는 code 언어: {line}')
            in_code = True
            continue
        match = re.fullmatch(r'\{(info|warning|note|tip|quote)(:[^}]*)?\}', line)
        if match:
            tag, options = match.groups()
            if not options and stack and stack[-1] == tag:
                stack.pop()
            else:
                stack.append(tag)
        if line.lstrip().startswith('```'):
            errors.append(f'{number}행: Markdown fence 잔존')
    if in_code:
        errors.append('닫히지 않은 code 블록')
    if stack:
        errors.append('닫히지 않거나 잘못 중첩된 박스: ' + ', '.join(stack))
    return errors


def grade(expected, actual):
    errors = structural_errors(actual)
    if actual != expected:
        diff = ''.join(difflib.unified_diff(expected.splitlines(True),
                       actual.splitlines(True), fromfile='expected', tofile='actual'))
        errors.append('전체 출력 불일치\n' + diff)
    return errors


class RecordedResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = []

    def startTest(self, test):
        super().startTest(test)
        self.current = dict(id='unit:' + test.id(), category='existing-unit',
                            status='PASS', reasons=[])

    def stopTest(self, test):
        self.rows.append(self.current)
        super().stopTest(test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.current['status'] = 'FAIL'
        self.current['reasons'].append(self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.current['status'] = 'FAIL'
        self.current['reasons'].append(self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.current['status'] = 'FAIL'
        self.current['reasons'].append('검증 미실행: ' + reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.current['status'] = 'FAIL'
        self.current['reasons'].append('expected failure: ' + self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.current['status'] = 'FAIL'
        self.current['reasons'].append('unexpected success: 테스트 정의 확인 필요')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.current['status'] = 'FAIL'
            self.current['reasons'].append(str(subtest) + ': ' + self._exc_info_to_string(err, test))


def existing_tests(root):
    spec = importlib.util.spec_from_file_location('eval_existing_tests', root / 'tests/test_converter.py')
    module = importlib.util.module_from_spec(spec)
    # 기존 테스트의 sys.path.append보다 평가 대상 경로가 우선한다.
    sys.path.insert(0, str(root / 'scripts'))
    spec.loader.exec_module(module)
    result = RecordedResult()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        unittest.defaultTestLoader.loadTestsFromModule(module).run(result)
    if not result.rows:
        raise ValueError('기존 테스트가 0개이다')
    return result.rows


def evaluate(case, root, artifacts):
    row = dict(id='dataset:' + case['id'], category=case['category'], status='PASS', reasons=[])
    try:
        if artifacts:
            actual = (artifacts / (case['id'] + '.wiki')).read_text(encoding='utf-8')
        else:
            with tempfile.TemporaryDirectory(prefix='wiki-eval-') as directory:
                source = Path(directory) / case['filename']
                source.write_bytes(case['markdown'].encode('utf-8'))
                output = source.with_suffix('.wiki')
                command = [sys.executable, '-B', str(root / 'scripts/md_to_confluence.py'), str(source)]
                if case.get('explicit_output'):
                    output = Path(directory) / 'custom.wiki'
                    command.append(str(output))
                if case.get('include_markdown_source'):
                    command.append('--include-markdown-source')
                run = subprocess.run(command, capture_output=True, text=True, timeout=15)
                if run.returncode:
                    raise RuntimeError(f'CLI exit={run.returncode}: {run.stderr}')
                actual = output.read_text(encoding='utf-8')
        row['reasons'] = grade(case['expected'], actual)
        row['output_sha256'] = digest(actual.encode('utf-8'))
    except Exception as exc:
        row['reasons'] = [f'{type(exc).__name__}: {exc}']
    if row['reasons']:
        row['status'] = 'FAIL'
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-root', type=Path, default=ROOT)
    parser.add_argument('--dataset', type=Path, default=Path(__file__).with_name('cases.json'))
    parser.add_argument('--report', type=Path, default=Path('eval-report.json'))
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--artifacts-dir', type=Path, help='외부에서 생성한 <case-id>.wiki를 동일 기준으로 채점')
    args = parser.parse_args()
    root = args.skill_root.resolve()
    data = json.loads(args.dataset.read_text(encoding='utf-8'))
    cases = data['cases']
    if data['version'] != 1 or not cases:
        raise ValueError('지원하지 않는 dataset version 또는 빈 dataset')
    ids = set()
    for case in cases:
        if not re.fullmatch(r'[a-z0-9-]+', case['id']) or case['id'] in ids:
            raise ValueError('잘못되거나 중복된 case id: ' + case['id'])
        ids.add(case['id'])
        if Path(case['filename']).name != case['filename'] or not case['filename'].endswith('.md'):
            raise ValueError('filename은 경로 없는 .md 파일명이어야 한다')
        for key in ('markdown', 'expected', 'category', 'prompt'):
            if not isinstance(case[key], str):
                raise ValueError('문자열 필드 필요: ' + key)
        for key in ('explicit_output', 'include_markdown_source'):
            if key in case and not isinstance(case[key], bool):
                raise ValueError('boolean 필드 필요: ' + key)
    rows = existing_tests(root)
    rows.extend(evaluate(case, root, args.artifacts_dir) for case in cases)
    contract = dict(dataset=data, tests_sha256=digest((root / 'tests/test_converter.py').read_bytes()),
                    grader_sha256=digest(Path(__file__).read_bytes()))
    report = dict(schema_version=1, mode='artifacts' if args.artifacts_dir else 'cli',
                  contract_sha256=digest(json.dumps(contract, ensure_ascii=False, sort_keys=True).encode('utf-8')),
                  converter_sha256=digest((root / 'scripts/md_to_confluence.py').read_bytes()),
                  skill_sha256=digest((root / 'SKILL.md').read_bytes()),
                  summary=summary(rows), categories={}, cases=rows)
    for category in sorted({row['category'] for row in rows}):
        report['categories'][category] = summary([row for row in rows if row['category'] == category])
    if args.baseline:
        old = json.loads(args.baseline.read_text(encoding='utf-8'))
        if old['contract_sha256'] != report['contract_sha256'] or old['mode'] != report['mode']:
            raise ValueError('baseline과 dataset/기존 테스트/grader/mode가 다르므로 직접 비교할 수 없다')
        previous = {row['id']: row['status'] for row in old['cases']}
        if set(previous) != {row['id'] for row in rows}:
            raise ValueError('baseline case ID 집합 불일치')
        report['comparison'] = dict(
            regressions=[row['id'] for row in rows if previous[row['id']] == 'PASS' and row['status'] == 'FAIL'],
            fixes=[row['id'] for row in rows if previous[row['id']] == 'FAIL' and row['status'] == 'PASS'],
            pass_rate_delta=round(report['summary']['pass_rate']-old['summary']['pass_rate'], 2))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for category, counts in report['categories'].items():
        print(f"{category}: total={counts['total']} pass={counts['passed']} fail={counts['failed']} pass_rate={counts['pass_rate']:.2f}%")
    counts = report['summary']
    print(f"TOTAL: cases={counts['total']} pass={counts['passed']} fail={counts['failed']} pass_rate={counts['pass_rate']:.2f}%")
    for row in rows:
        if row['status'] == 'FAIL':
            print('\nFAIL ' + row['id'] + '\n' + '\n'.join(row['reasons']))
    if 'comparison' in report:
        print('BASELINE: ' + json.dumps(report['comparison'], ensure_ascii=False))
    print('JSON: ' + str(args.report.resolve()))
    return 1 if counts['failed'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, ImportError, TypeError) as exc:
        print('평가 실행 오류: ' + str(exc), file=sys.stderr)
        sys.exit(2)
