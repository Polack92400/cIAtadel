# KMS key for data at rest (S3, RDS, ElastiCache, logs, secrets) and the
# application secrets. Secret *values* are set out-of-band (never in state
# for production; random_password here is acceptable for a dev environment).

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "data" {
  description             = "${var.name} data at rest"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AccountAdmin"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "CloudWatchLogs"
        Effect    = "Allow"
        Principal = { Service = "logs.${var.region}.amazonaws.com" }
        Action    = ["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"]
        Resource  = "*"
      },
    ]
  })
}

resource "aws_kms_alias" "data" {
  name          = "alias/${var.name}-data"
  target_key_id = aws_kms_key.data.key_id
}

resource "random_password" "django_secret" {
  length  = 64
  special = false
}

resource "random_password" "jwt_signing" {
  length  = 64
  special = false
}

resource "random_password" "db_app" {
  length  = 40
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name       = "${var.name}/app"
  kms_key_id = aws_kms_key.data.arn
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DJANGO_SECRET_KEY = random_password.django_secret.result
    JWT_SIGNING_KEY   = random_password.jwt_signing.result
  })
}
