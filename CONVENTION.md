# CONVENTION.md

Conventions for **commit messages** and **pull requests** in this repository. Human contributors and **coding assistants (Cursor, Claude Code, etc.)** should follow this document when drafting commits, amending messages, or writing PR titles and descriptions.

For application stack, Docker, and tests, see **CLAUDE.md** at the repo root.

---

## Instructions for assistants

When the user asks for a commit message, `git commit` text, or PR copy:

1. **Match Conventional Commits** for the subject line (see below).
2. **Use imperative mood** in the description (e.g. "add", "fix", "remove" — not "added", "fixes", "adding").
3. **Keep the subject ≤ ~72 characters** when practical; no trailing period on the subject.
4. **Choose the narrowest accurate `type`**. If unsure between `feat` and `fix`, ask one clarifying question or default to what the code actually does (user-visible behavior → `feat`/`fix`; tooling-only → `chore`/`ci`).
5. For **PRs**, prefer a Conventional-Commit-style **title** and a **body** with Overview, Changes, Testing, and links to tickets (Trello/Jira) when the user supplied them.
6. This project hosts code on **GitHub**; issue keys in footers may be Jira-style (`PROJ-123`) or whatever the team uses — do not assume `#123` unless the user referenced it.
7. When a change affects **architecture** (layers, routers, services, context/CAG, LLM providers, config, or cross-package dependencies), update **`docs/ARCHITECTURE.md`** in the same change set (diagrams, tables, flows). Link from `README.md`; do not duplicate full architecture prose there.

---

## Commit messages (Conventional Commits)

### Format

```text
<type>(<optional-scope>): <description>

<optional body — blank line before this block>

<optional footer(s)>
```

### Allowed `<type>` values

Use one of these literals in lowercase:

| type | Use when |
|------|----------|
| `feat` | New user-facing capability or API behavior |
| `fix` | Bug fix or correcting broken behavior |
| `chore` | Maintenance that is not a product fix/feature (deps, config noise, ignore files) |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `style` | Formatting / whitespace only (no behavior change) |
| `test` | Tests only (add/fix coverage) |
| `ci` | CI/CD pipelines, automation around builds |
| `build` | Build system or compiled artifacts configuration |

### Scope

- Optional parenthetical after the type: `feat(sales): ...`, `fix(api): ...`, `chore(docker): ...`.
- Use a short domain: area of the codebase, gem, or subsystem (e.g. `sales`, `api`, `webpack`, `deps`).

### Subject (`<description>`)

- Imperative, present tense: completes *"If applied, this commit will …"*
- Lowercase first letter (types like `API` in scope are fine).
- **No** trailing period.

### Body

- Explains **what** and **why**, not line-by-line **how** (the diff shows how).
- Use bullets for multiple distinct points.
- One blank line between subject and body.

### Footer

- **Breaking change:** start a line with `BREAKING CHANGE:` followed by what breaks and what callers should do.
- **Tickets:** e.g. `Resolves #123`, `Closes PROJ-456`, or a Trello card URL if that is team standard.

### Examples

**Good**

```text
feat(sales): add manual ad report cost entry form

Validate overlapping date ranges server-side before save.

Closes ABC-789
```

```text
chore(cursor): ignore local environment files in cursorignore
```

**Avoid**

```text
Fixed the bug.
```

```text
feat: updates
```

```text
feat(sales): Added manual reports.
```

(last: wrong tense / ends with period)

---

## Pull requests (GitHub)

PRs are opened on **GitHub** against the target branch the team uses (often **`main`** — confirm if unsure).

### Title

- Same spirit as commits: optional Conventional Commits shape, e.g. `feat(sales): manual ad reports for non-integrated channels`.
- Should stand alone: a reviewer understands the theme without opening every file.

### Description (suggested sections)

Use markdown. Suggested structure:

```markdown
## Overview
<Why this change exists; link to product/Trello/Jira context if available.>

## Changes
- <bullet — major behavior or file areas>
- <bullet>

## Testing
1. <step a reviewer can run>
2. <step>

## Related
- <Trello / Jira / doc links>
```

Optional checklist (toggle as appropriate):

```markdown
- [ ] Tests added or updated
- [ ] No unintended secrets or credentials
- [ ] docs/ARCHITECTURE.md updated if architecture changed
- [ ] CLAUDE.md / migrations / locales updated if applicable
```

### Hygiene

- Keep the branch reasonably up to date with the base branch (merge or rebase per team preference) before final review.
- Prefer **small, reviewable PRs**; if the diff is huge, call that out in Overview and justify.

---

## Why this matters

Structured commits improve **history search**, **changelogs**, and **review focus**. Structured PRs reduce round-trips and make **QA steps** explicit.
