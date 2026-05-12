# WorkforceIQ AWS Free-Tier Demo Deployment

Use this path when the priority is keeping the stack simple and low-cost on AWS. It keeps everything on one EC2 host:

- Nginx on port `80`.
- Flask API container.
- Celery worker container.
- MySQL container with an EBS-backed Docker volume.
- Redis container with an EBS-backed Docker volume.
- Local daily JSON backups on the same EC2 volume.
- ECR repository with lifecycle retention set to one image.

This is a demo/staging shape, not the company-migration production shape. It avoids RDS, ElastiCache, ALB, Secrets Manager, and S3 because those can add cost or consume credits.

The current validated keeper instance is:

- instance id: `i-0064b45ececace888`
- type: `t3.small`
- public health URL: `http://ec2-44-211-148-129.compute-1.amazonaws.com/api/health`

## Cost Rules

- Do not apply `infra/aws/terraform` if you want free-tier mode. That path creates RDS, ElastiCache, ALB, S3, and Secrets Manager resources.
- Use only `infra/aws-free/terraform`.
- `t3.micro` is not enough for this full single-host stack in practice. The first stable shape here was `t3.small`.
- Keep `root_volume_size <= 30`.
- Keep only one ECR image. The Terraform lifecycle policy expires older images.
- Destroy the stack when you are not using it.

AWS can still charge if your account is not free-tier eligible, credits are depleted, usage exceeds limits, public IPv4 billing applies to your account, or you leave resources running after the trial period.

## IAM Prerequisite

Your AWS user or role must be allowed to:

- read EC2 availability zones and AMIs,
- create and delete EC2 networking and instances,
- create and manage the ECR repository,
- create and pass the EC2 IAM role and instance profile,
- send SSM commands after the instance is up.

If `terraform apply` fails with `UnauthorizedOperation`, use one of these:

- attach `AdministratorAccess` temporarily to the IAM user or role you are using, or
- attach the custom policy at `infra/aws-free/iam/terraform-deployer-policy.json`.

If your AWS account is inside an AWS Organization, an SCP can still block these actions even when the IAM user policy allows them. In that case, the organization admin must relax the SCP.

## Manual Setup

Create this ignored file:

```text
infra/aws-free/terraform/free.auto.tfvars
```

Example:

```hcl
aws_region       = "us-east-1"
cors_origins     = "http://localhost:3000"
ec2_instance_type = "t3.small"
root_volume_size = 20
```

If you want SSH, add:

```hcl
ec2_key_name     = "your-existing-keypair-name"
ssh_ingress_cidr = "YOUR_PUBLIC_IP/32"
```

## Create Free-Tier Infrastructure

From PowerShell:

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI

wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 init'

wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 apply'
```

## Push First Image

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI\infra\aws-free\terraform

$region = "us-east-1"
$repo = wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 output -raw ecr_repository_url'
$registry = $repo.Split("/")[0]

aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $registry

cd C:\Users\danny\Desktop\Projects\WorkFlow-AI
docker build -t "${repo}:latest" .
docker push "${repo}:latest"
```

## One-Command Redeploy

The simplest local redeploy path is:

```powershell
.\scripts\deploy_active_aws_free.ps1
```

What it does:

- logs into ECR,
- builds and pushes `latest` with WSL Docker,
- restarts the active EC2 stack through SSM,
- checks the public health endpoint.

Current defaults inside that script:

- region: `us-east-1`
- active instance: `i-0064b45ececace888`
- repository: `187528943333.dkr.ecr.us-east-1.amazonaws.com/workforceiq-free`
- health URL: `http://ec2-44-211-148-129.compute-1.amazonaws.com/api/health`

If the active instance changes later, update the parameter or pass a new one:

```powershell
.\scripts\deploy_active_aws_free.ps1 -InstanceId "i-new-instance-id" -HealthUrl "http://new-host/api/health"
```

## Start Or Restart The App

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI\infra\aws-free\terraform

$region = "us-east-1"
$instance = wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 output -raw app_instance_id'

aws ssm send-command `
  --region $region `
  --instance-ids $instance `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["cd /opt/workforceiq","docker compose -f docker-compose.free.yml --env-file .env.free pull","docker compose -f docker-compose.free.yml --env-file .env.free up -d","docker compose -f docker-compose.free.yml --env-file .env.free ps"]'
```

## Health Check

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI\infra\aws-free\terraform

$health = wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 output -raw health_check_url'
Invoke-RestMethod -Uri $health
```

## Backup

Manual backup:

```powershell
aws ssm send-command `
  --region $region `
  --instance-ids $instance `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["/usr/local/bin/workforceiq-free-backup","ls -lh /opt/workforceiq/backups"]'
```

Daily backup runs at `02:15 UTC` and keeps `backup_retention_days` locally.

## Stop Charges

Destroy the free-tier demo stack when you are done:

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI

wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws-free:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 destroy'
```

## GitHub Actions Secrets

If you want GitHub Actions redeploys, set these repository secrets:

- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `AWS_FREE_ECR_REPOSITORY`
- `AWS_FREE_EC2_INSTANCE_ID`
- `AWS_FREE_HEALTH_URL`

For the current working instance:

- `AWS_REGION = us-east-1`
- `AWS_FREE_ECR_REPOSITORY = workforceiq-free`
- `AWS_FREE_EC2_INSTANCE_ID = i-0064b45ececace888`
- `AWS_FREE_HEALTH_URL = http://ec2-44-211-148-129.compute-1.amazonaws.com/api/health`

## Domain And HTTPS

Domain and HTTPS are the next step, but they require a real domain name that you control. Without that, the current AWS public DNS name can only stay on plain HTTP.

Once you have a domain, the clean path is:

1. point a DNS record to the EC2 public IP,
2. install a TLS certificate on the instance,
3. update Nginx to listen on `443`,
4. force `80 -> 443` redirects.
