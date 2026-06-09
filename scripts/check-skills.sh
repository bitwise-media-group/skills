#!/usr/bin/env sh
# Tier 0 static checks: skill frontmatter, manifest structure, version sync.
# Pure POSIX sh + awk/sed + jq. Run from anywhere; exits non-zero on any failure.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fail=0

err() {
  echo "FAIL: $*" >&2
  fail=1
}

command -v jq >/dev/null || { echo "error: jq is required" >&2; exit 2; }

# --- skill frontmatter ------------------------------------------------------

frontmatter() {
  awk 'NR==1 && $0 != "---" { exit 1 }
       NR == 1 { next }
       /^---$/ { exit }
       { print }' "$1"
}

field() {
  printf '%s\n' "$1" | sed -n "s/^$2:[[:space:]]*//p" | head -n 1
}

for skill_md in "$repo_root"/plugins/*/skills/*/SKILL.md; do
  [ -f "$skill_md" ] || continue
  dir=$(basename "$(dirname "$skill_md")")
  rel=${skill_md#"$repo_root"/}

  if ! fm=$(frontmatter "$skill_md"); then
    err "$rel: no YAML frontmatter"
    continue
  fi

  name=$(field "$fm" name)
  description=$(field "$fm" description)
  license=$(field "$fm" license)

  [ "$name" = "$dir" ] || err "$rel: name '$name' != directory '$dir'"
  printf '%s' "$name" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$' \
    || err "$rel: name '$name' not kebab-case"
  [ "${#name}" -le 64 ] || err "$rel: name longer than 64 chars"

  [ -n "$description" ] || err "$rel: empty description"
  [ "${#description}" -le 1024 ] || err "$rel: description longer than 1024 chars"
  printf '%s' "$description" | grep -Eq "Use (when|after|before)" \
    || err "$rel: description missing a 'Use when/after/before' trigger phrase"

  [ "$license" = "MIT" ] || err "$rel: license must be MIT (got '$license')"

  lines=$(wc -l < "$skill_md")
  [ "$lines" -le 500 ] || err "$rel: SKILL.md exceeds 500 lines ($lines)"
done

# --- marketplace manifests ----------------------------------------------------

claude_mp="$repo_root/.claude-plugin/marketplace.json"
codex_mp="$repo_root/.agents/plugins/marketplace.json"

for mp in "$claude_mp" "$codex_mp"; do
  rel=${mp#"$repo_root"/}
  [ -f "$mp" ] || { err "missing $rel"; continue; }
  jq -e '.name and (.plugins | type == "array" and length > 0)' "$mp" >/dev/null \
    || err "$rel: missing name or non-empty plugins array"
done

jq -e '.owner.name' "$claude_mp" >/dev/null || err ".claude-plugin/marketplace.json: missing owner.name"

# Every marketplace source must be ./-prefixed and resolve to a plugin directory.
for src in $(jq -r '.plugins[].source | if type == "object" then .path else . end' \
    "$claude_mp" "$codex_mp"); do
  case $src in
    ./*) [ -d "$repo_root/$src" ] || err "marketplace source '$src' does not resolve" ;;
    *) err "marketplace source '$src' is not ./-prefixed" ;;
  esac
done

# Both marketplaces must list the same plugin set.
claude_names=$(jq -r '[.plugins[].name] | sort | join(",")' "$claude_mp")
codex_names=$(jq -r '[.plugins[].name] | sort | join(",")' "$codex_mp")
[ "$claude_names" = "$codex_names" ] \
  || err "marketplaces disagree on plugins: claude=[$claude_names] codex=[$codex_names]"

# --- plugin manifests ---------------------------------------------------------

for plugin_dir in "$repo_root"/plugins/*/; do
  plugin=$(basename "$plugin_dir")
  claude_pj="$plugin_dir.claude-plugin/plugin.json"
  codex_pj="$plugin_dir.codex-plugin/plugin.json"

  [ -f "$claude_pj" ] || { err "plugins/$plugin: missing .claude-plugin/plugin.json"; continue; }
  [ -f "$codex_pj" ] || { err "plugins/$plugin: missing .codex-plugin/plugin.json"; continue; }

  for pj in "$claude_pj" "$codex_pj"; do
    name=$(jq -r '.name' "$pj")
    [ "$name" = "$plugin" ] || err "${pj#"$repo_root"/}: name '$name' != directory '$plugin'"
  done

  claude_ver=$(jq -r '.version' "$claude_pj")
  codex_ver=$(jq -r '.version' "$codex_pj")
  [ "$claude_ver" = "$codex_ver" ] \
    || err "plugins/$plugin: version mismatch (claude=$claude_ver codex=$codex_ver)"
  printf '%s' "$codex_ver" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' \
    || err "plugins/$plugin: version '$codex_ver' is not strict semver"

  # Codex default-discovers hooks/hooks.json with a non-Claude schema — forbid it.
  [ ! -d "${plugin_dir}hooks" ] || err "plugins/$plugin: hooks/ directory is forbidden (see AGENTS.md)"

  # Every plugin must ship at least one skill.
  found=false
  for sk in "$plugin_dir"skills/*/SKILL.md; do
    [ -f "$sk" ] && found=true && break
  done
  [ "$found" = true ] || err "plugins/$plugin: no skills under skills/"
done

if [ "$fail" -eq 0 ]; then
  echo "check-skills: all checks passed"
else
  exit 1
fi
