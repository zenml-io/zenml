# Documentation Agent Guidelines

This file applies when Codex starts in `docs/book/` or below. For detailed
GitBook URL examples, link-checking notes, and docs workflow recipes, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Source of Truth

- `docs/book/` is the source of truth for documentation content.
- Other docs directories such as `docs/mkdocs/` and `docs/site/` contain
  generated output; do not edit those directly.
- Docs changes can affect the API docs buildability check in fast CI.

## Structure

- Multiple docs sections have their own `toc.md`; update the relevant `toc.md`
  when adding, moving, or removing pages.
- Assets belong in a `.gitbook` folder at the same level as the relevant
  `toc.md`.
- GitBook URLs follow TOC hierarchy, not filesystem paths.
- Use absolute `https://docs.zenml.io/...` links when linking across major docs
  sections such as OSS docs and Pro docs.

## Style

- Include metadata fields at the top of pages when existing nearby pages do so.
- Match the tone and structure of nearby documentation.
- Prioritize readable prose over dense bullet lists.
- Include code examples, cross-references, and usage guidance where they help
  users complete the task.

## Verification

- For changed relative markdown links, run the relevant local link checks.
- For absolute docs URLs, check the current URL or inspect the relevant
  `toc.md`.
- Use Lychee when the change affects many links:
  `lychee --offline --no-progress 'docs/book/**/*.md'`.
