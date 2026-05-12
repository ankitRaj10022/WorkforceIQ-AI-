output "public_ip" {
  description = "Public IP of the free-tier EC2 host."
  value       = aws_instance.app.public_ip
}

output "public_dns" {
  description = "Public DNS of the free-tier EC2 host."
  value       = aws_instance.app.public_dns
}

output "health_check_url" {
  description = "Public health endpoint through Nginx on EC2."
  value       = "http://${aws_instance.app.public_dns}/api/health"
}

output "ecr_repository_url" {
  description = "ECR repository URL for the WorkforceIQ image."
  value       = aws_ecr_repository.app.repository_url
}

output "app_instance_id" {
  description = "EC2 instance ID that runs the free-tier Docker Compose stack."
  value       = aws_instance.app.id
}
