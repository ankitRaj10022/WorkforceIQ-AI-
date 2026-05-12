variable "aws_region" {
  description = "AWS region for the free-tier demo stack."
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
  default     = "free"
}

variable "cors_origins" {
  description = "Comma-separated list of approved frontend origins."
  type        = string
  default     = "http://localhost:3000"
}

variable "allowed_http_cidrs" {
  description = "CIDR ranges allowed to reach Nginx on EC2."
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
  description = "Free-tier eligible instance type. Confirm eligibility in your AWS account before apply."
  type        = string
  default     = "t3.micro"
}

variable "root_volume_size" {
  description = "EC2 root EBS volume size in GB. Keep <= 30 GB for classic EC2 free-tier limits."
  type        = number
  default     = 20
}

variable "image_tag" {
  description = "Application image tag referenced by the EC2 bootstrap environment."
  type        = string
  default     = "latest"
}

variable "backup_retention_days" {
  description = "Days of local JSON backups retained on the EC2 EBS volume."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags applied to AWS resources."
  type        = map(string)
  default     = {}
}
