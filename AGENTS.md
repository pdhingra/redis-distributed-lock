# Project Orchestration & Review Protocol

This repository uses **`uv`** for Python dependency and test execution (`uv run pytest -v`) and **Docker Compose** for 5 standalone Redis instances.

## Multi-Agent Pipeline & Escalation Protocol

1. **Implement:** `@lock-implementer` builds or updates code according to `SPEC.md`.
2. **Instrument:** `@observability-instrumentor` adds structured concurrency logs (`worker_id`, `resource`, `owner_token`, `quorum_count`, `elapsed_ms`).
3. **Review:** `@senior-code-reviewer` audits all changes across 6 lenses (Functionality, Thread Safety, Simplicity, Maintainability, Performance, Security) and outputs a structured `CR-*` table plus `REVIEW_STATUS: APPROVED` or `CHANGES_REQUESTED`.
4. **Fix or Pushback Loop (Max 3 Rounds):** If `REVIEW_STATUS: CHANGES_REQUESTED`:
   - Pass all `OPEN` `CR-*` findings back to `@lock-implementer`.
   - `@lock-implementer` must address every `CR-*` ID by either applying the fix (`ACCEPTED`) or writing a technical rebuttal (`PUSHBACK`) if the request violates `SPEC.md` scope or adds unnecessary complexity.
   - Re-run `@senior-code-reviewer` to verify fixes and evaluate rebuttals.
5. **Escalate Deadlocks to User:** If any `BLOCKER` or `MAJOR` item remains unresolved after **3 review rounds**, **STOP immediately** and present an **Architectural Escalation Brief** to the user detailing:
   - Disputed `CR-*` ID & Review Dimension
   - `@senior-code-reviewer`'s position and failure-mode risk
   - `@lock-implementer`'s rebuttal and complexity/scope trade-off
   - Concrete **Option A vs. Option B** choices for the user to decide.
6. **Chaos & Concurrency Verification:** Once `REVIEW_STATUS: APPROVED`, run `@chaos-qa-engineer` to execute `uv run pytest -v` against Docker Compose and confirm all 4 test suites pass.
7. **Technical Docs & Storytelling Content:** Once tests pass, run `@docs-and-diagrams-writer` to generate `README.md`, then run `@blog-storyteller` to produce `docs/blog/medium-article.md` and `docs/blog/linkedin-post.md`.
