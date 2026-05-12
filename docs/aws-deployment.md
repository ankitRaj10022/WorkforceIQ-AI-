# WorkforceIQ AWS Deployment

This managed AWS path is production-oriented, not free-tier safe. If you want the lowest-cost/free-tier demo stack, use `docs/aws-free-tier-deployment.md` and `infra/aws-free/terraform` instead.

This path runs the production app on AWS with:

- API, Celery, and Nginx on one EC2 host using Docker Compose.
- MySQL on Amazon RDS with encrypted storage, automated backups, and TLS-required connections.
- Redis on Amazon ElastiCache with in-transit encryption and AUTH.
- App-level JSON backups copied to S3 by cron.
- Application Load Balancer health checks against `/api/health`.
- Secrets in AWS Secrets Manager, deployment through ECR and SSM.

This is the lowest-cost AWS shape that still separates stateful services from the app host. For larger companies, the next step is ECS/Fargate or EKS, private app subnets, NAT or VPC endpoints, WAF, centralized log retention, and Multi-AZ RDS enabled.

## Prerequisites

- AWS CLI authenticated to the target account.
- Terraform `>= 1.6`.
- Docker for building the application image.
- Optional ACM certificate in the same region as the ALB for HTTPS.
- Optional SNS topic ARN if you want unhealthy-host alarms.

## Create Infrastructure

From the repo root:

```powershell
cd infra/aws/terraform
terraform init
terraform plan -out tfplan `
  -var "aws_region=us-east-1" `
  -var "cors_origins=https://your-frontend.example.com" `
  -var "app_domain=api.your-domain.example" `
  -var "acm_certificate_arn=arn:aws:acm:us-east-1:123456789012:certificate/..." `
  -var "ssh_ingress_cidr="
terraform apply tfplan
```

For a temporary HTTP-only staging stack, omit `app_domain` and `acm_certificate_arn`. Do not use HTTP-only for real HR data.

## Push First Image

Terraform creates ECR before the app is deployed. Push the first image manually:

```powershell
$region = "us-east-1"
$repo = terraform output -raw ecr_repository_url
$registry = $repo.Split("/")[0]
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $registry
docker build -t "${repo}:latest" ..\..\..
docker push "${repo}:latest"
```

Then restart the EC2 Docker Compose stack through SSM:

```powershell
$instance = terraform output -raw app_instance_id
aws ssm send-command `
  --region $region `
  --instance-ids $instance `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["cd /opt/workforceiq","docker compose -f docker-compose.aws.yml --env-file .env.aws pull","docker compose -f docker-compose.aws.yml --env-file .env.aws up -d","docker compose -f docker-compose.aws.yml --env-file .env.aws ps"]'
```

## Health Check

```powershell
$health = terraform output -raw health_check_url
Invoke-RestMethod -Uri $health
```

The ALB target group also checks `/api/health` on the EC2 host through Nginx port `8080`.

## GitHub Actions Deploy

Use `.github/workflows/aws-deploy.yml` after creating these GitHub secrets:

- `AWS_ROLE_TO_ASSUME`: IAM role ARN trusted by GitHub OIDC.
- `AWS_REGION`: same AWS region as Terraform.
- `AWS_ECR_REPOSITORY`: ECR repository name, for example `workforceiq-prod`.
- `AWS_EC2_INSTANCE_ID`: output from `terraform output -raw app_instance_id`.

Run the workflow manually and type `DEPLOY`.

## Backups

There are two backup layers:

- RDS automated backups retain point-in-time recovery for `rds_backup_retention_days`.
- The EC2 cron job runs `/usr/local/bin/workforceiq-backup` daily and uploads redacted JSON exports to `s3://<backup_bucket>/json/`.

Run an immediate app-level backup:

```powershell
$instance = terraform output -raw app_instance_id
aws ssm send-command `
  --region $region `
  --instance-ids $instance `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["/usr/local/bin/workforceiq-backup"]'
```

## Production Cutover Checklist

- Use HTTPS with ACM and Route 53 DNS before importing real company data.
- Set `rds_multi_az=true` for production HR workloads when budget allows.
- Keep `deletion_protection=true` and `skip_final_snapshot=false`.
- Configure `alarm_sns_topic_arn` for unhealthy ALB target notifications.
- Confirm GitHub OIDC deploy role has least-privilege access to ECR and SSM.
- Run a restore drill from RDS point-in-time recovery and from the S3 JSON backup before customer migration.
- Move EC2 into private subnets with NAT gateways or VPC endpoints for stricter enterprise isolation.
