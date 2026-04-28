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
```

## 테스트

스크립트 수정 후 회귀 방지를 위해 테스트를 실행한다.
문서 변환 작업을 수행한 뒤에도 결과 안정성 확인을 위해 회귀 테스트를 반드시 실행한다.

```bash
python tests/test_converter.py
```

## 핵심 변환 규칙

- 제목: `#`, `##`, `###` -> `h1.`, `h2.`, `h3.`
- 박스: Info/Warning/Note를 `{info}`, `{warning}`, `{note}`로 변환하고 반드시 닫는다
- 코드 블록: 지원 언어만 `{code:<lang>}`로, 미지원 언어는 `{code}` 사용
- Mermaid 코드 블록: `.wiki`에서는 기본적으로 `{code:title=mermaid code|collapse=true}`를 사용하고, 내부에는 Mermaid 본문만 넣는다
- 금지: `{code:json}`, `{code:yaml}`
- 번호 목록 + 코드블록: 번호 항목 바로 아래 코드블록이 오면 Confluence 표시 안정성을 위해 `1)`, `2)` 텍스트 번호를 사용
- 테이블 헤더: `|| Header ||`
- 링크: `[Text](URL)` -> `[Text|URL]`
- 이미지: `![Alt](images/foo.png)` -> `!foo.png|width=900!`로 변환한다. 이미지는 Confluence 페이지 첨부파일로 수동 업로드한다.
- 수평선 `---`: 제거
- 이모지: 제거

## 주의사항

- 박스 내부는 가능한 평문으로 유지한다
- 중괄호는 필요 시 `\{` `\}`로 이스케이프한다
- 코드 블록 백틱 쌍이 맞는지 확인한다
- 제목(`#`) 앞 공백을 두지 않는다

## 체크리스트

1. `{code:json}`, `{code:yaml}`을 사용하지 않았는지 확인한다
2. 테이블 내 중괄호 이스케이프를 확인한다
3. 박스 태그가 올바르게 닫혔는지 확인한다
4. 코드 블록 언어가 적절히 지정되었는지 확인한다
5. 제목이 `h1.`, `h2.` 형식으로 변환되었는지 확인한다
6. Markdown 이미지가 `!파일명.png|width=900!` 형태로 변환되었는지 확인한다
7. 번호 목록 바로 아래 코드블록 구간이 `1)`, `2)` 텍스트 번호로 출력되는지 확인한다
8. Mermaid 코드 블록이 `{code:title=mermaid code|collapse=true}`로 접히고, 백틱 펜스 없이 본문만 들어가는지 확인한다

