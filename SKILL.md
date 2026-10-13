---
name: confluence-wiki-skill
description: Markdown 문서를 Confluence Wiki(4.3.7) 포맷으로 변환하는 스킬. 문서를 Confluence로 옮기거나 Wiki 마크업 호환성 문제를 해결할 때 사용한다.
---

# Confluence Wiki 변환 가이드 (v4.3.7)

사용자가 "이 문서를 위키 포맷으로 변환해줘" 또는 "Confluence로 옮겨줘"라고 요청하면 수동 치환 대신 스크립트를 우선 실행한다.

## 자동화

```bash
# 기본 사용 (출력: INPUT_FILE.wiki)
python scripts/md_to_confluence.py <INPUT_FILE>

# 출력 파일명 지정
python scripts/md_to_confluence.py <INPUT_FILE> <OUTPUT_FILE>

# 원본 Markdown 첨부 링크 섹션 포함
python scripts/md_to_confluence.py <INPUT_FILE> <OUTPUT_FILE> --include-markdown-source
```

원본 Markdown 첨부 링크 섹션은 기본적으로 생성하지 않는다. 사용자가 요청한 경우에만 `--include-markdown-source`를 지정한다. 이 옵션을 지정하면 결과 하단에 `h2. MarkDown 원본문서`와 `[파일명|^파일명]`을 추가한다. Markdown 원본은 Confluence 페이지에 같은 파일명으로 수동 첨부한다.

## 테스트

스크립트 수정 후 회귀 방지를 위해 테스트를 실행한다.
문서 변환 작업을 수행한 뒤에도 결과 안정성 확인을 위해 회귀 테스트를 반드시 실행한다.

```bash
python tests/test_converter.py
```

## Skill 품질 평가

변환기나 Skill 지침 변경 후 품질과 회귀를 측정할 때는 [eval suite](evals/README.md)를 참고한다. 기존 unit test와 문서 dataset을 함께 평가하며 전체 case 수, pass/fail, pass rate, 실패 원인과 baseline 대비 변화를 출력한다.

```bash
python -B evals/run_eval.py --baseline evals/baseline.json --report /tmp/confluence-eval.json
```

## 핵심 변환 규칙

- 제목: `#`, `##`, `###` -> `h1.`, `h2.`, `h3.`
- 박스: Info/Warning/Note를 `{info}`, `{warning}`, `{note}`로 변환하고 반드시 닫는다
- 코드 블록: 지원 언어만 `{code:<lang>}`로, 미지원 언어는 `{code}` 사용
- Mermaid 코드 블록: `.wiki`에서는 코드 블록 앞에 `!파일명.png|width=900!` 이미지 태그를 넣고, 이어서 `{code:title=파일명.mmd|collapse=true}`를 사용해 Mermaid 본문만 접힌 코드로 넣는다. 파일명은 입력 Markdown 파일명과 가장 가까운 의미 있는 제목을 조합한다.
- 금지: `{code:json}`, `{code:yaml}`
- 번호 목록 + 코드블록: 번호 항목 바로 아래 코드블록이 오면 Confluence 표시 안정성을 위해 `1)`, `2)` 텍스트 번호를 사용
- 테이블 헤더: `|| Header ||`. 셀 안의 `\|`는 열 구분이 아니라 셀 내용으로 유지한다
- 링크: `[Text](URL)` -> `[Text|URL]`. 같은 페이지에 첨부할 로컬 Markdown 파일 링크(`[Text](file.md)`, `[Text](./file.md)`)는 `[Text|^file.md]` 첨부 링크로 변환한다.
- 강조: `**굵게**` -> `*굵게*`, `*기울임*` -> `_기울임_`, `~~취소선~~` -> `-취소선-`. 짝이 맞지 않는 `*`(`*.log`, `/path/**`, `2 * 3`)와 인라인 코드 안의 `*`, `~~`는 강조로 바꾸지 않는다
- 번호 목록 뒤의 불릿 목록: 번호 항목 바로 아래 불릿은 `#*`로 중첩하고, 더 들여쓴 불릿은 들여쓰기 폭(2·3·4칸)과 관계없이 한 단계씩 `#**`, `#***`로 내보낸다. 중첩된 번호 항목(`##`) 아래 불릿은 `##*`가 된다. 빈 줄 뒤에 오는 불릿 목록은 새 목록(`*`)으로 내보내되, 그 뒤에 같은 번호 목록이 이어지면 중첩을 유지한다. 체크박스(`- [ ]`, `- [x]`)는 `\[ ]`, `\[x]` 문자 그대로 둔다
- 인라인 코드: `` `text` `` -> 평문으로 변환한다. Confluence Wiki 문법과 충돌하는 리터럴은 원본 Markdown에서 코드 블록이나 문장 표현으로 분리한다.
- 원본 Markdown 링크 섹션: 기본값은 `false`이다. `--include-markdown-source`를 지정한 경우에만 파일 변환 결과 하단에 `h2. MarkDown 원본문서`와 `[파일명|^파일명]`을 추가한다
- 이미지: `![Alt](images/foo.png)` -> `!foo.png|width=900!`로 변환한다. 이미지는 Confluence 페이지 첨부파일로 수동 업로드한다.
- 수평선 `---`: 제거
- 이모지: 제거

