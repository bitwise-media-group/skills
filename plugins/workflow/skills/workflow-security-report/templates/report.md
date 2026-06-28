# Code scanning finding {n} — {title}

**Finding:**
[github.com/{owner}/{repo}/security/code-scanning/{n}](https://github.com/{owner}/{repo}/security/code-scanning/{n})

| Field    | Value                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------- |
| Rule     | `{rule-id}` ({CWE})                                                                                                 |
| Tool     | CodeQL {tool-version}                                                                                               |
| Severity | {Severity} (security-severity: {level})                                                                             |
| Location | [`{path}:{line}`](https://github.com/{owner}/{repo}/blob/{full-sha}/{path}#L{line}) (cols {start}–{end}, {operand}) |
| Detected | {date} against commit [`{short-sha}`](https://github.com/{owner}/{repo}/commit/{full-sha})                          |
| Outcome  | **{False positive, Remediated, or Pending}**                                                                        |

## What CodeQL reported

{What the rule flagged and the source it traced. Show the flagged code, pinned to the finding's SHA; replace `text`
below with the source file's language.}

```text
{the flagged line(s)}
```

## Why this is a false positive

{Replace this whole section with a `## Remediation` section when the finding is a true positive.}

{Numbered, verifiable reasons the rule does not apply here. Cite surrounding code by SHA permalink, not by assertion.}

## Resolution

{The decision and action — dismissed in the code-scanning UI as a false positive, or remediated in commit {commit-link}
— restating the Outcome.}
