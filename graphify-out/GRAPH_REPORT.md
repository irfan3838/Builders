# Graph Report - Builders  (2026-11-20)

## Corpus Check
- Corpus is ~2,326 words - fits in a single context window. You may not need a graph.

## Summary
- 63 nodes · 72 edges · 8 communities
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.82)
- Token cost: 55,853 input · 0 output

## Community Hubs (Navigation)
- AWS Deployment & CI/CD
- CI Hygiene Job Steps
- Secrets & Phase 0 Setup
- CI Workflow Config
- Local MVP & Demo Reliability
- Solution Planning
- CI Triggers
- Mission & Project Docs

## God Nodes (most connected - your core abstractions)
1. `Phase 3: AWS Deployment and CI/CD` - 8 edges
2. `Planned Approach` - 8 edges
3. `hygiene` - 6 edges
4. `steps` - 5 edges
5. `Golden-Path Demo` - 5 edges
6. `on` - 4 edges
7. `Phase 2: Working Local MVP` - 4 edges
8. `OpenAI API` - 4 edges
9. `GitHub Actions CI/CD` - 4 edges
10. `concurrency` - 3 edges

## Surprising Connections (you probably didn't know these)
- `CI Repository Hygiene Checks` --implements--> `GitHub Actions CI/CD`  [INFERRED]
  README.md → CLAUDE.md
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `CI Repository Hygiene Checks` --implements--> `Phase 0: Before the Problem Statement`  [INFERRED]
  README.md → CLAUDE.md
- `README: Builders` --references--> `Phase 0: Before the Problem Statement`  [EXTRACTED]
  README.md → CLAUDE.md
- `Planned Approach` --references--> `OpenAI API`  [EXTRACTED]
  README.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (8 total, 0 thin omitted)

### Community 0 - "AWS Deployment & CI/CD"
Cohesion: 0.20
Nodes (10): AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Status Report Format (LOCAL ONLY / READY / DEPLOYED / BLOCKED), GitHub Actions CI/CD, GitHub OIDC for AWS Auth, Phase 3: AWS Deployment and CI/CD, S3 / CloudFront Static Frontend (+2 more)

### Community 1 - "CI Hygiene Job Steps"
Cohesion: 0.17
Nodes (12): GITLEAKS_VERSION, env, name, runs-on, steps, timeout-minutes, hygiene, name (+4 more)

### Community 2 - "Secrets & Phase 0 Setup"
Cohesion: 0.29
Nodes (7): Agent Guardrails (step limits, budgets, timeouts, retries), OpenAI API, Phase 0: Before the Problem Statement, Secrets via Secrets Manager / SSM, CI Repository Hygiene Checks, .env.example Local Setup, gitleaks Secret Scanning

### Community 3 - "CI Workflow Config"
Cohesion: 0.25
Nodes (7): concurrency, cancel-in-progress, group, jobs, name, permissions, contents

### Community 4 - "Local MVP & Demo Reliability"
Cohesion: 0.38
Nodes (5): Definition of Done, Golden-Path Demo, /health Endpoint and Smoke Tests, Phase 2: Working Local MVP, Phase 4: Demo Quality and Selective Hardening

### Community 5 - "Solution Planning"
Cohesion: 0.40
Nodes (3): Tiny Agent Evaluation Set, Smallest Compelling MVP, Phase 1: Problem Statement to Solution Plan

### Community 6 - "CI Triggers"
Cohesion: 0.40
Nodes (5): on, pull_request, push, workflow_dispatch, branches

### Community 7 - "Mission & Project Docs"
Cohesion: 0.50
Nodes (3): CLAUDE.md Hackathon Agent Rules, Mission: Best Demonstrable Hackathon Solution, README: Builders

## Knowledge Gaps
- **4 isolated node(s):** `Tiny Agent Evaluation Set`, `S3 / CloudFront Static Frontend`, `Definition of Done`, `Status Report Format (LOCAL ONLY / READY / DEPLOYED / BLOCKED)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 25 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Planned Approach` connect `AWS Deployment & CI/CD` to `Secrets & Phase 0 Setup`, `Local MVP & Demo Reliability`, `Mission & Project Docs`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **What connects `Tiny Agent Evaluation Set`, `S3 / CloudFront Static Frontend`, `Definition of Done` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Why does `Replaceable OpenAI Service Boundary` connect `Local MVP & Demo Reliability` to `AWS Deployment & CI/CD`, `Secrets & Phase 0 Setup`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._