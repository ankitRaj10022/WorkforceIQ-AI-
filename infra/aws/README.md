# AWS Infrastructure Layout

This directory holds the AWS deployment assets for WorkforceIQ.

## Paths

- `terraform/`: managed AWS deployment with ALB, EC2, RDS MySQL, ElastiCache Redis, S3 backups, Secrets Manager, and optional Cognito.
- `app/`: Docker Compose and Nginx files rendered onto the EC2 host by Terraform user data.

## Terraform File Map

- `data.tf`: AWS data sources used by the stack.
- `random.tf`: generated secrets and suffix values.
- `locals.tf`: derived environment values, Cognito URLs, and runtime env map written into Secrets Manager.
- `network.tf`: VPC, public app subnets, and private data subnets.
- `security.tf`: security groups for ALB, app, RDS, and Redis.
- `ecr.tf`: container registry for the WorkforceIQ image.
- `data_services.tf`: RDS MySQL and ElastiCache Redis resources.
- `storage_secrets.tf`: S3 backups and Secrets Manager runtime secret.
- `identity_cognito.tf`: Cognito user pool, frontend client, hosted UI domain, and RBAC groups.
- `compute_balancer.tf`: IAM runtime role, EC2 app host, ALB, target group, and listeners.
- `alarms.tf`: CloudWatch alarms.
- `variables.tf`, `outputs.tf`, `versions.tf`: public interface for the stack.

## Recommended Use

Use this directory for the real cloud deployment path. The `infra/aws-free` path is still available for low-cost demos, but this managed stack is the correct base for frontend, Cognito, and managed MySQL/Redis integration.
