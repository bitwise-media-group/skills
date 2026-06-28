# workflow-security-report reference

How to turn a `gh api` code-scanning alert into the fields the report template expects, plus the permalink and outcome
rules. The `SKILL.md` body is the procedure; this file is the lookup table.

## Pull the fields in one call

```sh
gh api repos/<owner>/<repo>/code-scanning/alerts/<n> --jq '{
  state,
  title: .rule.description,
  rule_id: .rule.id,
  severity: .rule.severity,
  security_severity: .rule.security_severity_level,
  cwe: [.rule.tags[] | select(startswith("external/cwe/"))],
  tool: (.tool.name + " " + .tool.version),
  path: .most_recent_instance.location.path,
  start_line: .most_recent_instance.location.start_line,
  end_line: .most_recent_instance.location.end_line,
  start_column: .most_recent_instance.location.start_column,
  end_column: .most_recent_instance.location.end_column,
  sha: .most_recent_instance.commit_sha,
  created_at,
  html_url
}'
```

## Field map

| Report field | `gh api` source                                                                        |
| ------------ | -------------------------------------------------------------------------------------- |
| Title (H1)   | `.rule.description`                                                                    |
| Finding link | `.html_url` (equals `.../security/code-scanning/<n>`)                                  |
| Rule         | `.rule.id` + the CWE derived from `.rule.tags` (see below)                             |
| Tool         | `.tool.name` + `.tool.version`                                                         |
| Severity     | `.rule.severity` (capitalized) + `(security-severity: .rule.security_severity_level)`  |
| Location     | `.most_recent_instance.location.{path,start_line,start_column,end_column}` → permalink |
| Detected     | `.created_at` (date only, `YYYY-MM-DD`) + `.most_recent_instance.commit_sha`           |
| Outcome      | your recommendation — `False positive`, `Remediated`, or `Pending`                     |

The column range in the Location cell is `start_column`–`end_column`; the short operand note after it (for example "the
`len(e.Assertions)` operand") is your own description of what the columns cover.

## Deriving the CWE

`.rule.tags` holds entries like `external/cwe/cwe-190`. Keep the ones under `external/cwe/`, take the last segment, and
uppercase it: `external/cwe/cwe-190` → `CWE-190`. List all that apply, comma separated, in the Rule cell:
`` `go/allocation-size-overflow` (CWE-190) ``.

## Permalinks (the immutability rule)

`<full-sha>` is `.most_recent_instance.commit_sha` — the 40-character SHA, never the short form, in the URL path:

- a line: `https://github.com/<owner>/<repo>/blob/<full-sha>/<path>#L<line>`
- a range: `https://github.com/<owner>/<repo>/blob/<full-sha>/<path>#L<start>-L<end>`
- the commit: `https://github.com/<owner>/<repo>/commit/<full-sha>` (render the link text as the short 7-character SHA)

Every code reference in the report — in the metadata table and in the prose analysis — uses one of these. A branch name
or `HEAD` would rot once the code moves; the SHA keeps the closed report honest.

## Outcome vocabulary

| Outcome          | When                                                                       |
| ---------------- | -------------------------------------------------------------------------- |
| `False positive` | The rule does not apply; recommend dismissing the alert in the UI.         |
| `Remediated`     | A code change fixes the issue; reference the remediating commit.           |
| `Pending`        | The recommendation is recorded but the finding is still open / unactioned. |

Set the same value in the report's **Outcome** row and in the index row. The index intro lists the outcomes it uses, so
keep the vocabulary consistent across reports.

## Re-detections

When CodeQL re-detects an issue after the code moves, it closes the old alert as `fixed` and opens a new number against
the byte-identical code. Write a **new** report for the new number and cross-link the prior one by number and `./<n>.md`
(and note the move, old SHA → new SHA). Do not edit the closed report — it is immutable.
