# docs/handoff — the mailbox between sessions

Three sessions work on this repository and only two of them can message each other.
This folder is the conversation, and it stays versioned.

| file | written by | read by |
|---|---|---|
| `from-design.md` | the design session (the owner's laptop, claude.ai) | the two sessions on the VM |
| `from-build.md` | the sessions on the VM: `novaforge-05` (builds) and the coordinating session (specifies, reviews, writes `/docs` and the deck) | the design session |

Rule (`AGENTS.md` §1): read this folder before starting a block of work; update your file when you close one. `git pull --rebase` before every commit.
