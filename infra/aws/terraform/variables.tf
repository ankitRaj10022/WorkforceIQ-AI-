variable "aws_region" {
  description = "AWS region for the WorkforceIQ stack."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "workforceiq"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "app_domain" {
  description = "Public API domain, for example api.example.com. Leave empty to use the ALB DNS name."
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "Comma-separated list of approved frontend origins."
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS on the ALB. Leave empty for HTTP-only staging."
  type        = string
  default     = ""
}

variable "allowed_http_cidrs" {
  description = "CIDR ranges allowed to reach the public load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_ingress_cidr" {
  description = "Optional single CIDR allowed to SSH into EC2. Leave empty to disable SSH."
  type        = string
  default     = ""
}

variable "ec2_key_name" {
  description = "Optional EC2 key pair name. Leave empty when managing the instance through SSM."
  type        = string
  default     = ""
}

variable "ec2_instance_type" {
  description = "EC2 instance type for API, Celery, and Nginx containers."
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS MySQL instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Initial RDS storage in GB."
  type        = number
  default     = 20
}

variable "mysql_engine_version" {
  description = "RDS MySQL engine version."
  type        = string
  default     = "8.0"
}

variable "rds_backup_retention_days" {
  description = "RDS automated backup retention period in days."
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Whether to enable Multi-AZ for RDS. Enable for production HA when cost allows."
  type        = bool
  default     = false
}

variable "rds_performance_insights_enabled" {
  description = "Whether to enable RDS Performance Insights. Keep false for lowest-cost staging."
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection on stateful or public resources."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final RDS snapshot when destroying the DB instance."
  type        = bool
  default     = false
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_engine_version" {
  description = "ElastiCache Redis engine version."
  type        = string
  default     = "7.1"
}

variable "image_tag" {
  description = "Default application image tag referenced by the EC2 bootstrap secret."
  type        = string
  default     = "latest"
}

variable "backup_retention_days" {
  description = "Lifecycle retention in days for app-level JSON backups stored in S3."
  type        = number
  default     = 30
}

variable "alarm_sns_topic_arn" {
  description = "Optional SNS topic ARN for ALB unhealthy-host alarms."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags applied to AWS resources."
  type        = map(string)
  default     = {}
}
