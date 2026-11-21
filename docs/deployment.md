# Deployment (AWS, us-west-2)

Account: AWS Workshop Studio event account (role `WSParticipantRole`). Region `us-west-2`.
Organiser rule: no GPUs, no Amazon Bedrock. AI calls go to the OpenAI API; compute is CPU-only Fargate.

## Architecture

```
browser ──HTTPS──> CloudFront (*.cloudfront.net, default cert)
                     │ adds secret X-Origin-Verify header; /assets/* cached, everything else not cached
                     ▼
                   ALB :80 (security group: CloudFront origin-facing prefix list only; 403 without the header)
                     ▼
                   ECS Fargate service "munshi" — 1 task, 1 vCPU / 2 GB, one uvicorn process
                     │ public IP for outbound (OpenAI, ECB/Frankfurter, Gmail SMTP, ECR); no NAT gateway
                     ├──> RDS Postgres 16 db.t4g.micro (not public; 5432 from the app security group only)
                     ├──> S3 private uploads bucket (SSE, 30-day expiry, gateway endpoint)
                     ├──> Google Calendar API (OAuth refresh token): events with a Meet link; Google emails the invites
                     └──> Secrets Manager: munshi/database-url, session-secret, openai-api-key, gmail-app-password,
                          google-client-secret, google-refresh-token
```

Why one task: live-update subscribers (`app/events.py`) are in process memory.

## First deploy

```bash
# 0. tools: terraform >= 1.6, docker, aws cli logged in to the account
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars   # non-secret settings (gitignored)
terraform -chdir=infra/terraform init

# 1. registry first, then the image (tag = git commit)
terraform -chdir=infra/terraform apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app
REPO=$(terraform -chdir=infra/terraform output -raw ecr_repository_url); TAG=$(git rev-parse --short HEAD)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build -t "$REPO:$TAG" . && docker push "$REPO:$TAG"

# 2. everything else
terraform -chdir=infra/terraform apply -var image_tag=$TAG

# 3. secrets that Terraform does not know (read from .env, never printed)
uv run python -m scripts.aws_put_secrets

# 4. schema + synthetic demo data, then restart the service so it picks up the secrets
scripts/aws_run_task.sh seed-reset   # or seed-demo: same plus the larger synthetic demo dataset (seed/demo_data.py)
aws ecs update-service --region us-west-2 --cluster munshi --service munshi --force-new-deployment

# 5. smoke
curl -s "$(terraform -chdir=infra/terraform output -raw url)/health"     # {"ok":true}
```

## Redeploy (new code)

```bash
TAG=$(git rev-parse --short HEAD); docker build -t "$REPO:$TAG" . && docker push "$REPO:$TAG"
scripts/aws_run_task.sh migrate                     # only when a migration was added (run with the NEW image: apply first)
terraform -chdir=infra/terraform apply -var image_tag=$TAG
```

## Email and Google Meet

- `EMAIL_ALLOWED_RECIPIENTS` (tfvars `app_env`): a comma list of addresses, or `*` to email any address on file.
- `OPENAI_VOICE_NAME` / `OPENAI_VOICE_SPEED` (tfvars `app_env`): live voice and speaking pace (0.25-1.5, default 1.15). If the live API rejects `speed`, the session is retried without it and a warning is logged.
- Google Calendar: one-time `uv run python -m scripts.google_oauth` (needs `.secrets/google_client.json`, a Desktop
  OAuth client with the `calendar.events` scope) writes `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` to `.env`.
  `GOOGLE_CLIENT_ID` goes in tfvars `app_env`; `scripts.aws_put_secrets` copies the secret and refresh token.
  Placeholder values (`replace-me`) mean "calendar not connected": meetings are recorded without a Meet link.
- Keep the OAuth app **published** (not Testing), or the refresh token expires after 7 days.

## Rollback

`terraform -chdir=infra/terraform apply -var image_tag=<previous tag>` (ECR keeps the last 10 images).
The ECS deployment circuit breaker also rolls back automatically when a new task never becomes healthy.
Migrations are forward-only; a rollback across a migration needs `alembic downgrade` run as a one-off task.

## Teardown

`terraform -chdir=infra/terraform destroy` — RDS takes a final snapshot (`munshi-final`); ECR and S3 are force-deleted.

## Notes

- Terraform state is local (`infra/terraform/terraform.tfstate`, gitignored). It contains generated secrets: keep it private.
- Secrets Manager uses the AWS-managed key and no rotation (72-hour demo). The OpenAI key and Gmail app password
  are copied by `scripts/aws_put_secrets.py`; their placeholders are ignored by Terraform afterwards.
- Logs: CloudWatch `/ecs/munshi`, 7 days.
- Cost (on-demand, us-west-2): about $0.12/hour, roughly $8–9 for 72 hours. OpenAI usage is separate.
