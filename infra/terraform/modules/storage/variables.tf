variable "bucket_name" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "noncurrent_retention_days" {
  type    = number
  default = 30
}
