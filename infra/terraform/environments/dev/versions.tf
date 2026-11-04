terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state (create the bucket/table once, outside this configuration):
  # backend "s3" {
  #   bucket         = "ciatadel-terraform-state"
  #   key            = "dev/terraform.tfstate"
  #   region         = "eu-west-3"
  #   dynamodb_table = "ciatadel-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "ciatadel"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
