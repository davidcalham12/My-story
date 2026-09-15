# My-story# NovaForge

A multi-agent harness that writes short science-fiction novels.

## The idea

Instead of one prompt writing a whole book, a small team of specialised agents cooperates
under a fixed process:

1. **Build the universe** — three agents write the *Story Bible* (world rules, characters,
   timeline, open mysteries, chapter outline). The Bible is the single source of truth.
2. **Write chapter by chapter** — a writer drafts each chapter reading only the Bible and a
   short summary of what came before. Critics score the draft (continuity, science, length).
   Below the threshold, the chapter is rewritten — up to a fixed number of times.
3. **Polish and publish** — an editor unifies the voice; the publisher exports Markdown and PDF.

The orchestrator only sequences the steps and saves progress, so a run can be resumed.
The model is swappable: a deterministic offline `mock` engine lets the whole pipeline run
with no API key and no cost.

## Start small, grow by configuration

The harness starts with tiny novels (3 chapters, ~400 words each). Everything that shapes the
novel — chapters, words and lines per chapter, quality threshold, retries, budget, output
formats — lives in `config/novel.config.json`. Scaling up to a full novel is a change in that
file, never in the code.

## Flow

```mermaid
flowchart TD
    U(["User<br/>premise + tone"]) --> ORQ["Orchestrator<br/>runs the steps · saves progress"]
    CFG[("config/novel.config.json<br/>chapters · length · gate · outputs")] -.-> ORQ

    ORQ --> F1
    subgraph F1["1 · Build the universe"]
        WB["Worldbuilder"] --> CA["Character Architect"] --> PA["Plot Architect"]
    end
    F1 --> BIBLE[("Story Bible")]
    BIBLE -.->|"read only"| CW

    subgraph F2["2 · Per-chapter loop"]
        CW["Chapter Writer"] --> CRIT{"Critics<br/>continuity · science · length"}
        CRIT -->|"below threshold"| CW
        CRIT -->|"pass"| NEXT{"more chapters?"}
        NEXT -->|"yes"| CW
    end

    NEXT -->|"no"| SE["Style Editor"] --> PUB["Publisher"] --> OUT(["book.md · book.pdf"])
```

## Specs

- [`specs/CONFIG-SPEC.md`](specs/CONFIG-SPEC.md) — the configuration file that parametrises
  chapter count, chapter length (words, lines, paragraphs), quality gate, budget, growth
  profiles (`tiny` → `full`) and outputs (Markdown + PDF only).

More specs will be added incrementally as the harness matures.
