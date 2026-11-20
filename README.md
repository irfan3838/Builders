# Builders

Hackathon project: an AI-assisted solution to a problem statement that hasn't been announced yet, deployed on AWS.

**Status:** Phase 0, setup only. There's no application code or infrastructure yet; the stack will be chosen once the problem statement arrives.

## Planned approach

- **AI:** OpenAI API, behind a small replaceable service boundary. An agent is used only where multi-step autonomy actually helps.
- **Hosting:** AWS. The runtime (App Runner, Lambda + API Gateway, or ECS Fargate) will be picked to fit the solution.
- **Infra as code:** Terraform, added once the hosting architecture is decided.
- **CI/CD:** GitHub Actions, using GitHub OIDC for AWS auth (no long-lived keys).

See [`CLAUDE.md`](CLAUDE.md) for the full working rules and phase plan.

## Local setup

```bash
cp .env.example .env   # then fill in real values locally; never commit .env
```

Run, test, and deploy commands will be added here once the stack is chosen.

## CI

`.github/workflows/ci.yml` runs repository hygiene checks on every push and pull request:

- no committed `.env` files, Terraform state, or private keys
- no unresolved merge-conflict markers
- no files over 5 MB
- secret scanning with gitleaks

Language-specific lint, test, and build steps will be added with the stack.

## Repository layout

```text
.
├── CLAUDE.md          # Working rules for AI-assisted development
├── README.md
├── .env.example       # Placeholder config, no real secrets
├── .gitignore
└── .github/workflows/ci.yml
```
