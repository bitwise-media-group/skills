---
description:
    Triage a GitHub code-scanning (CodeQL) finding and write an immutable SHA-pinned report plus index entry,
    recommending remediation or dismissal.
argument-hint: <finding-number | finding-URL>
---

# Security finding report

Apply the `workflow-security-report` skill to triage this code-scanning finding:

$ARGUMENTS

Follow the skill exactly:

- A bare number refers to a finding in the current repository; a URL identifies the org, repo, and number.
- Fetch the finding with `gh api`. If it does not exist, or is already closed (dismissed or fixed), stop and tell the
  user — closed findings are immutable and must not be re-triaged.
- Anchor every code reference to the finding's commit SHA with a GitHub permalink, write the report to
  `security/code-scanning/<n>.md`, update `security/code-scanning/index.md`, and ensure `SECURITY.md` links the triage
  index.
