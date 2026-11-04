output "kms_key_arn" {
  value = aws_kms_key.data.arn
}

output "db_app_password" {
  value     = random_password.db_app.result
  sensitive = true
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}
