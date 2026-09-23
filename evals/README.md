# Confluence Wiki Skill eval

이 suite는 Skill이 사용하는 변환기, CLI 옵션, 산출물 계약을 평가한다. Python 표준 라이브러리만 사용하며 LLM judge, 네트워크, Confluence 서버가 필요하지 않다.

## 기존 검증 분석과 재사용

기존 `tests/test_converter.py`에는 독립 validator 함수 없이 `unittest.TestCase` 31개가 있다. 제목, 강조, 목록, 박스, 링크, 이미지, Mermaid, 인라인 코드, 원본 첨부 옵션을 `assertIn`, `assertNotIn`, `assertEqual`로 검증한다. eval 실행기는 이 모듈을 직접 로드하여 assertion과 테스트 입력을 그대로 재사용하고, 각 테스트 메서드를 하나의 case로 집계한다. eval 실행기는 기존 테스트와 변환기 코드를 수정하지 않는다.

기존 검증은 부분 문자열 검사 중심이므로 불필요한 출력 추가, 문서 전체의 순서 변화, CLI 기본 출력 경로, 박스 안 코드의 원문 손실을 충분히 포착하지 못한다. 이를 보완하는 `cases.json`의 34개 문서 case는 CLI를 임시 디렉터리에서 실행하고 전체 결과를 독립적으로 작성한 기대 출력과 비교한다. 기대 출력은 현재 변환기로 자동 생성하지 않는다.

| 평가 층 | case 수 | 범위 |
|---|---:|---|
| 기존 unit test | 31 | 기존 assertion 전체 재사용 |
| 대표 문법 | 20 | h1–h6, 강조, 인라인 코드, 목록, 표, 링크, 이미지, 언어별 코드, 박스, 인용, 수평선 |
| 복합 문서 | 4 | 번호와 코드, 박스·목록·코드, 중복 Mermaid, 배포 안내 문서 |
| 경계 조건 | 8 | 빈 입력, CRLF, 마지막 개행 없음, Unicode, Windows 이미지 경로, alert, 코드 내 Wiki 리터럴, 박스 코드 보존 |
| CLI workflow | 2 | 원본 첨부 옵션 활성화, 명시적 출력 경로 |
| 합계 | 65 | 기존 메서드와 추가 문서를 각각 한 case로 집계 |

기본 원본 첨부 제외와 기본 출력 경로는 나머지 dataset case에서 함께 검증한다. 여러 assertion이 있는 기존 테스트도 case 수는 1이다. 유사 문법이 두 층에 있으므로 65를 서로 독립적인 기능 수로 해석하지 않는다.

## 실행과 regression 측정

Skill 디렉터리에서 다음 명령을 실행한다.

```bash
python -B evals/run_eval.py --report /tmp/wiki-eval-current.json
python -B evals/run_eval.py --baseline evals/baseline.json --report /tmp/wiki-eval-compared.json
python -B evals/test_eval.py
```

다른 버전의 Skill을 같은 dataset과 grader로 평가하려면 `--skill-root /path/to/candidate-skill`을 지정한다. 각 CLI 실행의 제한 시간은 15초이다. 산출물은 임시 디렉터리에서 읽은 후 삭제한다.

콘솔과 JSON에는 전체 및 category별 total, pass, fail, pass rate를 기록한다. 실패 case에는 expected/actual unified diff, 구조 위반 또는 실행 예외를 기록한다. pass rate는 `passed / total * 100`이다. skip과 expected failure는 검증 완료로 인정하지 않고 FAIL로 집계한다. 종료 코드는 전부 통과하면 0, case 실패가 있으면 1, dataset 또는 baseline 등 평가 설정 오류이면 2이다.

baseline 비교는 case별 PASS→FAIL을 regression, FAIL→PASS를 fix로 출력하고 pass rate 변화량을 percentage point로 기록한다. 이미 실패한 case도 계속 FAIL로 집계한다. baseline에 알려진 실패가 있어도 종료 코드를 0으로 바꾸지 않는다. dataset, 기존 unit test, grader, 평가 mode가 달라지면 비교를 거부한다. 평가 기준을 변경한 경우 새 기준으로 변경 전·후 변환기를 모두 재평가해야 한다. Skill과 변환기의 SHA-256도 결과에 남긴다.

