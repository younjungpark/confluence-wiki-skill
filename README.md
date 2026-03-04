# Confluence Wiki Skill

A reusable Markdown-to-Confluence Wiki converter skill.

This project provides a small Python-based converter that turns common Markdown syntax into Confluence Wiki markup (Confluence 4.3.7 style), with practical handling for headings, tables, lists, links, code blocks, and alert-style blockquotes.

## Why this project

When moving operational docs, runbooks, or technical notes from Markdown into Confluence, manual conversion is error-prone and repetitive. This skill automates the conversion workflow and includes tests for regression safety.

## Features

- Converts Markdown headings (`#`, `##`, `###`) to Confluence headings (`h1.`, `h2.`, `h3.`)
- Converts Markdown links (`[Text](URL)`) to Confluence links (`[Text|URL]`)
- Converts table headers to `|| Header ||` format
- Converts numbered and bullet lists, including nested list scenarios
- Converts info/warning/note style blockquotes to Confluence macros (`{info}`, `{warning}`, `{note}`)
- Converts fenced code blocks to `{code}` (or language-aware code macros for supported languages)
- Removes horizontal rules (`---`) and strips emojis to improve Confluence rendering consistency
- Includes regression tests for core conversion behaviors

## Project Structure

```text
confluence-wiki-skill/
  SKILL.md
  scripts/
    md_to_confluence.py
  tests/
    test_converter.py
```

## Requirements

- Python 3.9+ (3.11 recommended)

No external Python packages are required.

## Usage

From the project root:

```bash
python scripts/md_to_confluence.py <INPUT_FILE>
```

This generates:

- `<INPUT_FILE>.wiki` (same directory) by default

To provide an explicit output file:

```bash
python scripts/md_to_confluence.py <INPUT_FILE> <OUTPUT_FILE>
```

## Example

```bash
python scripts/md_to_confluence.py docs/guide.md docs/guide.wiki
```

## Run Tests

```bash
python tests/test_converter.py
```

## Notes

- `json` and `yaml` code fence language labels are intentionally not emitted as Confluence code languages.
- Unsupported code fence labels fall back to `{code}`.
- Mermaid blocks are preserved in a safe collapsed code macro format.

## Intended Use

This repository is intentionally generic and can be used beyond Codex-specific workflows.

## License

Add your preferred license (for example, MIT) before publishing publicly.
