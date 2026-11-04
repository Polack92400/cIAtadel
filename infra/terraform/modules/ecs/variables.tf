variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "certificate_arn" {
  description = "ACM certificate for domain_name."
  type        = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "app_security_group_id" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "app_secret_arn" {
  type = string
}

variable "database_url_secret_arn" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "bucket_arn" {
  type = string
}

variable "redis_endpoint" {
  type = string
}

variable "redis_auth_token" {
  type      = string
  sensitive = true
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "llm_provider" {
  description = "ollama (self-hosted GPU endpoint) or bedrock (adapter to add in ai_engine)."
  type        = string
  default     = "ollama"
}

variable "llm_model" {
  type    = string
  default = "llama3.2:3b"
}

variable "llm_base_url" {
  description = "Private inference endpoint (e.g. EC2 GPU running Ollama/vLLM)."
  type        = string
  default     = ""
}

variable "embedding_provider" {
  type    = string
  default = "ollama"
}

variable "embedding_model" {
  type    = string
  default = "nomic-embed-text"
}

variable "backend_count" {
  type    = number
  default = 2
}

variable "worker_count" {
  type    = number
  default = 1
}

variable "frontend_count" {
  type    = number
  default = 2
}
