# Validators and where they run

| kind | validator | runs at |
|---|---|---|
| programmatic | schema_brief | FLOW-0, before anything is spent |
| programmatic | schema_role_output | validate-chapter hook |
| programmatic | canonical_names | validate-chapter hook |
| programmatic | chapter_length | the gate, every attempt |
| programmatic | forbidden_words | policy hook, every attempt |
| programmatic | mandatory_facts | publish gate, per version |
| programmatic | visual_check (browser MCP) | publish gate, once per version, documented session |
| semantic | six gate characteristics (continuity, rules, outline, prose by model; length, heading by count) | the gate, every attempt |
| semantic | judge_rubric (six criteria with justification) | publish gate, per version |
| semantic | human_review | once, one full novel |
| formal, story | lean_chronology | publish gate, if elan is installed |
| formal, system | tla_harness | development, not per generation |
