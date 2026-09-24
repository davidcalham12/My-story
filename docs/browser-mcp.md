# Browser MCP — how the rendered novel is inspected

Source: `docs/spec.md` §1 (row "browser MCP configured and its use documented"),
§2 validator `visual_check`, §7 (a documented manual session, not a test);
configuration committed in `1fd3218`.

## Configuration

`.mcp.json` at the repository root, where Claude Code reads project-scoped
servers:

```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] } } }
```

No credentials, no network target beyond `file://` pages under `dist/`.

## What the session checks — `visual_check`

One session per published version, on `dist/v<N>/novel.html` (the HTML the PDF
is printed from, so what the browser sees is what the PDF contains).

| # | check | pass when |
|---|---|---|
| 1 | cover | recipient alias and dedication visible on the first page |
| 2 | index | one entry per chapter; each link lands on that chapter's heading |
| 3 | character and place sheet | every entry links to its first chapter, and the link lands there |
| 4 | "what changed" page (v > 1 only) | it opens the book; each listed chapter links to the regenerated chapter |
| 5 | no leftovers | no raw Markdown, no `TODO`, no placeholder text on any page |

The result is recorded as a `visual_check` row (pass/fail, with the failing
check numbers in the comment) and exported as a Langfuse score with the
version's trace.

## Why manual

Two days, and the checks are about what a reader sees. The links themselves are
also covered by `test_pdf.py` (one anchor per chapter, one link per character);
this session is the D-letter evidence that they work in a real browser, not a
replacement for the test.

## Sessions

| date | version | file | result | notes |
|---|---|---|---|---|
| pending | v1 | `dist/v1/novel.html` | — | runs once the example novel is published |
| pending | v2 | `dist/v2/novel.html` | — | after the reader-change demo (E8) |