## 주의사항

- 박스 내부는 가능한 평문으로 유지한다
- 중괄호는 필요 시 `\{` `\}`로 이스케이프한다
- 코드 블록 백틱 쌍이 맞는지 확인한다
- 제목(`#`) 앞 공백을 두지 않는다

## Markdown 원본문서 작성 주의사항

Confluence Wiki로 옮길 목적의 Markdown은 일반 Markdown 렌더링보다 Confluence Wiki 문법 충돌을 우선 고려한다.

- 인라인 코드 백틱은 가능한 사용하지 않는다. 변환기는 인라인 코드를 별도 스타일로 만들지 않고 평문으로 내보낸다.
- URL은 백틱으로 감싸지 말고 평문 URL로 둔다. URL 안의 하이픈을 이스케이프하거나 HTML 엔티티로 바꾸면 Confluence 자동 링크에서 깨질 수 있다.
- 하이픈이 많은 파일명, 배포 아티팩트명, 명령 예시는 문장 안 인라인 코드로 두지 말고 fenced code block으로 분리한다.
- `*`, `**`, `_`, `-...-`, `{{...}}`, `{...}`, `[...|...]`, `!image!`처럼 Confluence Wiki 문법으로 해석될 수 있는 조합은 표나 문장 안에 그대로 두지 않는다.
- `/actuator/**`, `stream/*`처럼 와일드카드가 들어간 경로는 꼭 리터럴 표기가 필요하지 않으면 "하위 경로", "계열 엔드포인트"처럼 문장 표현으로 바꾼다.
- 표 셀에는 꾸밈보다 평문을 우선 사용한다. 리터럴을 반드시 보존해야 하는 값은 표 밖 코드 블록으로 빼거나 표현을 완화한다.
- 변환 후에는 Confluence에 붙여 넣기 전에 `.wiki` 원문에서 `{{`, `}}`, `\_`, `\-`, `&#45;`, `&#95;` 같은 잔여 변환 흔적이 없는지 확인한다.

## 체크리스트

1. `{code:json}`, `{code:yaml}`을 사용하지 않았는지 확인한다
2. 테이블 내 중괄호 이스케이프를 확인한다
3. 박스 태그가 올바르게 닫혔는지 확인한다
4. 코드 블록 언어가 적절히 지정되었는지 확인한다
5. 제목이 `h1.`, `h2.` 형식으로 변환되었는지 확인한다
6. Markdown 이미지가 `!파일명.png|width=900!` 형태로 변환되었는지 확인한다
7. 번호 목록 바로 아래 코드블록 구간이 `1)`, `2)` 텍스트 번호로 출력되는지 확인한다
8. Mermaid 코드 블록 앞에 이미지 태그가 있고, `{code:title=파일명.mmd|collapse=true}`로 접히며, 백틱 펜스 없이 본문만 들어가는지 확인한다
9. `--include-markdown-source` 지정 여부와 결과 하단의 `MarkDown 원본문서` 섹션 생성 여부가 일치하는지 확인한다
10. Confluence 이관용 원본에서 인라인 코드 백틱을 남발하지 않았는지 확인한다
11. URL, jar 파일명, 와일드카드 경로가 Confluence 렌더링에서 깨지지 않는 형태인지 확인한다
