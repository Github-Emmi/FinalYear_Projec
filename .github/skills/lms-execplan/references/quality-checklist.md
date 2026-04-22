# ExecPlan Quality Checklist

Run this checklist before delivering any ExecPlan. Do not submit a plan that fails a **Critical** or **High** item.

---

## Critical — Plan fails to be executable if any of these are violated

- [ ] **Self-contained**: No step says "see FastAPI docs" or links to an external URL for required knowledge. All required knowledge is embedded in the plan in the author's own words.
- [ ] **No assumed context**: The plan does not rely on anything the reader would only know from a prior conversation or an unchecked-in document. All context is stated explicitly.
- [ ] **Exact commands**: Every shell step contains an exact, copy-pasteable command. No step says "run the app" without the full command.
- [ ] **Exact file content**: Every file-creation step includes the complete file content (not a summary or skeleton comment like `# add imports here`).
- [ ] **No unresolved forks**: Every decision point is resolved by the author. The plan never says "choose option A or B".
- [ ] **Acceptance criteria are verifiable**: Every acceptance criterion can be checked by running a command or reading a file. None say "it works" or "it feels right".
- [ ] **Rollback exists**: The plan has a complete rollback section covering all created and modified files.
- [ ] **Phase gate respected**: The plan does not implement work from Phase N+1 without an explicit note that user approval is required first.

---

## High — Plan likely fails or produces broken output

- [ ] **Expected outputs present**: Every shell step has an `Expected output:` block with a realistic, trimmed example.
- [ ] **File paths are correct**: All file paths are relative to the repository root and match the canonical structure in the agent file.
- [ ] **Pinned versions**: `requirements.txt` and `docker-compose.yml` use pinned versions (no `latest` image tags, no `>=x` without upper bound for critical deps).
- [ ] **No undefined jargon**: All acronyms and domain terms (RBAC, UUID, ORM, lifespan, etc.) are defined at first use within the plan.
- [ ] **Imports are real**: Any Python import shown in a code block is from a package that is listed in `requirements.txt` in the same plan or in the existing checked-in `requirements.txt`.
- [ ] **Tests are specified**: If the phase includes code, at least one test step is included with a pytest invocation and expected output.
- [ ] **Security — no hardcoded secrets**: No plan embeds real API keys, passwords, or tokens. All secret values use placeholder syntax: `your-secret-key-here`.

---

## Medium — Plan quality is degraded but may still execute

- [ ] **Pre-conditions block present**: The plan has a Pre-conditions section with verification commands.
- [ ] **Design decisions table populated**: At least 3 non-trivial design decisions are documented with rationale.
- [ ] **Scope table complete**: Every file the plan touches is listed in the Scope table.
- [ ] **Step titles are descriptive**: Step titles name the action and the target file (e.g. "Create `backend/app/core/database.py`", not "Step 3").
- [ ] **No large blobs**: No single fenced code block exceeds ~150 lines. Longer files are split across steps or placed in `assets/`.

---

## Low — Cosmetic / consistency

- [ ] **Consistent heading levels**: Steps use `###`, sub-steps use `####`.
- [ ] **Permission gate present**: The final section ends with the standard gate prompt.
- [ ] **Author date set**: The plan header has an `Author date` field filled in.
- [ ] **Prior ExecPlan referenced**: If this plan builds on a prior one, it is referenced or its context is inlined.

---

## OWASP Quick Reference for Security-Sensitive Steps

When the plan touches auth, tokens, passwords, or external services, additionally verify:

| OWASP Risk | Check |
|---|---|
| A01 Broken Access Control | RBAC roles are explicitly named; no endpoint is left unauthenticated by accident |
| A02 Cryptographic Failures | JWT uses HS256 minimum; bcrypt cost factor ≥ 12; no MD5/SHA1 for passwords |
| A03 Injection | All database queries use SQLAlchemy parameterised statements; no f-string SQL |
| A05 Security Misconfiguration | `DEBUG=false` and `SECRET_KEY` change required in production checklist |
| A07 Identification & Auth Failures | Access tokens ≤ 30 min; refresh tokens rotate on use |
| A09 Security Logging | Audit log entries are written for auth events and data mutations |
