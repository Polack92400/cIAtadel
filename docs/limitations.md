# Known limitations and production-hardening plan

cIAtadel is a proof of concept. It is functional and security-conscious, but
it is **not** production-ready and makes no compliance claim (GDPR, SOC 2,
ISO 27001, professional secrecy rules...). This page lists what is knowingly
missing.

## Security

| Area | POC state | Production recommendation |
|---|---|---|
| Identity | Local email/password, no MFA, no password reset | OIDC (Keycloak / Cognito / Entra ID) with MFA; `User.external_subject` is ready for it |
| Invitations | Admin sets an initial password | Email invitation with single-use link, forced password change |
| Sessions | 15 min access / 1 day refresh, rotation + blacklist | Session listing & revocation, idle timeout, device binding |
| Malware | Magic-byte check + pypdf in a time-limited worker | Antivirus / CDR (e.g. ClamAV, Glasswall) before indexing; sandboxed parser container without network |
| OCR | Scanned PDFs fail with `no_text` | OCR pipeline (Tesseract / Textract) in an isolated worker |
| Encryption at rest | MinIO SSE with one static key; Postgres volume not encrypted | KMS (one key per tenant for premium), encrypted RDS, encrypted EBS |
| Encryption in transit | Plain HTTP inside the Docker network, localhost-only frontend | TLS everywhere (ALB, RDS `force_ssl`, Redis TLS), HSTS |
| Secrets | `.env` file with random values | AWS Secrets Manager, IAM task roles instead of static S3 keys |
| MinIO credentials | Django uses the MinIO root user | Dedicated MinIO/S3 user restricted to `tenants/*` |
| Ollama | Unauthenticated, internal network only | Private inference endpoint with auth (or Bedrock via IAM) |
| CSP | `script-src 'unsafe-inline'` (Next.js bootstrap) | Nonce-based CSP |
| Audit | Append-only via DB trigger, per firm | Ship to an external immutable store (CloudTrail Lake / S3 Object Lock), hash-chaining, alerting |
| Denied cross-tenant attempts | Logged to application logs, not to the audit table (the request transaction is rolled back) | Write security denials through a separate connection; alert on bursts |
| Rate limiting | DRF throttles (per account, per IP, per user for questions) | WAF rate rules + bot protection |
| Prompt injection | Delimited untrusted sources, no tools, authorization before retrieval, citations | Output filtering, injection classifiers, red-team test corpus |

## Functional

- Answers are not streamed: the UI shows a progress state until the full
  answer arrives (15–60 s on CPU). Streaming (SSE) is the next UX step.
- Conversations are private to their author; no sharing between colleagues.
- No document versioning, retention policies or legal hold.
- Only PDF; no Word/email ingestion.
- Search on the documents page is by title/file name (semantic search is
  in the assistant).
- The embedding dimension is part of the schema; changing the embedding
  model requires a migration and re-indexing.
- `insufficient_context` is detected by matching the model's fixed refusal
  sentence; small models occasionally paraphrase it.

## Scalability

- One Celery queue; long LLM calls hold a gunicorn thread and a database
  transaction for the duration of the answer.
- Filtered HNSW search relies on pgvector iterative scans
  (`hnsw.iterative_scan`); very large tenants may need partitioning per
  tenant or a per-tenant index.
- No horizontal scaling tests or load tests were performed.

## Operations

- No backups for the local volumes; no monitoring/alerting stack locally.
- The Terraform code is validated (`terraform validate`) but has **never been
  applied**; it is a starting point, not a deployable environment.
- MinIO's upstream images are no longer published on Docker Hub; the stack
  uses `bitnamilegacy/minio` (overridable with `MINIO_IMAGE`).
