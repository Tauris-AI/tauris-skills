# Tauris Skills Copilot Instructions

This repository contains reusable agent skills for petroleum engineering workflows.

When editing skills:

- Keep `SKILL.md` concise and workflow-focused.
- Put schemas, field notes, and examples in `references/`.
- Put deterministic validators or converters in `scripts/`.
- Do not commit secrets, connection strings, raw production exports, or customer confidential data.
- Use sanitized schemas and synthetic examples unless real examples have been scrubbed.
- Require dry-run or review steps before any database or ARIES mutation workflow.
- Do not invent ARIES or PhdWIN behavior; mark unverified details clearly.

The ARIES domain should be split into multiple skills. `aries-ac-economic` is one major skill, not the entire ARIES knowledge base.
