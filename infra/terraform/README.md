# Terraform (AWS target), not applied in the POC

Validated with `terraform validate` (Terraform 1.9, AWS provider 5.x) but
**never applied**. It encodes the target architecture so the move to AWS
changes configuration, not application code.

```
modules/
  security/   KMS key (rotation), Secrets Manager (Django + JWT keys)
  network/    VPC, public/private subnets, NAT, S3 gateway endpoint,
              flow logs, ALB and application security groups
  storage/    document bucket: SSE-KMS, versioning, no public access, TLS only
  database/   RDS PostgreSQL 16 (pgvector), KMS, force_ssl, private
  cache/      ElastiCache Redis, TLS + AUTH, KMS
  ecs/        Fargate cluster, ALB (TLS 1.3 policy), frontend/backend/worker
              services, Cloud Map, least-privilege task role, CloudWatch logs
environments/
  dev/        wires the modules together
```

| Local (compose) | AWS |
|---|---|
| MinIO | S3 + SSE-KMS (`S3_ENDPOINT_URL` empty, IAM task role) |
| PostgreSQL + pgvector | RDS PostgreSQL 16 + pgvector |
| Redis | ElastiCache (TLS) |
| frontend / backend / worker containers | ECS Fargate services (same images) |
| `.env` | Secrets Manager |
| Ollama | GPU instance running Ollama/vLLM (`llm_base_url`) or Bedrock (provider adapter to add in `ai_engine`) |
| stdout logs | CloudWatch Logs (KMS-encrypted) |
| Django auth | Cognito / OIDC (planned) |

Not covered yet: WAF/CloudFront, Route 53, ECR repositories, CI/CD deploy
pipeline with plan/approval (see `mermaid-diagram.png`), a migration task,
GuardDuty/CloudTrail, the dedicated-account "premium" tenant option.

```bash
cd infra/terraform/environments/dev
```

```bash
terraform init -backend=false && terraform validate
```
