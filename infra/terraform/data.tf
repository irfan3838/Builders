# Persistent stores: ECR (images), S3 (private uploads), RDS Postgres, Secrets Manager.

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # hackathon account: allow teardown with images present
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({ rules = [{
    rulePriority = 1, description = "keep the last 10 images"
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
    action       = { type = "expire" }
  }] })
}

resource "aws_s3_bucket" "uploads" {
  bucket_prefix = "${local.name}-uploads-"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Retention: uploaded documents expire after 30 days (synthetic demo data).
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    id     = "expire-uploads"
    status = "Enabled"
    filter {}
    expiration {
      days = 30
    }
  }
}

# ---- RDS Postgres ---------------------------------------------------------------------------------------

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "db" {
  name       = local.name
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "db" {
  identifier                 = local.name
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = "db.t4g.micro"
  allocated_storage          = 20
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = "munshi"
  username                   = "munshi"
  password                   = random_password.db.result
  db_subnet_group_name       = aws_db_subnet_group.db.name
  vpc_security_group_ids     = [aws_security_group.db.id]
  publicly_accessible        = false
  multi_az                   = false
  backup_retention_period    = 1
  deletion_protection        = false
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${local.name}-final"
  auto_minor_version_upgrade = true
  apply_immediately          = true
}

# ---- Secrets (values never in git; the OpenAI key and Gmail password are set out of band) ---------------

resource "random_password" "session" {
  length  = 48
  special = false
}

resource "random_password" "origin_verify" {
  length  = 40
  special = false
}

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${local.name}/database-url"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://munshi:${random_password.db.result}@${aws_db_instance.db.address}:5432/munshi"
}

resource "aws_secretsmanager_secret" "session_secret" {
  name                    = "${local.name}/session-secret"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "session_secret" {
  secret_id     = aws_secretsmanager_secret.session_secret.id
  secret_string = random_password.session.result
}

# Placeholders so the task can start; the real values are put with `aws secretsmanager put-secret-value`
# (see docs/deployment.md). Terraform ignores later changes so it never overwrites them.
resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${local.name}/openai-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = "replace-me"
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "gmail_app_password" {
  name                    = "${local.name}/gmail-app-password"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "gmail_app_password" {
  secret_id     = aws_secretsmanager_secret.gmail_app_password.id
  secret_string = "replace-me"
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "google_client_secret" {
  name                    = "${local.name}/google-client-secret"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "google_client_secret" {
  secret_id     = aws_secretsmanager_secret.google_client_secret.id
  secret_string = "replace-me" # app treats this as "calendar not connected" until aws_put_secrets copies the real value
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "google_refresh_token" {
  name                    = "${local.name}/google-refresh-token"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "google_refresh_token" {
  secret_id     = aws_secretsmanager_secret.google_refresh_token.id
  secret_string = "replace-me" # app treats this as "calendar not connected" until aws_put_secrets copies the real value
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "serpapi_api_key" {
  name                    = "${local.name}/serpapi-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "serpapi_api_key" {
  secret_id     = aws_secretsmanager_secret.serpapi_api_key.id
  secret_string = "replace-me" # app treats this as "flight search not configured" until aws_put_secrets copies the real value
  lifecycle {
    ignore_changes = [secret_string]
  }
}
