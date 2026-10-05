# Design decisions from the requested readings

Read on 26/09/2026. Both requested pages were fetched in full; project behavior was checked against local source.

- [Anthropic: Claude Code in large codebases, 14/05/2026](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start): applied concise layered context, a navigable source map, scoped checks and deterministic automation. Root/scoped `CLAUDE.md` files import the shared AGENTS contracts instead of duplicating them. This project does not currently need a new MCP service, code index or plugin distribution system.
- [OpenAI: Rethinking skills and prompts for GPT-6 Astra, 11/09/2026](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra): applied task-specific document routing, one narrowly triggered experiment skill, explicit completion evidence and permission to execute already-authorized local work. No mandatory full-document reading or full-suite run for every edit.
- [Claude Code memory documentation](https://code.claude.com/docs/en/memory): checked the `@path` import convention. Codex uses the AGENTS.md hierarchy; the project skill is stored in `.agents/skills/`.

Research-specific additions come from this project's observed failure: prediction, policy learning and app integration were being conflated. The workboard therefore tracks these separately, with evidence paths and remaining gaps. These are project decisions, not claims made by either blog.
