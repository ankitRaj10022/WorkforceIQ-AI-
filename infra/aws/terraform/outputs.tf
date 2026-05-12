output "alb_dns_name" {
  description = "Application Load Balancer DNS name."
  value       = aws_lb.app.dns_name
}

output "health_check_url" {
  description = "Public health endpoint through the ALB."
  value       = "${local.public_base_url}/api/health"
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
