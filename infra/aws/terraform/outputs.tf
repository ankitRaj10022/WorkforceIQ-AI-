output "alb_dns_name" {
  description = "Application Load Balancer DNS name."
  value       = aws_lb.app.dns_name
}

output "health_check_url" {
  description = "Public health endpoint through the ALB."
  value       = "${local.public_base_url}/api/health"
}

output "ready_check_url" {
  description = "Public readiness endpoint through the ALB."
  value       = "${local.public_base_url}/api/health/ready"
}

output "ecr_repository_url" {
  description = "ECR repository URL for the WorkforceIQ API image."
  value       = aws_ecr_repository.app.repository_url
}

output "app_instance_id" {
  description = "EC2 instance ID that runs Docker Compose."
  value       = aws_instance.app.id
}

output "app_secret_arn" {
  description = "Secrets Manager ARN containing the app runtime environment."
  value       = aws_secretsmanager_secret.app.arn
}

output "backup_bucket" {
  description = "S3 bucket for app-level JSON backups."
  value       = aws_s3_bucket.backups.bucket
}

output "rds_endpoint" {
  description = "RDS MySQL endpoint."
  value       = aws_db_instance.mysql.address
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "frontend_api_base_url" {
  description = "Base URL the frontend should use for WorkforceIQ API requests."
  value       = local.public_base_url
}

output "cognito_user_pool_id" {
  description = "AWS Cognito user pool ID for frontend authentication."
  value       = var.enable_cognito ? aws_cognito_user_pool.app[0].id : null
}

output "cognito_user_pool_client_id" {
  description = "AWS Cognito app client ID for the frontend."
  value       = var.enable_cognito ? aws_cognito_user_pool_client.frontend[0].id : null
}

output "cognito_user_pool_domain" {
  description = "Hosted UI base URL for the Cognito user pool domain."
  value       = var.enable_cognito ? local.cognito_hosted_ui_base_url : null
}

output "cognito_login_url" {
  description = "Convenience login URL for the Cognito hosted UI."
  value       = var.enable_cognito ? local.cognito_login_url : null
}

output "cognito_logout_url" {
  description = "Convenience logout URL for the Cognito hosted UI."
  value       = var.enable_cognito ? local.cognito_logout_url : null
}

output "frontend_env" {
  description = "Frontend environment values for Cognito and API integration."
  value = var.enable_cognito ? {
    NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL    = local.public_base_url
    NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID = "org-demo"
    NEXT_PUBLIC_COGNITO_REGION              = var.aws_region
    NEXT_PUBLIC_COGNITO_USER_POOL_ID        = aws_cognito_user_pool.app[0].id
    NEXT_PUBLIC_COGNITO_APP_CLIENT_ID       = aws_cognito_user_pool_client.frontend[0].id
    NEXT_PUBLIC_COGNITO_DOMAIN              = local.cognito_hosted_ui_base_url
    NEXT_PUBLIC_COGNITO_CALLBACK_URL        = length(local.cognito_callback_urls) > 0 ? local.cognito_callback_urls[0] : null
    NEXT_PUBLIC_COGNITO_LOGOUT_URL          = length(local.cognito_logout_urls) > 0 ? local.cognito_logout_urls[0] : null
  } : null
}
