# Munshi on AWS (us-west-2): CloudFront (HTTPS on *.cloudfront.net) -> ALB (CloudFront-only) -> ECS Fargate (1 task)
# -> RDS Postgres (private to the app) + S3 (private uploads) + Secrets Manager. Default VPC, no NAT gateway.
# CPU only: no GPUs, no Bedrock (organiser rule). AI calls go to the OpenAI API.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  # Local state (single operator, hackathon). State is gitignored; it holds generated secrets, keep it private.
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "munshi", Environment = var.env, ManagedBy = "terraform" }
  }
}

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "env" {
  type    = string
  default = "demo"
}

variable "name" {
  type    = string
  default = "munshi"
}

variable "image_tag" {
  description = "Image tag in ECR to run (the git commit)."
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  type    = number
  default = 1024 # 1 vCPU (the user chose the faster size)
}

variable "task_memory" {
  type    = number
  default = 2048
}

variable "app_env" {
  description = "Non-secret app settings passed as environment variables (model names, email allow-list, FX provider)."
  type        = map(string)
  default     = {}
}

data "aws_caller_identity" "me" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_route_tables" "default" {
  vpc_id = data.aws_vpc.default.id
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

locals {
  name = var.name
}

# ---- security groups ----------------------------------------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "ALB - HTTP from CloudFront origin-facing IPs only"
  vpc_id      = data.aws_vpc.default.id
  ingress {
    description     = "CloudFront to ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "Fargate task - port 8000 from the ALB only; outbound to OpenAI, ECB, SMTP, AWS APIs"
  vpc_id      = data.aws_vpc.default.id
  ingress {
    description     = "ALB to app"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "RDS Postgres - 5432 from the app task only"
  vpc_id      = data.aws_vpc.default.id
  ingress {
    description     = "App to Postgres"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}

# Free S3 gateway endpoint: uploads stay on the AWS network.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.default.ids
}
