# Contributing / Branching Workflow

## Branch structure

| Branch | Purpose |
|---|---|
| `main` | Stable, protected — no direct pushes |
| `feature/<name>` | New features (e.g. `feature/batch-export`) |
| `fix/<name>` | Bug fixes (e.g. `fix/thumbnail-crash`) |

## Starting new work

```bash
# Always branch off the latest main
git checkout main
git pull
git checkout -b feature/your-feature-name
```

## Finishing up

```bash
# Commit your work
git add -A
git commit -m "Short description of change"

# Push the branch
git push -u origin feature/your-feature-name

# Open a PR → main
gh pr create --base main --title "Your title" --body "What and why"
```

## Rules

- **Never push directly to `main`** — it is branch-protected
- One feature / fix per branch
- PR title should be clear enough to understand from the commit list alone
- Screenshots required for any UI change
