variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "cidr_block" {
  type    = string
  default = "10.40.0.0/16"
}

variable "az_count" {
  type    = number
  default = 2
}

variable "kms_key_arn" {
  type = string
}