## 판정 기준

기존 Python assertion을 우선 재사용한다. 추가 문서는 전체 Wiki 문자열을 비교하며 파일 읽기의 개행 정규화 외에는 공백, 빈 줄, 내용 순서를 임의로 무시하지 않는다. 코드 및 info/warning/note/tip/quote 블록의 닫힘과 금지된 json/yaml code 언어도 검사한다. 코드 본문의 Markdown, 중괄호, 이미지처럼 보이는 리터럴에는 일반 문서 규칙을 적용하지 않는다.

구조 검사는 이 dataset이 사용하는 블록 문법을 위한 보조 검사이며 Confluence 전체 parser가 아니다. 정확한 문서 비교가 주 판정이다. 실제 Confluence 4.3.7 렌더링, 첨부파일 업로드, PNG 생성, 지원을 선언하지 않은 Markdown 전체 문법은 검증하지 않는다. 닫히지 않은 입력 fence는 Skill의 입력 전제조건 위반이므로 자동 복구 동작을 이번 계약으로 추가하지 않는다.

저장된 baseline은 수정 전 결과인 65개 중 64개 PASS, 1개 FAIL, 98.46%를 유지한다. 실패했던 `box-code-preservation`은 일반 코드 블록과 마찬가지로 박스 안에서도 코드 문자열을 보존한다는 평가 기준이다. 변환기가 박스 안 코드에도 이모지 제거를 적용하여 `print("🐳")`를 `print("")`로 바꾸던 문제를 수정했다. 이모지 제거는 박스의 일반 텍스트에만 적용하며 코드 내부 문자열은 유지한다. 기대값과 기존 테스트를 변경하지 않은 재검증 결과는 65개 전체 PASS, 100%이며 baseline 대비 fix 1개, regression 0개이다.

## Skill 동작 자체의 평가 범위

기본 CLI mode는 에이전트를 실행하지 않으므로 Skill 선택, 지시문 준수, 도구 실행 여부를 측정하지 않는다. 지시문만 바꾸면 CLI 점수가 같을 수 있다. 이를 에이전트의 종합 품질 점수로 보고하지 않는다.

실제 에이전트 산출물을 비교하려면 각 case의 `prompt`와 `filename`, `markdown`을 제공하고, 현재 Skill로 작업하게 한다. 평가자는 실행 결과 Wiki를 `<case-id>.wiki`로 모은 후 다음 명령을 실행한다. 기대 출력은 실행 에이전트에게 제공하지 않는다.

```bash
python -B evals/run_eval.py --artifacts-dir /path/to/generated-wiki --report /tmp/wiki-agent-artifacts.json
```

이 mode도 같은 Python 판정을 사용하며 파일 누락을 FAIL로 기록한다. 기존 unit test 31개는 로컬 변환기 검증이고 dataset 34개만 외부 산출물 점수이므로 category별 결과를 함께 읽는다. 실행 로그의 도구 사용 여부는 이 mode에서 검사하지 않는다. agent mode 결과를 비교할 때에는 같은 모델·설정·prompt·입력을 유지하고 모델 및 실행 식별자는 별도로 기록한다. CLI baseline과 artifacts baseline은 혼합하지 않는다.

현재 모든 산출물 기준은 deterministic하게 검사할 수 있어 LLM-based evaluation을 사용하지 않는다. 향후 자유로운 문장 재작성의 의미 보존처럼 고정 기대값이나 Python 규칙으로 판정하기 어려운 작업이 실제 범위에 추가될 때만 별도 rubric과 사람이 검토한 표본을 마련한다.

## dataset 유지보수

각 case는 고유 id, category, 파일명, 사용자 요청 prompt, Markdown, 기대 Wiki를 포함한다. 선택 필드는 원본 첨부 여부와 명시적 출력 경로이다. 기준 변경은 입력과 기대값, 변경 이유를 함께 검토하고 baseline을 명시적으로 교체한다. 실행기는 baseline과 기대값을 자동 갱신하지 않는다.

`test_eval.py`는 구조 검사, 추가 내용 탐지, 코드 리터럴 허용을 검증하며 임시 Skill 복사본의 제목 변환을 고의로 변경해 regression 검출을 확인한다. 이 실행기 자체 검증 7개는 품질 점수 65개에 중복 합산하지 않는다.
