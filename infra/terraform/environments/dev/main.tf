# Development environment on AWS. NOT applied during the POC.
# Local -> AWS mapping: MinIO->S3, Postgres->RDS, Redis->ElastiCache,
# compose services->ECS Fargate, .env->Secrets Manager, Ollama->GPU endpoint
# or Bedrock, logs->CloudWatch, everything encrypted with one KMS key.

locals {
  name = "ciatadel-${var.environment}"
}

module "security" {
  source = "../../modules/security"
  name   = local.name
  region = var.region
}

module "network" {
  source      = "../../modules/network"
  name        = local.name
  region      = var.region
  kms_key_arn = module.security.kms_key_arn
}

module "storage" {
  source      = "../../modules/storage"
  bucket_name = "${local.name}-documents-${var.bucket_suffix}"
  kms_key_arn = module.security.kms_key_arn
}

module "database" {
  source                     = "../../modules/database"
  name                       = local.name
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.private_subnet_ids
  allowed_security_group_ids = [module.network.app_security_group_id]
  kms_key_arn                = module.security.kms_key_arn
}

module "cache" {
  source                     = "../../modules/cache"
  name                       = local.name
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.private_subnet_ids
  allowed_security_group_ids = [module.network.app_security_group_id]
  kms_key_arn                = module.security.kms_key_arn
}

# Runtime connection string for the least-privileged application role
# (created by the migration job, see docker/postgres/10-app-role.sh).
resource "aws_secretsmanager_secret" "database_url" {
  name       = "${local.name}/database-url"
  kms_key_id = module.security.kms_key_arn
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgres://ciatadel_app:${module.security.db_app_password}@${module.database.endpoint}:5432/ciatadel?sslmode=require"
}

module "ecs" {
  source                  = "../../modules/ecs"
  name                    = local.name
  region                  = var.region
  domain_name             = var.domain_name
  certificate_arn         = var.certificate_arn
  vpc_id                  = module.network.vpc_id
  public_subnet_ids       = module.network.public_subnet_ids
  private_subnet_ids      = module.network.private_subnet_ids
  alb_security_group_id   = module.network.alb_security_group_id
  app_security_group_id   = module.network.app_security_group_id
  kms_key_arn             = module.security.kms_key_arn
  app_secret_arn          = module.security.app_secret_arn
  database_url_secret_arn = aws_secretsmanager_secret.database_url.arn
  bucket_name             = module.storage.bucket_name
  bucket_arn              = module.storage.bucket_arn
  redis_endpoint          = module.cache.primary_endpoint
  redis_auth_token        = module.cache.auth_token
  backend_image           = var.backend_image
  frontend_image          = var.frontend_image
  llm_base_url            = var.llm_base_url
}
