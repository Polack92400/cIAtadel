# ECS Fargate: three services from two images.
#   frontend (Next.js)  <- ALB (HTTPS)
#   backend  (Django)   <- frontend only, via Cloud Map private DNS
#   worker   (Celery)   <- no inbound traffic
# Same containers as docker compose; only configuration changes.

locals {
  backend_dns = "backend.${var.name}.internal"
  common_env = [
    { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.prod" },
    { name = "DJANGO_ALLOWED_HOSTS", value = "${var.domain_name},${local.backend_dns}" },
    { name = "DJANGO_CSRF_TRUSTED_ORIGINS", value = "https://${var.domain_name}" },
    { name = "AUTH_COOKIE_SECURE", value = "true" },
    { name = "DJANGO_SECURE_SSL_REDIRECT", value = "false" }, # TLS ends at the ALB
    { name = "S3_ENDPOINT_URL", value = "" },                 # real S3, IAM task role
    { name = "S3_BUCKET", value = var.bucket_name },
    { name = "S3_REGION", value = var.region },
    { name = "S3_SSE", value = "aws:kms" },
    { name = "REDIS_URL", value = "rediss://:${var.redis_auth_token}@${var.redis_endpoint}:6379/0" },
    { name = "CACHE_URL", value = "rediss://:${var.redis_auth_token}@${var.redis_endpoint}:6379/1" },
    { name = "LLM_PROVIDER", value = var.llm_provider },
    { name = "LLM_MODEL", value = var.llm_model },
    { name = "LLM_BASE_URL", value = var.llm_base_url },
    { name = "EMBEDDING_PROVIDER", value = var.embedding_provider },
    { name = "EMBEDDING_MODEL", value = var.embedding_model },
    { name = "EMBEDDING_BASE_URL", value = var.llm_base_url },
  ]
  common_secrets = [
    { name = "DJANGO_SECRET_KEY", valueFrom = "${var.app_secret_arn}:DJANGO_SECRET_KEY::" },
    { name = "JWT_SIGNING_KEY", valueFrom = "${var.app_secret_arn}:JWT_SIGNING_KEY::" },
    { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
  ]
}

resource "aws_ecs_cluster" "this" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "app" {
  for_each          = toset(["frontend", "backend", "worker"])
  name              = "/${var.name}/${each.key}"
  retention_in_days = 90
  kms_key_id        = var.kms_key_arn
}

# --- IAM ----------------------------------------------------------------------
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [var.app_secret_arn, var.database_url_secret_arn]
      },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = [var.kms_key_arn] },
    ]
  })
}

# Runtime permissions of the Django/Celery containers: least privilege.
resource "aws_iam_role" "task" {
  name               = "${var.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "task" {
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid      = "DocumentObjects"
          Effect   = "Allow"
          Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
          Resource = ["${var.bucket_arn}/tenants/*"]
        },
        { Sid = "Bucket", Effect = "Allow", Action = ["s3:ListBucket"], Resource = [var.bucket_arn] },
        {
          Sid      = "DataKey"
          Effect   = "Allow"
          Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
          Resource = [var.kms_key_arn]
        },
      ],
      var.llm_provider == "bedrock" ? [{
        Sid      = "Bedrock"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = ["*"]
      }] : []
    )
  })
}

# --- Service discovery (frontend -> backend) -------------------------------------
resource "aws_service_discovery_private_dns_namespace" "this" {
  name = "${var.name}.internal"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "backend" {
  name = "backend"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      type = "A"
      ttl  = 10
    }
  }
}

# --- Load balancer --------------------------------------------------------------
resource "aws_lb" "this" {
  name                       = var.name
  load_balancer_type         = "application"
  internal                   = false
  subnets                    = var.public_subnet_ids
  security_groups            = [var.alb_security_group_id]
  drop_invalid_header_fields = true
  enable_deletion_protection = true
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.name}-frontend"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path    = "/login"
    matcher = "200"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# --- Task definitions & services -------------------------------------------------
locals {
  backend_container = {
    image                  = var.backend_image
    essential              = true
    environment            = local.common_env
    secrets                = local.common_secrets
    readonlyRootFilesystem = true
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp" }]
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  volume {
    name = "tmp"
  }
  container_definitions = jsonencode([merge(local.backend_container, {
    name         = "backend"
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app["backend"].name
        awslogs-region        = var.region
        awslogs-stream-prefix = "backend"
      }
    }
  })])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  volume {
    name = "tmp"
  }
  container_definitions = jsonencode([merge(local.backend_container, {
    name    = "worker"
    command = ["docker/start-worker.sh"]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app["worker"].name
        awslogs-region        = var.region
        awslogs-stream-prefix = "worker"
      }
    }
  })])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  container_definitions = jsonencode([{
    name         = "frontend"
    image        = var.frontend_image
    essential    = true
    portMappings = [{ containerPort = 3000, protocol = "tcp" }]
    # The image must be built with BACKEND_INTERNAL_URL=http://backend.<name>.internal:8000
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app["frontend"].name
        awslogs-region        = var.region
        awslogs-stream-prefix = "frontend"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "backend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.app_security_group_id]
  }
  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }
}

resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.app_security_group_id]
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.app_security_group_id]
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }
  depends_on = [aws_lb_listener.https]
}
