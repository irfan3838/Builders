#!/usr/bin/env bash
# Run a one-off command in the deployed task image (same secrets, network and DB as the service).
#   scripts/aws_run_task.sh migrate        -> alembic upgrade head
#   scripts/aws_run_task.sh seed-reset     -> alembic upgrade head && reseed SYNTHETIC demo data (TRUNCATES all tables)
#   scripts/aws_run_task.sh seed-demo      -> same, plus the larger synthetic demo dataset (seed/demo_data.py) + role logins
#   scripts/aws_run_task.sh seed-roles     -> add the irfmed38 / ceo / employee logins to the existing data (non-destructive)
# Waits for the task to stop and prints its exit code and the last log lines.
set -euo pipefail
cd "$(dirname "$0")/.."
TF="terraform -chdir=infra/terraform"
REGION=us-west-2
CLUSTER=$($TF output -raw cluster)
FAMILY=$($TF output -raw task_definition_family)
SUBNETS=$($TF output -json run_task_network | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["subnets"]))')
SG=$($TF output -json run_task_network | python3 -c 'import json,sys; print(json.load(sys.stdin)["security_groups"][0])')
LOG_GROUP=$($TF output -raw log_group)

case "${1:-}" in
  migrate)    CMD='alembic upgrade head' ;;
  seed-reset) CMD='alembic upgrade head && python -m seed.seed_v1 --reset' ;;
  seed-demo)  CMD='alembic upgrade head && python -m seed.seed_v1 --reset --demo && python -m seed.role_users' ;;
  seed-roles) CMD='alembic upgrade head && python -m seed.role_users' ;;
  *) echo "usage: $0 migrate|seed-reset|seed-demo|seed-roles" >&2; exit 2 ;;
esac

# Optional: SEED_ADMIN_NAME="Irfan" scripts/aws_run_task.sh seed-reset  (non-secret; passed as a task env override)
OVERRIDES=$(python3 -c 'import json,os,sys
env=[{"name":"SEED_ADMIN_NAME","value":os.environ["SEED_ADMIN_NAME"]}] if os.environ.get("SEED_ADMIN_NAME") else []
print(json.dumps({"containerOverrides":[{"name":"app","command":["sh","-c",sys.argv[1]],"environment":env}]}))' "$CMD")
TASK=$(aws ecs run-task --region "$REGION" --cluster "$CLUSTER" --task-definition "$FAMILY" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=ENABLED}" \
  --overrides "$OVERRIDES" --query 'tasks[0].taskArn' --output text)
echo "task: $TASK ($1)"
aws ecs wait tasks-stopped --region "$REGION" --cluster "$CLUSTER" --tasks "$TASK"
CODE=$(aws ecs describe-tasks --region "$REGION" --cluster "$CLUSTER" --tasks "$TASK" --query 'tasks[0].containers[0].exitCode' --output text)
REASON=$(aws ecs describe-tasks --region "$REGION" --cluster "$CLUSTER" --tasks "$TASK" --query 'tasks[0].stoppedReason' --output text)
echo "exit code: $CODE  ($REASON)"
aws logs get-log-events --region "$REGION" --log-group-name "$LOG_GROUP" --log-stream-name "app/app/${TASK##*/}" \
  --limit 15 --query 'events[].message' --output text 2>/dev/null | tr '\t' '\n' | tail -15 || true
[ "$CODE" = "0" ]
