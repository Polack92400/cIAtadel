variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "domain_name" {
  type = string
}

variable "certificate_arn" {
  type = string
}

variable "bucket_suffix" {
  description = "Makes the S3 bucket name globally unique."
  type        = string
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "llm_base_url" {
  description = "Private inference endpoint (GPU instance running Ollama/vLLM)."
  type        = string
}
