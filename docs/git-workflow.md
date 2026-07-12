# Git Workflow

This project uses a simple branch and pull request workflow.

## Main Branch

`main` should always stay stable.

Do not push feature work directly to `main`.

## Working on a Task

1. Pull the latest `main`.
2. Create a branch.
3. Make focused changes.
4. Commit with the project commit format.
5. Push the branch.
6. Open a pull request.

## Branch Examples

```txt
feature/transcript-agent
feature/status-page
fix/alignment-timestamps
docs/setup-update
```

## Commit Examples

```txt
feature(transcript): add structured script generation
fix(assets): handle missing license metadata
docs(api): document the video status endpoint
```

See `CONTRIBUTING.md` for the full policy.
